# Tool LLM

In this method, the tool section of newer models will be used to let the models directly formulate tool calls. This method is only available for models, which support the generation of tools.

## Agents

### Tool Generator

Once a message has been received, the Tool Generator is tasked to output the next required tool call in its tool section. Generally, if the Tool Generator has not generated any tool calls, it is assumed no tool calls were necessary and the generated content will be redundant and can be ignored. The final output generation then takes place immediately after by the Output Generator.

The Tool Generator receives a formatted list of all available OPACA action, transformed into the function definition, [defined by OpenAI](https://platform.openai.com/docs/guides/function-calling). Due to limitations, it is only possible to provide up to 128 tools per call. If an OPACA environment with more than 128 actions is used in combination with the OPACA LLM, a warning is printed in the backend and the excessive tools will simply be ignored.

Models outputting tools are also able to formulate multiple tool calls at the same time, if those calls can be independently executed in parallel.

After the initial tool generation, a simple type fix is used to cast parameter values in their correct type. This is only available for the types _string_, _number_, _integer_, and _boolean_. This procedure will not throw any errors if a type cast was unsuccessful.

Once the Tool Generator has formulated a tool call and the types were checked and potentially fixed, the action information is extracted and used to invoke the OPACA action on the connected platform. The action names, parameters, and responses are each stored in an internal message history, which will be given to the Tool Evaluator and the Tool Generator during the next internal iteration. This internal history is disregarded, once the final output has been generated.

### Tool Evaluator

After the invocation of the generated OPACA action calls, the Tool Evaluator will receive the original user query, a list of invoked actions, a list of used parameters, and a list of received responses for each of the generated actions during the current user request.

The Tool Evaluator outputs a formatted JSON with the fields `decision` and `reason` to decide, whether the called tools so far are sufficient to answer the current user query. The `decision` field will be either `FINISHED` or `CONTINUE`. The `reason` field serves as a thinking output, making the Tool Evaluator explain its decision.

### Output Generator

The Output Generator is responsible for generating the final output to the user request. It receives the message history, the current user query, and the called tools including their results. Its output is directly streamed to the user via the UI.

If no tool calls were generated, the Output Generator will further receive the list of all available tools, while setting `tool_choice=None`, to prevent it from generating tool calls. If no tool calls were generated, it is assumed that the user query was asking about specific tool definitions, which the Output Generator then needs access to. If tool calls have been generated, the Output Generator then only serves as a summarization role.

## Configuration

The following values are **defaults**.

```
{
    "tool_gen_model": "gpt-4o-mini",
    "tool_eval_model": "gpt-4o-mini",
    "output_model": "gpt-4o-mini",
    "temperature": 0,
}
```

- `tool_gen_model`: The model name that will be used for tool generation. Also supports Llama models.
- `tool_eval_model`: The model name that will be used for tool evaluation. Also supports Llama models.
- `output_model`: The model name that will be used for output generation. Also supports Llama models.
- `temperature`: The temperature used for the given model.
