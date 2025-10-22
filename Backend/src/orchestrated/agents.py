from __future__ import annotations
import json
from typing import Dict, Any, List, Optional, Union, Iterator
import logging
from datetime import datetime
import pytz
from copy import deepcopy


from ..models import ChatMessage, AgentMessage
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
            chat_history: Optional[Iterator[ChatMessage]] = None,
            tools: List = None
    ):
        super().__init__()
        self.agent_summaries = agent_summaries
        self.chat_history = list(chat_history)
        self.tools = tools

    @staticmethod
    def system_prompt():
        return ORCHESTRATOR_PROMPT

    def messages(self, user_request: str):
        return [
            ChatMessage(role="assistant", content="# CHAT HISTORY\n\nThe following messages are part of the previous chat history and do not follow my output schema. " \
                                                  "I can use information from the chat history for the latest user request if they are relevant."),
            *self.chat_history,
            ChatMessage(role="assistant", content="# END OF CHAT HISTORY"),
            ChatMessage(role="user", content=f'Now create a plan by outputting tool calls including ALL necessary tasks to fulfill the following request:\n'
                                             f'{user_request}')
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
            tool["strict"] = True
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
                if any(tc.result for tc in result.tool_calls):
                    context += f"### Tool Results:\n\t\t" + "\t\t".join([str(tc.result) + "\n" for tc in result.tool_calls])

        return [ChatMessage(role="user", content=f"""{context}

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
        )]

    @property
    def schema(self):
        return PlannerPlan

    @staticmethod
    def get_orchestrator_context(previous_results: Optional[List[AgentResult]] = None) -> str:
        # Create context from previous orchestrator round results if available
        orchestrator_context = ""
        if previous_results:
            orchestrator_context = "\n\nPrevious orchestrator round results:\n"
            for i, result in enumerate(previous_results, 1):
                orchestrator_context += f"\n# Result {i} from {result.agent_name}:\nTask: {result.task}\n"

                # Split the output by rounds and process each round
                for round_output in result.output.split("\n\n"):
                    if round_output.strip():
                        orchestrator_context += f"{round_output}\n"

                # Process tool calls by round
                if any(tc.result for tc in result.tool_calls):
                    for tc in result.tool_calls:
                        orchestrator_context += f"\n### Tool Results:\n- {tc.name}: {tc.result}\n"
        return orchestrator_context


class AgentEvaluator(BaseAgent):
    @staticmethod
    def system_prompt():
        return AGENT_EVALUATOR_PROMPT

    @staticmethod
    def messages(task: Union[str, AgentTask], result: AgentResult):
        results = json.dumps({
            "task": task.task if isinstance(task, AgentTask) else task,
            "agent_output": result.output,
            "tool_calls": list(map(str, result.tool_calls)),
        }, indent=2)
        return [
            ChatMessage(
                role = "user",
                content = f"{results}\n\nNOW: EVALUATE IF THE TASK HAS BEEN COMPLETED WITH THE GIVEN TOOL RESULTS. "
                          f"CHOOSE REITERATE OR FINISHED! KEEP IN MIND THAT YOU ARE ONLY ALLOWED TO REITERATE IF THERE IS "
                          f"A CONCRETE IMPROVEMENT PATH FOR THE GIVEN USER REQUEST!\n\n"
                          f"IT IS ABSOLUTELY IMPORTANT THAT YOU ANSWER ONLY WITH REITERATE OR FINISHED! DO NOT INCLUDE ANY OTHER TEXT! "
                          f"ONLY CLASSIFY THE GIVEN RESULTS AS REITERATE OR FINISHED!"
            )
        ]

    @property
    def schema(self):
        return AgentEvaluation

    def evaluate_results(self, result: AgentResult) -> bool:
        """Manually checks for errors in the results and returns True if any are found."""
        if (error := get_first_error(result)):
            self.logger.info(error)
            return True
        return False


class OverallEvaluator(BaseAgent):

    @staticmethod
    def system_prompt():
        return OVERALL_EVALUATOR_PROMPT

    @staticmethod
    def messages(original_request: str, current_results: List[AgentResult]):
        return [
            ChatMessage(role="user",
                content=json.dumps({
                    "original_request": original_request,
                    "current_results": [r.model_dump() for r in current_results]
                }, indent=2)
            )
        ]

    @property
    def schema(self):
        return AgentEvaluation

    def evaluate_results(self, current_results: List[AgentResult]) -> bool:
        """Manually checks for errors in the results and returns True if any are found."""
        for result in current_results:
            if (error := get_first_error(result)):
                self.logger.info(f"{error} in {result.agent_name}")
                return True
        return False


class IterationAdvisor(BaseAgent):
    """Agent that provides structured advice for improving the next iteration"""

    @staticmethod
    def system_prompt():
        return ITERATION_ADVISOR_PROMPT

    @staticmethod
    def messages(original_request: str, current_results: List[AgentResult]):
        return [
            ChatMessage(
                role= "user",
                content= json.dumps({
                    "original_request": original_request,
                    "current_results": [r.model_dump() for r in current_results]
                }, indent=2)
            )
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
            ChatMessage(
                role= "user",
                content= f"""\nSolve the following task with the tools available to you: 

        {task_str}

        Remember: 
        1. NEVER use placeholders - always use actual values.
        2. Be extremely careful with the data types you use for the function arguments. ALWAYS USE THE CORRECT DATA TYPE!"""
            )
        ]


def get_first_error(result: AgentResult) -> str | None:
    # Check for errors in tool results
    for tc in result.tool_calls:
        if isinstance(tc.result, str) and any(x in tc.result.lower() for x in ["error", "failed", "502"]):
            return f"Found failed tool call: {tc}"

    # Check for incomplete sequential operations
    # If we have multiple tool calls and one uses a placeholder that wasn't replaced
    if len(result.tool_calls) > 1:
        for tool_call in result.tool_calls:
            # XXX THIS DOES NOT MAKE SENSE! (did it before? can this be removed?)
            if '<' in tool_call.args and '>' in tool_call.args:
                return f"Found unresolved placeholder"
    return None


def get_current_time():
    location = "Europe/Berlin"
    berlin_tz = pytz.timezone(location)
    return f"""
# CURRENT TIME 

The current date and time in ({location}) is {datetime.now(berlin_tz).strftime("%A, %d %B %Y (currently in Calender Week %W), %H:%M:%S (%p), (in Time Zone %Z)")}.
YOU ARE ALLOWED AND ABSOLUTELY ENCOURAGED TO REDUCE THE INFORMATION TO A SHORTER FORMAT (eg. leaving out seconds, leaving out AM/PM or the calendar week) IF IT IS NOT NECESSARY!


"""