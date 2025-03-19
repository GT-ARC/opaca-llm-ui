from __future__ import annotations
import json
from typing import Dict, Any, List, Optional, Union
from openai import AsyncOpenAI
import logging
from pydantic import BaseModel, Field
import time
import asyncio
from datetime import datetime
import pytz
import re


from ..models import AgentMessage, ChatMessage
from .models import (
    AgentTask, OrchestratorPlan, OrchestratorPlan_no_thinking, PlannerPlan, AgentEvaluation, 
    OverallEvaluation, AgentResult, IterationAdvice
)
from .prompts import (
    BACKGROUND_INFO,
    ORCHESTRATOR_SYSTEM_PROMPT,
    ORCHESTRATOR_SYSTEM_PROMPT_NO_THINKING,
    AGENT_SYSTEM_PROMPT,
    AGENT_EVALUATOR_PROMPT,
    OVERALL_EVALUATOR_PROMPT,
    OUTPUT_GENERATOR_PROMPT,
    GENERAL_CAPABILITIES_RESPONSE,
    ITERATION_ADVISOR_PROMPT,
    AGENT_PLANNER_PROMPT,
)



class BaseAgent:
    # Static class variables for logging configuration
    LOG_FILE = "agents.log"  # Default log file path
    LOG_TO_FILE = False  # Default logging state - disabled by default
    
    def __init__(self, client: AsyncOpenAI, model: str):
        self.client = client
        self.model = model
        self.logger = logging.getLogger("src.models")
        self.chat_history = None
        self.response_metadata = {}

    def _log_llm_interaction(self, agent_name: str, messages: List[Dict[str, str]], response_content: str, output_structure: Optional[str] = "") -> None:
        """Log an LLM interaction to the log file with clear separation of system prompt, user input, and response"""
        try:
            if BaseAgent.LOG_TO_FILE:
                with open(BaseAgent.LOG_FILE, 'a') as f:
                    # Write agent header with more context for evaluators
                    if "Evaluator" in agent_name:
                        f.write(f"\n{'=' * 35} {agent_name} Evaluation {'=' * 35}\n\n")
                    else:
                        f.write(f"\n{'=' * 35} {agent_name} LLM Call {'=' * 35}\n\n")
                
                    # Write messages in order
                    for msg in messages:
                        role = msg["role"].upper()
                        f.write(f"{'-' * 35} {role} MESSAGE {'-' * 35}\n\n")
                        f.write(f"{msg['content']}\n\n")

                        if role == "USER":
                            if output_structure:
                                f.write(f"\n\n{'-' * 5} Expected Response Format {'-' * 5}\n\n")
                                f.write(f"{output_structure}\n\n\n")
                
                    # Write response with context for evaluators
                    if "Evaluator" in agent_name:
                        f.write(f"{'-' * 35} EVALUATION RESULT {'-' * 35}\n\n")
                    else:
                        f.write(f"{'-' * 35} ASSISTANT RESPONSE {'-' * 35}\n\n")
                    f.write(f"{response_content}\n\n\n")
                    
                    # Write separator
                    f.write(f"{'=' * 90}\n\n")

                # Log the message to the logger in debug mode
                self.logger.debug(f"=== [{agent_name}] - [LLM RESPONSE]=== \n Message: {response_content}\n\n")

        except Exception as e:
            self.logger.error(f"Error writing to log file: {str(e)}")

    @classmethod
    def enable_file_logging(cls, log_file_path: Optional[str] = None):
        """Enable logging to a file for all agents"""
        cls.LOG_TO_FILE = True
        if log_file_path:
            cls.LOG_FILE = log_file_path
        
        # Clear the log file when enabling logging
        with open(cls.LOG_FILE, 'w') as f:
            f.write(f"\n{'=' * 35} New Session Started {'=' * 35}\n\n\n\n")

    @classmethod
    def disable_file_logging(cls):
        """Disable logging to file for all agents"""
        cls.LOG_TO_FILE = False

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
        output_structure = ""
        try:
            
            # Check if we're using a GPT model
            is_gpt = "gpt" in self.model.lower() or "o3" in self.model.lower() or "4o" in self.model.lower()
            
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

                completion = await self.client.chat.completions.create(**kwargs)
                response = completion.choices[0].message
                
                # Log the LLM interaction
                self._log_llm_interaction(
                    self.__class__.__name__,  # Use the class name as agent name
                    kwargs["messages"],
                    json.dumps(response.model_dump(), indent=2)
                )
                self.response_metadata = completion.usage.to_dict()
                
                return response
                
            # Handle guided outputs for non-tool calls
            if guided_choice:
                if is_gpt:
                    # For OpenAI, add instruction to choose from options
                    if kwargs["messages"] and kwargs["messages"][0]["role"] == "system":
                        options_str = ", ".join(guided_choice)
                        kwargs["messages"][0]["content"] = kwargs["messages"][0]["content"] + f"\nPlease choose exactly one of these options: {options_str}"
                    if kwargs["messages"] and kwargs["messages"][1]["role"] == "user":
                        kwargs["messages"][1]["content"] = kwargs["messages"][1]["content"] + f"You MUST select one AND ONLY ONE of these choices to answer the request:\n\n {json.dumps(guided_choice, indent=2)} \n\n ONLY ANSWER WITH THE CHOICE AND NOTHING ELSE!"
                    output_structure = f"You MUST select one of these choices to answer the request:\n\n {json.dumps(guided_choice, indent=2)}"
                else:
                    # For vLLM, keep original system prompt and add choice options
                    system_msg = kwargs["messages"][0]["content"] if kwargs["messages"] else ""
                    options_str = ", ".join(guided_choice)
                    system_msg = f"{system_msg}\n\nYou must choose exactly one of these options: {options_str}"
                    
                    # Move everything except the actual task/query to system message
                    user_msg = kwargs["messages"][1]["content"] if len(kwargs["messages"]) > 1 else ""
                    
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

                    output_structure = f"You MUST select one of these choices to answer the request:\n {json.dumps(guided_choice, indent=2)}"
            elif guided_json:
                guided_json = transform_schema(guided_json)

                if is_gpt:
                    # For OpenAI, use json_schema mode and add schema to system message
                    kwargs["response_format"] = {
                        "type": "json_schema",
                        "json_schema": guided_json
                    }
                    if kwargs["messages"] and kwargs["messages"][0]["role"] == "system":
                        schema_str = json.dumps(guided_json, indent=2)
                        kwargs["messages"][0]["content"] = (
                            kwargs["messages"][0]["content"] + 
                            f"\n\nYou MUST provide your response as a JSON object that follows this schema. Your response must include ALL required fields.\n\nSchema:\n{schema_str}\n\n" +
                            "DO NOT return the schema itself. Return a valid JSON object matching the schema."
                        )
                else:
                    # For vLLM, keep original system prompt and add JSON schema
                    system_msg = kwargs["messages"][0]["content"] if kwargs["messages"] else ""
                    schema_str = json.dumps(guided_json, indent=2)
                    system_msg = system_msg + f"""\n
You MUST provide your response as a JSON object that follows this schema.
Your response must include ALL required fields.\n\n
Schema:\n
{schema_str}\n
DO NOT return the schema itself. Return a valid JSON object matching the schema."""
                    
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
                
                output_structure = f"You MUST provide your response as a JSON object that follows this schema: {json.dumps(guided_json, indent=2)}"
            
            response = await self.client.chat.completions.create(**kwargs)
            
            # Log the LLM interaction with the actual agent name
            agent_name = self.__class__.__name__
            if hasattr(self, 'agent_name'):
                agent_name = self.agent_name
            
            self._log_llm_interaction(
                agent_name,  # Use the actual agent name
                kwargs["messages"],
                response.choices[0].message.content, 
                output_structure
            )

            self.response_metadata = response.usage.to_dict()
            
            return response.choices[0].message
        finally:
            execution_time = time.time() - start_time
            self.logger.debug(f"LLM call took {execution_time:.2f} seconds")

