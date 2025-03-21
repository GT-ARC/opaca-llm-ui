import json
import os
import logging
import time
import traceback
from typing import Dict, Any, List, Tuple
from pathlib import Path

from yaml import load, CLoader as Loader
import asyncio

from .prompts import (
    OUTPUT_GENERATOR_PROMPT, BACKGROUND_INFO, GENERAL_CAPABILITIES_RESPONSE
)
from ..abstract_method import AbstractMethod

from ..models import Response, SessionData, AgentMessage, ConfigParameter, ChatMessage

from .agents import (
    OrchestratorAgent,
    WorkerAgent,
    AgentEvaluator,
    OverallEvaluator,
    IterationAdvisor,
    AgentPlanner, get_current_time
)
from .models import (
    AgentEvaluation, 
    OverallEvaluation, 
    AgentResult,
    AgentTask
)
from ..utils import openapi_to_functions


class SelfOrchestratedBackend(AbstractMethod):
    NAME = "self-orchestrated"

    def __init__(self, agents_file: str = "agents_tools.json"):
        # Set up logging
        self.logger = logging.getLogger("src.models")
        
        # Initialize session tracking
        self.current_session_id = None
        self.current_session_log = []
        self.logged_interactions = set()  # Track unique interactions to prevent duplicates

    @property
    def config_schema(self) -> Dict[str, ConfigParameter]:
        return {
            # Which model to use for the orchestrator and worker agents
            "model_config_name": ConfigParameter(
                type="string", 
                required=True, 
                default="vllm", 
                enum=["vllm", "vllm-fast", "vllm-faster", "vllm-superfast", "vllm-large", "vllm-superlarge", "vllm-mixed",
                      "4o-mixed", "4o", "4o-mini", "o3-mini", "o3-mini-large"],
                description="Which model to use for the orchestrator and worker agents"),
            # Temperature for the orchestrator and worker agents
            "temperature": ConfigParameter(
                type="number", 
                required=True, 
                default=0.0, 
                minimum=0.0, 
                maximum=2.0,
                enum=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0],
                description="Temperature for the orchestrator and worker agents"),
            # Maximum number of orchestration and worker rounds
            "max_rounds": ConfigParameter(
                type="integer", 
                required=True, 
                default=5, 
                minimum=1, 
                maximum=10,
                enum=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                description="Maximum number of orchestration and worker rounds"),
            # Maximum number of re-iterations (retries after failed attempts)
            "max_iterations": ConfigParameter(
                type="integer", 
                required=True, 
                default=3, 
                minimum=1, 
                maximum=10,
                enum=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                description="Maximum number of re-iterations (retries after failed attempts)"),
            # Whether to use the worker model for output generation
            "use_worker_for_output": ConfigParameter(
                type="boolean", 
                required=True, 
                default=False,
                description="Whether to use the worker model for output generation"),
            # Whether to use the planner agent or not
            "use_agent_planner": ConfigParameter(
                type="boolean", 
                required=True, 
                default=True,
                description="Whether to use the planner agent or not"),
            # Whether to use the agent evaluator or not
            "use_agent_evaluator": ConfigParameter(
                type="boolean", 
                required=True, 
                default=False,
                description="Whether to use the agent evaluator or not"),

            # Whether to use the orchestrator without thinking
            "disable_orchestrator_thinking": ConfigParameter(
                type="boolean", 
                required=True, 
                default=True,
                description="Whether to disable the thinking process of the orchestrator"
            )
        }

    async def execute_round_task(self, worker_agent, config, subtask, orchestrator_context, round_context, round_num):
        current_task = subtask.task

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
        #result = await worker_agent.execute_task(current_task)
        result = await self.call_llm(
            agent="WorkerAgent",
            model=config["worker_model"],
            system_prompt=worker_agent.system_prompt(),
            messages=worker_agent.messages(subtask),
            temperature=config["temperature"],
            vllm_api_key=os.getenv("VLLM_API_KEY"),
            vllm_base_url=config["worker_base_url"],
            tools=worker_agent.tools
        )
        agent_result = await worker_agent.invoke_tools(current_task, result.tools)

        return agent_result
    
    async def _execute_round(
        self,
        round_tasks: List[AgentTask],
        worker_agents: Dict[str, WorkerAgent],
        config: Dict[str, Any],
        all_results: List[AgentResult],
        agent_summaries: Dict[str, Any],
        websocket=None,
        agent_messages: List[AgentMessage] = None
    ) -> Tuple[List[AgentResult], List[AgentMessage]]:
        """Execute a single round of tasks in parallel when possible"""
        # Create agent evaluator
        agent_evaluator = AgentEvaluator() if self._parse_bool_config(config.get("use_agent_evaluator", True)) else None

        async def execute_single_task(task: AgentTask):
            agent = worker_agents[task.agent_name]
            task_str = task.task if isinstance(task, AgentTask) else task
            
            # Log the task being executed
            self.logger.info(f"Executing task for {task.agent_name}: {task_str}")
            
            # Create planner if enabled
            if self._parse_bool_config(config.get("use_agent_planner", True)) and task.agent_name != "GeneralAgent":
                # Start Planner timer
                planner_start_time = time.time()

                await send_to_websocket(websocket, "AgentPlanner", f"Planning function calls for {task.agent_name}'s task: {task_str} \n\n", 0.0)
                
                planner = AgentPlanner(
                    agent_name=task.agent_name,
                    tools=agent.tools,
                    worker_agent=agent,
                    config=config
                )
                
                # Create plan first, passing previous results
                plan = await self.call_llm(
                    model=config["orchestrator_model"],
                    agent="AgentPlanner",
                    system_prompt=planner.system_prompt(),
                    messages=planner.messages(task, previous_results=all_results),
                    temperature=config["temperature"],
                    vllm_api_key=os.getenv("VLLM_API_KEY"),
                    vllm_base_url=config["base_url"],
                    response_format=planner.schema,
                )
                plan = plan.formatted_output
                
                # Calculate planner time
                planner_time = time.time() - planner_start_time

                # Send plan via websocket if needed
                agent_messages.append(await send_to_websocket(websocket, "AgentPlanner", f"Generated plan:\n{json.dumps(plan.model_dump(), indent=2)}\n\n", execution_time=planner_time, response_metadata=planner.response_metadata))
            
                await send_to_websocket(websocket, "WorkerAgent", f"Executing function calls.\n\n", 0.0)

                # Start Worker timer
                worker_start_time = time.time()

                # Initialize results storage
                ex_results = []
                ex_tool_calls = []
                ex_tool_results = []
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
                            if prev_result.tool_results:
                                round_context += f"Tool Results:\n"
                                for tr in prev_result.tool_results:
                                    round_context += f"- {tr['name']}: {json.dumps(tr['result'])}\n"

                    round_results = await asyncio.gather(*[self.execute_round_task(planner.worker_agent, config, subtask, planner.get_orchestrator_context(all_results), round_context, round_num) for subtask in current_tasks])

                    # Process round results
                    for result in round_results:
                        ex_results.append(result)
                        ex_tool_calls.extend(result.tool_calls)
                        ex_tool_results.extend(result.tool_results)
                        combined_output.append(result.output)

                # Create final combined result with clear round separation
                final_output = "\n\n".join(combined_output)
                result = AgentResult(
                    agent_name=planner.worker_agent.agent_name,  # Use worker agent's name for proper attribution
                    task=task_str,  # Use the original task string
                    output=final_output,
                    tool_calls=ex_tool_calls,
                    tool_results=ex_tool_results
                )
                
                # Calculate worker time
                worker_time = time.time() - worker_start_time
                
                # Send only tool calls and results via websocket
                if result.tool_calls:
                    await send_to_websocket(websocket, "WorkerAgent", f"Tool calls:\n{json.dumps(result.tool_calls, indent=2)}\n\n", 0.0)
                
                if result.tool_results:
                    agent_messages.append(await send_to_websocket(websocket, "WorkerAgent", f"Tool results:\n{json.dumps(result.tool_results, indent=2)}", execution_time=worker_time, response_metadata=agent.response_metadata))
                else:
                    agent_messages.append(await send_to_websocket(websocket, "WorkerAgent", f"No tool results for the task...", execution_time=worker_time, response_metadata=agent.response_metadata))
            else:
                await send_to_websocket(websocket, "WorkerAgent", f"Executing function calls.\n\n", 0.0)

                # Start Worker timer
                worker_start_time = time.time()

                # Execute task directly
                if agent.agent_name == "GeneralAgent":
                    result = await self.get_general_agent_response(task_str, agent_summaries)
                else:
                    result = await self.call_llm(
                        agent="WorkerAgent",
                        model=config["worker_model"],
                        system_prompt=agent.system_prompt(),
                        messages=agent.messages(task),
                        temperature=config["temperature"],
                        vllm_api_key=os.getenv("VLLM_API_KEY"),
                        vllm_base_url=config["worker_base_url"],
                        tools=agent.tools,
                    )
                    result = await agent.invoke_tools(task.task, result.tools)

                print(f'Worker result: {result}')

                # Calculate worker time
                worker_time = time.time() - worker_start_time
                
                # Send only tool calls and results via websocket
                if result.tool_calls:
                    await send_to_websocket(websocket, "WorkerAgent", f"Tool calls:\n{json.dumps(result.tool_calls, indent=2)}\n\n", 0.0)
                
                if result.tool_results:
                    agent_messages.append(await send_to_websocket(websocket, "WorkerAgent", f"Tool results:\n{json.dumps(result.tool_results, indent=2)}", execution_time=worker_time, response_metadata=agent.response_metadata))
                else:
                    agent_messages.append(await send_to_websocket(websocket, "WorkerAgent", f"No tool results for the task...", execution_time=worker_time, response_metadata=agent.response_metadata))
            
            if agent_evaluator and task.agent_name != "GeneralAgent":
                # Now evaluate the result after we have it
                await send_to_websocket(websocket, "AgentEvaluator", f"Evaluating {task.agent_name}'s task completion...\n\n", 0.0)

                # Start AgentEvaluator timer
                evaluator_start_time = time.time()

                if not (evaluation := agent_evaluator.evaluate_results(result)):
                    evaluation = await self.call_llm(
                        agent="AgentEvaluator",
                        model=config["evaluator_model"],
                        system_prompt=agent_evaluator.system_prompt(),
                        messages=agent_evaluator.messages(task_str, result),
                        temperature=config["temperature"],
                        vllm_api_key=os.getenv("VLLM_API_KEY"),
                        vllm_base_url=config["evaluator_base_url"],
                        guided_choice=agent_evaluator.guided_choice(),
                    )
                    evaluation = evaluation.content

                # Calculate evaluator time
                evaluator_time = time.time() - evaluator_start_time
            
                # Send evaluation results via websocket
                agent_messages.append(await send_to_websocket(websocket, "AgentEvaluator", f"Evaluation result for {task.agent_name}: {evaluation}", execution_time=evaluator_time, response_metadata=agent_evaluator.response_metadata))
            else: 
                evaluation = None
            
            # If evaluation indicates we need to retry, do so
            if evaluation and evaluation == AgentEvaluation.REITERATE:
                # Update task for retry
                retry_task = f"""# Evaluation 
                
The Evaluator of your task has indicated that there is crucial information missing to solve the task.. 

# Your Task: 

{task_str}

# Your previous output: 

{result.output}

# Your Previous tool calls: 

{json.dumps(result.tool_calls, indent=2)}

# Your previous tool results: 

{json.dumps(result.tool_results, indent=2)}

# YOUR GOAL:

Now, using the tools available to you and the previous results, continue with your original task and retrieve all the information necessary to complete and solve the task!"""

                await send_to_websocket(websocket, "WorkerAgent", f"Retrying task...\n\n", 0.0)

                # Start Worker timer
                worker_start_time = time.time()
                
                # Execute retry
                #retry_result = await agent.execute_task(retry_task)
                #result = retry_result  # Use the retry result
                result = await self.call_llm(
                    agent="WorkerAgent",
                    model=config["worker_model"],
                    system_prompt=agent.system_prompt(),
                    messages=agent.messages(retry_task),
                    temperature=config["temperature"],
                    vllm_api_key=os.getenv("VLLM_API_KEY"),
                    vllm_base_url=config["worker_base_url"],
                    tools=agent.tools
                )

                # Calculate worker time
                worker_time = time.time() - worker_start_time
                
                # Send only tool calls and results via websocket
                if result.tool_calls:
                    await send_to_websocket(websocket, "WorkerAgent", f"Tool calls:\n{json.dumps(result.tool_calls, indent=2)}\n\n", 0.0)
                    
                if result.tool_results:
                    agent_messages.append(await send_to_websocket(websocket, "WorkerAgent", f"Tool results:\n{json.dumps(result.tool_results, indent=2)}", execution_time=worker_time, response_metadata=agent.response_metadata))
                else:
                    agent_messages.append(await send_to_websocket(websocket, "WorkerAgent", f"No tool results for the task...", execution_time=worker_time, response_metadata=agent.response_metadata))
            
            return result

        # Execute all tasks in parallel using asyncio.gather
        results = await asyncio.gather(*[execute_single_task(task) for task in round_tasks])
        
        return results, agent_messages

    def _parse_bool_config(self, value: Any) -> bool:
        """Parse a configuration value as a boolean, handling various input types."""
        if isinstance(value, str):
            return value.lower() in ['true', '1', 'yes', 'on']
        return bool(value)
    
    async def query(self, message: str, session: SessionData) -> Response:
        return await self.query_stream(message, session)   
    
    async def query_stream(self, message: str, session: SessionData, websocket=None) -> Response:
        """Process a user message using multiple agents"""

        # Initialize response
        response = Response(query=message)

        try:
            # Track overall execution time
            overall_start_time = time.time()

            agent_messages = []
            
            # Get base config and merge with model config
            config = session.config.get(self.NAME, self.default_config())
            with open(f'{Path(__file__).parent}/model_config.yaml', 'r') as f:
                data = load(f, Loader=Loader)
                config.update(data['model_configs'][config.get('model_config_name')])
            
            # Send initial waiting message
            await send_to_websocket(websocket, "preparing", "Initializing the OPACA AI Agents", 0.0)
            
            # Get simplified agent summaries for the orchestrator
            agent_details = await session.client.get_agent_details()
            
            # Add GeneralAgent summary
            agent_details["GeneralAgent"] = {"description": """"**Purpose:** The GeneralAgent is designed to handle general queries about system capabilities and provide overall assistance.

**Overview:** This agent can explain the system's features, available agents, and their capabilities. It serves as the primary point of contact for general inquiries and capability questions.
**Note:** If you believe that the Output Generator LLM would be able to answer the question directly, USE THIS AGENT! This agent has absolutely no latency and retrieves context very fast. Therefore, it is the best choice for very simple questions or questions that are related to the system's capabilities.
**Expected Output from this agent:** An immediate summary of the system containing the current time, location, and capabilities.

**Goals and Capabilities:** The GeneralAgent can:
1. Explain what the system can do
2. Provide information about available agents and their capabilities
3. Answer general questions about the system
4. Answer very simple questions
5. Retrieve the current time
6. Retrieve the current location

**IMPORTANT:** This agent only has one function to call. Therefore, you MUST be extremely short with your task for this agent to reduce latency!""", "actions": []}
            
            # Initialize agents
            orchestrator = OrchestratorAgent(
                agent_summaries=agent_details,
                chat_history=session.messages,  # Pass chat history to orchestrator
                disable_thinking=self._parse_bool_config(config.get("disable_orchestrator_thinking", False))
            )
            
            # Initialize evaluators with evaluator model
            overall_evaluator = OverallEvaluator()
            
            # Initialize iteration advisor with orchestrator model (since it's part of orchestration)
            iteration_advisor = IterationAdvisor()
            
            # Initialize worker agents
            worker_agents = {
                "GeneralAgent": WorkerAgent("GeneralAgent", "", [], None),
            }
            
            all_results = []
            rounds = 0
            
            while rounds < config["max_rounds"]:
                # Get execution plan from orchestrator
                await send_to_websocket(websocket, "Orchestrator", "Creating detailed orchestration plan...\n\n", 0.0)

                # Start orchestration timer
                orchestration_time = time.time()
                
                # Create orchestration plan
                plan = await self.call_llm(
                    model=config["orchestrator_model"],
                    agent="Orchestrator",
                    system_prompt=orchestrator.system_prompt(),
                    messages=orchestrator.messages(message),
                    temperature=config["temperature"],
                    vllm_api_key=os.getenv("VLLM_API_KEY"),
                    vllm_base_url=config["base_url"],
                    response_format=orchestrator.schema,
                )
                plan = plan.formatted_output
                
                # Calculate orchestration time
                orchestration_time = time.time() - orchestration_time
                
                # First send the thinking process
                if not self._parse_bool_config(config.get("disable_orchestrator_thinking", False)):
                    await send_to_websocket(websocket, "Orchestrator", f"Thinking process:\n{plan.thinking}\n\n", 0.0)
                
                # Then send the tasks
                agent_messages.append(await send_to_websocket(websocket, "Orchestrator", f"Created execution plan with {len(plan.tasks)} tasks:\n{json.dumps([task.model_dump() for task in plan.tasks], indent=2)}\n\n", execution_time=orchestration_time, response_metadata=orchestrator.response_metadata))
                
                # Mark planning phase complete
                await send_to_websocket(websocket, "Orchestrator", "Execution plan created ✓\n\n", execution_time=orchestration_time, response_metadata=orchestrator.response_metadata)

                # Handle orchestrator follow-up questions
                if plan.needs_follow_up and plan.follow_up_question:
                    response.content = plan.follow_up_question
                    # TODO probably need to set more information in response
                    return response
                
                # Create worker agents for each unique agent in the plan
                for task in plan.tasks:
                    agent_name = task.agent_name

                    print(f'task: {task}')
                    
                    if agent_name not in worker_agents:
                        agent_data = agent_details[agent_name]["description"]
                        
                        # Get functions from platform instead of JSON file
                        agent_tools = []
                        actions_spec = await session.client.get_actions_with_refs()
                        functions, error = openapi_to_functions(actions_spec, use_agent_names=True)
                        
                        # Filter functions for this specific agent and clean up parameters
                        for func in functions:
                            if func["function"]["name"].startswith(f"{agent_name}--"):
                                # Create a cleaned version of the function
                                cleaned_func = {
                                    "type": "function",
                                    "function": {
                                        "name": func["function"]["name"],
                                        "description": func["function"]["description"],
                                        "parameters": {
                                            "type": "object",
                                            "properties": {
                                                "requestBody": func["function"]["parameters"]["properties"]["requestBody"]
                                            }
                                        }
                                    }
                                }
                                agent_tools.append(cleaned_func)
                        
                        # Create worker agents for each unique agent in the plan
                        worker_agents[agent_name] = WorkerAgent(
                            agent_name=agent_name,
                            summary=agent_data,
                            tools=agent_tools,
                            session_client=session.client,
                        )
                
                # Group tasks by round
                tasks_by_round = {}
                for task in plan.tasks:
                    tasks_by_round.setdefault(task.round, []).append(task)  # Use task directly since it's already an AgentTask
                
                # Execute each round
                for round_num in sorted(tasks_by_round.keys()):
                    await send_to_websocket(websocket, "Orchestrator", f"Starting execution round {round_num}\n\n", execution_time=orchestration_time, response_metadata=orchestrator.response_metadata)
                    
                    round_results, agent_messages = await self._execute_round(
                        tasks_by_round[round_num],
                        worker_agents,
                        config,
                        all_results,
                        agent_details,
                        websocket,
                        agent_messages
                    )
                    
                    all_results.extend(round_results)

                await send_to_websocket(websocket, "OverallEvaluator", "Overall evaluation...\n\n", 0.0)

                # Start OverallEvaluator timer
                evaluator_start_time = time.time()

                # Evaluate overall progress
                if not (evaluation := overall_evaluator.evaluate_results(all_results)):
                    evaluation_message = await self.call_llm(
                        agent="OverallEvaluator",
                        model=config["evaluator_model"],
                        system_prompt=overall_evaluator.system_prompt(),
                        messages=overall_evaluator.messages(message, all_results),
                        temperature=config["temperature"],
                        vllm_api_key=os.getenv("VLLM_API_KEY"),
                        vllm_base_url=config["evaluator_base_url"],
                        guided_choice=overall_evaluator.guided_choice,
                    )
                    evaluation = evaluation_message.content
                    print(f'Evaluation results: {evaluation}')

                # Calculate evaluator time
                evaluator_time = time.time() - evaluator_start_time

                agent_messages.append(await send_to_websocket(websocket, "OverallEvaluator", f"Overall evaluation result: {evaluation}\n\n", execution_time=evaluator_time, response_metadata=overall_evaluator.response_metadata))
                await send_to_websocket(websocket, "OverallEvaluator", "Overall evaluation complete ✓", execution_time=evaluator_time, response_metadata=overall_evaluator.response_metadata)
                            
                if evaluation == OverallEvaluation.REITERATE:
                    # Get iteration advice before continuing
                    await send_to_websocket(websocket, "IterationAdvisor", "Analyzing results and preparing advice for next iteration...\n\n", 0.0)

                    # Start IterationAdvisor timer
                    advisor_start_time = time.time()

                    advice = await self.call_llm(
                        agent="IterationAdvisor",
                        model=config["orchestrator_model"],
                        system_prompt=iteration_advisor.system_prompt(),
                        messages=iteration_advisor.messages(message, all_results),
                        temperature=config["temperature"],
                        vllm_api_key=os.getenv("VLLM_API_KEY"),
                        vllm_base_url=config["base_url"],
                        response_format=iteration_advisor.schema
                    )
                    advice = advice.formatted_output

                    # Calculate advisor time
                    advisor_time = time.time() - advisor_start_time

                    agent_messages.append(await send_to_websocket(websocket, "IterationAdvisor", f"Iteration Advice:\n{json.dumps(advice.model_dump(), indent=2)}\n\n", execution_time=advisor_time, response_metadata=iteration_advisor.response_metadata))

                    # Handle follow-up questions from iteration advisor
                    if advice.needs_follow_up and advice.follow_up_question:
                        response.content = advice.follow_up_question#
                        # TODO Here some more response contents as well
                        return response
                    
                    # If advisor suggests not to retry, proceed to output generation
                    if not advice.should_retry:
                        await send_to_websocket(websocket, "IterationAdvisor", "Tasks completed successfully. Proceeding to final output with the following summary:\n\n" + advice.context_summary, 0.0)
                        break
                    
                    # Add the advice to the message for the next iteration
                    message = f"""Original request: {message}

Previous iteration summary: {advice.context_summary}

Issues identified:
{chr(10).join(f'- {issue}' for issue in advice.issues)}

Please address these specific improvements:
{chr(10).join(f'- {step}' for step in advice.improvement_steps)}"""
                    
                    await send_to_websocket(websocket, "IterationAdvisor", "Proceeding with next iteration using provided advice ✓", 0.0)
                else:
                    break
                
                rounds += 1
            
            # Generate final output with streaming
            await send_to_websocket(websocket, "OutputGenerator", "Generating final response...\n\n", 0.0)

            # Stream the final response
            final_output = await self.call_llm(
                agent="output_generator",
                model=config["generator_model"],
                system_prompt=OUTPUT_GENERATOR_PROMPT,
                messages=[ChatMessage(role="user", content=f"Based on the following execution results, please provide a clear response to this user request: {message}\n\nExecution results:\n{json.dumps([r.model_dump() for r in all_results], indent=2)}")],
                temperature=config["temperature"],
                vllm_api_key=os.getenv("VLLM_API_KEY"),
                vllm_base_url=config["generator_base_url"],
                websocket=websocket,
            )

            # Set the complete response content after streaming
            response.content = "".join(final_output.content)

            # Calculate and set total execution time
            response.execution_time = time.time() - overall_start_time
            
            # Send completion message for output generator
            agent_messages.append(await send_to_websocket(websocket, "OutputGenerator", "Final response generated ✓", execution_time=final_output.execution_time, response_metadata=final_output.response_metadata))
            
            # Store agent messages for debug view and add execution time
            response.agent_messages = agent_messages

            self.logger.info(f"\n\n TOTAL EXECUTION TIME: \nMultiAgentBackend completed analysis in {response.execution_time:.2f} seconds\n\n")

            # Extract the execution times with 2 decimal places in seconds from the agent messages and save them in a dict with the agent name as the key
            execution_times = {msg.agent: f"{msg.execution_time:.2f} seconds" for msg in agent_messages if msg.execution_time is not None}

            token_usage = {msg.agent: {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0} for msg in agent_messages}
            for msg in agent_messages:
                token_usage[msg.agent]['total_tokens'] += msg.response_metadata.get('total_tokens', 0)
                token_usage[msg.agent]['prompt_tokens'] += msg.response_metadata.get('prompt_tokens', 0)
                token_usage[msg.agent]['completion_tokens'] += msg.response_metadata.get('completion_tokens', 0)
            token_usage = {agent: f"{usage['total_tokens']} ({usage['prompt_tokens']}, {usage['completion_tokens']})" for agent, usage in token_usage.items()}
            


            # Send the execution times in a final websocket message from system agent
            await send_to_websocket(websocket, "system", f"⏱️ Execution Times:\n\nTotal Execution Time: {response.execution_time:.2f} seconds\n {json.dumps(execution_times, indent=2)}\n"
                                                         f"Total Tokens used: {sum([msg.response_metadata.get('total_tokens', 0) for msg in agent_messages])}\nTotal (Prompt, Complete)\n{json.dumps(token_usage, indent=2)}\n", 0.0)

            # Send the final message from the system agent
            await send_to_websocket(websocket, "system", "Execution complete ✓", 0.0)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error in query_stream: {str(e)}\n{traceback.format_exc()}", exc_info=True)
            response.error = str(e)
            await send_to_websocket(websocket, "system", f"\n\nError: {str(e)}\n\n", 0.0)
            return response

    async def get_general_agent_response(self, task_str, agent_summaries):
        predefined_response = get_current_time() + BACKGROUND_INFO + GENERAL_CAPABILITIES_RESPONSE.format(
            agent_capabilities=json.dumps(agent_summaries, indent=2)
        )
        return AgentResult(
            agent_name="GeneralAgent",
            task=task_str,
            output="Retrieved system capabilities",  # Keep output minimal since data is in tool result
            tool_calls=[{"name": "GetCapabilities", "args": "{}"}],
            tool_results=[{"name": "GetCapabilities", "result": predefined_response}]
        )


async def send_to_websocket(websocket=None, agent: str = "", message: str = "", execution_time=0.0, response_metadata = None):
    message = AgentMessage(
        agent=agent,
        content=message,
        execution_time=execution_time,
        response_metadata=response_metadata or {},
    )
    if websocket:
        await websocket.send_json(message.model_dump_json())
    
    return message
