# Methods

The OPACA LLM implements different methods/strategies to fulfill user queries. Each of these methods/strategies have their own advantages and disadvantages. To give a brief overview of the implemented methods, the  following list is given to provide a brief overview of each method/strategy and their general idea and functionality.

## Tool LLM

- Transforms OPACA actions into tool definitions, given to an LLM within a special input field
- 2 LLM Agents:
  - Tool Generator: Generates tool calls in a special output field in a properly formatted JSON. If no tools are necessary, will answer the user directly.
  - Tool Evaluator: Receives the responses of each generated tool call and summarizes the events in natural language. Also decides whether another iteration is necessary. Provides its summary directly to the user.
- Only available for models supporting tool calling
- Can formulate more than one action call per iteration

## Rest-GPT

- Based on the paper [RestGPT](https://github.com/Yifan-Song793/RestGPT)
- 4 LLM Agents:
  - Planner: Outputs the next concrete step in natural language to solve the user query.
  - Action Selector: Based on the Planner's step, generates an Action call consisting of an action name and the action parameters.
  - Caller: After invoking the generated action call, summarizes the results based on the associated action definition.
  - Evaluator: Decides whether another iteration is necessary or generates the response to the user.
- Actions are given within the system prompt in a formatted style
- Only one action call per iteration

## Simple

- Only 1 agent per iteration
- If agent outputs JSON, assume an action call was formatted. Otherwise, return output to user. 
