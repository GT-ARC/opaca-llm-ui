"""
LLM Client based on RestGPT (https://github.com/Yifan-Song793/RestGPT), but somewhat simplified and adapted to OPACA.

It consists of four different agents:
* Planner: Responsible for dividing a task into smaller subtasks if necessary. Also handles questions about services
  or unrelated questions that can be answered without calling actions.
* API Selector: Based on the output of the Planner, selects a suitable action and generates parameters if necessary.
* Caller: Parses the output of the API Selector, calls the connected Opaca platform to invoke the specified action 
  and finally evaluates with call stack to give a short summary in natural language
* Evaluator: Evaluates the complete plan history and determines if the user query has been fulfilled. If so, generate
  an answer that will be shown to the user including the achieved results; if not, start over with the Planner.
"""

from .restgpt_routes import RestGptBackend
