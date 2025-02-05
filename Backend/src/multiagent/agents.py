from __future__ import annotations
import json
from typing import Dict, Any, List, Optional, Union
from openai import AsyncOpenAI
import logging
from pydantic import BaseModel, Field
import time
import asyncio

from ..models import AgentMessage
from .models import (
    AgentTask, OrchestratorPlan, PlannerPlan, AgentEvaluation, 
    OverallEvaluation, AgentResult, IterationAdvice, ChatHistory
)
from .prompts import (
    BACKGROUND_INFO,
    ORCHESTRATOR_SYSTEM_PROMPT,
    AGENT_SYSTEM_PROMPT,
    AGENT_EVALUATOR_PROMPT,
    OVERALL_EVALUATOR_PROMPT,
    OUTPUT_GENERATOR_PROMPT,
    GENERAL_CAPABILITIES_RESPONSE,
    ITERATION_ADVISOR_PROMPT,
    AGENT_PLANNER_PROMPT,
)



class BaseAgent:
    def __init__(self, client: AsyncOpenAI, model: str):
        self.client = client
        self.model = model
        self.logger = logging.getLogger(__name__)
        self.chat_history = None
        self.log_file = "agents.log"  # Default log file path

    def _log_llm_interaction(self, agent_name: str, messages: List[Dict[str, str]], response_content: str) -> None:
        """Log an LLM interaction to the log file with clear separation of system prompt, user input, and response"""
        try:
            with open(self.log_file, 'a') as f:
                # Write agent header
                f.write(f"\n{'=' * 35} {agent_name} LLM Call {'=' * 35}\n\n")
                
                # Write messages in order
                for msg in messages:
                    role = msg["role"].upper()
                    f.write(f"{'-' * 35} {role} MESSAGE {'-' * 35}\n\n")
                    f.write(f"{msg['content']}\n\n")
                
                # Write response
                f.write(f"{'-' * 35} ASSISTANT RESPONSE {'-' * 35}\n\n")
                f.write(f"{response_content}\n\n\n")
                
                # Write separator
                f.write(f"{'=' * 90}\n\n")
        except Exception as e:
            self.logger.error(f"Error writing to log file: {str(e)}")

    async def _call_llm(
        self,
        messages: List[Dict[str, str]],
        guided_choice: Optional[List[str]] = None,
        guided_json: Optional[Dict] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None
    ) -> Any:
        """Generic method to call the LLM with various guidance options"""
        start_time = time.time()
        try:
            logger = logging.getLogger(__name__)
            
            # Check if we're using a GPT model
            is_gpt = "gpt" in self.model.lower() or "o3" in self.model.lower()
            
            if self.model == "o3-mini":
                # Base kwargs that are always included
                kwargs = {
                    "model": self.model,
                    "messages": messages.copy(),  # Make a copy to avoid modifying the original
                }
                if tools: 
                    kwargs["reasoning_effort"] = "medium"
                else:
                    kwargs["reasoning_effort"] = "high"

            else:
                # Base kwargs that are always included
                kwargs = {
                    "model": self.model,
                    "messages": messages.copy(),  # Make a copy to avoid modifying the original
                    "temperature": 0.0  # Always use temperature 0 for deterministic outputs
                }



            # Handle tool calls first since they're simpler
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice or "auto"
                #return await self.client.chat.completions.create(**kwargs)

                # self.logger.info("\n\n\n")
                # self.logger.info("TOOLS: ", tools)
                # self.logger.info("\n\n\n")

                completion = await self.client.chat.completions.create(**kwargs)
                response = completion.choices[0].message
                
                # Log the LLM interaction
                self._log_llm_interaction(
                    self.__class__.__name__,  # Use the class name as agent name
                    kwargs["messages"],
                    json.dumps(response.model_dump(), indent=2)
                )
                
                return response
                
            # Handle guided outputs for non-tool calls
            if guided_choice:
                if is_gpt:
                    # For OpenAI, add instruction to choose from options
                    if kwargs["messages"] and kwargs["messages"][0]["role"] == "system":
                        options_str = ", ".join(guided_choice)
                        kwargs["messages"][0]["content"] = kwargs["messages"][0]["content"] + f"\nPlease choose exactly one of these options: {options_str}"
                else:
                    # For vLLM, keep original system prompt and add choice options
                    system_msg = kwargs["messages"][0]["content"] if kwargs["messages"] else ""
                    options_str = ", ".join(guided_choice)
                    system_msg = f"{system_msg}\n\nYou must choose exactly one of these options: {options_str}"
                    
                    # Move everything except the actual task/query to system message
                    user_msg = kwargs["messages"][-1]["content"] if len(kwargs["messages"]) > 1 else ""
                    
                    kwargs["messages"] = [
                        {
                            "role": "system",
                            "content": system_msg
                        },
                        {
                            "role": "user",
                            "content": user_msg
                        }
                    ]
                    kwargs["extra_body"] = {"guided_choice": guided_choice}
            elif guided_json:
                if is_gpt:
                    # For OpenAI, use json_object mode and add schema to system message
                    kwargs["response_format"] = {"type": "json_object"}
                    if kwargs["messages"] and kwargs["messages"][0]["role"] == "system":
                        schema_str = json.dumps(guided_json, indent=2)
                        kwargs["messages"][0]["content"] = kwargs["messages"][0]["content"] + f"\nPlease provide your response in JSON format following this schema:\n{schema_str}"
                else:
                    # For vLLM, keep original system prompt and add JSON schema
                    system_msg = kwargs["messages"][0]["content"] if kwargs["messages"] else ""
                    schema_str = json.dumps(guided_json, indent=2)
                    system_msg = f"{system_msg}\n\nYou must provide your response in JSON format following this schema:\n{schema_str}"
                    
                    # Move everything except the actual task/query to system message
                    user_msg = kwargs["messages"][-1]["content"] if len(kwargs["messages"]) > 1 else ""
                    
                    kwargs["messages"] = [
                        {
                            "role": "system",
                            "content": system_msg
                        },
                        {
                            "role": "user",
                            "content": user_msg
                        }
                    ]
                    kwargs["extra_body"] = {"guided_json": guided_json}
            
            response = await self.client.chat.completions.create(**kwargs)
            
            # Log the LLM interaction
            self._log_llm_interaction(
                self.__class__.__name__,  # Use the class name as agent name
                kwargs["messages"],
                response.choices[0].message.content
            )
            
            return response.choices[0].message
        finally:
            execution_time = time.time() - start_time
            self.logger.debug(f"LLM call took {execution_time:.2f} seconds")

