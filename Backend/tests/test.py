import datetime
import json
import os
from typing import Dict, List

import numpy as np
import subprocess
import time
import unittest
import requests
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from Backend.src.models import LLMAgent
from question_sets.complex import complex_questions
from question_sets.simple import simple_questions
from question_sets.deployment import deployment_questions

#########################################
###  Set the backend that is tested   ###

BACKEND = "simple-openai"

#########################################
### Change configuration if necessary ###

BACKENDS = {
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
#########################################
###     Change connection settings    ###

opaca_url = "http://localhost:8000"
llm_url = "http://localhost:3001"
query_url = f"http://localhost:3001/{BACKEND}/query"

#########################################

session = requests.Session()
test_containers = ["smart-office", "warehouse", "music-platform", "calculator"]

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


class Metric(BaseModel):
    quality: str
    reason: str
    score: float


async def benchmark_test(file_name: str, question_set: List[Dict[str, str]]) -> bool:
    print("In benchmark test")
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
                result = session.post(query_url, json={'user_query': call["input"], 'api_key': ""}).content
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

                # Reset the message history
                session.post(llm_url + "/reset", json={})

            # Write a summary of all tests
            f.write(f'-------------- Summary --------------\n')
            f.write(f'Used backend: {BACKEND}\n'
                    f'Used config: {BACKENDS[BACKEND]}\n'
                    f'Total Execution time: {total_time}\n'
                    f'Avg Execution time per iteration: {np.average(np.array(execution_times) / np.array(iterations))}\n'
                    f'Helpful answers: {helpful_counter}/{len(question_set)}\n'
                    f'Avg Score: {total_score / len(question_set)}\n')
            return True
        except Exception as e:
            f.write(f'EXCEPTION: {str(e)}\n\n\n')
            return False


class TestOpacaLLM(unittest.IsolatedAsyncioTestCase):

    file_name = f'{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    container_ids = []

    def setUp(self):
        # Start the OPACA platform
        # The compose stack should have been started and exited previously...
        print("Setup OPACA platform")
        subprocess.run(["docker", "start", "opaca-platform-opaca-platform-userdb-1", "opaca-platform-opaca-platform-1"], check=True)
        time.sleep(10)       # Wait to let OPACA platform start

        print("Deploying OPACA containers for testing...")
        for name in test_containers:
            response = requests.post(opaca_url + "/containers", json={"image": {"imageName": f"rkader2811/{name}"}})
            self.container_ids.append(response.content.decode('ascii'))
            print(f"Deployed {name}!")

        print("Setup OPACA-LLM")
        self.server_process = subprocess.Popen(['python', '-m', 'src.server'], cwd=os.path.dirname(os.getcwd()))
        time.sleep(7)       # Needs to be long enough to let the server start
        try:
            session.post(llm_url + "/connect", json={"url": opaca_url, "user": "", "pwd": ""})
            session.put(llm_url + f'/{BACKEND}/config', json=BACKENDS[BACKEND])
        except Exception as e:
            print(f'Unable to establish a connection: {str(e)}')
            self.server_process.terminate()
            self.server_process.wait()
            raise RuntimeError(str(e))
        print("Setup finished")

    def tearDown(self):
        self.server_process.terminate()
        self.server_process.wait()
        print(f'Tear down OPACA-LLM')
        for container_id in self.container_ids:
            requests.delete(opaca_url + f'/containers/{container_id}', json={})
            print(f'Removed container {container_id}')
        subprocess.run(["docker", "stop", "opaca-platform-opaca-platform-userdb-1", "opaca-platform-opaca-platform-1"])
        print(f'Stopping OPACA platform')


    async def testDeployment(self):
        assert await benchmark_test(f'deployment-{self.file_name}', deployment_questions)

    async def testSimpleQuestionSet(self):
        assert await benchmark_test(f'simple-{self.file_name}', simple_questions)

    async def testComplexQuestionSet(self):
        assert await benchmark_test(f'complex-{self.file_name}', complex_questions)


if __name__ == "__main__":
    unittest.main()
