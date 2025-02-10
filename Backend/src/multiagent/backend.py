import json
import os
import logging
import time
from typing import Dict, Any, List, Union
from pathlib import Path
import yaml

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



class MultiAgentBackend(OpacaLLMBackend):
    NAME = "multi-agent"

    
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
        
        # Initialize logging settings
        self.log_to_file = False
        self.log_file = "agents.log"
        
        # Clear the log file at startup
        if self.log_to_file:
            with open(self.log_file, 'w') as f:
                f.write(f"\n{'=' * 35} New Session Started {'=' * 35}\n\n\n\n")
        
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
                enum=["vllm", "vllm-large", "vllm-fast" "vllm-mixed", 
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
        }
    
    async def _create_openai_client(self, session: SessionData, is_worker: bool = False) -> AsyncOpenAI:
        """Create OpenAI client with appropriate configuration"""
        try:
            config = session.config.get(self.NAME, self.default_config())

            # Determine base_url and api_key based on configuration
            if is_worker:
                if config["worker_backend_type"] == "vllm":
                    api_key = config.get("worker_api_key") or session.api_key or os.getenv("VLLM_API_KEY")
                    base_url = config["worker_base_url"] or os.getenv("VLLM_BASE_URL", "http://10.0.64.101:8001/v1")
                else:
                    api_key = config.get("worker_api_key") or session.api_key or os.getenv("OPENAI_API_KEY")
                    base_url = config["worker_base_url"]
            else:
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
            await websocket.send_json(AgentMessage(
                agent="assistant",
                content=f"I need some additional information to help you better:\n\n{follow_up_question}"
            ).model_dump_json())
            
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
        orchestrator_client=None
    ) -> List[AgentResult]:
        """Execute a single round of tasks in parallel when possible"""
        results = []
        
        # Create agent evaluator
        agent_evaluator = AgentEvaluator(orchestrator_client, config["orchestrator_model"])
        
        for task in round_tasks:
            agent = worker_agents[task.agent_name]
            task_str = task.task if isinstance(task, AgentTask) else task
            
            # Log the task being executed
            self.logger.info(f"Executing task for {task.agent_name}: {task_str}")
            
            # Create planner if enabled
            if self._parse_bool_config(config.get("use_agent_planner", True)):
                if websocket:
                    await websocket.send_json(AgentMessage(
                        agent="AgentPlanner",
                        content=f"Planning function calls for {task.agent_name}'s task: {task_str} \n\n",
                        execution_time=0.0
                    ).model_dump_json())
                
                planner = AgentPlanner(
                    client=orchestrator_client,
                    model=config["orchestrator_model"],
                    agent_name=task.agent_name,
                    tools=agent.tools,
                    worker_agent=agent,
                    config=config
                )
                
                # Create plan first, passing previous results
                plan = await planner.create_plan(task, previous_results=all_results)
                
                # Send plan via websocket if needed
                if websocket:
                    await websocket.send_json(AgentMessage(
                        agent="AgentPlanner",
                        content=f"Generated plan:\n{json.dumps(plan.dict(), indent=2)}\n\n",
                        execution_time=0.0
                    ).model_dump_json())

                    await websocket.send_json(AgentMessage(
                        agent="WorkerAgent",
                        content=f"Executing function calls.\n\n",
                        execution_time=0.0
                    ).model_dump_json())
                
                # Execute task with planning
                result = await planner.execute_task(task, existing_plan=plan)
                
                # Send only tool calls and results via websocket
                if websocket:
                    if result.tool_calls:
                        await websocket.send_json(AgentMessage(
                            agent=f"WorkerAgent",
                            content=f"Tool calls:\n{json.dumps(result.tool_calls, indent=2)}",
                            execution_time=0.0
                        ).model_dump_json())
                    
                    if result.tool_results:
                        await websocket.send_json(AgentMessage(
                            agent="WorkerAgent",
                            content=f"Tool results:\n{json.dumps(result.tool_results, indent=2)}",
                            execution_time=0.0
                        ).model_dump_json())
            else:
                if websocket:
                    await websocket.send_json(AgentMessage(
                        agent="WorkerAgent",
                        content=f"Executing function calls.\n\n",
                        execution_time=0.0
                    ).model_dump_json())
                # Execute task directly
                result = await agent.execute_task(task)
                
                # Send only tool calls and results via websocket
                if websocket:
                    if result.tool_calls:
                        await websocket.send_json(AgentMessage(
                            agent=f"WorkerAgent",
                            content=f"Tool calls:\n{json.dumps(result.tool_calls, indent=2)}",
                            execution_time=0.0
                        ).model_dump_json())
                    
                    if result.tool_results:
                        await websocket.send_json(AgentMessage(
                            agent="WorkerAgent",
                            content=f"Tool results:\n{json.dumps(result.tool_results, indent=2)}",
                            execution_time=0.0
                        ).model_dump_json())
            
            # Now evaluate the result after we have it
            if websocket:
                await websocket.send_json(AgentMessage(
                    agent="AgentEvaluator",
                    content=f"Evaluating {task.agent_name}'s task completion...",
                    execution_time=0.0
                ).model_dump_json())
            
            evaluation = await agent_evaluator.evaluate(task_str, result)
            
            # Send evaluation results via websocket
            if websocket:
                await websocket.send_json(AgentMessage(
                    agent="AgentEvaluator",
                    content=f"Evaluation result for {task.agent_name}: {evaluation}",
                    execution_time=0.0
                ).model_dump_json())
            
            # If evaluation indicates we need to retry, do so
            if evaluation == AgentEvaluation.REITERATE:
                # Update task for retry
                retry_task = f"""Previous task: {task_str}
Previous output: {result.output}
Tool calls: {json.dumps(result.tool_calls, indent=2)}
Tool results: {json.dumps(result.tool_results, indent=2)}

Continue with the task using these results."""
                
                if websocket:
                    await websocket.send_json(AgentMessage(
                        agent="WorkerAgent",
                        content=f"Retrying task...",
                        execution_time=0.0
                    ).model_dump_json())
                
                # Execute retry
                retry_result = await agent.execute_task(retry_task)
                result = retry_result  # Use the retry result
            
            results.append(result)
        
        return results

    async def _send_results_to_websocket(self, results: List[AgentResult], websocket) -> None:
        """Send execution results to websocket"""
        for result in results:
            await websocket.send_json(AgentMessage(
                agent="WorkerAgent",
                content=f"Task execution results:\n{result.output}",
                execution_time=0.0
            ).model_dump_json())
            
            if result.tool_calls:
                await websocket.send_json(AgentMessage(
                    agent=f"WorkerAgent",
                    content=f"Tool calls:\n{json.dumps(result.tool_calls, indent=2)}",
                    execution_time=0.0
                ).model_dump_json())
            
            if result.tool_results:
                await websocket.send_json(AgentMessage(
                    agent="WorkerAgent",
                    content=f"Tool results:\n{json.dumps(result.tool_results, indent=2)}",
                    execution_time=0.0
                ).model_dump_json())

    def _parse_bool_config(self, value: Any) -> bool:
        """Parse a configuration value as a boolean, handling various input types."""
        if isinstance(value, str):
            return value.lower() in ['true', '1', 'yes', 'on']
        return bool(value)

    async def _execute_single_task(
        self,
        agent_name: str,
        agent: WorkerAgent,
        task: Union[str, AgentTask],
        config: Dict[str, Any],
        agent_evaluator: AgentEvaluator,
        websocket=None,
        orchestrator_client=None
    ) -> AgentResult:
        """Execute a single task with retries"""
        iterations = 0
        current_task = task
        task_str = task.task if isinstance(task, AgentTask) else task
        
        
        while iterations < config["max_iterations"]:
            # Get the latest config in case it was updated
            use_agent_planner = self._parse_bool_config(config.get("use_agent_planner", True))
            
            # Execute task with or without planner
            if use_agent_planner:
                # Send planning phase status
                if websocket:
                    await websocket.send_json(AgentMessage(
                        agent="AgentPlanner",
                        content=f"Planning function calls for {agent_name}'s task...",
                        execution_time=0.0
                    ).model_dump_json())
                
                # Create agent-specific planner
                planner = AgentPlanner(
                    client=orchestrator_client,
                    model=config["orchestrator_model"],
                    agent_name=agent_name,
                    tools=agent.tools,
                    worker_agent=agent
                )
                
                # Execute task with planning
                result = await planner.execute_task(current_task)
            else:
                # Execute task directly
                result = await agent.execute_task(current_task)
            
            # Send results via websocket
            if websocket:
                await websocket.send_json(AgentMessage(
                    agent="WorkerAgent",
                    content=f"Task execution results:\n{result.output}",
                    execution_time=0.0
                ).model_dump_json())
                
                if result.tool_calls:
                    tool_calls_str = json.dumps(result.tool_calls, indent=2)
                    await websocket.send_json(AgentMessage(
                        agent="WorkerAgent",
                        content=f"Tool calls:\n{tool_calls_str}",
                        execution_time=0.0
                    ).model_dump_json())
                
                if result.tool_results:
                    tool_results_str = json.dumps(result.tool_results, indent=2)
                    await websocket.send_json(AgentMessage(
                        agent="WorkerAgent",
                        content=f"Tool results:\n{tool_results_str}",
                        execution_time=0.0
                    ).model_dump_json())
            
            # Evaluate result
            if websocket:
                await websocket.send_json(AgentMessage(
                    agent="AgentEvaluator",
                    content=f"Evaluating {agent_name}'s task completion...",
                    execution_time=0.0
                ).model_dump_json())
            
            evaluation = await agent_evaluator.evaluate(task_str, result)
            
            # Send evaluation results via websocket
            if websocket:
                await websocket.send_json(AgentMessage(
                    agent="AgentEvaluator",
                    content=f"Evaluation result for {agent_name}: {evaluation}",
                    execution_time=0.0
                ).model_dump_json())
            
            if evaluation == AgentEvaluation.FINISHED:
                return result
            
            # Update task for next iteration if needed
            current_task = f"""Previous task: {task_str}
Previous output: {result.output}
Tool calls: {json.dumps(result.tool_calls, indent=2)}
Tool results: {json.dumps(result.tool_results, indent=2)}

Continue with the task using these results."""
            
            iterations += 1
            
            if websocket and iterations < config["max_iterations"]:
                await websocket.send_json(AgentMessage(
                    agent="WorkerAgent",
                    content=f"Agent {agent_name} starting new iteration...",
                    execution_time=0.0
                ).model_dump_json())
        
        # If we reach here, we've exhausted all iterations
        return result

    async def query(self, message: str, session: SessionData) -> Response:
        return await self.query_stream(message, session)
    
    async def query_stream(self, message: str, session: SessionData, websocket=None) -> Response:
        """Process a user message using multiple agents"""
        try:
            # Track overall execution time
            overall_start_time = time.time()
            
            # Add message to chat history
            self.chat_history.messages.append(ChatMessage(
                role="user",
                content=message
            ))
            
            # Log initial user message
            if self.log_to_file:
                self._log_non_llm_interaction("User", message)
            
            # Get base config and merge with model config
            config = session.config.get(self.NAME, self.default_config())
            model_config_loader = ModelConfigLoader() 
            model_config = model_config_loader.get_model_config(config.get("model_config_name"))
            config.update(model_config)  # Merge model config into session config
            
            # Create separate clients for orchestration and worker agents
            orchestrator_client = await self._create_openai_client(session, is_worker=False)
            worker_client = await self._create_openai_client(session, is_worker=True)
            
            # Initialize response
            response = Response(query=message)
            
            # Send initial waiting message
            if websocket:
                await websocket.send_json({
                    "agent": "preparing",
                    "content": "Initializing the OPACA AI Agents"
                })
            
            # Get simplified agent summaries for the orchestrator
            agent_summaries = {
                name: data["summary"]
                for name, data in self.agents_data["agents_simple"].items()
            }
            
            # Add GeneralAgent summary
            agent_summaries["GeneralAgent"] = """**Purpose:** The GeneralAgent is designed to handle general queries about system capabilities and provide overall assistance.

**Overview:** This agent can explain the system's features, available agents, and their capabilities. It serves as the primary point of contact for general inquiries and capability questions.

**Goals and Capabilities:** The GeneralAgent can:
1. Explain what the system can do
2. Provide information about available agents and their capabilities
3. Answer general questions about the system"""
            
            # Initialize agents
            orchestrator = OrchestratorAgent(
                client=orchestrator_client,
                model=config["orchestrator_model"],
                agent_summaries=agent_summaries,
                chat_history=self.chat_history  # Pass chat history to orchestrator
            )
            
            # Initialize agents with orchestrator model from model config
            overall_evaluator = OverallEvaluator(orchestrator_client, config["orchestrator_model"])
            output_generator = OutputGenerator(orchestrator_client, config["orchestrator_model"])
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
                if websocket:
                    await websocket.send_json({
                        "agent": "Planning",
                        "content": "Creating detailed execution plan..."
                    })
                
                plan = await orchestrator.create_execution_plan(message)
                
                # Send orchestrator's plan via websocket
                if websocket:
                    # First send the thinking process
                    await websocket.send_json(AgentMessage(
                        agent="Orchestrator",
                        content=f"Thinking process:\n{plan.thinking}",
                        execution_time=0.0
                    ).model_dump_json())
                    
                    # Then send the tasks
                    await websocket.send_json(AgentMessage(
                        agent="Orchestrator",
                        content=f"Created execution plan with {len(plan.tasks)} tasks:\n{json.dumps([task.dict() for task in plan.tasks], indent=2)}\n",
                        execution_time=0.0
                    ).model_dump_json())
                    
                    # Mark planning phase complete
                    await websocket.send_json(AgentMessage(
                        agent="Orchestrator",
                        content="Execution plan created ✓\n\n",
                        execution_time=0.0
                    ).model_dump_json())
                
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
                    if websocket:
                        await websocket.send_json(AgentMessage(
                            agent="Orchestrator",
                            content=f"Starting execution round {round_num}",
                            execution_time=0.0
                        ).model_dump_json())
                    
                    round_results = await self._execute_round(
                        tasks_by_round[round_num],
                        worker_agents,
                        config,
                        all_results,
                        websocket,
                        orchestrator_client
                    )
                    
                    all_results.extend(round_results)
                
                # Evaluate overall progress
                evaluation = await overall_evaluator.evaluate(
                    f"{message}\n\nKeep in mind: The OutputGenerator will summarize all results at the end of the pipeline. If the necessary information exists in the results (even if not perfectly formatted), choose FINISHED.",
                    all_results
                )
                
                if websocket:
                    await websocket.send_json(AgentMessage(
                        agent="OverallEvaluator",
                        content="Overall evaluation...",
                        execution_time=0.0
                    ).model_dump_json())

                    await websocket.send_json(AgentMessage(
                        agent="OverallEvaluator",
                        content=f"Overall evaluation result: {evaluation}",
                        execution_time=0.0
                    ).model_dump_json())
                    
                    await websocket.send_json(AgentMessage(
                        agent="OverallEvaluator",
                        content="Overall evaluation complete ✓",
                        execution_time=0.0
                    ).model_dump_json())
                
                if evaluation == OverallEvaluation.REITERATE:
                    # Get iteration advice before continuing
                    if websocket:
                        await websocket.send_json(AgentMessage(
                            agent="IterationAdvisor",
                            content="Analyzing results and preparing advice for next iteration...",
                            execution_time=0.0
                        ).model_dump_json())
                    
                    advice = await iteration_advisor.get_advice(
                        f"{message}\n\nKeep in mind: The OutputGenerator will summarize all results at the end of the pipeline. Only suggest retrying if CRITICAL information is completely missing from the results.",
                        all_results
                    )
                    
                    if websocket:
                        await websocket.send_json(AgentMessage(
                            agent="IterationAdvisor",
                            content=f"Iteration Advice:\n{json.dumps(advice.dict(), indent=2)}",
                            execution_time=0.0
                        ).model_dump_json())
                    
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
                        if websocket:
                            await websocket.send_json(AgentMessage(
                                agent="IterationAdvisor",
                                content="Tasks completed successfully. Proceeding to final output with the following summary:\n\n" + advice.context_summary,
                                execution_time=0.0
                            ).model_dump_json())
                        break
                    
                    # Add the advice to the message for the next iteration
                    message = f"""Original request: {message}

Previous iteration summary: {advice.context_summary}

Issues identified:
{chr(10).join(f'- {issue}' for issue in advice.issues)}

Please address these specific improvements:
{chr(10).join(f'- {step}' for step in advice.improvement_steps)}"""
                    
                    if websocket:
                        await websocket.send_json(AgentMessage(
                            agent="IterationAdvisor",
                            content="Proceeding with next iteration using provided advice ✓",
                            execution_time=0.0
                        ).model_dump_json())
                else:
                    break
                
                rounds += 1
            
            # Generate final output with streaming
            if websocket:
                await websocket.send_json(AgentMessage(
                    agent="OutputGenerator",
                    content="Generating final response...",
                    execution_time=0.0
                ).model_dump_json())
            
            # Stream the final response
            messages = [{
                "role": "system",
                "content": OUTPUT_GENERATOR_PROMPT
            }, {
                "role": "user",
                "content": f"Based on the following execution results, please provide a clear response to this user request: {message}\n\nExecution results:\n{json.dumps([r.dict() for r in all_results], indent=2)}"
            }]
            
            # Use worker model and client if configured
            use_worker_for_output = self._parse_bool_config(config.get("use_worker_for_output", True))
            output_client = worker_client if use_worker_for_output else orchestrator_client
            output_model = config["worker_model"] if use_worker_for_output else config["orchestrator_model"]
            
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
                    if websocket:
                        await websocket.send_json(AgentMessage(
                            agent="assistant",
                            content=content,
                            execution_time=0.0
                        ).model_dump_json())
            
            # Set the complete response content after streaming
            response.content = "".join(final_output)
            
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
            if websocket:
                await websocket.send_json(AgentMessage(
                    agent="OutputGenerator",
                    content="Final response generated ✓",
                    execution_time=0.0
                ).model_dump_json())
            
            # Store agent messages for debug view and add execution time
            response.agent_messages = [
                AgentMessage(
                    agent=result.agent_name,
                    content=result.output,
                    execution_time=result.agent_message.execution_time if result.agent_message else 0.0
                )
                for result in all_results
            ]
            
            # Set the total execution time in the response
            response.execution_time = total_execution_time

            self.logger.info(f"\n\n TOTAL EXECUTION TIME: \nMultiAgentBackend completed analysis in {total_execution_time:.2f} seconds\n\n")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error in query_stream: {str(e)}", exc_info=True)
            response.error = str(e)
            if websocket:
                await websocket.send_json(AgentMessage(
                    agent="system",
                    content=f"Error: {str(e)}",
                    execution_time=0.0
                ).model_dump_json())
            # Log error
            self._log_non_llm_interaction("System", f"Error: {str(e)}")
            return response

    def enable_file_logging(self, log_file_path: str):
        """Enable logging to a file for multi-agent interactions"""
        self.log_to_file = True
        self.log_file = log_file_path

    def disable_file_logging(self):
        """Disable logging to file"""
        self.log_to_file = False
        self.log_file = None

    def _save_session_log(self):
        """Save the complete session log to file if logging is enabled"""
        if self.log_to_file and self.log_file and self.current_session_log:
            try:
                with open(self.log_file, 'a') as f:
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
        try:
            with open(self.log_file, 'a') as f:
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