class OrchestratorAgent(BaseAgent):
    def __init__(self, client: AsyncOpenAI, model: str, agent_summaries: Dict[str, Any], chat_history: Optional[List[ChatMessage]] = None, disable_thinking: bool = False):
        super().__init__(client, model)
        self.agent_summaries = agent_summaries
        self.chat_history = chat_history.copy()
        self.disable_thinking = disable_thinking

    @property
    def remark(self):
        if self.disable_thinking:
            return """REMEMBER: YOU ARE THE ONLY AGENT THAT HAS ACCESS TO THE CHAT HISTORY! EVERYTHING THAT YOU DO NOT PUT INTO THE TASK FIELD WILL BE LOST!
THE CONCRETE TASKS MUST BE IN THE JSON FIELD DEDICATED TO THE TASKS!"""
        return """REMEMBER: YOU ARE THE ONLY AGENT THAT HAS ACCESS TO THE CHAT HISTORY AND TO YOUR THINKING PROCESS! EVERYTHING THAT YOU DO NOT PUT INTO THE TASK FIELD WILL BE LOST!
YOUR THINKING MUST BE IN THE CORRECT JSON FIELD DEDICATED TO THE THINKING PROCESS!
THE CONCRETE TASKS MUST BE IN THE JSON FIELD DEDICATED TO THE TASKS!"""

    @property
    def system_prompt(self):
        prompt = get_current_time() + BACKGROUND_INFO + ORCHESTRATOR_SYSTEM_PROMPT.format(
                agent_summaries=json.dumps(self.agent_summaries, indent=2)
            ) + """\n\nIMPORTANT: Provide your response as a raw JSON object, not wrapped in markdown code blocks."""
        print(f'orchestrator prompt: {prompt}')
        return prompt

    def messages(self, user_request: str):
        chat_context = ""
        if self.chat_history:
            # Get last 5 messages for context
            recent_messages = self.chat_history[-4:]
            chat_context = "Consider the chat history if applicable: \n\nRecent chat history:\n\n"
            for msg in recent_messages:
                chat_context += f"{msg.role}: {msg.content}\n"

            chat_context = chat_context + """\n\n IF YOU UTILIZE INFORMATION FROM THE CHAT HISTORY, YOU MUST ALWAYS INCLUDE IT WITHIN YOUR TASKS. YOU ARE THE ONLY AGENT IN THE WHOLE CHAIN THAT HAS ACCESS TO THE CHAT HISTORY!"""

        return [
            {
                "role": "user",
                "content": f"""
        {chat_context} \n\n

        {self.remark}

        Keep in mind that there is an output generating LLM-Agent at the end of the chain (WHICH SUMMARIZES THE RESULTS OF THE TASKS AUTOMATICALLY!!!).
        If the user request requires a summary, NO seperate agent or function is needed for that, as the output generating agent will do that!
        NEVER, ABSOLUTELY NEVER CREATE A SUMMARIZATION TAKS! 
        IF YOU SHOULD RETRIEVE AND SUMMARIZE INFORMATION, ONLY CREATE A TASK FOR THE RETRIEVAL, NOT FOR THE SUMMARIZATION!
        THE SUMMARIZATION HAPPENS AUTOMATICALLY AND NO ACTION FROM YOUR SIDE IS REQUIRED FOR THAT!!

        NOW, Create an execution plan for this request: \n 
        {user_request}
        """
            }
        ]

    def validate_output(self, content):
        if self.disable_thinking:
            return OrchestratorPlan_no_thinking.model_validate_json(content)
        return OrchestratorPlan.model_validate_json(content)

    @property
    def schema(self):
        if self.disable_thinking:
            return OrchestratorPlan_no_thinking
        return OrchestratorPlan


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
        self.predefined_response = get_current_time() + BACKGROUND_INFO + GENERAL_CAPABILITIES_RESPONSE.format(
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
        self.logger = logging.getLogger("src.models")
    
    async def create_plan(self, task: Union[str, AgentTask], previous_results: Optional[List[AgentResult]] = None) -> PlannerPlan:
        """Create a high-level task plan with rounds and dependencies."""
        task_str = task.task if isinstance(task, AgentTask) else task       
        # Create context from previous results if available
        context = ""
        if previous_results:
            context = "# Context \n\n Consider the following context and previous execution results when creating your execution plan:\n"
            for i, result in enumerate(previous_results, 1):
                context += f"\n## Result {i} from {result.agent_name}:\n"
                context += f"### Task:\n {result.task}\n"
                context += f"### Worker Agent Output:\n {result.output}\n"
                if result.tool_results:
                    context += f"### Tool Results:\n {json.dumps(result.tool_results, indent=2)}\n"

        remark = ""
        if self.agent_name == "exchange-agent":
            remark = """\n\nIMPORTANT: 
- If you need to retrieve the next meeting info, retrieve my upcoming appointments for the next 7 days!
- If you need to retrieve phone numbers, always try to use email addresses where possible!
- If you need to retrieve email addresses, always use 'umlauts' in the name (like 'ä', 'ö', 'ü' - Tobias Kuester would be Tobias Küster in that case)!"""
        elif self.agent_name == "DataVisAgent":
            remark = """\n\nIMPORTANT: 
- IF THE USER DID NOT REQUEST A SPECIFIC COLOR, DON'T USE ANY COLOR!
- The extracted noise levels from our mutlimeter sensor are not in decibels, but a different arbitrary unit. It is completely normal that those values are above 100 or even 200!
- ALWAYS PROVIDE AXIS LABELS FOR THE X and Y AXIS!"""
        elif self.agent_name == "home-assistant-agent":
            remark = """\n\nIMPORTANT: 
- The extracted noise levels from our mutlimeter sensor are not in decibels, but a different arbitrary unit. It is completely normal that those values are above 100 or even 200!
- Noise levels should never be outputted with the unit 'dB'!
- Every other sensor value uses their common metric unit (e.g. temperature in °C, humidity in %, etc.)"""

        messages = [{
            "role": "system",
            "content": get_current_time() + BACKGROUND_INFO + AGENT_PLANNER_PROMPT + f"""

THE AVAILABLE FUNCTIONS OF YOUR WORKER AGENT ARE:

{json.dumps(self.tools, indent=2)}

IMPORTANT: Provide your response as a raw JSON object, not wrapped in markdown code blocks."""
        }, {
            "role": "user",
            "content": f"""{context}

# YOUR TASK:

Create a plan that breaks down this task into subtasks ONLY if necessary: {task_str.strip()}


Remember: 
1. If this task can be done with a single tool call, DO NOT break it down into subtasks.
2. If you have results from previous tasks, use the CONCRETE VALUES from those results in your task descriptions.
3. NEVER use placeholders - always use actual values.
4. Be extreamly careful with the data types you use for the function arguments. ALWAYS USE THE CORRECT DATA TYPE!
5. YOU ABSOLUTELY HAVE TO REMEBER THAT THE WORKER AGENTS ONLY HAVE ACCESS TO THE TASK FIELD YOU CREATE. ALL THE INFORMATION WITHIN THE THINKING PROCESS IS NOT AVAILABLE FOR THE WORKER AGENTS!
6. Put all the information needed to execute the task into the task field.

{remark}

YOU ABSOLUTELY HAVE TO PROVIDE ALL THE REQUIRED FUNCTION ARGUMENTS AND ALL THE INFORMATION NECESSARY FOR THE WORKER AGENT INTO THE TASK FIELD.
EVERY INFORMATION THAT IS NECESSARY FOR THE WORKER AGENT TO EXECUTE THE TASK MUST BE PROVIDED IN THE TASK FIELD!
DO NOT ADD OTHER FIELDS LIKE 'requestBody'!"""
        }]
        
        response = await self._call_llm(
            messages=messages,
            guided_json=PlannerPlan.model_json_schema()
        )
        
        # Clean up the response if it's wrapped in markdown code blocks
        content = response.content
        if content.startswith("```") and content.endswith("```"):
            # Remove markdown code blocks
            content = re.sub(r"^```\w*\n|```\s*$", "", content).strip()
        
        return PlannerPlan.model_validate_json(content)

    async def execute_task(self, task: Union[str, AgentTask], existing_plan: Optional[PlannerPlan] = None, previous_results: Optional[List[AgentResult]] = None) -> AgentResult:
        """Execute a task with or without planning"""
        try:
            # Extract task string if AgentTask object is passed
            task_str = task.task if isinstance(task, AgentTask) else task
            self.logger.info(f"AgentPlanner executing task: {task_str}")
            
            # Create context from previous orchestrator round results if available
            orchestrator_context = ""
            if previous_results:
                orchestrator_context = "\n\nPrevious orchestrator round results:\n"
                for i, result in enumerate(previous_results, 1):
                    orchestrator_context += f"\n# Result {i} from {result.agent_name}:\n"
                    orchestrator_context += f"Task: {result.task}\n"
                    
                    # Split the output by rounds and process each round
                    round_outputs = result.output.split("\n\n")
                    for round_output in round_outputs:
                        if round_output.strip():
                            orchestrator_context += f"{round_output}\n"
                    
                    # Process tool results by round
                    if result.tool_results:
                        # Group tool results by round based on their sequence
                        round_tool_results = dict(enumerate(result.tool_results))
                        
                        # Output tool results by round
                        for round_num, tr in sorted(round_tool_results.items()):
                            orchestrator_context += f"\n### Tool Results:\n"
                            orchestrator_context += f"- {tr['name']}: {json.dumps(tr['result'])}\n"
                
                # Add the context to the task
                task_str = f"{task_str}\n\n{orchestrator_context}"
            
            # If planning is disabled, execute directly
            if not self.config.get("use_agent_planner", True):
                self.logger.info("Planning disabled, executing directly with worker agent")
                return await self.worker_agent.execute_task(task_str)

            elif self.agent_name == "GeneralAgent":
                self.logger.info("Skipping planning for GeneralAgent. Directly executing task: " + task_str)
                return await self.worker_agent.execute_task(task_str)
            
            # Use existing plan or create new one
            plan = existing_plan if existing_plan else await self.create_plan(task_str)
            
            # Initialize results storage
            all_results = []
            all_tool_calls = []
            all_tool_results = []
            combined_output = []
            
            # Group tasks by round
            tasks_by_round = {}
            for subtask in plan.tasks:
                tasks_by_round.setdefault(subtask.round, []).append(subtask)
            
            # Execute rounds sequentially
            for round_num in sorted(tasks_by_round.keys()):
                self.logger.info(f"AgentPlanner executing round {round_num}")
                round_tasks = tasks_by_round[round_num]
                
                # Add context from previous planner rounds if needed
                round_context = ""
                if round_num > 1 and all_results:
                    round_context = "\n\nPrevious planner round results:\n"
                    for prev_result in all_results:
                        round_context += f"\nTask: {prev_result.task}\n"
                        round_context += f"Output: {prev_result.output}\n"
                        if prev_result.tool_results:
                            round_context += f"Tool Results:\n"
                            for tr in prev_result.tool_results:
                                round_context += f"- {tr['name']}: {json.dumps(tr['result'])}\n"

                async def execute_round_task(subtask):
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
                    result = await self.worker_agent.execute_task(current_task)
                    
                    # Add the round number to the result output for better context
                    result.output = f"Round {round_num}: {result.output}"
                    return result
                
                # Execute all tasks in this round in parallel
                round_results = await asyncio.gather(*[execute_round_task(subtask) for subtask in round_tasks])
                
                # Process round results
                for result in round_results:
                    all_results.append(result)
                    all_tool_calls.extend(result.tool_calls)
                    all_tool_results.extend(result.tool_results)
                    combined_output.append(result.output)
                
                # Log completion of round with detailed information
                self.logger.debug(f"Round {round_num} results: {json.dumps([r.dict() for r in round_results], indent=2)}")
            
            # Create final combined result with clear round separation
            final_output = "\n\n".join(combined_output)
            
            # Create a result that includes both planner and worker information
            result = AgentResult(
                agent_name=self.worker_agent.agent_name,  # Use worker agent's name for proper attribution
                task=task_str,  # Use the original task string
                output=final_output,
                tool_calls=all_tool_calls,
                tool_results=all_tool_results
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in planner execution: {str(e)}")
            return AgentResult(
                agent_name=self.worker_agent.agent_name,
                task=task_str,
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
                    }, indent=2) + "\n\n" + "NOW: EVALUATE IF THE TASK HAS BEEN COMPLETED WITH THE GIVEN TOOL RESULTS. CHOOSE REITERATE OR FINISHED! KEEP IN MIND THAT YOU ARE ONLY ALLOWED TO REITERATE IF THERE IS A CONCRETE IMPROVEMENT PATH FOR THE GIVEN USER REQUEST!" +
                    "\n\n" + "IT IS ABSOLUTELY IMPORTANT THAT YOU ANSWER ONLY WITH REITERATE OR FINISHED! DO NOT INCLUDE ANY OTHER TEXT! ONLY CLASSIFY THE GIVEN RESULTS AS REITERATE OR FINISHED!"
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
                        "current_results": [r.model_dump() for r in current_results]
                    }, indent=2) +
                    "\n\n" + "NOW: EVALUATE IF THE USER REQUEST CAN BE ANSWERED WITH THE GIVEN RESULTS. CHOOSE REITERATE OR FINISHED! KEEP IN MIND THAT YOU ARE ONLY ALLOWED TO REITERATE IF THERE IS A CONCRETE IMPROVEMENT PATH FOR THE GIVEN USER REQUEST!" +
                    "\n\n" + "IMPORTANT: The OutputGenerator will summarize all results at the end of the pipeline. If the necessary information exists in the results (even if not perfectly formatted), choose FINISHED." +
                    "\n\n" + "IT IS ABSOLUTELY IMPORTANT THAT YOU ANSWER ONLY WITH REITERATE OR FINISHED! DO NOT INCLUDE ANY OTHER TEXT! ONLY CLASSIFY THE GIVEN RESULTS AS REITERATE OR FINISHED!"
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
                "execution_results": [r.model_dump() for r in execution_results]
            }
            
            messages = [
                {
                    "role": "system",
                    "content": get_current_time() + BACKGROUND_INFO + OUTPUT_GENERATOR_PROMPT
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
                        "current_results": [r.model_dump() for r in current_results]
                    }, indent=2) +
                    "\n\n" + "NOW: Create a concrete improvement plan for the given user request! CONSIDER THAT YOU ARE ALLOWED AND ALSO EXPECTED TO VETO THE REITERATION IF THERE IS NO CONCRETE IMPROVEMENT PATH FOR THE GIVEN USER REQUEST!" +
                    "\n\n" + "If you have doubts or wish to not reiterate, set 'should_retry' to false. YOU ARE EXPECTED TO HAVE A STRONG REASON TO BELIEVE THE RESULTS CAN BE IMPROVED WITH A REITERATION IF YOU CHOOSE TO RETRY." +
                    "\n\n" + "IMPORTANT: The OutputGenerator will summarize all results at the end of the pipeline. If the necessary information exists in the results (even if not perfectly formatted), choose FINISHED."
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
        self.logger = logging.getLogger("src.models")

    async def execute_task(self, task: Union[str, AgentTask]) -> AgentResult:
        """Execute a task using the agent's tools"""
        start_time = time.time()
        task_str = task.task if isinstance(task, AgentTask) else task
        self.logger.debug(f"Executing task: {task_str}")

        try:
            # Create messages with task description and tools
            messages = [{
                "role": "system",
                "content": get_current_time() + BACKGROUND_INFO + AGENT_SYSTEM_PROMPT.format(
                    agent_name=self.agent_name,
                    agent_summary=self.summary
                )
            }, {
                "role": "user",
                "content": f"""\nSolve the following task with the tools available to you: 

{task_str}

Remember: 
1. NEVER use placeholders - always use actual values.
2. Be extremely careful with the data types you use for the function arguments. ALWAYS USE THE CORRECT DATA TYPE!"""
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
                    "result": result
                })


                # EVEN THOUGH WE ARE NO LONGER PASSING THE RESULTS, IT MAKES SENSE TO KEEP THIS FOR LOGGING OR FUTURE USE!
                # Format the result for output
                if isinstance(result, (dict, list)):
                    result_str = json.dumps(result, indent=2)
                else:
                    result_str = str(result)
                
                # Limit the result string to 250 characters
                result_str = result_str[:250] + "..." if len(result_str) > 250 else result_str
                
                # Log the tool result
                self.logger.info(f"Tool call completed: {action_name}")
                self.logger.debug(f"Tool result: {result_str}")
                
                # Add the result to the tool outputs list
                tool_outputs.append(f"\n- Worker Agent Executed: {tool_call.function.name}.") # Since we are already passing the tool results in the AgentResult object, we no longer need to pass the result here

            # Join all tool outputs into a single string
            output = "\n\n".join(tool_outputs)

            # Stop the execution timer
            execution_time = time.time() - start_time
            self.logger.info(f"{self.agent_name} completed task in {execution_time:.2f} seconds")
        
            
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