class OrchestratorAgent(BaseAgent):
    def __init__(self, client: AsyncOpenAI, model: str, agent_summaries: Dict[str, Any], chat_history: Optional[ChatHistory] = None):
        super().__init__(client, model)
        self.agent_summaries = agent_summaries
        self.chat_history = chat_history
    
    async def create_execution_plan(self, user_request: str) -> OrchestratorPlan:
        """Create an execution plan for the user's request"""
        # Prepare chat history context if available
        chat_context = ""
        if self.chat_history and self.chat_history.messages:
            # Get last 5 messages for context
            recent_messages = self.chat_history.messages[-5:]
            chat_context = "\n\nRecent chat history:\n"
            for msg in recent_messages:
                chat_context += f"{msg.role}: {msg.content}\n"
        
        messages = [
            {
                "role": "system",
                "content": BACKGROUND_INFO + ORCHESTRATOR_SYSTEM_PROMPT.format(
                    agent_summaries=json.dumps(self.agent_summaries, indent=2)
                ) + """\n\nIMPORTANT: Provide your response as a raw JSON object, not wrapped in markdown code blocks."""
            },
            {
                "role": "user",
                "content": f"""Create an execution plan for this request: \n {user_request} \n\n 
Consider the chat history if applicable: \n {chat_context} \n\n
Keep in mind that there is an output generating LLM-Agent at the end of the chain.
If the user request requires a summary, no seperate agent or function is needed for that, as the output generating agent will do that!"""
            }
        ]
        
        response = await self._call_llm(
            messages=messages,
            guided_json=OrchestratorPlan.model_json_schema()
        )
        
        # Clean up the response if it's wrapped in markdown code blocks
        content = response.content
        if content.startswith("```") and content.endswith("```"):
            # Remove markdown code blocks
            content = content.strip("`").strip()
            # Remove language identifier if present (e.g., "json")
            if content.startswith("json\n"):
                content = content[5:]
            elif "\n" in content:
                content = content[content.find("\n")+1:]
        
        return OrchestratorPlan.model_validate_json(content)

