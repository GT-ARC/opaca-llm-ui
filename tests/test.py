import argparse
import asyncio
import datetime
import json
import os
import socket
import sys
from typing import List
import logging
from collections import defaultdict, Counter
from copy import deepcopy

import httpx
import subprocess
import time
import random
from rich.progress import Progress, TaskID

import requests
from openai import OpenAI
from pydantic import BaseModel

from models import EvalMatch, EvalToolParam
from question_sets.complex import complex_questions
from question_sets.simple import simple_questions


# Configure logging
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


# Parse command-line arguments
def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--scenario", required=True, type=str, default="simple", choices=["simple", "complex", "all"], help="The scenario that should be tested. Use 'all' to test everything.")
    parser.add_argument("-b", "--backend", type=str, default="tool-llm", help="Specify the backend that should be used.")
    parser.add_argument("-m", "--model", type=str, default="gpt-4o-mini", help="Specifies the model that will be used with the backend. If backend is 'multi-agent', defines the model setting that will be used.")
    parser.add_argument("-o", "--opaca-url", type=str, default=None, help="Where the OPACA platform is running.")
    parser.add_argument("-l", "--llm-url", type=str, default=f"http://localhost:3001", help="Where the OPACA-LLM Backend is running.")
    parser.add_argument("-i", "--iterations", type=int, default=1, help="The number of iterations that should be run for each question set.")
    parser.add_argument("-c", "--chunks", type=int, default=5, help="The number of chunks the question set will be split into and evaluated in parallel.")
    parser.add_argument("-j", "--judge", action=argparse.BooleanOptionalAction, help="Whether the Judge LLM should be used for evaluation.")
    parser.add_argument("-p", "--portion", type=int, default=100, help="The portion of the question set that should be evaluated in percentage.")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level.")
    return parser.parse_args()


# Define the test container names (should all be located in docker hub repo "rkader2811")
test_containers = ["rkader2811/smart-office", "rkader2811/warehouse", "rkader2811/music-platform", "rkader2811/calculator"]


# Instruct the Judge LLM
judge_system_message = ("""You are given a question, expected answer, and response. Evaluate if the response was helpful and 
included the information that were mentioned in the expected answer. You are judging the quality of 
the answer by giving a score from 1 to 5. Here are the definitions of those scores:

1 – Completely Irrelevant:
The response does not include any of the expected information and does not address the initial request in a meaningful way. It may be entirely off-topic, misleading, or nonsensical.

2 – Attempted but Unsuccessful:
The response attempts to address the request but fails to include any correct or expected information. It may contain generic or off-base content with no real value in context.

3 – Partially Correct:
The response includes some of the expected information, but omits key details or contains significant inaccuracies. The answer is incomplete or only partially useful.

4 – Mostly Correct:
The response includes all key expected information, but lacks precision, clarity, or depth. It may contain minor inaccuracies, vague phrasing, or insufficient justification.

5 – Fully Correct and Precise:
The response includes all expected information and is clear, precise, well-structured, and meets the requirements of the request completely. It may also demonstrate nuance or thorough understanding.

Important: Always provide a reason for your decision.""")


# Message template for the Judge LLM
judge_template = ("A user had the following question: {question}\n\n"
                  "The expected answer for this question: {expected_answer}\n\n"
                  "This was the generated response: {response}")


# Structured output how the JudgeLLM should answer
class Metric(BaseModel):
    score: int
    reason: str


# Method to invoke the Judge LLM
async def invoke_judge(question, expected_answer, response):
    formatted_message = judge_template.format(
        question=question, expected_answer=expected_answer, response=response
    )

    messages =  [
        {"role": "system", "content": judge_system_message},
        {"role": "user", "content": formatted_message}
    ]

    client = OpenAI()
    response = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=messages,
        temperature=0,
        response_format=Metric
    )

    return response.choices[0].message.parsed


def flatten(xss):
    return [x for xs in xss for x in xs]


def split(a, n):
    k, m = divmod(len(a), n)
    return [a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n)]


