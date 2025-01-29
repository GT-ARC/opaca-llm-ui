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

question_set_local_smart_office = [
    {
        "input": "Please tell me the name of the room with id 1.",
        "output": "The answer should have successfully determined that the name of the room with id 1 is 'Experience Hub'."
    },
    {
        "input": "What is the highest room id in the system and what is the name belonging to that id?",
        "output": "The highest room id is 100 and the name of that room is 'VIP Room'."
    },
    {
        "input": "Turn on the lights in every bathroom.",
        "output": "The answer should indicate that the lights were turned on the rooms 'Bathroom Women', 'Bathroom Men', and 'Bathroom Uni'. The ids of those rooms are 9, 10, 11 respectively."
    },
    {
        "input": "Set the light intensity in the Focus space to 50%.",
        "output": "The answer should indicate, that the light intensity was set to 50%. In the given context, the answer might also indicate 50% as 0.5."
    },
    {
        "input": "Check if the Conference room is currently free and if it is, book it.",
        "output": "In the answer, the status of the conference occupation should be returned. If it is occupied, a booking procedure should not have happened. But if the conference room is free, it should also have already been booked."
    },
    {
        "input": "Please run a full system check. Summarize the results for me and for every damaged device, I want you to schedule a maintenance date on the 1st of February 2025",
        "output": "The answer should give an overview of the current status of each device in the system. Further, it should give a confirmation about the scheduling of maintenance dates on the 1st of February 2025."
    },
    {
        "input": "Please order me the snack with the longest name",
        "output": "The answer should tell the user, that the snack with the longest name is 'chocolate bar'. Further, the answer should confirm that a 'chocolate bar' has been ordered for the user."
    },
    {
        "input": "Please book me any available desk",
        "output": "The answer should include a specific desk id that was booked for the user."
    },
    {
        "input": "Please create an overview in the form of a table what contents are in which fridge spaces",
        "output": "The answer should include a formatted table in markdown. In this table, the fridge ids ranging from 60 to 66 should be listed alongside their contents."
    },
    {
        "input": "Please schedule cleaning days for the kitchen as follows: Begin with the 1st of February 2025 and then until the end of March, schedule a cleaning day every two weeks.",
        "output": "The answer should confirm a successful scheduling of cleaning days for the following days: 1st of February 2025, 15th of February 2025, 1st of March 2025, 15th of March 2025, and 29th of March 2025."
    },
    {
        "input": "Can you check if there is any milk left in my fridge? If not, add 'milk' to my grocery list.",
        "output": "The answer should indicate, that there was no milk found in the fridge and that the item 'milk' has been added to the list of groceries, or that 'milk' is already part of the grocery list."
    },
    {
        "input": "Check the sensor battery in each room and tell me in which rooms the sensor battery is less than 30%.",
        "output": "The answer needs to include a list of the room names, in which the sensor battery is below 30%. The room names should be given as their actual names and not called 'Room 1' or 'Room 2'."
    },
    {
        "input": "What is the biggest room?",
        "output": "There is no way to know which room is the biggest in the office. The answer should tell the user, that it is not possible to retrieve the information with the available tools."
    },
    {
        "input": "Check the device health of every device in the system. If any device appears to be damaged, try to restart that device and then check its status again. Only attempt a restart once.",
        "output": "The answer should include the status of every device in the system. In total, there are 5 devices in the system. For each device that was damaged, the answer should further indicate, that it has restarted that device and also give the updated status of that device. It might happen, that a restarted device is still damaged, but in context of correctness, this is okay as long as the answer states that it has restarted every damaged device."
    }
]

question_set_local_warehouse = [
    {
        "input": "Please get the total size of the warehouse. Given a monthly rent cost of 7.50$ per square meter, what would be the monthly rent for the entire warehouse?",
        "output": "The answer should tell the user, that the total size of the warehouse is 5000 square meters. The answer then should give value for the monthly rent, which would be 37,500$."
    },
    {
        "input": "Find out in which warehouse zone the item 'curtain' is and navigate the logistic robot 2 to that zone to pick up two sets of curtains.",
        "output": "The answer should tell the user, the curtains were located in 'zone-E'. It should then have sent specifically the logistic robot number 2 to the 'zone-E' and should have made it pick up exactly 2 sets of curtains."
    },
    {
        "input": "I want to buy a printer and also a new sink, where would I find them?",
        "output": "The answer should tell the user, that the printers are located in 'zone-C', while the sinks are located in 'zone-E'."
    },
    {
        "input": "Please find out the contact details for the warehouse and prepare a formal written letter, that I would like to seek a job opportunity as a logistics manager in that warehouse.",
        "output": "The answer should include the address of the warehouse, which is 'Industrial Street 1'. Additionally, it might include that the name of the warehouse is 'Super Awesome Warehouse', the owner's name is 'John Warehouse', and the email address of the warehouse is 'Warehouse@mail.com'. It then has to include a formal letter, addressing the wish to start working at that warehouse as a logistics manager."
    },
    {
        "input": "I want to order a new pair of green scissors and a pair of blue jeans.",
        "output": "The answer should confirm the creation of two orders, one which has as an item a pair of green scissors and the other one which has an item of a pair of blue jeans. The order ids should be provided as well"
    },
    {
        "input": "Please move every logistics robot to 'zone-A'.",
        "output": "The answer should confirm, that the logistics robots number 1, 2, and 3 were all moved to 'zone-A'."
    },
    {
        "input": "Where in the warehouse are the paints?",
        "output": "The answer should let the user know, that the warehouse currently does not have any paints or paint canister stored and therefore, no location should be named."
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

    async def testLocalSmartOffice(self):
        assert await benchmark_test(f'smart-office-{self.file_name}', question_set_local_smart_office)

    async def testLocalWarehouse(self):
        assert await benchmark_test(f'warehouse-{self.file_name}', question_set_local_warehouse)


if __name__ == "__main__":
    unittest.main()
