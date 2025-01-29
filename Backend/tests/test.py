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

BACKEND = "tool-llm-openai"             # Which backend is used

tool_llm_config = {
    "model": "gpt-4o-mini",             # Which model is used
    "temperature": 0,
    "use_agent_names": True,
}

rest_gpt_config = {
    "slim_prompts": {                       # Use slim prompts -> cheaper
        "planner": True,
        "action_selector": True,
        "evaluator": False
    },
    "examples": {                           # How many examples are used per agent
        "planner": False,
        "action_selector": True,
        "caller": True,
        "evaluator": True
    },
    "use_agent_names": True,
    "temperature": 0,  # Temperature for models
    "gpt-model": "gpt-4o-mini",
}

# ATTENTION this config object should match the config object within the selected method
CONFIG = tool_llm_config

opaca_url = "http://localhost:8000"
llm_url = "http://localhost:3001"
query_url = f"http://localhost:3001/{BACKEND}/query"
session = requests.Session()

question_set_deployment = [
    {
        "input": "What is the current weather condition in Berlin?",
        "output": "Answer should include a hint for the current day, the temperature, the general condition, the precipitation, and humidity."
    },
    {
        "input": "When is the next federal election in germany?",
        "output": "Answer should give an exact date of the next election, which is the 23rd of February 2025."
    },
    {
        "input": "Give me the contact details about someone from go-KI who knows about LLM.",
        "output": "The answer should include the name of a person familiar with the LLM topic and include its phone number and email address."
    },
    {
        "input": "Get me the current stock prices for Amazon, Apple and Microsoft. Also try to find out when these stocks had their all time high.",
        "output": "The answer should include the current stock prices of all the three companies: Amazon, Apple, and Microsoft. Further, for each of the stocks, the answer should include the all time high value and the date when this value was reached."
    },
    {
        "input": "Please summarize my latest 5 emails",
        "output": "The answer should include an overview of exactly the last 5 emails."
    },
    {
        "input": "I want you to give me the temperature data for each available sensor with an even id and give me the CO2 value for each sensor with an odd id.",
        "output": "The answer should include a lot of well structured sensor data. Make sure that the temperature data should only be given for sensors with an even id, while the CO2 value should only be given for sensors with an odd id."
    },
    {
        "input": "What is the Co2 value in the kitchen, and is that value considered normal? What ranges are considered dangerous?",
        "output": "The answer should include the current Co2 value in the kitchen. The answer should also tell the user whether the received value lies in a normal range of Co2. Finally the answer should give an explanation including a range of values for Co2 levels that are considered dangerous."
    },
    {
        "input": "Please plot the saved temperature data for the kitchen and show the plot to me.",
        "output": "The answer should include an image file in markdown language, which is linking to the generated image file. The image should be directly shown within the message, meaning it should start with an exclamation mark (!). The answer should make it clear, that the displayed data concerns the captured temperature data of the kitchen room"
    }
]


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
                f.write(f'-------------- Question {i+1} --------------\n')
                cur_time = time.time()
                result = session.post(query_url, json={'user_query': call["input"], 'api_key': ""}).content
                run_time = time.time() - cur_time
                result = json.loads(result)
                judge_response = judge_llm.invoke({"question": call["input"], "expected_answer": call["output"], "response": result["content"]}, response_format=Metric)
                metric = judge_response.content
                f.write(f'Question: {call["input"]}\n'
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

                if metric.quality == "helpful":
                    helpful_counter += 1
                total_score += metric.score
                total_time += result["execution_time"]
                execution_times.append(result["execution_time"])
                iterations.append(result["iterations"])
                number_tools += sum(len(message["tools"]) for message in result["agent_messages"])

                # Reset the message history
                session.post(llm_url + "/reset", json={})
                return True

            f.write(f'-------------- Summary --------------\n')
            f.write(f'Used backend: {BACKEND}\n'
                    f'Used config: {CONFIG}\n'
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

    def setUp(self):
        print("In setup")
        self.server_process = subprocess.Popen(['python', '-m', 'src.server'], cwd=os.path.dirname(os.getcwd()))
        time.sleep(5)       # Needs to be long enough to let the server start
        try:
            session.post(llm_url + "/connect", json={"url": opaca_url, "user": "", "pwd": ""})
            session.put(llm_url + f'/{BACKEND}/config', json=CONFIG)
        except Exception as e:
            print(f'Unable to establish a connection: {str(e)}')
            self.server_process.terminate()
            self.server_process.wait()
            raise RuntimeError(str(e))
        print("Setup finished")

    def tearDown(self):
        self.server_process.terminate()
        self.server_process.wait()

    async def testDeployment(self):
        assert await benchmark_test(f'deployment-{self.file_name}', question_set_deployment)

    async def testSimpleQuestionSet(self):
        assert await benchmark_test(f'simple-{self.file_name}', simple_questions)

    async def testComplexQuestionSet(self):
        assert await benchmark_test(f'complex-{self.file_name}', complex_questions)


if __name__ == "__main__":
    unittest.main()
