import argparse
import datetime
import json
import os
import socket
from typing import Dict, List
import logging

import numpy as np
import subprocess
import time
import requests
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from Backend.src.models import LLMAgent
from question_sets.complex import complex_questions
from question_sets.simple import simple_questions
from question_sets.deployment import deployment_questions


# Define a logger
logger = logging.getLogger(__name__)


# Parse command-line arguments
def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--scenario", required=True, type=str, default="simple", choices=["simple", "complex", "deployment", "simple-complex", "all"], help="The scenario that should be tested. Use 'all' to test everything.")
    parser.add_argument("-b", "--backend", type=str, default="tool-llm-openai", help="Specify the backend that should be used.")
    parser.add_argument("-o", "--opaca-url", type=str, default=f"http://{socket.gethostbyname(socket.gethostname())}:8000", help="Where the OPACA platform is running.")
    parser.add_argument("-l", "--llm-url", type=str, default=f"http://{socket.gethostbyname(socket.gethostname())}:3001", help="Where the OPACA-LLM Backend is running.")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level.")
    return parser.parse_args()


# Define the default configuration for every method
CONFIGS = {
    "simple-openai": {
        "model": "gpt-4o-mini",
        "temperature": 1.0,
        "ask_policy": 0,
    },
    "simple-llama": {
        "api-url": "http://10.0.64.101:11000",
        "model": "gpt-4o-mini",
        "temperature": 1.0,
        "ask_policy": 0,
    },
    "rest-gpt-openai" : {
        "slim_prompts": {
            "planner": True,
            "action_selector": True,
            "evaluator": False
        },
        "examples": {
            "planner": False,
            "action_selector": True,
            "caller": True,
            "evaluator": True
        },
        "use_agent_names": True,
        "temperature": 0,
        "gpt-model": "gpt-4o-mini",
    },
    "tool-llm-openai": {
        "model": "gpt-4o-mini",
        "temperature": 0,
        "use_agent_names": True,
    },
    "multi-agent": {
        "model_config_name": "vllm",  # Model Config
        "temperature": 0,
        "max_rounds": 5,  # Maximum number of orchestration rounds
        "max_iterations": 3,  # Maximum iterations per agent task
        "use_worker_for_output": False,  # Whether to use worker model for output generation
        "use_agent_planner": True  # Whether to use agent planner for function planning
    }
}


# Create a unique session for requests
session = requests.Session()


# Define the test container names (should all be located in docker hub repo "rkader2811")
test_containers = ["smart-office", "warehouse", "music-platform", "calculator"]


# Create the JudgeLLM using gpt-4o
judge_llm = LLMAgent(
    name="Judge LLM",
    llm=ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        ),
    system_prompt="Given a question, expected answer, and response. Evaluate if the response was helpful and "
                  "included the information that were mentioned in the expected answer. Helpful responses include "
                  "all the expected information. Unhelpful responses include errors or a missing vital parts "
                  "of the expected information. Decide the quality by using the keywords 'helpful' or 'unhelpful'. "
                  "Further give the answer a score between 0.0 and 1.0, in which 0.0 is very unhelpful with no "
                  "information and 1.0 is very helpful and every required information present."
                  "Always provide a reason for your decision.",
    input_variables=["question", "expected_answer", "response"],
    message_template="A user had the following question: {question}\n\n"
                     "The expected answer for this question: {expected_answer}\n\n"
                     "This was the generated response: {response}"
)


# Structured output how the JudgeLLM should answer
class Metric(BaseModel):
    quality: str
    reason: str
    score: float


def benchmark_test(file_name: str, question_set: List[Dict[str, str]], llm_url: str, backend: str) -> None:
    """
    Test a scenario. Will iterate through every pair of (question, expected_answer) pairs. Will print
    its results to the given file_name in the same directory.
    :return: None
    """
    logging.info("In benchmark test")
    if not os.path.exists('test_runs'):
        os.makedirs('test_runs')

    total_time = .0
    iterations = []
    execution_times = []
    number_tools = 0
    helpful_counter = 0
    total_score = 0.0

    with open(f'test_runs/{file_name}', 'a', encoding="utf-8") as f:
        try:
            for i, call in enumerate(question_set):
                # Generate a response by the OPACA LLM
                cur_time = time.time()
                result = session.post(f'{llm_url}/{backend}/query', json={'user_query': call["input"], 'api_key': ""}).content
                run_time = time.time() - cur_time

                # Load the results and evaluate them by the JudgeLLM
                result = json.loads(result)
                judge_response = judge_llm.invoke({"question": call["input"], "expected_answer": call["output"], "response": result["content"]}, response_format=Metric)
                metric = judge_response.content

                # Write the results into a file
                f.write(f'-------------- Question {i+1} --------------\n'
                        f'Question: {call["input"]}\n'
                        f'Expected Answer Reference: {call["output"]}\n'
                        f'Response: {result["content"]}\n'
                        f'Iterations: {result["iterations"]}\n'
                        f'Time: {result["execution_time"]}(Test side: {run_time})\n'
                        f'Tools called: {sum(len(message["tools"]) for message in result["agent_messages"])}\n'
                        f'Tools: {[message["tools"] for message in result["agent_messages"] if message["tools"]]}\n'
                        f'Judge Results:\n'
                        f'Quality: {metric.quality}\n'
                        f'Score: {metric.score}\n'
                        f'Reason: {metric.reason}\n\n\n')

                # Save the results in memory for a summary
                if metric.quality == "helpful":
                    helpful_counter += 1
                total_score += metric.score
                total_time += result["execution_time"]
                execution_times.append(result["execution_time"])
                iterations.append(result["iterations"])
                number_tools += sum(len(message["tools"]) for message in result["agent_messages"])

                logging.info(f'Question {i+1}: {metric.quality}')

                # Reset the message history
                session.post(llm_url + "/reset", json={})

            # Write a summary of all tests
            f.write(f'-------------- Summary --------------\n')
            f.write(f'Used backend: {backend}\n'
                    f'Used config: {CONFIGS[backend]}\n'
                    f'Helpful answers: {helpful_counter}/{len(question_set)}\n'
                    f'Avg Score: {total_score / len(question_set)}\n'
                    f'Total Execution time: {total_time}\n'
                    f'Avg Execution time per iteration: {np.average(np.array(execution_times) / np.array(iterations))}\n')
        except Exception as e:
            raise RuntimeError(str(e))


