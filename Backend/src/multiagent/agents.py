import json
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
import logging
from pydantic import BaseModel, Field

from .models import (
    AgentTask, ExecutionPlan, AgentEvaluation, OverallEvaluation, 
    AgentResult, IterationAdvice, ChatHistory
)
from .prompts import (
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

    async def _call_llm(
        self,
        messages: List[Dict[str, str]],
        guided_choice: Optional[List[str]] = None,
        guided_json: Optional[Dict] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None
    ) -> Any:
        """Generic method to call the LLM with various guidance options"""
        logger = logging.getLogger(__name__)
        
        # Check if we're using a GPT model
        is_gpt = "gpt" in self.model.lower()
        
        # Base kwargs that are always included
        kwargs = {
            "model": self.model,
            "messages": messages.copy(),  # Make a copy to avoid modifying the original
            "temperature": 0
        }
        
        # Handle tool calls first since they're simpler
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"
            return await self.client.chat.completions.create(**kwargs)
            
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
        return response.choices[0].message

class OrchestratorAgent(BaseAgent):
    def __init__(self, client: AsyncOpenAI, model: str, agent_summaries: Dict[str, Any], chat_history: Optional[ChatHistory] = None):
        super().__init__(client, model)
        self.agent_summaries = agent_summaries
        self.chat_history = chat_history
    
    async def create_execution_plan(self, user_request: str) -> ExecutionPlan:
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
                "content": ORCHESTRATOR_SYSTEM_PROMPT.format(
                    agent_summaries=json.dumps(self.agent_summaries, indent=2)
                )
            },
            {
                "role": "user",
                "content": f"""Create an execution plan for this request: \n {user_request} \n\n 
Consider the chat history if applicable: \n {chat_context} \n\n
Keep in mind that there is an output generating LLM-Agent at the end of the chain.
If the user request requires a summary, no seperate agent or function is needed for that, as the output generating agent will do that!
NO NEED TO ASSIGN A TASK OR INVOKE THE AGENT. THIS ALL HAPPENS AUTOMATICALLY.
NEVER USE AN AGENT TO SUMMARIZE INFORMATION!
                """
            }
        ]
        
        response = await self._call_llm(
            messages=messages,
            guided_json=ExecutionPlan.model_json_schema()
        )
        
        return ExecutionPlan.model_validate_json(response.content)

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
        self.predefined_response = GENERAL_CAPABILITIES_RESPONSE.format(
            agent_capabilities=json.dumps(agent_summaries, indent=2)
        )
        
    async def execute_task(self, task: str) -> AgentResult:
        """Return capabilities response with proper tool structure."""
        # Create a dummy tool call to maintain consistent structure
        tool_call = {
            "name": "GetCapabilities",
            "arguments": json.dumps({"request": task})
        }
        
        # Create a dummy tool result with the actual response
        tool_result = {
            "name": "GetCapabilities",
            "result": self.predefined_response
        }
        
        return AgentResult(
            agent_name=self.agent_name,
            task=task,
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
    """Agent-specific planner that creates function calling plans for tasks."""
    
    def __init__(self, client: AsyncOpenAI, model: str, agent_name: str, tools: List[Dict]):
        super().__init__(client, model)
        self.agent_name = agent_name
        self.tools = tools
    
    async def create_plan(self, task: str) -> PlannerOutput:
        """Create a function calling plan for the given task."""
        messages = [{
            "role": "system",
            "content": AGENT_PLANNER_PROMPT
        }, {
            "role": "user",
            "content": f"""You are planning for the {self.agent_name}. Here are the available functions:
{json.dumps(self.tools, indent=2)}

Create a minimal, efficient function calling plan for this specific task: {task.strip()}"""
        }]
        
        response = await self._call_llm(
            messages=messages,
            guided_json=PlannerOutput.model_json_schema()
        )
        
        return PlannerOutput.model_validate_json(response.content)

class WorkerAgent(BaseAgent):
    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        agent_name: str,
        summary: str,
        tools: List[Dict],
        internal_tools: List[Dict],
        config: Dict[str, Any] = None
    ):
        if config and "worker_model" in config:
            model = config["worker_model"]
        super().__init__(client, model)
        self.agent_name = agent_name
        self.summary = summary
        self.tools = tools
        self.internal_tools = internal_tools
        self.planner = AgentPlanner(client, model, agent_name, tools)

    async def execute_task(self, task: str) -> AgentResult:
        """Execute a task using the agent's tools"""
        logger = logging.getLogger(__name__)
        
        try:
            # Create the tool call
            messages = [{
                "role": "system",
                "content": AGENT_SYSTEM_PROMPT.format(
                    agent_name=self.agent_name,
                    agent_summary=self.summary,
                    # tools=json.dumps(self.tools, indent=2) # Only add if we want to show the tools in the system prompt
                )
            }, {
                "role": "user",
                "content": task
            }]
            
            response = await self._call_llm(
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )
            
            tool_calls = []
            tool_results = []
            output = ""
            needs_follow_up = False
            follow_up_question = None
            
            if response.choices[0].message.tool_calls:
                for tool_call in response.choices[0].message.tool_calls:
                    # Create the tool call
                    tool_call_dict = {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                    tool_calls.append(tool_call_dict)
                    
                    # Execute the tool call
                    result = await self._execute_tool_call_direct(tool_call_dict)
                    
                    # Check if this is a follow-up request
                    try:
                        result_json = json.loads(result)
                        if isinstance(result_json, dict) and result_json.get("needs_follow_up"):
                            needs_follow_up = True
                            follow_up_question = result_json.get("question")
                            # Don't add follow-up requests to tool results
                            continue
                    except (json.JSONDecodeError, AttributeError):
                        pass  # Not a JSON response or not a follow-up request
                    
                    tool_results.append({
                        "name": tool_call.function.name,
                        "result": result
                    })
                    output += f"Result from {tool_call.function.name}: {result}\n"
            else:
                output = response.choices[0].message.content or "No tool calls made."
            
            return AgentResult(
                agent_name=self.agent_name,
                task=task,
                output=output.strip(),
                tool_calls=tool_calls,
                tool_results=tool_results,
                needs_follow_up=needs_follow_up,
                follow_up_question=follow_up_question
            )
        
        except Exception as e:
            logger.error(f"Error executing function calls: {str(e)}")
            return AgentResult(
                agent_name=self.agent_name,
                task=task,
                output=f"Error executing function calls: {str(e)}",
                tool_calls=[],
                tool_results=[],
                needs_follow_up=False
            )

    async def _execute_tool_call_direct(self, tool_call: Dict[str, str]) -> str:
        """Execute a tool call directly without LLM involvement"""
        try:
            args = json.loads(tool_call["arguments"])
            func_name = tool_call["name"]
            
            if "--" in func_name:
                agent_name, action_name = func_name.split("--", maxsplit=1)
            else:
                agent_name = None
                action_name = func_name
            
            # Get the session client from the internal tools
            session_client = None
            for tool in self.internal_tools:
                if tool["function"]["name"] == func_name:
                    session_client = tool.get("session_client")
                    break
            
            if not session_client:
                return f"Error: No session client found for tool {func_name}"
            
            # Special handling for RequestFollowUp
            if action_name == "RequestFollowUp":
                # Return the question directly - it will be handled by the agent framework
                return json.dumps({
                    "question": args["question"],
                    "needs_follow_up": True
                })
            
            # Invoke the OPACA action for other tools
            result = await session_client.invoke_opaca_action(
                action=action_name,
                agent=agent_name,
                params=args.get("requestBody", {})
            )
            
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error executing tool call: {str(e)}"

class AgentEvaluator(BaseAgent):
    async def evaluate(self, task: str, result: AgentResult) -> AgentEvaluation:
        """Evaluate if an agent's execution needs another iteration"""
        messages = [
            {
                "role": "system",
                "content": AGENT_EVALUATOR_PROMPT
            },
            {
                "role": "user",
                "content": json.dumps({
                    "task": task,
                    "agent_output": result.output,
                    "tool_calls": result.tool_calls,
                    "tool_results": result.tool_results
                }, indent=2) + "\n\nKeep in mind: The OutputGenerator will summarize all results at the end of the pipeline. If the necessary information exists in the results (even if not perfectly formatted), choose FINISHED."
            }
        ]
        
        response = await self._call_llm(
            messages=messages,
            guided_choice=[e.value for e in AgentEvaluation]
        )
        
        return AgentEvaluation(response.content.strip())

class OverallEvaluator(BaseAgent):
    async def evaluate(
        self,
        original_request: str,
        current_results: List[AgentResult]
    ) -> OverallEvaluation:
        """Evaluate if the current results are sufficient"""
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
                }, indent=2) + "\n\nKeep in mind: The OutputGenerator will summarize all results at the end of the pipeline. If the necessary information exists in the results (even if not perfectly formatted), choose FINISHED."
            }
        ]
        
        response = await self._call_llm(
            messages=messages,
            guided_choice=[e.value for e in OverallEvaluation]
        )
        
        return OverallEvaluation(response.content.strip())

class OutputGenerator(BaseAgent):
    async def generate_output(
        self,
        original_request: str,
        execution_results: List[AgentResult]
    ) -> str:
        """Generate the final response to the user"""
        # Create input data for logging
        input_data = {
            "original_request": original_request,
            "execution_results": [r.dict() for r in execution_results]
        }
        
        # Log the input data
        self.logger.info(f"Final output generation input: {json.dumps(input_data, indent=2)}")
        
        messages = [
            {
                "role": "system",
                "content": OUTPUT_GENERATOR_PROMPT
            },
            {
                "role": "user",
                "content": json.dumps(input_data, indent=2)
            }
        ]
        
        response = await self._call_llm(
            messages=messages,
            temperature=0  # Add temperature=0 to reduce creative thinking
        )
        return response.content 

class IterationAdvisor(BaseAgent):
    """Agent that provides structured advice for improving the next iteration"""
    
    async def get_advice(
        self,
        original_request: str,
        current_results: List[AgentResult]
    ) -> IterationAdvice:
        """Analyze current results and provide structured advice"""
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
        
        return IterationAdvice.model_validate_json(response.content) 