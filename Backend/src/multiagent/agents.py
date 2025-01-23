import json
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
import logging

from .models import AgentTask, ExecutionPlan, AgentEvaluation, OverallEvaluation, AgentResult
from .prompts import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    AGENT_SYSTEM_PROMPT,
    AGENT_EVALUATOR_PROMPT,
    OVERALL_EVALUATOR_PROMPT,
    OUTPUT_GENERATOR_PROMPT,
    GENERAL_CAPABILITIES_RESPONSE,
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
    def __init__(self, client: AsyncOpenAI, model: str, agent_summaries: Dict[str, Any]):
        super().__init__(client, model)
        self.agent_summaries = agent_summaries
        
    async def create_execution_plan(self, user_request: str) -> ExecutionPlan:
        """Create an execution plan for the user's request"""
        messages = [
            {
                "role": "system",
                "content": ORCHESTRATOR_SYSTEM_PROMPT.format(
                    agent_summaries=json.dumps(self.agent_summaries, indent=2)
                )
            },
            {"role": "user", "content": user_request}
        ]
        
        response = await self._call_llm(
            messages=messages,
            guided_json=ExecutionPlan.model_json_schema()
        )
        
        return ExecutionPlan.model_validate_json(response.content)

class WorkerAgent(BaseAgent):
    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        agent_name: str,
        instructions: str,
        tools: List[Dict],
        internal_tools: List[Dict],
        config: Dict[str, Any] = None
    ):
        # Use worker_model from config if available, otherwise fall back to default model
        if config and "worker_model" in config:
            model = config["worker_model"]
        super().__init__(client, model)
        self.agent_name = agent_name
        self.instructions = instructions
        self.tools = tools  # Tools without session client for OpenAI
        self.internal_tools = internal_tools  # Tools with session client for execution

    async def _execute_tool_call(self, tool_call) -> str:
        """Execute a tool call and return the result"""
        try:
            # Parse the tool call arguments
            args = json.loads(tool_call.function.arguments)
            
            # Get the function name and split into agent/action if needed
            func_name = tool_call.function.name
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
            
            # Invoke the OPACA action
            result = await session_client.invoke_opaca_action(
                action=action_name,
                agent=agent_name,
                params=args.get("requestBody", {})
            )
            
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error executing tool call: {str(e)}"

    async def execute_task(self, task: str) -> AgentResult:
        """Execute a task using the agent's tools"""
        # For tool calls, use a simple and direct system prompt
        system_prompt = f"You are the {self.agent_name}. YOU MUST USE THE TOOLS AVAILABLE TO YOU TO COMPLETE THE TASK. DO NOT PROVIDE ANY EXPLANATIONS, JUST USE THE TOOLS."
        
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"Make a tool call to complete this task: {task}"
            }
        ]
        
        response = await self._call_llm(
            messages=messages,
            tools=self.tools,
            tool_choice="auto"
        )
        
        tool_calls = []
        tool_results = []
        output = ""
        
        try:
            # Handle both OpenAI and vLLM response formats
            if hasattr(response, 'tool_calls'):
                # OpenAI format
                tool_calls_list = response.tool_calls
            elif hasattr(response, 'choices') and response.choices[0].message.tool_calls:
                # vLLM format
                tool_calls_list = response.choices[0].message.tool_calls
            else:
                tool_calls_list = []
            
            if tool_calls_list:
                tool_calls = [
                    {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                    for tool_call in tool_calls_list
                ]
                
                # Execute each tool call
                for tool_call in tool_calls_list:
                    result = await self._execute_tool_call(tool_call)
                    tool_results.append({
                        "name": tool_call.function.name,
                        "result": result
                    })
                    # Add the tool result to the output
                    output += f"Result from {tool_call.function.name}: {result}\n"
            else:
                # If no tool calls were made, use the response content as output
                output = response.content if hasattr(response, 'content') else response.choices[0].message.content
        
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing tool calls: {str(e)}")
            output = f"Error processing tool calls: {str(e)}"
        
        return AgentResult(
            agent_name=self.agent_name,
            task=task,
            output=output.strip(),
            tool_calls=tool_calls,
            tool_results=tool_results
        )

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
                }, indent=2)
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
                }, indent=2)
            }
        ]
        
        response = await self._call_llm(
            messages=messages,
            guided_choice=[e.value for e in OverallEvaluation]
        )
        
        return OverallEvaluation(response.content.strip())

class GeneralAgent(BaseAgent):
    """Agent that handles general capability questions without using tools."""
    
    def __init__(self, client: AsyncOpenAI, model: str, agent_summaries: Dict[str, Any], config: Dict[str, Any] = None):
        # Use worker_model from config if available, otherwise fall back to default model
        if config and "worker_model" in config:
            model = config["worker_model"]
        super().__init__(client, model)
        self.agent_name = "GeneralAgent"
        
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