class GeneralAgent(BaseAgent):
    """Agent that handles general capability questions without using tools."""
    
    def __init__(self, client: AsyncOpenAI, model: str, agent_summaries: Dict[str, Any], config: Dict[str, Any] = None):
        # Use worker_model from config if available, otherwise fall back to default model
        if config and "worker_model" in config:
            model = config["worker_model"]
        super().__init__(client, model)
        self.agent_name = "GeneralAgent"
        self.tools = []  # Empty list since GeneralAgent doesn't use real tools
        
        # Store the complete response with agent summaries as JSON
        self.predefined_response = BACKGROUND_INFO + GENERAL_CAPABILITIES_RESPONSE.format(
            agent_capabilities=json.dumps(agent_summaries, indent=2)
        )
        
    async def execute_task(self, task: Union[str, AgentTask]) -> AgentResult:
        """Execute a task by returning predefined capabilities"""
        task_str = task.task if isinstance(task, AgentTask) else task
        tool_call = {
            "name": "GetCapabilities",
            "arguments": "{}"
        }
        
        tool_result = {
            "name": "GetCapabilities",
            "result": self.predefined_response
        }
        
        return AgentResult(
            agent_name=self.agent_name,
            task=task_str,
            output="Retrieved system capabilities",  # Keep output minimal since data is in tool result
            tool_calls=[tool_call],
            tool_results=[tool_result]
        )

class AgentPlannerResult(BaseModel):
    """Model for storing agent planner results"""
    thinking: List[str] = Field(..., description="Step by step thinking process")
    function_calls: List[Dict[str, Any]] = Field(..., description="List of planned function calls")
    needs_follow_up: bool = Field(default=False, description="Whether follow-up information is needed")
    follow_up_question: Optional[str] = Field(default=None, description="Follow-up question if needed")

class PlannerOutput(BaseModel):
    """Model for the planner's structured output"""
    reasoning: str = Field(..., description="Short and precise thinking process on how to solve the task")
    execution_steps: List[Dict[str, Any]] = Field(..., description="List of concrete function calls to make, in sequential order if they depend on each other")
    sequential: bool = Field(default=False, description="Whether the steps must be executed in sequence")

