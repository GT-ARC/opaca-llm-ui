from __future__ import annotations
import json
from typing import Dict, Any, List, Optional, Union
import logging
from datetime import datetime
import pytz
from copy import deepcopy


from ..models import ChatMessage
from .models import (
    AgentTask, OrchestratorPlan, PlannerPlan, AgentEvaluation,
    AgentResult, IterationAdvice
)
from .prompts import (
    BACKGROUND_INFO,
    AGENT_SYSTEM_PROMPT,
    AGENT_EVALUATOR_PROMPT,
    OVERALL_EVALUATOR_PROMPT,
    ITERATION_ADVISOR_PROMPT,
    AGENT_PLANNER_PROMPT, ORCHESTRATOR_PROMPT,
)
from ..utils import enforce_strictness


class BaseAgent:
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.chat_history = None
        self.response_metadata = {}

class OrchestratorAgent(BaseAgent):
    def __init__(
            self,
            agent_summaries: Dict[str, Any],
            chat_history: Optional[List[ChatMessage]] = None,
            tools: List = None
    ):
        super().__init__()
        self.agent_summaries = agent_summaries
        self.chat_history = chat_history.copy()
        self.tools = tools

    @staticmethod
    def system_prompt():
        return ORCHESTRATOR_PROMPT

    def messages(self, user_request: str):
        return [{
            "role": "assistant",
            "content": "# CHAT HISTORY\n\nThe following messages are part of the previous chat history and do not follow my output schema. I can use information from the chat history for the latest user request if they are relevant."
        }] + self.chat_history + [
                {
                "role": "assistant",
                "content": "# END OF CHAT HISTORY"
                }
        ] + [
                {
                "role": "user",
                "content": f'Now create a plan by outputting tool calls including ALL necessary tasks to fulfill the following request:\n'
                           f'{user_request}'
                }
        ]

    @property
    def schema(self):
        return OrchestratorPlan

class AgentPlanner(BaseAgent):
    """Agent-specific planner that creates high-level task plans."""
    
    def __init__(
        self,
        agent_name: str,
        tools: List[Dict],
        worker_agent: "WorkerAgent",
        config: Dict[str, Any] = None
    ):
        super().__init__()
        self.agent_name = agent_name
        self.tools = deepcopy(tools)
        # The agent planner needs tools to be strict
        for tool in self.tools:
            tool["function"]["strict"] = True
            enforce_strictness(tool)
        self.worker_agent = worker_agent
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def system_prompt():
        return AGENT_PLANNER_PROMPT

    @staticmethod
    def messages(task: Union[str, AgentTask], previous_results: Optional[List[AgentResult]] = None):
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

        return [{"role": "user", "content": f"""{context}

            # YOUR TASK:
            
            Create a plan that breaks down this task into subtasks ONLY if necessary: {task_str.strip()}
            
            
            Remember: 
            1. If this task can be done with a single tool call, DO NOT break it down into subtasks.
            2. If you have results from previous tasks, use the CONCRETE VALUES from those results in your task descriptions.
            3. NEVER use placeholders - always use actual values.
            4. Be extremely careful with the data types you use for the function arguments. ALWAYS USE THE CORRECT DATA TYPE!
            5. YOU ABSOLUTELY HAVE TO REMEMBER THAT THE WORKER AGENTS ONLY HAVE ACCESS TO THE TASK FIELD YOU CREATE. ALL THE INFORMATION WITHIN THE THINKING PROCESS IS NOT AVAILABLE FOR THE WORKER AGENTS!
            6. Put all the information needed to execute the task into the task field.
            
            YOU ABSOLUTELY HAVE TO PROVIDE ALL THE REQUIRED FUNCTION ARGUMENTS AND ALL THE INFORMATION NECESSARY FOR THE WORKER AGENT INTO THE TASK FIELD.
            EVERY INFORMATION THAT IS NECESSARY FOR THE WORKER AGENT TO EXECUTE THE TASK MUST BE PROVIDED IN THE TASK FIELD!"""
        }]

    @property
    def schema(self):
        return PlannerPlan

    @staticmethod
    def get_orchestrator_context(previous_results: Optional[List[AgentResult]] = None):
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
        return orchestrator_context

    def get_task_str(self, task: Union[str, AgentTask], previous_results: Optional[List[AgentResult]] = None):
        # Extract task string if AgentTask object is passed
        task_str = task.task if isinstance(task, AgentTask) else task
        self.logger.info(f"AgentPlanner executing task: {task_str}")
        if previous_results:
            # Add the context to the task
            return f"{task_str}\n\n{self.get_orchestrator_context(previous_results)}"
        return task_str


