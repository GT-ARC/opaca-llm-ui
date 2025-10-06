from typing import Any, List
from pydantic import BaseModel
from enum import Enum


class EvalMatch(Enum):
    EXACT = "exact"                    # The parameter value has to match exactly the expected value
    PARTIAL = "partial"                # The parameter value should include the expected value (e.g. expected 'mouse' would be true for 'computer mouses')
    NONE = "none"                      # The value is not necessary for the comparison, only the type

class EvalToolParam(BaseModel):
    key: str                                # The key of a parameter
    value: Any                              # The value of a parameter
    match: EvalMatch = EvalMatch.EXACT      # How 'strict' the value should align with the actual value
    optional: bool = False                  # Optional means that this parameter is not required necessarily

class EvalTool(BaseModel):
    """Defines a tool evaluation class storing some additional information for consideration"""
    name: str                               # The exact name of the expected tool
    args: List[EvalToolParam] = []          # A list of the expected parameter names AND values
    optional: bool = False                  # Optional means that this tool call is not required necessarily
    id: int = -1                            # An id to identify a tool call. Used in combination with dependencies.
    depends: List[int] = []                 # A list of tool calls that should be executed before this one indicated by their id
    alternatives: List[List[int]] = []      # A list of alternative call ids, which could have been called instead. Can include one or multiple calls as alternatives

