import datetime
import json
import os
import subprocess
import time
import unittest
import requests

opaca_url = "http://localhost:8000"
llm_url = "http://localhost:3001"
query_url = "http://localhost:3001/rest-gpt/query"

calls = {
    "single": [
        "What is the current temperature in room 1?",
        "Get me a list of the desks in the office.",
        "Open shelf 3 for me please."
    ],
    "service": [
        "What services do you know?",
        "What parameters are required to call \"AddGroceries\"?",
        "What does the action \"GetUserBookings\" do?"
    ],
    "missing_svc": [
        "What is the current weather in australia?",
        "Order a pair of white shoes from Amazon.",
        "Create a new spotify playlist titled \"Best Hits\"."
    ],
    "stupid": [
        "What am I currently thinking of?",
        "Turn around.",
        "What are you currently listening to?"
    ],
    "spelling": [
        "Waht is the crrt tmperatre?",
        "Gt temprtrue 1.",
        "Lst of grceis pls."
    ],
    "fuzzing": [
        "itrohaw8r934ahih9gy923n20awh3246",
        """<div id="${id}" class="d-flex flex-row justify-content-start mb-4">
            <img src=/src/assets/Icons/ai.png alt="AI" class="chaticon">
            <div class="p-2 ms-3 small mb-0 chatbubble" style="background-color: #39c0ed33;">
                ${marked.parse(text)}
            </div>
        </div>""",
        "¦DË\"î{ÈºÃË►Å ãíºJ↓Y╝|ØãÆ#┌\""
    ],
    "medium": [
        "Open the shelf with the plates.",
        "Get me the temperature, humidity, and Co2 level for room 1.",
        "Book me a free desk in the office."
    ],
    "hard": [
        "Can you tell me the current temperature, then open the shelf with the plates, close it and finally add one \
        Banana to my Grocery list with the expiration date 2024-07-01 with the category \"fruit\"?",
        "Can you check for all desks in the office whether their are free or occupied?",
        "Tell me the average Co2 levels of all available rooms."
    ],
    "missing_params": [
        "Add bananas to my grocery list.",
        "Open the shelf",
        "Tell me the temperature"
    ]
}


def exec_test(test_key: str, test_name: str, file_name: str) -> bool:
    if not os.path.exists('test_runs'):
        os.makedirs('test_runs')
    with open(f'test_runs/{file_name}', 'a', encoding="utf-8") as f:
        f.write(f'-------------- {test_name} --------------\n')
        try:
            for call in calls[test_key]:
                result = requests.post(query_url, json={'user_query': call, 'debug': True}).content
                result = json.loads(result)
                f.write(f'{result["debug"]}\n')
            f.write('\n\n')
            return True
        except Exception as e:
            f.write(f'EXCEPTION: {str(e)}\n\n\n')
            return False


class TestOpacaLLM(unittest.TestCase):

    file_name = f'{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

    def setUp(self):
        self.server_process = subprocess.Popen(['python', '-m', 'Backend.server'])
        time.sleep(1)
        requests.post(llm_url + "/connect", json={"url": opaca_url, "user": "", "pwd": ""})

    def tearDown(self):
        self.server_process.terminate()
        self.server_process.wait()

    def testSingleCalls(self):
        assert exec_test('single', 'Single Execution Test', self.file_name)

    def testServiceCalls(self):
        assert exec_test('service', 'Service Questions Test', self.file_name)

    def testMissingServices(self):
        assert exec_test('missing_svc', "Missing Services Test", self.file_name)

    def testStupid(self):
        assert exec_test('stupid', 'Stupid Questions Test', self.file_name)

    def testSpellingMistakes(self):
        assert exec_test('spelling', 'Spelling Mistakes Test', self.file_name)

    def testFuzzing(self):
        assert exec_test('fuzzing', 'Fuzzing Test', self.file_name)

    def testMediumComplex(self):
        assert exec_test('medium', 'Medium Difficulty Test', self.file_name)

    def testVeryComplex(self):
        assert exec_test('hard', 'Hard Difficulty Test', self.file_name)

    def testMissingParams(self):
        assert exec_test('missing_params', 'Missing Parameter Test', self.file_name)


if __name__ == "__main__":
    unittest.main()
