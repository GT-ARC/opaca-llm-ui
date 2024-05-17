import openai
import requests
import json

# TODO move all opaca client stuff to separate module to be used by all backends

OPACA_URL = "http://localhost:8000"
TOKEN = None


def headers():
    return {'Authorization': f'Bearer {TOKEN}'} if TOKEN else None

def get_token(user, pwd):
    global TOKEN
    TOKEN = None
    if user and pwd:
        res = requests.post(f"{OPACA_URL}/login", json={"username": user, "password": pwd})
        res.raise_for_status()
        TOKEN = res.text

def get_opaca_services():
    try:
        res = requests.get(f"{OPACA_URL}/agents", headers=headers())
        res.raise_for_status()
        return res.text
    except Exception as e:
        print("COULD NOT CONNECT", e)
        return "(No Services. Failed to connect to OPACA Runtime.)"

def invoke_opaca_action(action, params):
    res = requests.post(f"{OPACA_URL}/invoke/{action}", json=params, headers=headers())
    res.raise_for_status()
    return res.json()



client = openai.OpenAI()

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

messages = [{"role": "system", "content": system + get_opaca_services()}]

async def connect(url: str, user: str, pwd: str):
    print("CONNECT", repr(url), user, pwd)
    global OPACA_URL
    OPACA_URL = url

    try:
        get_token(user, pwd)
        requests.get(f"{OPACA_URL}/info", headers=headers()).raise_for_status()
        messages[:1] = [{"role": "system", "content": system + get_opaca_services()}]
        return True
    except Exception as e:
        print("COULD NOT CONNECT", e)
        return False


async def query(message: str) -> str:
    print("QUERY", message)
    messages.append({"role": "user", "content": message})
    completion = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages)
    response = completion.choices[0].message.content
    print("RESPONSE:", repr(response))
    try:
        d = json.loads(response)
        result = invoke_opaca_action(d["action"], d["params"])
        response = f"I just called {d['action']} with {d['params']}. The result of this step was: {repr(result)}"
    except Exception as e:
        print("NOT JSON", e)
    messages.append({"role": "assistant", "content": response})
    return response


async def history():
    return messages


async def reset():
    print("RESET")
    messages[:] = [{"role": "system", "content": system + get_opaca_services()}]
