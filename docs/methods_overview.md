# Methods

The OPACA LLM implements different methods/strategies to fulfill user queries. Each of these methods/strategies have their own advantages and disadvantages. To give a brief overview of the implemented methods, the  following list is given to provide a brief overview of each method/strategy and their general idea and functionality.

## Tool LLM

- Transforms OPACA actions into tool definitions, given to an LLM within a special input field
- 2 LLM Agents:
  - Tool Generator: Generates tool calls in a special output field in a properly formatted JSON. If no tools are necessary, will answer the user directly.
  - Tool Evaluator: Receives the responses of each generated tool call and summarizes the events in natural language. Also decides whether another iteration is necessary. Provides its summary directly to the user.
- Only available for models supporting tool calling
- Can formulate more than one action call per iteration

[read more...](methods/tool_llm.md)

## Simple

- Only 1 agent per iteration
- If agent outputs JSON, assume an action call was formatted. Otherwise, return output to user. 

[read more...](methods/simple.md)

## Orchestration

- Two layers: outer Orchestration-layer, and inner "execution trios" for each OPACA agent
- Orchestrator only knows summaries of different agents, selects the execution-trio that best fits the request
- Execution-trio has full knowledge of the agent's actions, executes them, return the result to the outer layer
- More complex and potentially slower, but scales better for high number of agents and actions

[read more...](methods/orchestration.md)


## Performance

See [Benchmarks](benchmarks.md) for some performance evaluations.