async def evaluate_param(actual_args: dict[str, object], expected_args: list[EvalToolParam]):
    """
    Evaluates whether the actual arguments match the expected arguments based on specified conditions.
    """
    expected_dict = {e.key: e for e in expected_args}

    # Check if there are extra parameters
    if any(a not in expected_dict for a in actual_args):
        return False

    # Check if there are missing parameters
    if any(e.key not in actual_args for e in expected_args if not e.optional):
        return False

    # Check if all parameter values match the expected values
    def matches(act, exp):
        if type(act) != type(exp.value):
            return False
        if exp.match == EvalMatch.EXACT:
            return act == exp.value
        if exp.match == EvalMatch.PARTIAL and type(exp.value) == str:
            return exp.value.lower() in act.lower()
        return exp.match == EvalMatch.NONE
    return all(matches(actual_args[key], expected_dict[key]) for key in actual_args)


async def evaluate_tools(_actual_tools, _expected_tools):
    """
    Evaluate and compare the actual tools used with the expected tools.
    """

    # Make copy of tools, subtract matches and get missed/extra tool calls
    actual_tools = flatten(deepcopy(_actual_tools))
    expected_tools = deepcopy(_expected_tools)

    # Save results
    result = {
        "match": [],
        "missed": [],
        "extra": [],
    }

    ids = []

    # Iterate over all expected tools sorted by their ids (important for dependencies)
    for e_tool in sorted(_expected_tools, key=lambda x: x.id):

        # Iterate over list of tools until match is found
        for a_tool in actual_tools:
            if not e_tool.name in a_tool["name"]:
                continue

            # Check if any alternative tool calls have been made already
            # If yes, this expected tool call ca be disregarded
            if any(i in ids for i in e_tool.alternatives):
                expected_tools.remove(e_tool)
                continue

            # Optionally filter out the requestBody field
            a_args = a_tool["args"]
            if a_tool["args"].get('requestBody', {}):
                a_args = a_tool["args"].get('requestBody', {})

            # Evaluate the tool parameters, returns True if they match
            if not await evaluate_param(a_args, e_tool.args):
                continue

            # Check if dependent tool calls have been made
            # If not, mark this expected tool call as missed with a reason
            if not all(i in ids for i in e_tool.depends):
                e_tool.name += f"(missing dependencies: {e_tool.depends})"
                break

            ids.append(e_tool.id)
            result["match"].append(e_tool.name)
            expected_tools.remove(e_tool)
            actual_tools.remove(a_tool)
            break

    # Iterate over remaining expected tools and check if any alternatives have been found
    # Also check for optional tool calls that were not found and remove them
    remaining_tools = deepcopy(expected_tools)      # Deepcopy to avoid iteration errors while removing elements
    for e_tool in remaining_tools:
        if e_tool.optional:
            expected_tools.remove(e_tool)
        elif any(all(i in ids for i in e_ids) for e_ids in e_tool.alternatives):
            expected_tools.remove(e_tool)

    result["missed"].extend([t.name for t in expected_tools])
    result["extra"].extend([t["name"] for t in actual_tools])

    return result


async def parallel_test(question_set: List, llm_url: str, opaca_url: str, backend: str, model: str, use_judge: bool, progress: Progress, task_id: TaskID):
    # Create a unique session for requests
    async with httpx.AsyncClient(http2=False, limits=httpx.Limits(max_connections=1), headers={"Connection": "close"}) as session:

        # Make the OPACA-LLM connect with the OPACA platform
        try:
            await session.post(llm_url + "/connect", json={"url": opaca_url, "user": "", "pwd": ""})
        except Exception as e:
            logging.error(f'Unable to establish a connection to the OPACA platform: {str(e)}')
            raise RuntimeError(str(e))

        # Get default config and overwrite the model
        try:
            config = json.loads((await session.get(llm_url + f'/{backend}/config')).content)["value"]
            if backend == "self-orchestrated":
                config["model_config_name"] = model
            else:
                config["model"] = model
            await session.put(llm_url + f'/{backend}/config', json=config)
        except Exception as e:
            logging.error(f'Failed to get default config from OPACA-LLM. Does the backend ("{backend}")? exist?')
            raise RuntimeError(str(e))

        agent_time = defaultdict(float)

        results = []

        for i, call in enumerate(question_set):
            # Generate a response by the OPACA LLM
            server_time = time.time()
            result = await session.post(f'{llm_url}/{backend}/query', json={'user_query': call["input"]}, timeout=None)
            result = result.content
            server_time = time.time() - server_time

            # Load the results
            try:
                result = json.loads(result)
            except json.decoder.JSONDecodeError as e:
                print(f'Encountered following error: {e}\n handling result: {result}')
                continue

            # Accumulate the time of each agent
            for agent_message in result["agent_messages"]:
                agent_time[f'{agent_message["agent"]}'] += agent_message["execution_time"]

            # Write the results into a file
            results.append({
                "question": call["input"],
                "expected_answer": call["output"],
                "response": result["content"],
                "iterations": result["iterations"],
                "time": result["execution_time"],
                "agent_time": dict(agent_time),
                "response_metadata": {
                    "prompt_tokens": sum([message["response_metadata"].get("prompt_tokens", 0) for message in result["agent_messages"]]),
                    "completion_tokens": sum([message["response_metadata"].get("completion_tokens", 0) for message in result["agent_messages"]]),
                    "total_tokens": sum([message["response_metadata"].get("total_tokens", 0) for message in result["agent_messages"]]),
                },
                "server_time": server_time,
                "called_tools": sum(len(message["tools"]) for message in result["agent_messages"]),
                "tools": [message["tools"] for message in result["agent_messages"] if message["tools"]],
            })

            # Let results be evaluated by judge llm
            if use_judge:
                metric = await invoke_judge(call["input"], call["output"], result["content"])
                results[-1]["reason"] = metric.reason
                results[-1]["score"] = metric.score

            # Evaluate the tools against the expected tools
            results[-1]["tool_matches"] = await evaluate_tools(results[-1]["tools"], call["tools"])

            # Reset the message history
            await session.post(llm_url + "/reset", timeout=None)

            # Update progress bar
            progress.advance(task_id)

    return results


