import argparse
import datetime
import json
import os
import socket
import sys
from typing import Dict, List
import logging
from collections import defaultdict
from copy import deepcopy

import numpy as np
import subprocess
import time

import requests
from openai import OpenAI
from pydantic import BaseModel

from models import EvalMatch
from question_sets.complex import complex_questions
from question_sets.simple import simple_questions
from question_sets.deployment import deployment_questions


# Define a logger
logger = logging.getLogger(__name__)


# Parse command-line arguments
def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--scenario", required=True, type=str, default="simple", choices=["simple", "complex", "deployment", "simple-complex", "all"], help="The scenario that should be tested. Use 'all' to test everything.")
    parser.add_argument("-b", "--backend", type=str, default="tool-llm", help="Specify the backend that should be used.")
    parser.add_argument("-m", "--model", type=str, default="gpt-4o-mini", help="Specifies the model that will be used with the backend. If backend is 'multi-agent', defines the model setting that will be used.")
    parser.add_argument("-o", "--opaca-url", type=str, default=None, help="Where the OPACA platform is running.")
    parser.add_argument("-l", "--llm-url", type=str, default=f"http://localhost:3001", help="Where the OPACA-LLM Backend is running.")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level.")
    return parser.parse_args()


# Create a unique session for requests
session = requests.Session()


# Define the test container names (should all be located in docker hub repo "rkader2811")
test_containers = ["rkader2811/smart-office", "rkader2811/warehouse", "rkader2811/music-platform", "rkader2811/calculator"]


# Instruct the Judge LLM
judge_system_message = ("Given a question, expected answer, and response. Evaluate if the response was helpful and "
                  "included the information that were mentioned in the expected answer. Helpful responses include "
                  "all the expected information. Unhelpful responses include errors or a missing vital parts "
                  "of the expected information. Decide the quality by using the keywords 'helpful' or 'unhelpful'. "
                  "Further give the answer a score between 0.0 and 1.0, in which 0.0 is very unhelpful with no "
                  "information and 1.0 is very helpful and every required information present."
                  "Always provide a reason for your decision.")


# Message template for the Judge LLM
judge_template = ("A user had the following question: {question}\n\n"
                  "The expected answer for this question: {expected_answer}\n\n"
                  "This was the generated response: {response}")


# Structured output how the JudgeLLM should answer
class Metric(BaseModel):
    quality: str
    reason: str
    score: float


# Method to invoke the Judge LLM
def invoke_judge(question, expected_answer, response):
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


def evaluate_param(_actual_args, _expected_args):
    actual_args = deepcopy(_actual_args)
    expected_args = deepcopy(_expected_args)

    for e_p in _expected_args:
        if e_p.optional:
            expected_args.pop(e_p)
            if e_p.key in _actual_args.keys():
                actual_args.pop(_actual_args[e_p.key])
            continue
        if e_p.key not in _actual_args.keys():
            return False
        else:
            a_p = _actual_args[e_p.key]
        if not type(e_p.value) == type(a_p):
            return False
        if e_p.match == EvalMatch.EXACT and not e_p.value == a_p:
            return False
        elif e_p.match == EvalMatch.PARTIAL and not e_p.value in a_p:
            return False
        expected_args.remove(e_p)
        del actual_args[e_p.key]

    if not actual_args and not expected_args:
        return True
    return False



def evaluate_tools(_actual_tools, _expected_tools):
    # Make copy of tools, subtract matches and get missed/extra tool calls
    actual_tools = flatten(deepcopy(_actual_tools))
    expected_tools = deepcopy(_expected_tools)

    # Save results
    result = {
        "match": [],
        "missed": [],
        "extra": [],
    }

    for e_tool in _expected_tools:
        for a_tool in flatten(_actual_tools):
            if not e_tool.name in a_tool["name"]:
                continue

            # Filter out the requestBody field
            a_args = a_tool["args"]
            if a_tool["args"].get('requestBody', {}):
                a_args = a_tool["args"].get('requestBody', {})

            if not evaluate_param(a_args, e_tool.args):
                continue

            result["match"].append(a_tool["name"])
            expected_tools.remove(e_tool)
            actual_tools.remove(a_tool)

    result["missed"] = [t.name for t in expected_tools]
    result["extra"] = [t["name"] for t in actual_tools]

    return result