class AgentPlanner(BaseAgent):
    """Agent-specific planner that creates high-level task plans."""
    
    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        agent_name: str,
        tools: List[Dict],
        worker_agent: "WorkerAgent",
        config: Dict[str, Any] = None
    ):
        super().__init__(client, model)
        self.agent_name = agent_name
        self.tools = tools
        self.worker_agent = worker_agent
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
    
    async def create_plan(self, task: Union[str, AgentTask], previous_results: Optional[List[AgentResult]] = None) -> PlannerPlan:
        """Create a high-level task plan with rounds and dependencies."""
        task_str = task.task if isinstance(task, AgentTask) else task
        
        # Create context from previous results if available
        context = ""
        if previous_results:
            context = "\n\nPrevious execution results:\n"
            for i, result in enumerate(previous_results, 1):
                context += f"\n# Result {i} from {result.agent_name}:\n"
                context += f"# Task:\n {result.task}\n"
                context += f"# Output:\n {result.output}\n"

                # No longer needed as we show the tool results in the output
                # if result.tool_results:
                #     context += f"# Tool Results:\n {json.dumps(result.tool_results, indent=2)}\n"
        
        remark = ""
        if self.agent_name == "exchange-agent":
            remark = """\n\nIMPORTANT: 
- If you need to retrieve the next meeting info, retrieve my upcoming appointments for the next 7 days!
- If you need to retrieve phone numbers, always try to use email addresses where possible!
- If you need to retrieve email addresses, always use 'umlauts' in the name (like 'ä', 'ö', 'ü' - Tobias Kuester would be Tobias Küster in that case)!"""
        elif self.agent_name == "DataVisAgent":
            remark = """\n\nIMPORTANT: 
- THE VALUES FOR THE X AND Y AXIS MUST BE NUMERIC!
- At the moment you cannot pass string labels for the x or y axis!
- Since there can never be labels for the x-axis, you have to include information about which element in the chart belongs to which label.

EXAMPLE: 
- If the user asks for a visualization of temperature in kitchen and coworking space, the x values should be 0 and 1.
- The title of this chart should be 'Temperature in kitchen (left) and coworking space (right)' or Temperature in kitchen (0) and coworking space (1)."""
        
        messages = [{
            "role": "system",
            "content": BACKGROUND_INFO + AGENT_PLANNER_PROMPT + f"""

THE AVAILABLE FUNCTIONS OF YOUR WORKER AGENT ARE:

{json.dumps(self.tools, indent=2)}

IMPORTANT: Provide your response as a raw JSON object, not wrapped in markdown code blocks."""
        }, {
            "role": "user",
            "content": f"""Create a plan that breaks down this task into subtasks ONLY if necessary: {task_str.strip()}

{context}

Remember: 
1. If this task can be done with a single tool call, DO NOT break it down into subtasks.
2. If you have results from previous tasks, use the CONCRETE VALUES from those results in your task descriptions.
3. NEVER use placeholders - always use actual values.
4. Be extreamly careful with the data types you use for the function arguments. ALWAYS USE THE CORRECT DATA TYPE!

{remark}"""
        }]
        
        response = await self._call_llm(
            messages=messages,
            guided_json=PlannerPlan.model_json_schema()
        )
        
        # Clean up the response if it's wrapped in markdown code blocks
        content = response.content
        if content.startswith("```") and content.endswith("```"):
            # Remove markdown code blocks
            content = content.strip("`").strip()
            # Remove language identifier if present (e.g., "json")
            if content.startswith("json\n"):
                content = content[5:]
            elif "\n" in content:
                content = content[content.find("\n")+1:]
        
        return PlannerPlan.model_validate_json(content)

    async def execute_task(self, task: Union[str, AgentTask], existing_plan: Optional[PlannerPlan] = None) -> AgentResult:
        """Execute a task with or without planning"""
        try:
            # Extract task string if AgentTask object is passed
            task_str = task.task if isinstance(task, AgentTask) else task
            self.logger.info(f"AgentPlanner executing task: {task_str}")
            
            # If planning is disabled, execute directly
            if not self.config.get("use_agent_planner", True):
                self.logger.info("Planning disabled, executing directly with worker agent")
                return await self.worker_agent.execute_task(task_str)

            elif self.agent_name == "GeneralAgent":
                self.logger.info("Skipping planning for GeneralAgent. Directly executing task: " + task_str)
                return await self.worker_agent.execute_task(task_str)
            
            # Use existing plan or create new one
            plan = existing_plan if existing_plan else await self.create_plan(task_str)
            
            # Execute tasks by round
            all_results = []
            round_results_by_num = {}  # Store results by round number
            
            # Group tasks by round
            tasks_by_round = {}
            for subtask in plan.tasks:
                tasks_by_round.setdefault(subtask.round, []).append(subtask)
            
            # Execute each round in sequence
            for round_num in sorted(tasks_by_round.keys()):
                self.logger.info(f"AgentPlanner executing round {round_num}")
                round_tasks = tasks_by_round[round_num]
                
                # Execute tasks in this round in parallel
                tasks = []
                for subtask in round_tasks:
                    current_task = subtask.task
                    self.logger.info(f"AgentPlanner preparing subtask: {current_task}")
                    
                    # Add context from all previous rounds
                    if round_num > 1:
                        context = "\n\nPrevious round results:\n"
                        for prev_round in range(1, round_num):
                            if prev_round in round_results_by_num:
                                context += f"\nResults from round {prev_round}:\n"
                                for prev_result in round_results_by_num[prev_round]:
                                    context += f"\nAgent {prev_result.agent_name}:\n"
                                    context += f"Task: {prev_result.task}\n"
                                    context += f"Output: {prev_result.output}\n"
                        current_task = current_task + context
                    
                    # Pass the task to the worker agent
                    tasks.append(self.worker_agent.execute_task(current_task))
                
                # Execute all tasks in this round
                if tasks:
                    round_results = await asyncio.gather(*tasks)
                    all_results.extend(round_results)
                    round_results_by_num[round_num] = round_results
                    self.logger.debug(f"AgentPlanner completed round {round_num} with {len(round_results)} results")
            
            # Combine all results
            combined_output = "\n".join(r.output for r in all_results)
            combined_tool_calls = [tc for r in all_results for tc in r.tool_calls]
            combined_tool_results = [tr for r in all_results for tr in r.tool_results]
            
            self.logger.debug(f"AgentPlanner completed all rounds with {len(all_results)} total results")
            
            # Create a result that includes both planner and worker information
            result = AgentResult(
                agent_name=self.worker_agent.agent_name,  # Use worker agent's name for proper attribution
                task=task_str,  # Use the original task string
                output=combined_output,
                tool_calls=combined_tool_calls,
                tool_results=combined_tool_results
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in planner execution: {str(e)}")
            return AgentResult(
                agent_name=self.worker_agent.agent_name,  # Use worker agent's name for proper attribution
                task=task_str,  # Use the original task string
                output=f"Error in planner execution: {str(e)}",
                tool_calls=[],
                tool_results=[]
            )

class AgentEvaluator(BaseAgent):
    async def evaluate(self, task: Union[str, AgentTask], result: AgentResult) -> AgentEvaluation:
        """Evaluate if an agent's execution needs another iteration"""
        start_time = time.time()
        task_str = task.task if isinstance(task, AgentTask) else task
        self.logger.info(f"AgentEvaluator starting evaluation for {result.agent_name}")
        try:
            # Check for failed tool calls that might need retrying
            for tool_result in result.tool_results:
                if isinstance(tool_result.get("result"), str) and (
                    "error" in tool_result["result"].lower() or 
                    "failed" in tool_result["result"].lower() or
                    "502" in tool_result["result"]
                ):
                    self.logger.info(f"Found failed tool call: {tool_result}")
                    return AgentEvaluation.REITERATE

            # Check for incomplete sequential operations
            # If we have multiple tool calls and one uses a placeholder that wasn't replaced
            if len(result.tool_calls) > 1:
                for tool_call in result.tool_calls:
                    if '<' in tool_call["arguments"] and '>' in tool_call["arguments"]:
                        self.logger.info("Found unresolved placeholder in tool call")
                        return AgentEvaluation.REITERATE

            messages = [
                {
                    "role": "system",
                    "content": AGENT_EVALUATOR_PROMPT
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "task": task_str,
                        "agent_output": result.output,
                        "tool_calls": result.tool_calls,
                        "tool_results": result.tool_results
                    }, indent=2)
                }
            ]
            
            response = await self._call_llm(
                messages=messages,
                guided_choice=[e.value for e in AgentEvaluation]
            )
            
            execution_time = time.time() - start_time
            self.logger.info(f"AgentEvaluator completed evaluation in {execution_time:.2f} seconds")
            
            result.agent_message = AgentMessage(
                agent="AgentEvaluator",
                content=f"Evaluating {result.agent_name}'s task completion...\nEvaluation result: {response.content.strip()}",
                execution_time=execution_time,
                status="Completed",
                step="Evaluation complete"
            )
            
            return AgentEvaluation(response.content.strip())
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"AgentEvaluator failed in {execution_time:.2f} seconds: {str(e)}")
            result.agent_message = AgentMessage(
                agent="AgentEvaluator",
                content=f"Error evaluating: {str(e)}",
                execution_time=execution_time,
                status="Failed",
                step="Error occurred"
            )
            return AgentEvaluation.FINISHED

