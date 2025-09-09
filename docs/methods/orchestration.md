# Overall Architecture

The backend uses a self-orchestrated multi-agent approach to divide and conquer user requests into smaller tasks and subtasks. 

![Mutli-Agent-Architecture](/docs/img/multi-agent.png)

The architecture is built with the following LLM-Agents: 

## Orchestration
(Only able to see agent summaries - not all the function definitions)
- **Orchestrator**: Returns a structured json object with the tasks and OPACA agents that should solve them

## Execution Trio
(Able to see the functions assigned to the OPACA agent) - Dynamically created based on the containers within OPACA

- **Agent Planner**: Creates an execution plan to solve the task that was given by the orchestrator (also suggests function calls) - as structured json object
- **Worker Agent**: Makes the function calls to solve the given subtask
- **Agent Evaluator**: Evaluates whether a subtask was finished successfully - Only able to answer in 1 word (`FINISHED` or `REITERATE`)

## Evaluation Duo
- **Overall Evaluator**: Evaluates whether all tasks from the Orchestrator are finished and whether all the necessary information to answer the user request is collected - Only able to answer in 1 word (`FINISHED` or `REITERATE`)
- **Iteration Advisor**: Only triggered if the Overall Evaluator chooses `REITERATE` - Generates a structured json object summarising the execution and giving improvement suggestions for the next iteration. (The Iteration Advisor is able to deny the reiteration request)

## Output Generation
- **Output Generator**: Gets information on the executed iterations, executed tool calls and the user request to generate the final answer. The answer is then streamed as output for the front-end

# Further Considerations

## Follow-up questions
The orchestrator is able to ask a follow-up question. The orchestrator also has access to the chat history to see if relevant information is there as well. The Iteration Advisor has the option to request a follow up question that the orchestrator can then ask. 

## General Agent
We ingest a placeholder agent into the list of worker trios to quickly retrieve basic information. 
If the user asks "How can you assist me" for example, this agent would immediately return a static response with all the live OPACA agents as well as some basic information on OPACA. 

Further arbitrary agents could also be ingested into the backend to make answering certain questions faster and easier.

# File structure

- `backend.py`: Contains the core logic of the orchestration method. Further handles connection and routing.
- `agents.py`: Defines agent specific properties such as message structure or response schema.
- `models.py`: Defines the Pydantic models for data structures used specifically in the multi-agent system (tasks, plans, results, etc.).
- `prompts.py`: Contains the system prompts for each agent type that define their behaviour and responsibilities.