class AgentEvaluator(BaseAgent):
    @staticmethod
    def system_prompt():
        return AGENT_EVALUATOR_PROMPT

    @staticmethod
    def messages(task: Union[str, AgentTask], result: AgentResult):
        task_str = task.task if isinstance(task, AgentTask) else task
        return [
            {
                "role": "user",
                "content": json.dumps({
                    "task": task_str,
                    "agent_output": result.output,
                    "tool_calls": result.tool_calls,
                    "tool_results": result.tool_results
                },
                    indent=2) + "\n\n" + "NOW: EVALUATE IF THE TASK HAS BEEN COMPLETED WITH THE GIVEN TOOL RESULTS. CHOOSE REITERATE OR FINISHED! KEEP IN MIND THAT YOU ARE ONLY ALLOWED TO REITERATE IF THERE IS A CONCRETE IMPROVEMENT PATH FOR THE GIVEN USER REQUEST!" +
                           "\n\n" + "IT IS ABSOLUTELY IMPORTANT THAT YOU ANSWER ONLY WITH REITERATE OR FINISHED! DO NOT INCLUDE ANY OTHER TEXT! ONLY CLASSIFY THE GIVEN RESULTS AS REITERATE OR FINISHED!"
            }
        ]

    @staticmethod
    def guided_choice():
        return [e.value for e in AgentEvaluation]

    def evaluate_results(self, result: AgentResult) -> AgentEvaluation | None:
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
                if '<' in tool_call["args"] and '>' in tool_call["args"]:
                    self.logger.info("Found unresolved placeholder in tool call")
                    return AgentEvaluation.REITERATE
        return None


class OverallEvaluator(BaseAgent):

    @staticmethod
    def system_prompt():
        return OVERALL_EVALUATOR_PROMPT

    @staticmethod
    def messages(original_request: str, current_results: List[AgentResult]):
        return [
            {
                "role": "user",
                "content": json.dumps({
                    "original_request": original_request,
                    "current_results": [r.model_dump() for r in current_results]
                }, indent=2)
            }
        ]

    @property
    def guided_choice(self):
        return [e.value for e in AgentEvaluation]

    def evaluate_results(self, current_results: List[AgentResult]) -> AgentEvaluation | None:
        for result in current_results:
            # Check for errors in tool results
            for tool_result in result.tool_results:
                if isinstance(tool_result.get("result"), str) and (
                        "error" in tool_result["result"].lower() or
                        "failed" in tool_result["result"].lower() or
                        "502" in tool_result["result"]
                ):
                    self.logger.info(f"Found failed tool call in {result.agent_name}: {tool_result}")
                    return AgentEvaluation.REITERATE

            # Check for incomplete sequential operations
            if len(result.tool_calls) > 1:
                # Look for unresolved placeholders
                for tool_call in result.tool_calls:
                    if '<' in tool_call["args"] and '>' in tool_call["args"]:
                        self.logger.info(f"Found unresolved placeholder in {result.agent_name}")
                        return AgentEvaluation.REITERATE

                # Check if we have all necessary results for sequential operations
                tool_names = [tc["name"] for tc in result.tool_calls]
                result_names = [tr["name"] for tr in result.tool_results]
                if not all(tn in result_names for tn in tool_names):
                    self.logger.info(f"Missing tool results in {result.agent_name}")
                    return AgentEvaluation.REITERATE
        return None