def setUp(opaca_url: str, llm_url: str, backend: str):
    """
    Starts an already available container of the OPACA platform and then deploys all test containers to it.
    Also starts the OPACA-LLM. Returns the object for the server process of the OPACA-LLM (so it can be terminated
    afterwards) and a list of the created container ids.
    """
    # Start the OPACA platform
    # The compose stack should have been started and exited previously...
    logging.info("Setup OPACA platform")
    subprocess.run(["docker", "start", "opaca-platform-opaca-platform-userdb-1", "opaca-platform-opaca-platform-1"], check=True)
    time.sleep(10)       # Wait to let OPACA platform start
    container_ids = []

    logging.info("Deploying OPACA containers for testing...")
    for name in test_containers:
        response = requests.post(opaca_url + "/containers", json={"image": {"imageName": f"rkader2811/{name}"}})
        container_ids.append(response.content.decode('ascii'))
        logging.info(f"Deployed {name}!")

    logging.info("Setup OPACA-LLM")
    try:
        # subprocess.run(['docker', 'build', '-t', 'opaca-llm-test-backend', '../Backend'], check=True)
        subprocess.run(['docker', 'run', '-d',
                        '-e', 'OPENAI_API_KEY', '-e', 'VLLM_BASE_URL', '-e', 'VLLM_API_KEY',
                        '-p', '3001:3001', '--name', 'opaca-llm-test-backend', 'opaca-llm-test-backend'], check=True)
        time.sleep(7)       # Needs to be long enough to let the server start
    except Exception as e:
        logging.error(f'Unable to start OPACA-LLM: {str(e)}')
        tearDown(opaca_url, container_ids)
        raise RuntimeError(str(e))

    logging.info("Trying to connect to OPACA LLM...")
    try:
        # Make the OPACA-LLM connect with the OPACA platform and use the config defined in CONFIGS for the given method
        session.post(llm_url + "/connect", json={"url": opaca_url, "user": "", "pwd": ""})
        session.put(llm_url + f'/{backend}/config', json=CONFIGS[backend])
    except Exception as e:
        logging.error(f'Unable to establish a connection: {str(e)}')
        tearDown(opaca_url, container_ids)
        raise RuntimeError(str(e))
    logging.info("Setup finished")
    return container_ids


def tearDown(opaca_url, container_ids):
    """
    Cleans up the testing environment. Deletes the created containers from the specified OPACA platform,
    """
    logging.info(f'Tear down OPACA-LLM')
    for container_id in container_ids:
        requests.delete(opaca_url + f'/containers/{container_id}', json={})
        logging.info(f'Removed container {container_id}')
    subprocess.run(['docker', 'rm', '-f', 'opaca-llm-test-backend'])
    subprocess.run(["docker", "stop", "opaca-platform-opaca-platform-userdb-1", "opaca-platform-opaca-platform-1"])
    logging.info(f'Stopping OPACA platform')


def main():
    args = parse_arguments()

    # Extract arguments
    scenario = args.scenario
    backend = args.backend
    opaca_url = args.opaca_url
    llm_url = args.llm_url
    # Set the logging level
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(asctime)s - %(levelname)s - %(message)s")

    # Check that the provided backend name exists
    if not backend in CONFIGS.keys():
        raise RuntimeError(f"Your selected backend ({backend}) does not exist!")

    # Create a unique file name for the results
    file_name = f'{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

    # Setup the OPACA platform
    try:
        container_ids = setUp(opaca_url, llm_url, backend)
    except Exception as e:
        logging.error(f'Failed to setup the test environment: {str(e)}')
        return

    # Run the specified scenario
    try:
        match scenario:
            case "simple":
                questions = simple_questions
            case "complex":
                questions = complex_questions
            case "deployment":
                questions = deployment_questions
            case "simple-complex":
                questions = simple_questions
                questions.extend(complex_questions)
            case "all":
                questions = simple_questions
                questions.extend(complex_questions)
                questions.extend(deployment_questions)
            case _:
                logging.error(f"There is no such test scenario: '{scenario}'")
                tearDown(opaca_url, container_ids)
                return
        benchmark_test(f'{scenario}-{file_name}', questions, llm_url, backend)
    except Exception as e:
        logging.error(str(e))

    tearDown(opaca_url, container_ids)


if __name__ == "__main__":
    main()
