from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ..models import AgentMessage

class AgentTask(BaseModel):
    """Model for tasks assigned to agents by the orchestrator or planner"""
    agent_name: str = Field(description="Name of the agent to execute the task")
    task: str = Field(description="Detailed description of the task to be executed with all relevant parameter information")
    round: int = Field(description="Execution round number for ordering/parallelization")
    dependencies: List[str] = Field(description="List of task IDs that must complete before this one")

class OrchestratorPlan(BaseModel):
    """Model for the orchestrator's execution plan"""
    thinking: str = Field(description="Step by step reasoning about how to break down and solve the task")
    tasks: List[AgentTask] = Field(description="List of tasks to be executed")

class OrchestratorPlan_no_thinking(BaseModel):
    """Model for the orchestrator's execution plan"""
    tasks: List[AgentTask] = Field(description="List of tasks to be executed")

class PlannerPlan(BaseModel):
    """Model for the planner's execution plan"""
    thinking: str = Field(description="Short and precise step by step reasoning about how to break down and solve the task")
    tasks: List[AgentTask] = Field(description="List of tasks to be executed")

class AgentEvaluation(str, Enum):
    """Possible outcomes from the agent evaluator"""
    REITERATE = "REITERATE"  # Should try again with new context
    FINISHED = "FINISHED"    # Completed task successfully

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
    issues: List[str] = Field(description="List of specific issues identified in the current iteration")
    improvement_steps: List[str] = Field(description="Concrete steps to improve in the next iteration")
    context_summary: str = Field(description="Brief summary of relevant context to carry forward")
    should_retry: bool = Field(description="Whether retrying would be beneficial")
    needs_follow_up: bool = Field(description="Whether follow-up information is needed")
    follow_up_question: Optional[str] = Field(description="Follow-up question if needed")