def transform_schema(schema):
    """Transform a JSON schema to meet OpenAI's requirements.
    
    This function:
    1. Resolves $ref references from $defs
    2. Adds additionalProperties: False to all object types
    3. Removes unnecessary fields like title and default
    4. Flattens and simplifies the schema structure
    5. Adds required name field for OpenAI compatibility
    """
    # Extract $defs if present
    defs = schema.get('$defs', {})
    
    def resolve_ref(ref):
        """Resolve a $ref reference by getting the schema from $defs"""
        if not ref.startswith('#/$defs/'):
            return None
        def_name = ref.split('/')[-1]
        return defs.get(def_name, {})

    def clean_schema(s):
        """Remove unnecessary fields and add additionalProperties: False to objects"""
        if not isinstance(s, dict):
            return s

        # Start with a new dict to only keep what we want
        cleaned = {}
        
        # Copy essential fields
        if 'type' in s:
            cleaned['type'] = s['type']
        if 'description' in s:
            cleaned['description'] = s['description']
        if 'properties' in s:
            cleaned['properties'] = {
                k: clean_schema(v) for k, v in s['properties'].items()
            }
        if 'items' in s:
            cleaned['items'] = clean_schema(s['items'])
        if 'required' in s:
            cleaned['required'] = s['required']
        if 'enum' in s:
            cleaned['enum'] = s['enum']
        
        # Add additionalProperties: False to objects
        if s.get('type') == 'object':
            cleaned['additionalProperties'] = False
            
        # Handle anyOf/allOf/oneOf
        for field in ['anyOf', 'allOf', 'oneOf']:
            if field in s:
                cleaned[field] = [clean_schema(item) for item in s[field]]
        
        return cleaned

    def process_schema(s):
        """Process schema by resolving refs and cleaning"""
        if not isinstance(s, dict):
            return s
        
        # Create a new dict to store processed schema
        processed = {}
        
        # Handle $ref first
        if '$ref' in s:
            ref_schema = resolve_ref(s['$ref'])
            if ref_schema:
                # Merge the resolved schema with any additional properties
                processed = process_schema(ref_schema)
                # Add any additional fields from the original schema
                for k, v in s.items():
                    if k != '$ref':
                        processed[k] = process_schema(v)
                return processed
        
        # Process each field
        for k, v in s.items():
            if k == '$defs':
                continue  # Skip $defs as we handle them separately
            elif isinstance(v, dict):
                processed[k] = process_schema(v)
            elif isinstance(v, list):
                processed[k] = [process_schema(item) for item in v]
            else:
                processed[k] = v
        
        return processed
    
    # Process the main schema
    processed_schema = process_schema(schema)
    
    # Clean the processed schema
    cleaned_schema = clean_schema(processed_schema)
    
    # Create the final schema with the required name field
    final_schema = {
        "name": schema.get("title", "json_response"),  # Use title if available, otherwise default
        "schema": cleaned_schema
    }
    
    return final_schema

def get_current_time():
    location = "Europe/Berlin"
    berlin_tz = pytz.timezone(location)
    return f"""
# CURRENT TIME 

The current date and time in ({location}) is {datetime.now(berlin_tz).strftime("%A, %d %B %Y (currently in Calender Week %W), %H:%M:%S (%p), (in Time Zone %Z)")}.
YOU ARE ALLOWED AND ABSOLUTELY ENCOURAGED TO REDUCE THE INFORMATION TO A SHORTER FORMAT (eg. leaving out seconds, leaving out AM/PM or the calendar week) IF IT IS NOT NECESSARY!


"""