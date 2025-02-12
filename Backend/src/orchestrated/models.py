from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ..models import AgentMessage

class AgentTask(BaseModel):
    """Model for tasks assigned to agents by the orchestrator or planner"""
    agent_name: str = Field(..., description="Name of the agent to execute the task")
    task: str = Field(..., description="Description of the task to be executed")
    round: int = Field(..., description="Execution round number for ordering/parallelization")
    dependencies: List[str] = Field(default=[], description="List of task IDs that must complete before this one")

class OrchestratorPlan(BaseModel):
    """Model for the orchestrator's execution plan"""
    thinking: str = Field(..., description="Step by step reasoning about how to break down and solve the task")
    tasks: List[AgentTask] = Field(..., description="List of tasks to be executed")
    needs_follow_up: bool = Field(default=False, description="Whether the orchestrator needs follow-up information")
    follow_up_question: Optional[str] = Field(default=None, description="Follow-up question to ask the user if needed")

class PlannerPlan(BaseModel):
    """Model for the planner's execution plan"""
    thinking: str = Field(..., description="Short and precise step by step reasoning about how to break down and solve the task")
    tasks: List[AgentTask] = Field(..., description="List of tasks to be executed")

class AgentEvaluation(str, Enum):
    """Possible outcomes from the agent evaluator"""
    REITERATE = "REITERATE"  # Agent should try again with new context
    FINISHED = "FINISHED"    # Agent has completed its task successfully

class OverallEvaluation(str, Enum):
    """Possible outcomes from the overall evaluator"""
    REITERATE = "REITERATE"  # Need more agent actions
    FINISHED = "FINISHED"    # Ready for final output generation

class AgentResult(BaseModel):
    """Model for storing results from an agent's execution"""
    agent_name: str
    task: str
    output: str
    tool_calls: List[Dict[str, Any]] = []
    tool_results: List[Any] = []
    agent_message: Optional[AgentMessage] = Field(default=None, description="Debug message with execution details")

class IterationAdvice(BaseModel):
    """Model for providing structured advice for the next iteration"""
    issues: List[str] = Field(..., description="List of specific issues identified in the current iteration")
    improvement_steps: List[str] = Field(..., description="Concrete steps to improve in the next iteration")
    context_summary: str = Field(..., description="Brief summary of relevant context to carry forward")
    should_retry: bool = Field(..., description="Whether retrying would be beneficial")
    needs_follow_up: bool = Field(default=False, description="Whether follow-up information is needed")
    follow_up_question: Optional[str] = Field(default=None, description="Follow-up question if needed")

class ChatMessage(BaseModel):
    """Model for storing chat history messages"""
    role: str = Field(..., description="Role of the message sender (user/assistant)")
    content: str = Field(..., description="Content of the message")
    timestamp: Optional[str] = Field(default=None, description="Timestamp of the message")

class ChatHistory(BaseModel):
    """Model for storing the chat history"""
    messages: List[ChatMessage] = Field(default_factory=list, description="List of chat messages")
    context_summary: Optional[str] = Field(default=None, description="Summary of relevant context from chat history") 