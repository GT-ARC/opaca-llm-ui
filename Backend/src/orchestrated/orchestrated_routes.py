import json
import logging
import time
import traceback
from collections import defaultdict
from typing import Dict, Any, List, Tuple
import asyncio

from .prompts import (
    OUTPUT_GENERATOR_PROMPT, BACKGROUND_INFO, GENERAL_CAPABILITIES_RESPONSE, GENERAL_AGENT_DESC
)
from ..abstract_method import AbstractMethod
from ..models import QueryResponse, SessionData, AgentMessage, ConfigParameter, ChatMessage, Chat, ToolCall
from .agents import (
    OrchestratorAgent,
    WorkerAgent,
    AgentEvaluator,
    OverallEvaluator,
    IterationAdvisor,
    AgentPlanner, get_current_time
)
from .models import AgentResult, AgentTask
from ..utils import openapi_to_functions


class SelfOrchestratedMethod(AbstractMethod):
    NAME = "self-orchestrated"

    def __init__(self, session, websocket=None):
        super().__init__(session, websocket)
        self.logger = logging.getLogger(__name__)

    @classmethod
    def config_schema(cls) -> Dict[str, ConfigParameter]:
        return {
            # Which model to use for the orchestrator and worker agents
            "orchestrator_model": cls.make_llm_config_param(name="Orchestrator", description="For delegating tasks"),
            "worker_model": cls.make_llm_config_param(name="Workers", description="For selecting tools"),
            "evaluator_model": cls.make_llm_config_param(name="Evaluators", description="For evaluating tool results"),
            "generator_model": cls.make_llm_config_param(name="Output", description="For generating the final response"),
            "temperature": ConfigParameter(
                name="Temperature",
                description="Temperature for the orchestrator and worker agents",
                type="number",
                required=True, 
                default=0.0, 
                minimum=0.0, 
                maximum=2.0,
                step=0.1,
            ),
            "max_rounds": ConfigParameter(
                name="Max Rounds",
                description="Maximum number of orchestration and worker rounds",
                type="integer",
                required=True, 
                default=5, 
                minimum=1, 
                maximum=10,
                step=1,
            ),
            "max_iterations": ConfigParameter(
                name="Max Iterations",
                description="Maximum number of re-iterations (retries after failed attempts)",
                type="integer",
                required=True, 
                default=3, 
                minimum=1, 
                maximum=10,
                step=1,
            ),
            "use_agent_planner": ConfigParameter(
                name="Use Agent Planner?",
                description="Whether to use the planner agent or not",
                type="boolean",
                required=True, 
                default=True,
            ),
            "use_agent_evaluator": ConfigParameter(
                name="Use Agent Evaluator?",
                description="Whether to use the agent evaluator or not",
                type="boolean",
                required=True, 
                default=False,
            ),
        }

    async def _execute_round(
        self,
        round_tasks: List[AgentTask],
        worker_agents: Dict[str, WorkerAgent],
        config: Dict[str, Any],
        all_results: List[AgentResult],
        agent_summaries: Dict[str, Any],
        agent_messages: List[AgentMessage] = None,
        num_tools: int = 1,
    ) -> Tuple[List[AgentResult], List[AgentMessage]]:
        """Execute a single round of tasks in parallel when possible"""
        # Create agent evaluator
        agent_evaluator = AgentEvaluator() if config.get("use_agent_evaluator", True) else None
        tool_counter = num_tools
        tool_counter_lock = asyncio.Lock()

        async def execute_round_task(worker_agent, subtask, orchestrator_context, round_context,
                                     round_num):
            """Executes a single subtask with a WorkerAgent"""
            current_task = subtask.task
            nonlocal tool_counter

            # Build comprehensive context that includes:
            # 1. Previous orchestrator rounds
            # 2. Previous planner rounds
            # 3. Current round context
            task_context = []

            if orchestrator_context:
                task_context.append(orchestrator_context)
            if round_context:
                task_context.append(round_context)

            # Combine all contexts with proper separation
            if task_context:
                current_task = f"{current_task}\n\n{''.join(task_context)}"

            self.logger.debug(f"AgentPlanner executing subtask in round {round_num}: {current_task}")

            # Generate a concrete opaca action call for the given subtask
            worker_message = await self.call_llm(
                model=config["worker_model"],
                agent="WorkerAgent",
                system_prompt=worker_agent.system_prompt(),
                messages=worker_agent.messages(subtask),
                temperature=config["temperature"],
                tools=worker_agent.tools
            )

            # Update the tool ids
            async with tool_counter_lock:
                for tool in worker_message.tools:
                    tool.id = tool_counter
                    tool_counter += 1

            # Invoke the action on the connected opaca platform
            agent_result = await worker_agent.invoke_tools(current_task, worker_message)

            # Create agent message and stream content via websocket
            agent_messages.append(worker_message)
            await self.send_to_websocket(agent_message=worker_message)

            return agent_result

        async def execute_single_task(task: AgentTask):
            """Executes a single task"""
            # Get the agent name and task description that were generated for the task
            agent = worker_agents[task.agent_name]
            task_str = task.task if isinstance(task, AgentTask) else task

            # Keep track of the tool ids
            nonlocal tool_counter
            
            # Log that the task is being executed
            self.logger.info(f"Executing task for {task.agent_name}: {task_str}")
            
            # Create planner if enabled
            if config.get("use_agent_planner", True) and task.agent_name != "GeneralAgent":
                await self.send_to_websocket("AgentPlanner", f"Planning function calls for {task.agent_name}'s task: {task_str} \n\n")
                planner = AgentPlanner(
                    agent_name=task.agent_name,
                    tools=agent.tools,
                    worker_agent=agent,
                    config=config
                )
                
                # Create plan first, passing previous results
                planner_message = await self.call_llm(
                    model=config["orchestrator_model"],
                    agent="AgentPlanner",
                    system_prompt=planner.system_prompt(),
                    messages=planner.messages(task, previous_results=all_results),
                    temperature=config["temperature"],
                    tools=planner.tools,
                    tool_choice="none",
                    response_format=planner.schema,
                )
                agent_messages.append(planner_message)
                plan = planner_message.formatted_output

                # Send plan via websocket if needed
                await self.send_to_websocket(agent_message=planner_message)

                # If no plan was created, return empty AgentResult
                if not plan:
                    return AgentResult(
                        agent_name=task.agent_name,
                        task=task_str,
                        output="There was an error during the generation of an agent plan!",
                        tool_calls=[],
                    )
            
                await self.send_to_websocket("WorkerAgent", f"Executing function calls.\n\n")

                # Initialize results storage
                ex_results = []
                ex_tool_calls = []
                combined_output = []

                # Group tasks by round
                tasks_by_round = {}
                for subtask in plan.tasks:
                    tasks_by_round.setdefault(subtask.round, []).append(subtask)

                # Execute rounds sequentially
                for round_num in sorted(tasks_by_round.keys()):
                    self.logger.info(f"AgentPlanner executing round {round_num}")
                    current_tasks = tasks_by_round[round_num]

                    # Add context from previous planner rounds if needed
                    round_context = ""
                    if round_num > 1 and ex_results:
                        round_context = "\n\nPrevious planner round results:\n"
                        for prev_result in ex_results:
                            round_context += f"\nTask: {prev_result.task}\n"
                            round_context += f"Output: {prev_result.output}\n"
                            if any(tc.results for tc in prev_result.tool_calls):
                                round_context += f"Tool Results:\n"
                                for tc in prev_result.tool_calls:
                                    round_context += f"- {tc.name}: {tc.result}\n"

                    # Executes tasks in the same round in parallel
                    round_results = await asyncio.gather(*[execute_round_task(planner.worker_agent, subtask, planner.get_orchestrator_context(all_results), round_context, round_num) for subtask in current_tasks])

                    # Process round results
                    for result in round_results:
                        ex_results.append(result)
                        ex_tool_calls.extend(result.tool_calls)
                        combined_output.append(result.output)

                # Create final combined result with clear round separation
                final_output = "\n\n".join(combined_output)
                result = AgentResult(
                    agent_name=planner.worker_agent.agent_name,  # Use worker agent's name for proper attribution
                    task=task_str,  # Use the original task string
                    output=final_output,
                    tool_calls=ex_tool_calls,
                )
            else:
                await self.send_to_websocket("WorkerAgent", f"Executing function calls.\n\n")

                # Execute task directly
                if agent.agent_name == "GeneralAgent":
                    # The general agent returns a pre-defined response
                    predefined_response = get_current_time() + BACKGROUND_INFO + GENERAL_CAPABILITIES_RESPONSE.format(
                                            agent_capabilities=json.dumps(agent_summaries, indent=2))
                    worker_message = AgentMessage(
                        agent="WorkerAgent",
                        content="Called GeneralAgent!",
                    )
                    result = AgentResult(
                        agent_name="GeneralAgent",
                        task=task_str,
                        output="Retrieved system capabilities",  # Keep output minimal since data is in tool result
                        tool_calls=[ToolCall(id=-1, name="GetCapabilities", args={}, result=predefined_response)],
                    )
                else:
                    # Generate a concrete tool call by the worker agent with its tools
                    worker_message = await self.call_llm(
                        model=config["worker_model"],
                        agent="WorkerAgent",
                        system_prompt=agent.system_prompt(),
                        messages=agent.messages(task),
                        temperature=config["temperature"],
                        tools=agent.tools,
                    )

                    # Update the tool ids
                    async with tool_counter_lock:
                        for tool in worker_message.tools:
                            tool.id = tool_counter
                            tool_counter += 1

                    # Invoke the tool call on the connected opaca platform
                    result = await agent.invoke_tools(task.task, worker_message)
                    agent_messages.append(worker_message)
                
                # Send tool calls and results via websocket or generic GeneralAgent message
                await self.send_to_websocket(agent_message=worker_message)

            evaluation = task.agent_name != "GeneralAgent"

            if agent_evaluator and evaluation:
                # Now evaluate the result after we have it
                await self.send_to_websocket("AgentEvaluator", f"Evaluating {task.agent_name}'s task completion...\n\n")

                # If manual evaluation passes, run the AgentEvaluator
                if not agent_evaluator.evaluate_results(result):
                    evaluation_message = await self.call_llm(
                        model=config["evaluator_model"],
                        agent="AgentEvaluator",
                        system_prompt=agent_evaluator.system_prompt(),
                        messages=agent_evaluator.messages(task_str, result),
                        temperature=config["temperature"],
                        response_format=agent_evaluator.schema,
                    )
                    agent_messages.append(evaluation_message)
                    evaluation = evaluation_message.formatted_output.reiterate
            
                    # Send evaluation results via websocket
                    await self.send_to_websocket(agent_message=evaluation_message)

                else:
                    await self.send_to_websocket("AgentEvaluator", f"Evaluation result for {task.agent_name}: {evaluation}")
            
            # If evaluation indicates we need to retry, do so
            if evaluation:
                # Update task for retry
                retry_task = f"""# Evaluation 
                
The Evaluator of your task has indicated that there is crucial information missing to solve the task.. 

# Your Task: 

{task_str}

# Your previous output: 

{result.output}

# Your Previous tool calls: 

{[tc.model_dump_json() for tc in result.tool_calls]}

# YOUR GOAL:

Now, using the tools available to you and the previous results, continue with your original task and retrieve all the information necessary to complete and solve the task!"""

                await self.send_to_websocket("WorkerAgent", f"Retrying task...\n\n")
                
                # Execute retry
                worker_message = await self.call_llm(
                    model=config["worker_model"],
                    agent="WorkerAgent",
                    system_prompt=agent.system_prompt(),
                    messages=agent.messages(retry_task),
                    temperature=config["temperature"],
                    tools=agent.tools
                )

                # Update the tool ids
                async with tool_counter_lock:
                    for tool in worker_message.tools:
                        tool.id = tool_counter
                        tool_counter += 1

                result = await agent.invoke_tools(task.task, worker_message)
                agent_messages.append(worker_message)
                
                # Send only tool calls and results via websocket
                await self.send_to_websocket(agent_message=worker_message)
            
            return result

        # Execute all tasks in parallel using asyncio.gather
        results = await asyncio.gather(*[execute_single_task(task) for task in round_tasks])
        
        return results, agent_messages
    
    async def query_stream(self, message: str, chat: Chat) -> QueryResponse:
        """Process a user message using multiple agents and stream intermediate results"""

        # Initialize response
        response = QueryResponse(query=message)
        # Track overall execution time
        overall_start_time = time.time()

        try:
            # Get base config and merge with model config
            config = self.session.config.get(self.NAME, self.default_config())
            
            # Send initial waiting message
            await self.send_to_websocket(agent="preparing", message="Initializing the OPACA AI Agents")
            
            # Get simplified agent summaries for the orchestrator
            agent_details = {
                agent["agentId"]: {
                    "description": agent["description"],
                    "functions": [action["name"] for action in agent["actions"]]
                }
                for agent in await self.session.opaca_client.get_actions()
            }

            # Add GeneralAgent description
            agent_details["GeneralAgent"] = {"description": GENERAL_AGENT_DESC, "functions": ["GeneralAgent--getGeneralCapabilities"]}

            # Create tools from agent details
            orchestrator_tools = self.get_agents_as_tools(agent_details)
            
            # Initialize Orchestrator
            orchestrator = OrchestratorAgent(
                agent_summaries=agent_details,
                chat_history=chat.messages,  # Pass chat history to orchestrator
                tools=orchestrator_tools,
            )
            
            # Initialize evaluator and iteration advisor
            overall_evaluator = OverallEvaluator()
            iteration_advisor = IterationAdvisor()
            
            # Initialize worker agents
            worker_agents = {
                "GeneralAgent": WorkerAgent("GeneralAgent", "", [], None),
            }
            
            all_results = []
            rounds = 0
            
            while rounds < config["max_rounds"]:
                # Get execution plan from orchestrator
                await self.send_to_websocket("Orchestrator", "Creating detailed orchestration plan...\n\n")
                
                # Create orchestration plan
                orchestrator_message = await self.call_llm(
                    model=config["orchestrator_model"],
                    agent="Orchestrator",
                    system_prompt=orchestrator.system_prompt(),
                    messages=orchestrator.messages(message),
                    temperature=config["temperature"],
                    tools=orchestrator.tools,
                    tool_choice='none',
                    response_format=orchestrator.schema,
                )

                # Extract pre-formatted Orchestrator Plan
                plan = orchestrator_message.formatted_output
                response.agent_messages.append(orchestrator_message)

                # If the plan was not formatted properly, let the user know and ask for a retry
                if not plan:
                    response.content = ("I am sorry, but I was unable to generate a plan for your problem. Please "
                                        "try to reformulate your request!")
                    response.error = "Orchestrator was unable to generate a well-formatted plan!"
                    response.execution_time = time.time() - overall_start_time
                    return response
                
                # Then send the tasks
                await self.send_to_websocket(agent_message=orchestrator_message, message=f"Created execution plan with {len(plan.tasks)} tasks:\n{json.dumps([task.model_dump() for task in plan.tasks], indent=2)}\n\n")
                
                # Mark planning phase complete
                await self.send_to_websocket("Orchestrator", "Execution plan created ✓\n\n")
                
                # Iterate through every generated plan and add needed agents as worker agents
                for task in plan.tasks:
                    # Match the generated agent name with all existing agents
                    try:
                        task.agent_name = agent_name = next(_name for _name in agent_details.keys() if _name in task.agent_name)
                    except StopIteration:
                        # If the generated agent name is invalid, assign the general agent to it
                        task.task = (f"You have been given a task which was assigned to the agent {task.agent_name}. "
                                     f"This agent does not exist however. Check if the task could be solved by the "
                                     f"current environment. This was the original task:\n\n{task.task}")
                        task.agent_name = agent_name = "GeneralAgent"

                    if agent_name not in worker_agents:
                        agent_data = agent_details[agent_name]["description"]
                        
                        # Get functions from platform
                        agent_tools = await self.session.opaca_client.get_actions_openapi(inline_refs=True)
                        agent_tools, errors = openapi_to_functions(agent_tools, agent=agent_name, strict=True)
                        if errors:
                            self.logger.warning(errors)
                        
                        # Create worker agents for each unique agent in the plan
                        worker_agents[agent_name] = WorkerAgent(
                            agent_name=agent_name,
                            summary=agent_data,
                            tools=agent_tools,
                            session_client=self.session.opaca_client,
                        )
                
                # Group tasks by round
                tasks_by_round = {}
                for task in plan.tasks:
                    tasks_by_round.setdefault(task.round, []).append(task)  # Use task directly since it's already an AgentTask
                
                # Execute each round
                for round_num in sorted(tasks_by_round.keys()):
                    await self.send_to_websocket("Orchestrator", f"Starting execution round {round_num}\n\n")
                    
                    round_results, agent_messages = await self._execute_round(
                        tasks_by_round[round_num],
                        worker_agents,
                        config,
                        all_results,
                        agent_details,
                        response.agent_messages,
                        sum(len(message.tools) for message in response.agent_messages) + 1,
                    )
                    
                    all_results.extend(round_results)

                await self.send_to_websocket("OverallEvaluator", "Overall evaluation...\n\n")

                # Evaluate overall progress
                if not (evaluation := overall_evaluator.evaluate_results(all_results)):
                    evaluation_message = await self.call_llm(
                        model=config["evaluator_model"],
                        agent="OverallEvaluator",
                        system_prompt=overall_evaluator.system_prompt(),
                        messages=overall_evaluator.messages(message, all_results),
                        temperature=config["temperature"],
                        response_format=overall_evaluator.schema,
                    )
                    evaluation = evaluation_message.formatted_output.reiterate
                    response.agent_messages.append(evaluation_message)
                    await self.send_to_websocket(agent_message=evaluation_message)
                else:
                    await self.send_to_websocket("OverallEvaluator", f"Overall evaluation result: {evaluation}\n\nOverall evaluation complete ✓")
                            
                if evaluation:
                    # Get iteration advice before continuing
                    await self.send_to_websocket("IterationAdvisor", "Analyzing results and preparing advice for next iteration...\n\n")

                    advisor_message = await self.call_llm(
                        model=config["orchestrator_model"],
                        agent="IterationAdvisor",
                        system_prompt=iteration_advisor.system_prompt(),
                        messages=iteration_advisor.messages(message, all_results),
                        temperature=config["temperature"],
                        response_format=iteration_advisor.schema
                    )
                    advice = advisor_message.formatted_output
                    response.agent_messages.append(advisor_message)

                    await self.send_to_websocket(agent_message=advisor_message)

                    # If no advice context was successfully generated, assume that the final response can be generated
                    if not advice:
                        await self.send_to_websocket("IterationAdvisor", "Tasks completed successfully. Proceeding to final output.")
                        break

                    # Handle follow-up questions from iteration advisor
                    if advice.needs_follow_up and advice.follow_up_question:
                        response.content = advice.follow_up_question
                        response.execution_time = time.time() - overall_start_time
                        return response

                    # If advisor suggests not to retry, proceed to output generation
                    if not advice.should_retry:
                        await self.send_to_websocket("IterationAdvisor", "Tasks completed successfully. Proceeding to final output with the following summary:\n\n" + advice.context_summary)
                        break
                    
                    # Add the advice to the message for the next iteration
                    message = f"""Original request: {message}

Previous iteration summary: {advice.context_summary}

Issues identified:
{chr(10).join(f'- {issue}' for issue in advice.issues)}

Please address these specific improvements:
{chr(10).join(f'- {step}' for step in advice.improvement_steps)}"""
                    
                    await self.send_to_websocket("IterationAdvisor", "Proceeding with next iteration using provided advice ✓")
                else:
                    break
                
                rounds += 1
            
            # Generate final output with streaming
            await self.send_to_websocket("Output Generator", "Generating final response...\n\n")

            # Stream the final response
            final_output = await self.call_llm(
                model=config["generator_model"],
                agent="Output Generator",
                system_prompt=OUTPUT_GENERATOR_PROMPT,
                messages=[ChatMessage(role="user", content=f"Based on the following execution results, please provide a clear response to this user request: {message}\n\nExecution results:\n{json.dumps([r.model_dump() for r in all_results], indent=2)}")],
                temperature=config["temperature"],
            )
            response.agent_messages.append(final_output)
            await self.send_to_websocket(agent_message=final_output)

            # Set the complete response content after streaming
            response.content = final_output.content

            # Calculate and set total execution time
            response.execution_time = time.time() - overall_start_time
            
            # Send completion message for output generator
            await self.send_to_websocket("Output Generator", "Final response generated ✓")

            self.logger.info(f"\n\n TOTAL EXECUTION TIME: \nMultiAgentMethod completed analysis in {response.execution_time:.2f} seconds\n\n")

            # Extract the execution times with 2 decimal places in seconds from the agent messages and save them in a dict with the agent name as the key
            execution_times_data = defaultdict(int)
            token_usage = {msg.agent: {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0} for msg in response.agent_messages}
            for msg in response.agent_messages:
                execution_times_data[msg.agent] += msg.execution_time
                token_usage[msg.agent]['total_tokens'] += msg.response_metadata.get('total_tokens', 0)
                token_usage[msg.agent]['prompt_tokens'] += msg.response_metadata.get('prompt_tokens', 0)
                token_usage[msg.agent]['completion_tokens'] += msg.response_metadata.get('completion_tokens', 0)

            execution_times = {agent: f"{data:.2f} seconds" for agent, data in execution_times_data.items()}
            token_usage = {agent: f"{usage['total_tokens']} ({usage['prompt_tokens']}, {usage['completion_tokens']})" for agent, usage in token_usage.items()}

            # Send the execution times in a final websocket message from system agent
            await self.send_to_websocket("system", f"⏱️ Execution Times:\n\nTotal Execution Time: {response.execution_time:.2f} seconds\n {json.dumps(execution_times, indent=2)}\n"
                                                         f"Total Tokens used: {sum([msg.response_metadata.get('total_tokens', 0) for msg in response.agent_messages])}\nTotal (Prompt, Complete)\n{json.dumps(token_usage, indent=2)}\nExecution complete ✓")
            
            return response

        # If any errors were encountered, capture error desc and send to debug view
        except Exception as e:
            self.logger.error(f"Error in query_stream: {str(e)}\n{traceback.format_exc()}", exc_info=True)
            response.error = str(e)
            await self.send_to_websocket("system", f"\n\nError: {str(e)}\n\n")
            response.execution_time = time.time() - overall_start_time
            return response

    @staticmethod
    def get_agents_as_tools(agent_details: Dict):
        tools = []
        for name, content in agent_details.items():
            tools.append({
                "type": "function",
                "name": name,
                "description": f"{content['description']}\n\nFunctions:\n{content['functions']}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "A clear task description including all necessary steps and information "
                                           "to be fulfilled by this agent."
                        },
                        "round": {
                            "type": "integer",
                            "description": "The round in which this tool should be executed. First round is 1."
                        }
                    },
                    "required": ["task", "round"],
                    "additionalProperties": False
                },
                "strict": True
            })
        return tools

    async def send_to_websocket(self, agent: str = "system", message: str = "", agent_message: AgentMessage = None):
        """
        Sends either a given message or a full agent message via the given websocket.
        """
        if self.websocket:
            if not agent_message:
                agent_message = AgentMessage(agent=agent)
            if message:
                agent_message.content = message
            await self.websocket.send_json(agent_message.model_dump_json())
