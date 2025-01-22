import datetime
import json
import os
import numpy as np
import subprocess
import time
import unittest
import requests
from langchain_openai import ChatOpenAI

from Backend.src.models import LLMAgent

BACKEND = "tool-llm-openai"             # Which backend is used

# ATTENTION this config object should match the config object within the selected method
CONFIG = {
    "model": "gpt-4o-mini",             # Which model is used
    "temperature": 0,
    "use_agent_names": True,
}

opaca_url = "http://10.42.6.107:8000"
llm_url = "http://localhost:3001"
query_url = f"http://localhost:3001/{BACKEND}/query"
session = requests.Session()

questions = [
    {
        "input": "What is the current weather condition in Berlin?",
        "output": "Answer should include a hint for the current day, the temperature, the general condition, the precipitation, and humidity."
    },
    {
        "input": "When is the next federal election in germany?",
        "output": "Answer should give an exact date of the next election."
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
    }
]

other_questions = [
    {
        "input": "I want you to give me the temperature data for each available sensor with an even id and give me the CO2 value for each sensor with an odd id.",
        "output": "The answer should include a lot of well structured sensor data. Make sure that the temperature data should only be given for sensors with an even id, while the CO2 value should only be given for sensors with an odd id."
    },
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
                  "of the expected information. Return a label: 'helpful' or 'unhelpful'.",
    input_variables=["question", "expected_answer", "response"],
    message_template="A user had the following question: {question}\n\n"
                     "The expected answer for this question: {expected_answer}\n\n"
                     "This was the generated response: {response}"
)


async def benchmark_test(file_name: str) -> bool:

    if not os.path.exists('test_runs'):
        os.makedirs('test_runs')

    total_time = .0
    iterations = []
    execution_times = []
    number_tools = 0

    with open(f'test_runs/{file_name}', 'a', encoding="utf-8") as f:
        try:
            for i, call in enumerate(questions):
                f.write(f'-------------- Question {i+1} --------------\n')
                cur_time = time.time()
                result = session.post(query_url, json={'user_query': call["input"], 'api_key': ""}).content
                run_time = time.time() - cur_time
                result = json.loads(result)
                judge_response = await judge_llm.ainvoke({"question": call["input"], "expected_answer": call["output"], "response": result["content"]})
                f.write(f'Question: {call["input"]}\n'
                        f'Expected Answer Reference: {call["output"]}\n'
                        f'Response: {result["content"]}\n'
                        f'Iterations: {result["iterations"]}\n'
                        f'Time: {result["execution_time"]}(Test side: {run_time})\n'
                        f'Tools called: {sum(len(message["tools"]) for message in result["agent_messages"])}\n'
                        f'Judge Response: {judge_response.content}\n\n\n')

                total_time += result["execution_time"]
                execution_times.append(result["execution_time"])
                iterations.append(result["iterations"])
                number_tools += sum(len(message["tools"]) for message in result["agent_messages"])

            f.write(f'-------------- Summary --------------\n')
            f.write(f'Used backend: {BACKEND}\n'
                    f'Used config: {CONFIG}\n'
                    f'Total Execution time: {total_time}\n'
                    f'Avg Execution time per iteration: {np.average(np.array(execution_times) / np.array(iterations))}\n')
            return True
        except Exception as e:
            f.write(f'EXCEPTION: {str(e)}\n\n\n')
            return False


class TestOpacaLLM(unittest.IsolatedAsyncioTestCase):

    file_name = f'{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

    def setUp(self):
        self.server_process = subprocess.Popen(['python', '-m', 'src.server'], cwd=os.path.dirname(os.getcwd()))
        time.sleep(1)
        session.post(llm_url + "/connect", json={"url": opaca_url, "user": "", "pwd": ""})
        session.put(llm_url + f'/{BACKEND}/config', json=CONFIG)

    def tearDown(self):
        self.server_process.terminate()
        self.server_process.wait()

    async def testBenchmark(self):
        assert await benchmark_test(self.file_name)


if __name__ == "__main__":
    unittest.main()
