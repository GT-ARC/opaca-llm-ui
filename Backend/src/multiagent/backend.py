import json
import os
import logging
import asyncio
from typing import Dict, Any, List
from pathlib import Path

from openai import AsyncOpenAI

from .prompts import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    AGENT_SYSTEM_PROMPT,
    AGENT_EVALUATOR_PROMPT,
    OVERALL_EVALUATOR_PROMPT,
    OUTPUT_GENERATOR_PROMPT,
)

from ..models import OpacaLLMBackend, Response, SessionData, AgentMessage
from .agents import (
    OrchestratorAgent,
    WorkerAgent,
    AgentEvaluator,
    OverallEvaluator,
    OutputGenerator,
    GeneralAgent,
)
from .models import AgentEvaluation, OverallEvaluation, AgentResult

class MultiAgentBackend(OpacaLLMBackend):
    NAME = "multi-agent"
    
    def __init__(self, agents_file: str = "agents_tools.json"):
        # Look for the file in the Backend directory
        self.agents_file = Path(__file__).parent.parent.parent / agents_file
        if not self.agents_file.exists():
            raise FileNotFoundError(
                f"Agents file not found: {self.agents_file}. "
                "Please run get_agents_tools.py first."
            )
        
        with open(self.agents_file) as f:
            self.agents_data = json.load(f)
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
    @property
    def default_config(self) -> Dict[str, Any]:
        return {
            "model": "Mistral-Small-Instruct-2409-FP8-Dynamic",
            "temperature": 0,
            "max_rounds": 5,  # Maximum number of orchestration rounds
            "max_iterations": 3,  # Maximum iterations per agent task
            "base_url": "http://10.0.64.101:8000/v1",  # Base URL for the API (e.g., vLLM server)
            "backend_type": "vllm",  # Can be 'openai' or 'vllm'
        }
    
    async def _create_openai_client(self, session: SessionData) -> AsyncOpenAI:
        """Create OpenAI client with appropriate configuration"""
        try:
            config = session.config.get(self.NAME, self.default_config)

            # Add base_url if specified in config or if using vLLM
            if config["base_url"]:
                base_url = config["base_url"]
                api_key = session.api_key or os.getenv("OPENAI_API_KEY")
            elif config["backend_type"] == "vllm":
                base_url = os.getenv("VLLM_BASE_URL", "http://10.0.64.101:8000/v1")
                api_key = session.api_key or os.getenv("VLLM_API_KEY")
            
            
            if not api_key:
                raise ValueError("No OpenAI API key found in session or environment")
            
            # Initialize kwargs with api_key
            kwargs = {"api_key": api_key}
            kwargs["base_url"] = base_url
            

            
            client = AsyncOpenAI(**kwargs)
            return client
        except Exception as e:
            self.logger.error(f"Error creating OpenAI client: {str(e)}")
            raise

    async def _create_chat_completion(self, client: AsyncOpenAI, messages: List[Dict], config: Dict, stream: bool = False) -> Any:
        """Create a chat completion with proper structured output handling for both OpenAI and vLLM"""
        try:
            # Common parameters
            kwargs = {
                "model": config["model"],
                "messages": messages.copy(),  # Make a copy to avoid modifying the original
                "temperature": config["temperature"],
                "stream": stream
            }
            
            # Check if we're using a GPT model
            is_gpt = "gpt" in config["model"].lower()
            self.logger.info(f"Using {'OpenAI GPT' if is_gpt else 'vLLM'} model")
            
            if is_gpt:  # Using OpenAI API
                kwargs["response_format"] = {"type": "json_object"}
                # Add instruction to generate JSON in the system message
                if kwargs["messages"] and kwargs["messages"][0]["role"] == "system":
                    kwargs["messages"][0]["content"] = kwargs["messages"][0]["content"] + "\nPlease provide your response in JSON format with 'steps' (array of objects with 'explanation' and 'output') and 'final_answer' fields."
            else:  # Using vLLM
                kwargs["extra_body"] = {
                    "guided_json": {
                        "type": "object",
                        "properties": {
                            "steps": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "explanation": {"type": "string"},
                                        "output": {"type": "string"}
                                    },
                                    "required": ["explanation", "output"],
                                    "additionalProperties": False
                                }
                            },
                            "final_answer": {"type": "string"}
                        },
                        "required": ["steps", "final_answer"],
                        "additionalProperties": False
                    }
                }
            
            return await client.chat.completions.create(**kwargs)
        except Exception as e:
            self.logger.error(f"Error creating chat completion: {str(e)}")
            raise

    async def _execute_round(
        self,
        round_tasks: List[Dict],
        worker_agents: Dict[str, WorkerAgent],
        agent_evaluator: AgentEvaluator,
        config: Dict[str, Any],
        all_results: List[AgentResult],
        websocket=None
    ) -> List[AgentResult]:
        """Execute a single round of tasks in parallel when possible"""
        results = []
        
        # Create tasks for parallel execution
        tasks = []
        for task in round_tasks:
            agent = worker_agents[task["agent_name"]]
            current_task = task["task"]
            
            # Add context from dependent tasks if needed
            if task.get("dependencies"):
                dependent_results = []
                for dep in task["dependencies"]:
                    # Find the most recent result from the dependent agent
                    for result in reversed(all_results):
                        if result.agent_name == dep:
                            dependent_results.append(result)
                            break
                
                if dependent_results:
                    context = "\n\nPrevious task results:\n"
                    for dep_result in dependent_results:
                        context += f"\nAgent {dep_result.agent_name}:\n"
                        context += f"Task: {dep_result.task}\n"
                        context += f"Output: {dep_result.output}\n"
                        if dep_result.tool_calls:
                            context += f"Tool calls: {json.dumps(dep_result.tool_calls, indent=2)}\n"
                        if dep_result.tool_results:
                            context += f"Tool results: {json.dumps(dep_result.tool_results, indent=2)}\n"
                    current_task = current_task + context
            
            # Create coroutine for this task's execution
            tasks.append(self._execute_single_task(
                task["agent_name"],
                agent,
                current_task,
                config,
                agent_evaluator,
                websocket
            ))
        
        # Execute all tasks in parallel and gather results
        if tasks:
            results.extend(await asyncio.gather(*tasks))
        
        return results
    
    async def _execute_single_task(
        self,
        agent_name: str,
        agent: WorkerAgent,
        task: str,
        config: Dict[str, Any],
        agent_evaluator: AgentEvaluator,
        websocket=None
    ) -> AgentResult:
        """Execute a single task with retries"""
        iterations = 0
        current_task = task
        
        while iterations < config["max_iterations"]:
            # Send worker agent status
            if websocket:
                await websocket.send_json(AgentMessage(
                    agent="WorkerAgent",
                    content=f"Agent {agent_name} is working on task..."
                ).model_dump_json())
            
            # Execute task
            result = await agent.execute_task(current_task)
            
            # Log tool calls and results (terminal only)
            if result.tool_calls:
                self.logger.info(f"\n=== Tool Calls for {agent_name} ===\n{json.dumps(result.tool_calls, indent=2)}")
            if result.tool_results:
                self.logger.info(f"\n=== Tool Results for {agent_name} ===\n{json.dumps(result.tool_results, indent=2)}")
            
            # Send results via websocket
            if websocket:
                await websocket.send_json(AgentMessage(
                    agent=agent_name,
                    content=f"Task: {current_task}\nOutput: {result.output}"
                ).model_dump_json())
                
                if result.tool_calls:
                    tool_calls_str = json.dumps(result.tool_calls, indent=2)
                    await websocket.send_json(AgentMessage(
                        agent=f"{agent_name}-Tools",
                        content=f"Tool calls:\n{tool_calls_str}"
                    ).model_dump_json())
                
                if result.tool_results:
                    tool_results_str = json.dumps(result.tool_results, indent=2)
                    await websocket.send_json(AgentMessage(
                        agent=agent_name,
                        content=f"Tool results:\n{tool_results_str}"
                    ).model_dump_json())
                
                await websocket.send_json(AgentMessage(
                    agent="WorkerAgent",
                    content=f"Agent {agent_name} completed task ✓"
                ).model_dump_json())
                await websocket.send_json(AgentMessage(
                    agent=agent_name,
                    content=f"Task completed ✓"
                ).model_dump_json())
            
            # Evaluate result
            evaluation = await agent_evaluator.evaluate(current_task, result)
            
            # Log evaluation result (terminal only)
            self.logger.info(f"\n=== Evaluation Result for {agent_name} ===\n{evaluation}")
            
            # Send evaluation results
            if websocket:
                await websocket.send_json(AgentMessage(
                    agent="AgentEvaluator",
                    content=f"Evaluation result for {agent_name}: {evaluation}"
                ).model_dump_json())
                
                await websocket.send_json(AgentMessage(
                    agent="AgentEvaluator",
                    content="Task evaluation complete ✓"
                ).model_dump_json())
            
            if evaluation == AgentEvaluation.COMPLETE:
                return result
            
            # Update task for next iteration
            current_task = f"""Previous task: {current_task}
Previous output: {result.output}
Tool calls: {json.dumps(result.tool_calls, indent=2)}
Tool results: {json.dumps(result.tool_results, indent=2)}

Continue with the task using these results."""
            
            iterations += 1
            
            if websocket and iterations < config["max_iterations"]:
                await websocket.send_json(AgentMessage(
                    agent="WorkerAgent",
                    content=f"Agent {agent_name} starting new iteration..."
                ).model_dump_json())
                await websocket.send_json(AgentMessage(
                    agent=agent_name,
                    content=f"Starting iteration {iterations + 1} for task: {task}"
                ).model_dump_json())
        
        # If we reach here, we've exhausted all iterations
        return result  # Return the last result even if not complete

    async def query(self, message: str, session: SessionData) -> Response:
        return await self.query_stream(message, session)
    
    async def query_stream(self, message: str, session: SessionData, websocket=None) -> Response:
        """Process a query using the multi-agent system"""
        try:
            config = session.config.get(self.NAME, self.default_config)
            client = await self._create_openai_client(session)
            
            # Initialize response
            response = Response(query=message)
            
            # Send initial waiting message
            if websocket:
                await websocket.send_json(AgentMessage(
                    agent="preparing",
                    content="Initializing the OPACA AI Agents"
                ).model_dump_json())
            
            # Extract just the summaries from agents_simple
            agent_summaries = {
                name: data["summary"]  # Pass summary directly without extra nesting
                for name, data in self.agents_data["agents_simple"].items()
            }
            
            # Add GeneralAgent summary
            agent_summaries["GeneralAgent"] = """**Purpose:** The GeneralAgent is designed to handle general queries about system capabilities and provide overall assistance.

**Overview:** This agent can explain the system's features, available agents, and their capabilities. It serves as the primary point of contact for general inquiries and capability questions.

**Goals and Capabilities:** The GeneralAgent can:
1. Explain what the system can do
2. Provide information about available agents and their capabilities
3. Answer general questions about the system
4. Help users understand how to best utilize the system"""
            
            # Initialize agents
            orchestrator = OrchestratorAgent(
                client=client,
                model=config["model"],
                agent_summaries=agent_summaries
            )
            
            # Initialize evaluators and output generator
            agent_evaluator = AgentEvaluator(client, config["model"])
            overall_evaluator = OverallEvaluator(client, config["model"])
            output_generator = OutputGenerator(client, config["model"])
            
            # Add GeneralAgent to available worker agents
            worker_agents = {
                "GeneralAgent": GeneralAgent(
                    client=client,
                    model=config["model"],
                    agent_summaries=agent_summaries  # Use the same simplified summaries
                )
            }
            
            all_results = []
            rounds = 0
            
            while rounds < config["max_rounds"]:
                # Get execution plan from orchestrator
                plan = await orchestrator.create_execution_plan(message)
                
                # Log orchestrator plan
                self.logger.info(f"\n=== Orchestrator Plan ===\n{json.dumps(plan.dict(), indent=2)}")
                
                if websocket:
                    await websocket.send_json(AgentMessage(
                        agent="Orchestrator",
                        content=f"Execution plan created with {len(plan.tasks)} tasks:\n{json.dumps(plan.dict(), indent=2)}"
                    ).model_dump_json())
                
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
                        agent_functions = []
                        agent_tools = []
                        
                        # Create tools list for the agent
                        for func in self.agents_data["agents_detailed"]:
                            if func["function"]["name"].startswith(f"{agent_name}--"):
                                # Create a copy of the function for the tools list (sent to OpenAI/vLLM)
                                agent_tools.append(func.copy())
                                # Create a copy with the session client for internal use
                                tool_with_client = func.copy()
                                tool_with_client["session_client"] = session.client
                                agent_functions.append(tool_with_client)
                        
                        # Verify we have instructions
                        if "instructions" not in agent_data:
                            self.logger.error(f"Missing instructions for agent {agent_name}")
                            raise ValueError(f"Agent {agent_name} is missing required instructions")
                        
                        worker_agents[agent_name] = WorkerAgent(
                            client=client,
                            model=config["model"],
                            agent_name=agent_name,
                            instructions=agent_data["instructions"],
                            tools=agent_tools,
                            internal_tools=agent_functions
                        )
                
                # Group tasks by round
                tasks_by_round = {}
                for task in plan.tasks:
                    tasks_by_round.setdefault(task.round, []).append(task.dict())
                
                # Execute each round
                for round_num in sorted(tasks_by_round.keys()):
                    if websocket:
                        await websocket.send_json(AgentMessage(
                            agent="Orchestrator",
                            content=f"Starting execution round {round_num}"
                        ).model_dump_json())
                    
                    round_results = await self._execute_round(
                        tasks_by_round[round_num],
                        worker_agents,
                        agent_evaluator,
                        config,
                        all_results,
                        websocket
                    )
                    all_results.extend(round_results)
                
                # Evaluate overall progress
                evaluation = await overall_evaluator.evaluate(message, all_results)
                
                if websocket:
                    await websocket.send_json(AgentMessage(
                        agent="OverallEvaluator",
                        content="Overall evaluation..."
                    ).model_dump_json())

                    await websocket.send_json(AgentMessage(
                        agent="OverallEvaluator",
                        content=f"Overall evaluation result: {evaluation}"
                    ).model_dump_json())
                    
                    # Send completion message for overall evaluator
                    await websocket.send_json(AgentMessage(
                        agent="OverallEvaluator",
                        content="Overall evaluation complete ✓"
                    ).model_dump_json())
                
                if evaluation == OverallEvaluation.FINISHED:
                    break
                
                rounds += 1
            
            # Generate final output with streaming
            if websocket:
                await websocket.send_json(AgentMessage(
                    agent="OutputGenerator",
                    content="Generating final response..."
                ).model_dump_json())
            
            # Stream the final response
            messages = [{
                "role": "system",
                "content": OUTPUT_GENERATOR_PROMPT
            }, {
                "role": "user",
                "content": f"Based on the following execution results, please provide a clear response to this user request: {message}\n\nExecution results:\n{json.dumps([r.dict() for r in all_results], indent=2)}"
            }]

            # Simple streaming text request without any special constraints
            stream = await client.chat.completions.create(
                model=config["model"],
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
                            content=content
                        ).model_dump_json())
            
            # Set the complete response content after streaming
            response.content = "".join(final_output)
            
            # Send completion message for output generator
            if websocket:
                await websocket.send_json(AgentMessage(
                    agent="OutputGenerator",
                    content="Final response generated ✓"
                ).model_dump_json())
            
            # Store agent messages for debug view
            response.agent_messages = [
                AgentMessage(
                    agent=result.agent_name,
                    content=result.output
                )
                for result in all_results
            ]
            
        except Exception as e:
            self.logger.error(f"Error in query_stream: {str(e)}", exc_info=True)
            response.error = str(e)
            if websocket:
                await websocket.send_json(AgentMessage(
                    agent="system",
                    content=f"Error: {str(e)}"
                ).model_dump_json())
        
        return response 