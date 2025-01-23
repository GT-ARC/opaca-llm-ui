from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class AgentTask(BaseModel):
    """Model for tasks assigned to agents by the orchestrator"""
    agent_name: str = Field(..., description="Name of the agent to execute the task")
    task: str = Field(..., description="Description of the task to be executed")
    round: int = Field(..., description="Execution round number for ordering/parallelization")
    dependencies: List[str] = Field(default=[], description="List of agent names whose tasks must complete before this one")

class ExecutionPlan(BaseModel):
    """Model for the orchestrator's execution plan"""
    thinking: str = Field(..., description="Chain of thought reasoning about how to break down and solve the task")
    tasks: List[AgentTask] = Field(..., description="List of tasks to be executed")
    context: str = Field(..., description="Context or reasoning for the execution plan")

class AgentEvaluation(str, Enum):
    """Possible outcomes from the agent evaluator"""
    REITERATE = "REITERATE"  # Agent should try again with new context
    COMPLETE = "COMPLETE"    # Agent has completed its task successfully

class OverallEvaluation(str, Enum):
    """Possible outcomes from the overall evaluator"""
    CONTINUE = "CONTINUE"    # Need more agent actions
    FINISHED = "FINISHED"    # Ready for final output generation

class AgentResult(BaseModel):
    """Model for storing results from an agent's execution"""
    agent_name: str
    task: str
    output: str
    tool_calls: List[Dict[str, Any]] = []
    tool_results: List[Any] = [] 