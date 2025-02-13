import json
import os
import logging
import time
from typing import Dict, Any, List, Union
from pathlib import Path
import yaml
import asyncio

from openai import AsyncOpenAI

from .prompts import (
    OUTPUT_GENERATOR_PROMPT
)

from ..models import OpacaLLMBackend, Response, SessionData, AgentMessage, ConfigParameter


from .agents import (
    BaseAgent,
    OrchestratorAgent,
    WorkerAgent,
    AgentEvaluator,
    OverallEvaluator,
    OutputGenerator,
    GeneralAgent,
    IterationAdvisor,
    AgentPlanner,
)
from .models import (
    AgentEvaluation, 
    OverallEvaluation, 
    AgentResult,
    ChatHistory,
    ChatMessage,
    AgentTask
)
from ..utils import openapi_to_functions



class SelfOrchestratedBackend(OpacaLLMBackend):
    NAME = "self-orchestrated"

    
    def __init__(self, agents_file: str = "agents_tools.json"):
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        

        # Look for the file in the Backend directory
        self.agents_file = Path(__file__).parent.parent.parent / agents_file
        
        # Look for the file in the src directory
        self.agents_file_src = Path(__file__).parent.parent / agents_file

        if not self.agents_file.exists():
            self.logger.info(f"Agents file not found at: {self.agents_file}.\nChecking src directory..."
            )
        if not self.agents_file_src.exists():
            self.logger.info(f"Agents file not found at: {self.agents_file_src}."
            )

        if not self.agents_file.exists() and not self.agents_file_src.exists():
            raise FileNotFoundError(
                f"Agents file not found: {self.agents_file} or {self.agents_file_src}. "
                "Please run get_agents_tools.py first."
            )

        # if file in src directory exists, use it
        if self.agents_file_src.exists():
            self.agents_file = self.agents_file_src
        
        
        with open(self.agents_file) as f:
            self.agents_data = json.load(f)
        
        # Initialize session tracking
        self.current_session_id = None
        self.current_session_log = []
        self.logged_interactions = set()  # Track unique interactions to prevent duplicates
        self.chat_history = ChatHistory()  # Initialize chat history
    
    @property
    def name(self):
        return self.NAME

    @property
    def config_schema(self) -> Dict[str, ConfigParameter]:
        return {
            # Which model to use for the orchestrator and worker agents
            "model_config_name": ConfigParameter(
                type="string", 
                required=True, 
                default="vllm", 
                enum=["vllm", "vllm-large", "vllm-fast", "vllm-faster", "vllm-superfast", "vllm-mixed",
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
    
    async def _create_openai_client(self, session: SessionData, agent_type: str = "worker") -> AsyncOpenAI:
        """Create OpenAI client with appropriate configuration"""
        try:
            config = session.config.get(self.NAME, self.default_config())

            # Determine base_url and api_key based on configuration
            if agent_type == "worker":
                if config["worker_backend_type"] == "vllm":
                    api_key = config.get("worker_api_key") or session.api_key or os.getenv("VLLM_API_KEY")
                    base_url = config["worker_base_url"] or os.getenv("VLLM_BASE_URL", "http://10.0.64.101:8001/v1")
                else:
                    api_key = config.get("worker_api_key") or session.api_key or os.getenv("OPENAI_API_KEY")
                    base_url = config["worker_base_url"]
            elif agent_type == "generator":
                if config["generator_backend_type"] == "vllm":
                    api_key = config.get("generator_api_key") or session.api_key or os.getenv("VLLM_API_KEY")
                    base_url = config["generator_base_url"] or os.getenv("VLLM_BASE_URL", "http://10.0.64.101:8000/v1")
                else:
                    api_key = config.get("generator_api_key") or session.api_key or os.getenv("OPENAI_API_KEY")
                    base_url = config["generator_base_url"]
            elif agent_type == "evaluator":
                if config["evaluator_backend_type"] == "vllm":
                    api_key = config.get("evaluator_api_key") or session.api_key or os.getenv("VLLM_API_KEY")
                    base_url = config["evaluator_base_url"] or os.getenv("VLLM_BASE_URL", "http://10.0.64.101:8000/v1")
                else:
                    api_key = config.get("evaluator_api_key") or session.api_key or os.getenv("OPENAI_API_KEY")
                    base_url = config["evaluator_base_url"]
            else:  # orchestrator
                if config["orchestrator_backend_type"] == "vllm":
                    api_key = config.get("orchestrator_api_key") or session.api_key or os.getenv("VLLM_API_KEY")
                    base_url = config["base_url"] or os.getenv("VLLM_BASE_URL", "http://10.0.64.101:8000/v1")
                else:
                    api_key = config.get("orchestrator_api_key") or session.api_key or os.getenv("OPENAI_API_KEY")
                    base_url = config["base_url"]
            
            if not api_key:
                raise ValueError("No API key found in session or environment")
            
            # Initialize kwargs with api_key
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url

            client = AsyncOpenAI(**kwargs)
            return client
        except Exception as e:
            self.logger.error(f"Error creating OpenAI client: {str(e)}")
            raise

    async def _handle_follow_up(self, follow_up_question: str, websocket=None) -> None:
        """Handle follow-up questions by sending them to the user"""
        if websocket:
            # Send the follow-up question as an agent message with role 'assistant'
            await send_to_websocket(websocket, "assistant", f"I need some additional information to help you better:\n\n{follow_up_question}", 0.0)
            
            # Wait for user response
            response = await websocket.receive_text()
            
            # Add to chat history
            self.chat_history.messages.append(ChatMessage(
                role="assistant",
                content=follow_up_question
            ))
            self.chat_history.messages.append(ChatMessage(
                role="user",
                content=response
            ))
            
            return response
        else:
            # For non-websocket calls, we can't get follow-up answers
            raise ValueError("Follow-up questions require websocket connection")
    
    async def _execute_round(
        self,
        round_tasks: List[AgentTask],
        worker_agents: Dict[str, WorkerAgent],
        config: Dict[str, Any],
        all_results: List[AgentResult],
        websocket=None,
        evaluator_client=None, 
        planner_client=None,
        agent_messages: List[AgentMessage] = []
    ) -> List[AgentResult]:
        """Execute a single round of tasks in parallel when possible"""
        # Create agent evaluator
        agent_evaluator = AgentEvaluator(evaluator_client, config["evaluator_model"]) if self._parse_bool_config(config.get("use_agent_evaluator", True)) else None

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
                    client=planner_client,
                    model=config["orchestrator_model"],
                    agent_name=task.agent_name,
                    tools=agent.tools,
                    worker_agent=agent,
                    config=config
                )
                
                # Create plan first, passing previous results
                plan = await planner.create_plan(task, previous_results=all_results)
                
                # Calculate planner time
                planner_time = time.time() - planner_start_time

                # Send plan via websocket if needed
                agent_messages.append(await send_to_websocket(websocket, "AgentPlanner", f"Generated plan:\n{json.dumps(plan.model_dump(), indent=2)}\n\n", execution_time=planner_time))   
            
                await send_to_websocket(websocket, "WorkerAgent", f"Executing function calls.\n\n", 0.0)

                # Start Worker timer
                worker_start_time = time.time()
                
                # Execute task with planning
                result = await planner.execute_task(task, existing_plan=plan)
                
                # Calculate worker time
                worker_time = time.time() - worker_start_time
                
                # Send only tool calls and results via websocket
                if result.tool_calls:
                    await send_to_websocket(websocket, "WorkerAgent", f"Tool calls:\n{json.dumps(result.tool_calls, indent=2)}\n\n", 0.0)
                
                if result.tool_results:
                    agent_messages.append(await send_to_websocket(websocket, "WorkerAgent", f"Tool results:\n{json.dumps(result.tool_results, indent=2)}", execution_time=worker_time))
                else:
                    agent_messages.append(await send_to_websocket(websocket, "WorkerAgent", f"No tool results for the task...", execution_time=worker_time))
            else:
                await send_to_websocket(websocket, "WorkerAgent", f"Executing function calls.\n\n", 0.0)

                # Start Worker timer
                worker_start_time = time.time()

                # Execute task directly
                result = await agent.execute_task(task)

                # Calculate worker time
                worker_time = time.time() - worker_start_time
                
                # Send only tool calls and results via websocket
                if result.tool_calls:
                    await send_to_websocket(websocket, "WorkerAgent", f"Tool calls:\n{json.dumps(result.tool_calls, indent=2)}\n\n", 0.0)
                
                if result.tool_results:
                    agent_messages.append(await send_to_websocket(websocket, "WorkerAgent", f"Tool results:\n{json.dumps(result.tool_results, indent=2)}", execution_time=worker_time))
                else:
                    agent_messages.append(await send_to_websocket(websocket, "WorkerAgent", f"No tool results for the task...", execution_time=worker_time))
            
            if agent_evaluator and task.agent_name != "GeneralAgent":
                # Now evaluate the result after we have it
                await send_to_websocket(websocket, "AgentEvaluator", f"Evaluating {task.agent_name}'s task completion...\n\n", 0.0)

                # Start AgentEvaluator timer
                evaluator_start_time = time.time()
                
                evaluation = await agent_evaluator.evaluate(task_str, result)

                # Calculate evaluator time
                evaluator_time = time.time() - evaluator_start_time
            
                # Send evaluation results via websocket
                agent_messages.append(await send_to_websocket(websocket, "AgentEvaluator", f"Evaluation result for {task.agent_name}: {evaluation}", execution_time=evaluator_time))
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
                retry_result = await agent.execute_task(retry_task)
                result = retry_result  # Use the retry result

                # Calculate worker time
                worker_time = time.time() - worker_start_time
                
                # Send only tool calls and results via websocket
                if result.tool_calls:
                    await send_to_websocket(websocket, "WorkerAgent", f"Tool calls:\n{json.dumps(retry_result.tool_calls, indent=2)}\n\n", 0.0)
                    
                if result.tool_results:
                    agent_messages.append(await send_to_websocket(websocket, "WorkerAgent", f"Tool results:\n{json.dumps(result.tool_results, indent=2)}", execution_time=worker_time))
                else:
                    agent_messages.append(await send_to_websocket(websocket, "WorkerAgent", f"No tool results for the task...", execution_time=worker_time))
            
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
        try:
            # Track overall execution time
            overall_start_time = time.time()

            agent_messages = []
            
            # Add message to chat history
            self.chat_history.messages.append(ChatMessage(
                role="user",
                content=message
            ))
            
            # Log initial user message
            if BaseAgent.LOG_TO_FILE:
                self._log_non_llm_interaction("User", message)
            
            # Get base config and merge with model config
            config = session.config.get(self.NAME, self.default_config())
            model_config_loader = ModelConfigLoader() 
            model_config = model_config_loader.get_model_config(config.get("model_config_name"))
            config.update(model_config)  # Merge model config into session config
            
            # Create separate clients for orchestration and worker agents
            orchestrator_client = await self._create_openai_client(session, agent_type="orchestrator")
            worker_client = await self._create_openai_client(session, agent_type="worker")
            generator_client = await self._create_openai_client(session, agent_type="generator")
            evaluator_client = await self._create_openai_client(session, agent_type="evaluator")
            
            # Initialize response
            response = Response(query=message)
            
            # Send initial waiting message
            await send_to_websocket(websocket, "preparing", "Initializing the OPACA AI Agents", 0.0)
            
            # Get simplified agent summaries for the orchestrator
            agent_summaries = {
                name: data["summary"]
                for name, data in self.agents_data["agents_simple"].items()
            }
            
            # Add GeneralAgent summary
            agent_summaries["GeneralAgent"] = """**Purpose:** The GeneralAgent is designed to handle general queries about system capabilities and provide overall assistance.

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

**IMPORTANT:** This agent only has one function to call. Therefore, you MUST be extreamly short with your task for this agent to reduce latency!"""
            
            # Initialize agents
            orchestrator = OrchestratorAgent(
                client=orchestrator_client,
                model=config["orchestrator_model"],
                agent_summaries=agent_summaries,
                chat_history=self.chat_history,  # Pass chat history to orchestrator
                disable_thinking=self._parse_bool_config(config.get("disable_orchestrator_thinking", False))
            )
            
            # Initialize evaluators with evaluator model
            overall_evaluator = OverallEvaluator(evaluator_client, config["evaluator_model"])
            
            # Initialize output generator with generator model
            output_generator = OutputGenerator(generator_client, config["generator_model"])
            
            # Initialize iteration advisor with orchestrator model (since it's part of orchestration)
            iteration_advisor = IterationAdvisor(orchestrator_client, config["orchestrator_model"])
            
            # Initialize worker agents
            worker_agents = {
                "GeneralAgent": GeneralAgent(
                    client=worker_client,
                    model=config["worker_model"],
                    agent_summaries=agent_summaries,
                    config=config
                )
            }
            
            all_results = []
            rounds = 0
            
            while rounds < config["max_rounds"]:
                # Get execution plan from orchestrator
                await send_to_websocket(websocket, "Orchestrator", "Creating detailed orchestration plan...\n\n", 0.0)

                # Start orchestration timer
                orchestration_time = time.time()
                
                # Create orchestration plan
                plan = await orchestrator.create_execution_plan(message)
                
                # Calculate orchestration time
                orchestration_time = time.time() - orchestration_time
                
                # First send the thinking process
                if not self._parse_bool_config(config.get("disable_orchestrator_thinking", False)):
                    await send_to_websocket(websocket, "Orchestrator", f"Thinking process:\n{plan.thinking}\n\n", 0.0)
                
                # Then send the tasks
                agent_messages.append(await send_to_websocket(websocket, "Orchestrator", f"Created execution plan with {len(plan.tasks)} tasks:\n{json.dumps([task.model_dump() for task in plan.tasks], indent=2)}\n\n", execution_time=orchestration_time))
                
                # Mark planning phase complete
                await send_to_websocket(websocket, "Orchestrator", "Execution plan created ✓\n\n", 0.0)
                
                # Handle orchestrator follow-up questions
                if plan.needs_follow_up and plan.follow_up_question:
                    try:
                        # Get follow-up answer
                        answer = await self._handle_follow_up(plan.follow_up_question, websocket)
                        message = f"{message}\n\nAdditional information: {answer}"
                        continue  # Restart with new information
                    except Exception as e:
                        self.logger.error(f"Error handling orchestrator follow-up: {str(e)}")
                        break
                
                # Create worker agents for each unique agent in the plan
                for task in plan.tasks:
                    agent_name = task.agent_name
                    
                    # Try to normalize agent name if it doesn't exist
                    if agent_name not in worker_agents and agent_name not in self.agents_data["agents_simple"]:
                        # Try case-insensitive match
                        normalized_name = next(
                            (name for name in self.agents_data["agents_simple"].keys() 
                             if name.lower() == agent_name.lower()),
                            None
                        )
                        if normalized_name:
                            self.logger.warning(f"Normalized agent name from {agent_name} to {normalized_name}")
                            agent_name = normalized_name
                            task.agent_name = normalized_name
                        else:
                            self.logger.error(f"Unknown agent: {agent_name}")
                            raise ValueError(f"Unknown agent: {agent_name}")
                    
                    if agent_name not in worker_agents:
                        agent_data = self.agents_data["agents_simple"][agent_name]
                        
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
                        
                        # Verify we have a summary
                        if "summary" not in agent_data:
                            self.logger.error(f"Missing summary for agent {agent_name}")
                            raise ValueError(f"Agent {agent_name} is missing required summary")
                        
                        # Create worker agents for each unique agent in the plan
                        worker_agents[agent_name] = WorkerAgent(
                            client=worker_client,
                            model=config["worker_model"],
                            agent_name=agent_name,
                            summary=agent_data["summary"],
                            tools=agent_tools,
                            session_client=session.client,
                            config=config
                        )
                
                # Group tasks by round
                tasks_by_round = {}
                for task in plan.tasks:
                    tasks_by_round.setdefault(task.round, []).append(task)  # Use task directly since it's already an AgentTask
                
                # Execute each round
                for round_num in sorted(tasks_by_round.keys()):
                    await send_to_websocket(websocket, "Orchestrator", f"Starting execution round {round_num}\n\n", 0.0)
                    
                    round_results, agent_messages = await self._execute_round(
                        tasks_by_round[round_num],
                        worker_agents,
                        config,
                        all_results,
                        websocket,
                        evaluator_client,
                        orchestrator_client, 
                        agent_messages
                    )
                    
                    all_results.extend(round_results)

                await send_to_websocket(websocket, "OverallEvaluator", "Overall evaluation...\n\n", 0.0)

                # Start OverallEvaluator timer
                evaluator_start_time = time.time()

                # Evaluate overall progress
                evaluation = await overall_evaluator.evaluate(
                    f"{message}",
                    all_results
                )

                # Calculate evaluator time
                evaluator_time = time.time() - evaluator_start_time

                agent_messages.append(await send_to_websocket(websocket, "OverallEvaluator", f"Overall evaluation result: {evaluation}\n\n", execution_time=evaluator_time))
                await send_to_websocket(websocket, "OverallEvaluator", "Overall evaluation complete ✓", 0.0)
                            
                if evaluation == OverallEvaluation.REITERATE:
                    # Get iteration advice before continuing
                    await send_to_websocket(websocket, "IterationAdvisor", "Analyzing results and preparing advice for next iteration...\n\n", 0.0)

                    # Start IterationAdvisor timer
                    advisor_start_time = time.time()
                    
                    advice = await iteration_advisor.get_advice(
                        f"{message}",
                        all_results
                    )

                    # Calculate advisor time
                    advisor_time = time.time() - advisor_start_time

                    agent_messages.append(await send_to_websocket(websocket, "IterationAdvisor", f"Iteration Advice:\n{json.dumps(advice.model_dump(), indent=2)}\n\n", execution_time=advisor_time))
                    
                    # Handle follow-up questions from iteration advisor
                    if advice.needs_follow_up and advice.follow_up_question:
                        try:
                            # Get follow-up answer
                            answer = await self._handle_follow_up(advice.follow_up_question, websocket)
                            message = f"{message}\n\nAdditional information: {answer}"
                            continue  # Restart with new information
                        except Exception as e:
                            self.logger.error(f"Error handling iteration advisor follow-up: {str(e)}")
                    
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

            # Start OutputGenerator timer
            generator_start_time = time.time()
            
            # Stream the final response
            messages = [{
                "role": "system",
                "content": OUTPUT_GENERATOR_PROMPT
            }, {
                "role": "user",
                "content": f"Based on the following execution results, please provide a clear response to this user request: {message}\n\nExecution results:\n{json.dumps([r.dict() for r in all_results], indent=2)}"
            }]
            
            # Use generator model and client
            output_client = generator_client
            output_model = config["generator_model"]
            
            if output_model == "o3-mini":
                # Simple streaming text request without any special constraints
                stream = await output_client.chat.completions.create(
                    model=output_model,
                    messages=messages,
                    stream=True, 
                    reasoning_effort = "medium"
                )
            else:
                # Simple streaming text request without any special constraints
                stream = await output_client.chat.completions.create(
                    model=output_model,
                    messages=messages,
                    temperature=config["temperature"],
                    stream=True
                )
            
            final_output = []
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    final_output.append(content)
                    await send_to_websocket(websocket, "assistant", content, 0.0)
            
            # Set the complete response content after streaming
            response.content = "".join(final_output)

            # Calculate generator time
            generator_time = time.time() - generator_start_time

            
            # Calculate total execution time
            total_execution_time = time.time() - overall_start_time
            
            # Add response to chat history
            self.chat_history.messages.append(ChatMessage(
                role="assistant",
                content=response.content
            ))
            
            # Log the final output using the output generator's logging method
            output_generator._log_llm_interaction(
                "OutputGenerator",
                messages,  # This includes both system prompt and user input with execution results
                response.content
            )
            
            # Send completion message for output generator
            agent_messages.append(await send_to_websocket(websocket, "OutputGenerator", "Final response generated ✓", execution_time=generator_time))
            
            # Store agent messages for debug view and add execution time
            response.agent_messages = agent_messages
            
            # Set the total execution time in the response
            response.execution_time = total_execution_time

            self.logger.info(f"\n\n TOTAL EXECUTION TIME: \nMultiAgentBackend completed analysis in {total_execution_time:.2f} seconds\n\n")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error in query_stream: {str(e)}", exc_info=True)
            response.error = str(e)
            await send_to_websocket(websocket, "system", f"\n\nError: {str(e)}\n\n", 0.0)
            # Log error
            self._log_non_llm_interaction("System", f"Error: {str(e)}")
            return response

    def _save_session_log(self):
        """Save the complete session log to file if logging is enabled"""
        from .agents import BaseAgent
        if BaseAgent.LOG_TO_FILE and BaseAgent.LOG_FILE and self.current_session_log:
            try:
                with open(BaseAgent.LOG_FILE, 'a') as f:
                    f.write("\n" + "="*50 + "\n")
                    f.write("End of Session\n")
                    f.write("="*50 + "\n\n\n\n")
            except Exception as e:
                self.logger.error(f"Error saving session log: {str(e)}")
        
        # Clear the session log and interaction tracking
        self.current_session_log = []
        self.logged_interactions.clear()

    def _log_non_llm_interaction(self, agent: str, content: str) -> None:
        """Log non-LLM interactions like user inputs or system messages"""
        from .agents import BaseAgent
        try:
            if BaseAgent.LOG_TO_FILE:
                with open(BaseAgent.LOG_FILE, 'a') as f:
                    f.write(f"\n{'=' * 35} {agent} {'=' * 35}\n\n")
                    f.write(f"{content}\n\n")
                    f.write(f"{'=' * 90}\n\n")
        except Exception as e:
            self.logger.error(f"Error writing to log file: {str(e)}") 


class ModelConfigLoader:
    def __init__(self):
        self.config_path = Path(__file__).parent / "model_config.yaml"
        self._config_data = None
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self._config_data:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            with open(self.config_path, 'r') as f:
                self._config_data = yaml.safe_load(f)
        
        return self._config_data
    
    def get_model_config(self, config_name: str = "vllm") -> Dict[str, Any]:
        """Get model configuration by name, merged with default config"""
        config_data = self._load_config()
        
        if config_name:
            # If a specific configuration is requested, merge it with defaults
            if config_name not in config_data.get('model_configs', {}):
                raise ValueError(f"Model configuration '{config_name}' not found")
            
            result = config_data['model_configs'][config_name]
        
        return result
    
    def list_available_configs(self) -> list:
        """List all available model configurations"""
        config_data = self._load_config()
        return list(config_data.get('model_configs', {}).keys())


async def send_to_websocket(websocket=None, agent="DEFAULT AGENT", message="NO MESSAGE", execution_time=0.0): 
    message = AgentMessage(
        agent=agent,
        content=message,
        execution_time=execution_time
    )
    if websocket:
        await websocket.send_json(message.model_dump_json())
    
    return message