class OverallEvaluator(BaseAgent):
    async def evaluate(
        self,
        original_request: str,
        current_results: List[AgentResult]
    ) -> OverallEvaluation:
        """Evaluate if the current results are sufficient"""
        start_time = time.time()
        self.logger.info("OverallEvaluator starting evaluation")
        try:
            # First check for any failed or incomplete operations
            for result in current_results:
                # Check for errors in tool results
                for tool_result in result.tool_results:
                    if isinstance(tool_result.get("result"), str) and (
                        "error" in tool_result["result"].lower() or 
                        "failed" in tool_result["result"].lower() or
                        "502" in tool_result["result"]
                    ):
                        self.logger.info(f"Found failed tool call in {result.agent_name}: {tool_result}")
                        return OverallEvaluation.REITERATE

                # Check for incomplete sequential operations
                if len(result.tool_calls) > 1:
                    # Look for unresolved placeholders
                    for tool_call in result.tool_calls:
                        if '<' in tool_call["arguments"] and '>' in tool_call["arguments"]:
                            self.logger.info(f"Found unresolved placeholder in {result.agent_name}")
                            return OverallEvaluation.REITERATE

                    # Check if we have all necessary results for sequential operations
                    tool_names = [tc["name"] for tc in result.tool_calls]
                    result_names = [tr["name"] for tr in result.tool_results]
                    if not all(tn in result_names for tn in tool_names):
                        self.logger.info(f"Missing tool results in {result.agent_name}")
                        return OverallEvaluation.REITERATE

            messages = [
                {
                    "role": "system",
                    "content": OVERALL_EVALUATOR_PROMPT
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "original_request": original_request,
                        "current_results": [r.dict() for r in current_results]
                    }, indent=2)
                }
            ]
            
            response = await self._call_llm(
                messages=messages,
                guided_choice=[e.value for e in OverallEvaluation]
            )
            
            execution_time = time.time() - start_time
            self.logger.info(f"OverallEvaluator completed evaluation in {execution_time:.2f} seconds")
            
            if current_results:
                current_results[-1].agent_message = AgentMessage(
                    agent="OverallEvaluator",
                    content=f"Overall evaluation...\nOverall evaluation result: {response.content.strip()}",
                    execution_time=execution_time,
                    status="Completed",
                    step="Evaluation complete"
                )
            
            return OverallEvaluation(response.content.strip())
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"OverallEvaluator failed in {execution_time:.2f} seconds: {str(e)}")
            if current_results:
                current_results[-1].agent_message = AgentMessage(
                    agent="OverallEvaluator",
                    content=f"Error evaluating: {str(e)}",
                    execution_time=execution_time,
                    status="Failed",
                    step="Error occurred"
                )
            return OverallEvaluation.FINISHED