def benchmark_test(file_name: str, question_set: List[Dict[str, str]], llm_url: str, backend: str, config: Dict) -> None:
    """
    Test a scenario. Will iterate through every pair of (question, expected_answer) pairs. Will print
    its results to the given file_name in the same directory.
    :return: None
    """
    logging.info("In benchmark test")
    if not os.path.exists('test_runs'):
        os.makedirs('test_runs')

    iterations = []
    execution_times = []
    number_tools = 0
    helpful_counter = 0
    total_score = 0.0
    total_time = .0
    agent_time = defaultdict(float)
    total_server_time = time.time()
    total_token_usage = 0

    result_json = {"questions": {}, "summary": {}}

    try:
        for i, call in enumerate(question_set):
            # Generate a response by the OPACA LLM
            server_time = time.time()
            result = session.post(f'{llm_url}/{backend}/query', json={'user_query': call["input"], 'api_key': ""}).content
            server_time = time.time() - server_time

            # Load the results and evaluate them by the JudgeLLM
            result = json.loads(result)
            metric = invoke_judge(call["input"], call["output"], result["content"])

            # Write the results into a file
            result_json["questions"][f'question_{i+1}'] = {
                "question": call["input"],
                "expected_answer": call["output"],
                "response": result["content"],
                "iterations": result["iterations"],
                "time": result["execution_time"],
                "response_metadata": {
                    "prompt_tokens": sum([message["response_metadata"].get("prompt_tokens", 0) for message in result["agent_messages"]]),
                    "completion_tokens": sum([message["response_metadata"].get("completion_tokens", 0) for message in result["agent_messages"]]),
                    "total_tokens": sum([message["response_metadata"].get("total_tokens", 0) for message in result["agent_messages"]]),
                },
                "server_time": server_time,
                "called_tools": sum(len(message["tools"]) for message in result["agent_messages"]),
                "tools": [message["tools"] for message in result["agent_messages"] if message["tools"]],
                "quality": metric.quality,
                "score": metric.score,
                "reason": metric.reason,
            }

            # Accumulate the time of each agent
            for agent_message in result["agent_messages"]:
                agent_time[f'{agent_message["agent"]}'] += agent_message["execution_time"]

            # Save the results in memory for a summary
            if metric.quality == "helpful":
                helpful_counter += 1
            total_score += metric.score
            total_time += result["execution_time"]
            execution_times.append(result["execution_time"])
            iterations.append(result["iterations"])
            number_tools += sum(len(message["tools"]) for message in result["agent_messages"])
            total_token_usage += result_json["questions"][f'question_{i+1}']['response_metadata']['total_tokens'] or 0

            # Evaluate the tools against the expected tools
            result_json["question"][f'question_{i+1}']["tool_matches"] = evaluate_tools(result_json["questions"][f'question_{i+1}']["tools"], call["tools"])

            logging.info(f'Question {i+1}: {metric.quality}')

            # Reset the message history
            session.post(llm_url + "/reset", json={})

        # Write a summary of all tests
        result_json["summary"] = {
            "backend": backend,
            "config": config,
            "questions": len(question_set),
            "helpful": helpful_counter,
            "average_score": total_score / len(question_set),
            "total_time": total_time,
            "total_server_time": time.time() - total_server_time,
            "agent_time": agent_time,
            "avg_execution_time_per_iteration": np.average(np.array(execution_times) / np.array(iterations)),
            "total_token_usage": total_token_usage,
        }

        # Write results into json file
        with open(f'test_runs/{file_name}', "a") as f:
            json.dump(result_json, f, indent=2)

    except Exception as e:
        raise RuntimeError(str(e))


def setUp(opaca_url: str, llm_url: str, backend: str, model: str):
    """
    Starts an already available container of the OPACA platform and then deploys all test containers to it.
    Also starts the OPACA-LLM. Returns the object for the server process of the OPACA-LLM (so it can be terminated
    afterwards) and a list of the created container ids.
    """
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
    subprocess.run(["docker", "compose", "up", "-d", "--build"])

    # Wait until OPACA platform has started, set timeout to 15 seconds
    start_time = time.time()
    while time.time() - start_time < 15:
        try:
            response = session.get(opaca_url + "/info")
            if response.status_code == 200:
                logging.info("OPACA platform and OPACA-LLM successfully started.")
                break
        except requests.RequestException as e:
            pass    # OPACA platform not started yet
        time.sleep(1)

    # Deploy containers to OPACA platform
    container_ids = []
    logging.info("Deploying OPACA containers for testing...")
    for name in test_containers:
        response = requests.post(opaca_url + "/containers", json={"image": {"imageName": name}})
        container_ids.append(response.content.decode('ascii'))
        logging.info(f"Deployed {name}!")

    # Make the OPACA-LLM connect with the OPACA platform
    logging.info("Trying to connect to OPACA LLM...")
    try:
        session.post(llm_url + "/connect", json={"url": opaca_url, "user": "", "pwd": ""})
    except Exception as e:
        logging.error(f'Unable to establish a connection to the OPACA platform: {str(e)}')
        tearDown(opaca_url, container_ids)
        raise RuntimeError(str(e))


    # Get default config and overwrite the model
    try:
        config = json.loads(session.get(llm_url + f'/{backend}/config').content)["value"]
        if backend == "self-orchestrated":
            config["model_config_name"] = model
        else:
            config["model"] = model
        session.put(llm_url + f'/{backend}/config', json=config)
    except Exception as e:
        logging.error(f'Failed to get default config from OPACA-LLM. Does the backend ("{backend}")? exist?')
        tearDown(opaca_url, container_ids)
        raise RuntimeError(str(e))

    logging.info("Setup finished")
    return container_ids, config


def tearDown(opaca_url, container_ids):
    """
    Cleans up the testing environment. Deletes the created containers from the specified OPACA platform,
    """
    logging.info(f'Tearing down benchmark environment...')
    for container_id in container_ids:
        requests.delete(opaca_url + f'/containers/{container_id}', json={})
        logging.info(f'Removed container {container_id}')
    subprocess.run(["docker", "compose", "rm", "-s", "-f"])
    os.remove(".env")
    logging.info(f'Teardown finished!')


def main():
    args = parse_arguments()

    # Extract arguments
    scenario = args.scenario
    backend = args.backend
    model = args.model
    opaca_url = args.opaca_url
    llm_url = args.llm_url
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
        "deployment": deployment_questions,
        "simple-complex": simple_questions + complex_questions,
        "all": simple_questions + complex_questions + deployment_questions,
    }

    # Check if selected scenario is available
    if not scenario in questions.keys():
        logging.error(f'The scenario "{scenario}" is not supported.')
        return -1

    # Create a unique file name for the results
    file_name = f'{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

    # Setup the OPACA platform
    try:
        container_ids, config = setUp(opaca_url, llm_url, backend, model)
    except Exception as e:
        logging.error(f'Failed to setup the test environment: {str(e)}')
        return

    # Run the benchmark test
    benchmark_test(f'{scenario}-{file_name}', questions[scenario], llm_url, backend, config)

    # Cleanup the test environment
    tearDown(opaca_url, container_ids)


if __name__ == "__main__":
    main()
