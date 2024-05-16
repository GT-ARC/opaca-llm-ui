import openai
import requests
import json

OPACA_URL = "http://localhost:8000"

client = openai.OpenAI()


def get_opaca_services():
    return requests.get(OPACA_URL + "/agents").text

def invoke_opaca_action(action, params):
    return requests.post(f"http://localhost:8000/invoke/{action}", json=params).json()


system = """
You suggest web services to fulfil a given purpose.
You present the result as pseudo-code, including temporary variables if needed.
You know some agents providing different actions that you can use. Do not assume any other services.
If those services are not sufficient to solve the problem, just say so.
First, show only the pseudo code. Later, if the user says "do it", and only then, you repeat the first service call of the previous pseudo code in this specific JSON format and nothing else (not even Markup):
{
  "agentId": <AGENT-ID>,
  "action": <ACTION-NAME>,
  "params": {
    <NAME>: <VALUE>,
    ...
  }
}
Following is the list of available services described in JSON, which can be called as webservices:   
""" + get_opaca_services()

messages = [
    {"role": "system", "content": system}
]


async def query(message: str) -> str:
    print("QUERY", message)
    messages.append({"role": "user", "content": message})
    completion = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages)
    response = completion.choices[0].message.content
    try:
        d = json.loads(response)
        result = invoke_opaca_action(d["action"], d["params"])
        response = f"The result of this step was: {repr(result)}"        
    except Exception as e:
        print("ERROR", e)
    messages.append({"role": "assistant", "content": response})
    return response


async def history():
    return messages


async def reset():
    print("RESET")
    global messages
    messages = [
        {"role": "system", "content": system}
    ]