def setUp(opaca_url: str) -> None:
    """
    Starts an already available container of the OPACA platform and then deploys all test containers to it.
    Also starts the OPACA-LLM. Returns the object for the server process of the OPACA-LLM (so it can be terminated
    afterwards) and a list of the created container ids.
    """

    # If an opaca platform is already running, delete all running containers and deploy the benchmark containers
    # This is necessary to restore the initial variable states
    try:
        requests.get(opaca_url + "/info")
        logging.info("OPACA platform already running. Cleaning up container environment...")
        response = requests.get(opaca_url + "/containers")
        c_ids = [c["containerId"] for c in json.loads(response.content)]
        for c_id in c_ids:
            requests.delete(opaca_url + f'/containers/{c_id}', json={})
            logging.info(f'Removed container {c_id}')
        for name in test_containers:
            requests.post(opaca_url + "/containers", json={"image": {"imageName": name}})
            logging.info(f"Deployed {name}!")
        return
    except requests.exceptions.RequestException as e:
        logging.info("Creating new OPACA platform environment...")

    # Login to docker registry
    try:
        subprocess.run(["docker", "login", "registry.gitlab.dai-labor.de"], check=True)
    except Exception as e:
        raise Exception("Unable to login to gitlab.dai-labor.de")

    with open(".env", "w", encoding="utf-8") as f:
        f.write(f'OPACA_URL="{opaca_url}"\n')

    # Start the OPACA platform
    # The compose stack should have been started and exited previously...
    logging.info("Starting OPACA platform and OPACA-LLM...")
    subprocess.run(["docker", "compose", "up", "-d", "--build"], cwd=os.path.dirname(os.path.realpath(__file__)))

    # Wait until OPACA platform has started, set timeout to 15 seconds
    start_time = time.time()
    while time.time() - start_time < 15:
        try:
            response = requests.get(opaca_url + "/info")
            if response.status_code == 200:
                logging.info("OPACA platform and OPACA-LLM successfully started.")
                break
        except requests.RequestException as e:
            pass    # OPACA platform not started yet
        time.sleep(1)

    # Deploy containers to OPACA platform
    logging.info("Deploying OPACA containers for testing...")
    for name in test_containers:
        requests.post(opaca_url + "/containers", json={"image": {"imageName": name}})
        logging.info(f"Deployed {name}!")

    logging.info("Setup finished")
    return