class IterationAdvisor(BaseAgent):
    """Agent that provides structured advice for improving the next iteration"""

    @staticmethod
    def system_prompt():
        return ITERATION_ADVISOR_PROMPT

    @staticmethod
    def messages(original_request: str, current_results: List[AgentResult]):
        return [
            {
                "role": "user",
                "content": json.dumps({
                    "original_request": original_request,
                    "current_results": [r.model_dump() for r in current_results]
                }, indent=2)
            }
        ]

    @property
    def schema(self):
        return IterationAdvice


class WorkerAgent(BaseAgent):
    def __init__(
        self,
        agent_name: str,
        summary: str,
        tools: List[Dict],
        session_client: Any,
    ):
        super().__init__()
        self.agent_name = agent_name
        self.summary = summary
        self.tools = tools
        self.session_client = session_client
        self.logger = logging.getLogger(__name__)

    def system_prompt(self):
        return get_current_time() + BACKGROUND_INFO + AGENT_SYSTEM_PROMPT.format(
            agent_name=self.agent_name,
            agent_summary=self.summary
        )

    @staticmethod
    def messages(task: Union[str, AgentTask]):
        task_str = task.task if isinstance(task, AgentTask) else task
        return [
            {
                "role": "user",
                "content": f"""\nSolve the following task with the tools available to you: 

        {task_str}

        Remember: 
        1. NEVER use placeholders - always use actual values.
        2. Be extremely careful with the data types you use for the function arguments. ALWAYS USE THE CORRECT DATA TYPE!"""
            }
        ]

    async def invoke_tools(self, task_str, message) -> AgentResult:
        # Iterate over all tool calls
        # Initialize tool calls and results lists
        tool_calls = []
        tool_results = []
        tool_outputs = []

        for tool_call in message.tools:
            # Log the tool call being made
            self.logger.info(f"Making tool call: {tool_call['name']}")
            self.logger.debug(f"Tool call arguments: {tool_call['args']}")

            # Split function name to get action name (remove agent prefix)
            func_name = tool_call["name"]
            if "--" in func_name:
                agent_name, action_name = func_name.split("--", 1)
            else:
                agent_name = None
                action_name = func_name

            # Execute the action with the correct parameters
            try:
                result = await self.session_client.invoke_opaca_action(
                    action=action_name,
                    agent=agent_name,
                    params=tool_call["args"]  # Get requestBody from args
                )
            except Exception as e:
                self.logger.error(f"Failed to execute tool call: {tool_call['name']}")
                tool_calls.append(tool_call)
                tool_results.append({
                    "name": tool_call["name"],
                    "result": str(e)
                })
                tool_call["result"] = str(e)
                continue

            # Add the tool call and result to the lists
            tool_calls.append(tool_call)
            tool_results.append({
                "name": tool_call["name"],
                "result": result
            })
            tool_call["result"] = result

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
            tool_outputs.append(
                f"\n- Worker Agent Executed: {tool_call['name']}.")  # Since we are already passing the tool results in the AgentResult object, we no longer need to pass the result here

        # Join all tool outputs into a single string
        output = "\n\n".join(tool_outputs)

        return AgentResult(
            agent_name=self.agent_name,
            task=task_str,
            output=output,
            tool_calls=tool_calls,
            tool_results=tool_results,
        )

def get_current_time():
    location = "Europe/Berlin"
    berlin_tz = pytz.timezone(location)
    return f"""
# CURRENT TIME 

The current date and time in ({location}) is {datetime.now(berlin_tz).strftime("%A, %d %B %Y (currently in Calender Week %W), %H:%M:%S (%p), (in Time Zone %Z)")}.
YOU ARE ALLOWED AND ABSOLUTELY ENCOURAGED TO REDUCE THE INFORMATION TO A SHORTER FORMAT (eg. leaving out seconds, leaving out AM/PM or the calendar week) IF IT IS NOT NECESSARY!


"""