class OutputGenerator(BaseAgent):
    async def generate_output(
        self,
        original_request: str,
        execution_results: List[AgentResult]
    ) -> str:
        """Generate the final response to the user"""
        start_time = time.time()
        self.logger.info("OutputGenerator starting output generation")
        try:
            # Create input data for logging
            input_data = {
                "original_request": original_request,
                "execution_results": [r.dict() for r in execution_results]
            }
            
            messages = [
                {
                    "role": "system",
                    "content": BACKGROUND_INFO + OUTPUT_GENERATOR_PROMPT
                },
                {
                    "role": "user",
                    "content": json.dumps(input_data, indent=2)
                }
            ]
            
            response = await self._call_llm(
                messages=messages,
            )
            
            execution_time = time.time() - start_time
            self.logger.info(f"OutputGenerator completed generation in {execution_time:.2f} seconds")
            
            # Get response metadata from the completion response
            response_metadata = {}
            completion_response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            
            if hasattr(completion_response, 'usage'):
                response_metadata = completion_response.usage.model_dump()
            
            if execution_results:
                execution_results[-1].agent_message = AgentMessage(
                    agent="OutputGenerator",
                    content=response.content,
                    response_metadata=response_metadata,
                    execution_time=execution_time,
                    status="Completed",
                    step="Final response generated"
                )
            
            return response.content
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"OutputGenerator failed in {execution_time:.2f} seconds: {str(e)}")
            if execution_results:
                execution_results[-1].agent_message = AgentMessage(
                    agent="OutputGenerator",
                    content=f"Error generating output: {str(e)}",
                    execution_time=execution_time,
                    status="Failed",
                    step="Error occurred"
                )
            return str(e)

