# Simple

This was the very first method to interact with the actual LLM. Compared to the other method it is very simple, which can be both a strong and a weak point.

The method consists of a single AI agent that's given the list of agents and their actions as part of it's initial system prompt (i.e. not using the "tools" parameter). It is then asked to output the tools to call and their parameters in a specific JSON format along with it's regular output. The output is searched for those JSON objects, triggering the respective tool call. This is repeated in a loop, until either there was an error with a tool call, or the user's goal has been reached.

Compared with the other methods, this one can have problems with more complex requests. Also, the way the output is parsed and evaluated can yield to tool-calls going undetected (if the LLM add "chatter" along with the actual tool call). It can also have problems with hallucinations in case no tools are present. But at the same time, this method is also (by far) the simplest and a good starting point for understanding the basic workings of the OPACA-LLM and as a baseline for benchmarks. Also, it is most flexible when it comes to non-tool-calling tasks (e.g. when asked to just recommend which actions to take, or generate pseudo-code for those actions).

## Variant: Simple-Tools

This basically works the same as the simple method, with a single LLM agent, but with the difference that instead of injecting the available tools in the system prompt and parsing the tool-calls from the result, it uses the "tools" parameter present in most modern LLMs. This does not have the problems with hallucinations or "chatter" interfering with the tools parsing, but restricts the method to LLMs that support tools (which most do, but not all).

## Configuration

* `model`: The LLM model to be used, either an OpenAI model, or a model hosted on a local vLLM instance; default: `"gpt-4o-mini"`
* `temperature`: The "temperature" of the LLM, how "creative" it is, between `0.0` and `2.0`; default: `1.0`
* `ask_policy`: Determines how much the LLM will ask for confirmation between executing actions (`0`: don't ask for confirmation; `1`: ask for confirmation for ambiguous actions and action chains; `2`: always ask for confirmation first); default: `0`