async def main():
    args = parse_arguments()

    # Extract arguments
    scenario = args.scenario
    backend = args.backend
    model = args.model
    opaca_url = args.opaca_url
    iterations = args.iterations
    chunk_size = args.chunks
    llm_url = args.llm_url
    use_judge = args.judge
    portion = args.portion
    # Set the logging level
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    if opaca_url is None:
        opaca_url = f"http://{socket.gethostbyname(socket.gethostname())}:8000"
        if "127.0" in opaca_url:
            logging.error("Unable to determine own IP. Please provide full OPACA Platform URL using -o parameter.")
            exit(1)

    # Define question sets for scenarios
    questions = {
        "simple": simple_questions,
        "complex": complex_questions,
        "all": simple_questions + complex_questions,
    }

    # Check if selected scenario is available
    if not scenario in questions.keys():
        logging.error(f'The scenario "{scenario}" is not supported.')
        exit(1)

    # Create a unique file name for the results
    file_name = f'{scenario}-{model}-{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

    # Setup the OPACA platform
    try:
        setUp(opaca_url)
    except Exception as e:
        logging.error(f'Failed to setup the test environment: {str(e)}')
        exit(1)

    question_set = questions[scenario]
    results = {}

    # Samples a random portion of the selected question set
    if portion != 100:
        question_set = random.sample(question_set, int(len(question_set) * portion / 100))

    # Main test loop
    for i in range(1, iterations+1):
        logging.info(f'Iteration {i}/{iterations}')

        # Split the question set into chunks for parallel execution
        chunks = split(question_set, chunk_size)

        # Visualize progress
        progress = Progress()
        progress.start()
        tasks = [progress.add_task(f'Chunk-{i}', total=len(data)) for i, data in enumerate(chunks)]

        # Execute Tests and combine results
        q_results = await asyncio.gather(*(parallel_test(chunks[j], llm_url, opaca_url, backend, model, use_judge, progress, task_id) for task_id, j in zip(tasks, range(len(chunks)))))
        q_results = flatten(q_results)

        # Init benchmark values
        agent_time = Counter()
        correct_tool_usage = 0
        perfect_tool_usage = 0
        total_token_usage = 0
        total_time = 0
        total_server_time = 0
        average_score = 0.0

        # Extract benchmark results
        for q in q_results:
            agent_time += Counter(q["agent_time"])
            if len(q["tool_matches"]["missed"]) == 0:
                correct_tool_usage += 1
                if len(q["tool_matches"]["extra"]) == 0:
                    perfect_tool_usage += 1
            total_token_usage += q["response_metadata"]["total_tokens"]
            total_time += q["time"]
            total_server_time += q["server_time"]
            average_score += q.get("score", 0)
        average_score /= len(q_results)

        # Create a summary of the test run
        result = {"questions": q_results, "summary": {
            "backend": backend,
            "model": model,
            "questions": len(question_set),
            "correct_tool_usage": correct_tool_usage,
            "perfect_tool_usage": perfect_tool_usage,
            "total_time": total_time,
            "total_server_time": total_server_time,
            "agent_time": agent_time,
            "total_token_usage": total_token_usage,
        }}
        if use_judge:
            result["summary"]["average_score"] = average_score

        # If there is more than one iteration, save results into separated field
        if iterations > 1:
            results[f'iteration_{i}'] = result
        else:
            results = result
        progress.stop()

    # If there was more than one iteration, create a total summary
    if iterations > 1:
        results["total_summary"] = {
            "backend": backend,
            "model": model,
            "questions": len(question_set) * iterations,
            "correct_tool_usage": 0,
            "perfect_tool_usage": 0,
            "total_time": 0,
            "total_server_time": 0,
            "agent_time": Counter(),
            "total_token_usage": 0
        }
        if use_judge:
            results["total_summary"]["average_score"] = 0.0
        for i in range(1, iterations+1):
            results["total_summary"]["correct_tool_usage"] += results[f'iteration_{i}']['summary']['correct_tool_usage']
            results["total_summary"]["perfect_tool_usage"] += results[f'iteration_{i}']['summary']['perfect_tool_usage']
            results["total_summary"]["total_time"] += results[f'iteration_{i}']['summary']['total_time']
            results["total_summary"]["total_server_time"] += results[f'iteration_{i}']['summary']['total_server_time']
            results["total_summary"]["agent_time"] += Counter(results[f'iteration_{i}']['summary']['agent_time'])
            results["total_summary"]["total_token_usage"] += results[f'iteration_{i}']['summary']['total_token_usage']
            if use_judge:
                results["total_summary"]["average_score"] += results[f'iteration_{i}']['summary']['average_score']
        if use_judge:
            results["total_summary"]["average_score"] /= iterations

    logging.info(f"Finished benchmark test!\tTotal questions: {len(question_set) * iterations}")

    # Write results into json file
    if not os.path.exists('test_runs'):
        os.makedirs('test_runs')
    with open(f'test_runs/{file_name}', "a") as f:
        json.dump(results, f, indent=2)

    return


if __name__ == "__main__":
    asyncio.run(main())