class IterationAdvisor(BaseAgent):
    """Agent that provides structured advice for improving the next iteration"""
    
    async def get_advice(
        self,
        original_request: str,
        current_results: List[AgentResult]
    ) -> IterationAdvice:
        """Analyze current results and provide structured advice"""
        start_time = time.time()
        self.logger.info("IterationAdvisor starting analysis")
        try:
            messages = [
                {
                    "role": "system",
                    "content": ITERATION_ADVISOR_PROMPT
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "original_request": original_request,
                        "current_results": [r.dict() for r in current_results]
                    }, indent=2) + "\n\nKeep in mind: The OutputGenerator will summarize all results at the end of the pipeline. If the necessary information exists in the results (even if not perfectly formatted), do not suggest retrying."
                }
            ]
            
            response = await self._call_llm(
                messages=messages,
                guided_json=IterationAdvice.model_json_schema()
            )
            
            execution_time = time.time() - start_time
            self.logger.info(f"IterationAdvisor completed analysis in {execution_time:.2f} seconds")
            
            # Get response metadata from the completion response
            response_metadata = {}
            completion_response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0
            )
            if hasattr(completion_response, 'usage'):
                response_metadata = completion_response.usage.model_dump()
            
            if current_results:
                current_results[-1].agent_message = AgentMessage(
                    agent="IterationAdvisor",
                    content=response.content,
                    response_metadata=response_metadata,
                    execution_time=execution_time
                )
            
            return IterationAdvice.model_validate_json(response.content)
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"IterationAdvisor failed in {execution_time:.2f} seconds: {str(e)}")
            if current_results:
                current_results[-1].agent_message = AgentMessage(
                    agent="IterationAdvisor",
                    content=f"Error getting advice: {str(e)}",
                    execution_time=execution_time
                )
            return IterationAdvice(
                issues=["Error getting advice"],
                improvement_steps=["Try again"],
                context_summary="Error occurred",
                should_retry=False
            )

class WorkerAgent(BaseAgent):
    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        agent_name: str,
        summary: str,
        tools: List[Dict],
        session_client: Any,
        config: Dict[str, Any] = None
    ):
        if config and "worker_model" in config:
            model = config["worker_model"]
        super().__init__(client, model)
        self.agent_name = agent_name
        self.summary = summary
        self.tools = tools
        self.session_client = session_client
        self.logger = logging.getLogger(__name__)

    async def execute_task(self, task: Union[str, AgentTask]) -> AgentResult:
        """Execute a task using the agent's tools"""
        start_time = time.time()
        task_str = task.task if isinstance(task, AgentTask) else task
        self.logger.debug(f"Executing task: {task_str}")

        remark = ""
        if self.agent_name == "exchange-agent":
            remark = """\n\nIMPORTANT: 
- If you need to retrieve the next meeting info, retrieve my upcoming appointments for the next 7 days!
- If you need to retrieve phone numbers, always try to use email addresses where possible!
- If you need to retrieve email addresses, always use 'umlauts' in the name (like 'ä', 'ö', 'ü' - Tobias Kuester would be Tobias Küster in that case)!"""
        elif self.agent_name == "DataVisAgent":
            remark = """\n\nIMPORTANT: 
- THE VALUES FOR THE X AND Y AXIS MUST BE NUMERIC!
- At the moment you cannot pass string labels for the x or y axis!
- Since there can never be labels for the x-axis, you have to include information about which element in the chart belongs to which label.

EXAMPLE: 
- If the user asks for a visualization of temperature in kitchen and coworking space, the x values should be 0 and 1.
- The title of this chart should be 'Temperature in kitchen (left) and coworking space (right)' or Temperature in kitchen (0) and coworking space (1)."""


        try:
            # Create messages with task description and tools
            messages = [{
                "role": "system",
                "content": BACKGROUND_INFO + AGENT_SYSTEM_PROMPT.format(
                    agent_name=self.agent_name,
                    agent_summary=self.summary
                )
            }, {
                "role": "user",
                "content": f"""\nSolve the following task with the tools available to you: 

{task_str}

Remember: 
1. NEVER use placeholders - always use actual values.
2. Be extreamly careful with the data types you use for the function arguments. ALWAYS USE THE CORRECT DATA TYPE!
{remark}"""
            }]
            
            # Log the input to LLM
            self.logger.debug(f"Sending to LLM - Task: {task_str}")
            self.logger.debug(f"Full messages to LLM: {json.dumps(messages, indent=2)}")
            self.logger.debug(f"Available tools: {json.dumps(self.tools, indent=2)}")
            
            # Get function call from LLM
            response = await self._call_llm(
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )
            
            # Log the LLM response
            self.logger.debug(f"LLM Response received for {self.agent_name}")
            self.logger.debug(f"Full LLM response: {json.dumps(response.model_dump(), indent=2)}")
            
            if not hasattr(response, 'tool_calls') or not response.tool_calls:
                error_msg = f"No tool call received for task: {task_str}.\n\n Worker Agent Output: {response.content}"
                self.logger.error(error_msg)
                return AgentResult(
                    agent_name=self.agent_name,
                    task=task_str,
                    output=error_msg,
                    tool_calls=[],
                    tool_results=[]
                )
            

            # Iterate over all tool calls
            # Initialize tool calls and results lists
            tool_calls = []
            tool_results = []
            tool_outputs = []

            for tool_call in response.tool_calls:

                # Create a dictionary for each tool call
                tool_call_dict = {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments
                }
                
                # Log the tool call being made
                self.logger.info(f"Making tool call: {tool_call.function.name}")
                self.logger.debug(f"Tool call arguments: {tool_call.function.arguments}")
                
                # Parse arguments and execute the action
                args = json.loads(tool_call.function.arguments)
                
                # Split function name to get action name (remove agent prefix)
                func_name = tool_call.function.name
                if "--" in func_name:
                    agent_name, action_name = func_name.split("--", 1)
                else:
                    agent_name = None
                    action_name = func_name
                
                # Execute the action with the correct parameters
                result = await self.session_client.invoke_opaca_action(
                    action=action_name,
                    agent=agent_name,
                    params=args.get("requestBody", {})  # Get requestBody from args
                )

                # Add the tool call and result to the lists
                tool_calls.append(tool_call_dict)
                tool_results.append({
                    "name": tool_call.function.name,
                    "result": result  # Store the raw result without string conversion
                })

                # Format the result for output
                if isinstance(result, (dict, list)):
                    result_str = json.dumps(result, indent=2)
                else:
                    result_str = str(result)
                
                # Log the tool result
                self.logger.info(f"Tool call completed: {action_name}")
                self.logger.debug(f"Tool result: {result_str}")
                
                # Add the result to the tool outputs list
                tool_outputs.append(f"\n## Executed {tool_call.function.name}.\n\n ## Result: {result_str}")

            # Join all tool outputs into a single string
            output = "\n\n".join(tool_outputs)

            # Stop the execution timer
            execution_time = time.time() - start_time
            self.logger.info(f"{self.agent_name} completed task in {execution_time:.2f} seconds")
            
            # Create a meaningful output that summarizes the action and result
            output = f"# Executed task: {task_str} \n\n {output}"
            
            return AgentResult(
                agent_name=self.agent_name,
                task=task_str,
                output=output,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Error executing task: {str(e)}"
            self.logger.error(f"{self.agent_name} failed task in {execution_time:.2f} seconds: {error_msg}")
            
            return AgentResult(
                agent_name=self.agent_name,
                task=task_str,
                output=error_msg,
                tool_calls=[],
                tool_results=[]
            ) 