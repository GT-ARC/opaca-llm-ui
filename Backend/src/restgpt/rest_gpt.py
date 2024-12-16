import time
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from langchain.chains.base import Chain
from langchain.callbacks.manager import CallbackManagerForChainRun
from langchain_core.language_models import BaseChatModel

from .planner import Planner
from .action_selector import ActionSelector
from .caller import Caller
from .evaluator import Evaluator

logger = logging.getLogger()


class RestGPT(Chain):
    """Consists of an agent using tools."""

    llm: BaseChatModel
    action_spec: List
    planner: Planner
    action_selector: ActionSelector
    caller: Caller
    evaluator: Evaluator
    max_iterations: Optional[int] = 5
    max_execution_time: Optional[float] = None

    def __init__(
            self,
            llm: BaseChatModel,
            action_spec: List,
            **kwargs: Any,
    ) -> None:

        print(f'Initialized RestGPT with model type {type(llm)}')

        planner = Planner(llm=llm)
        action_selector = ActionSelector(llm=llm)
        caller = Caller(llm=llm)
        evaluator = Evaluator(llm=llm)

        super().__init__(
            llm=llm, action_spec=action_spec, planner=planner, action_selector=action_selector, caller=caller,
            evaluator=evaluator, **kwargs
        )

    def _finished(self, eval_input: str, history: List[Tuple[str, str]], config: Dict):
        return self.evaluator.invoke({"input": eval_input,
                                      "history": history,
                                      "config": config,
                                      })

    @property
    def _chain_type(self) -> str:
        return "Opaca-LLM"

    @property
    def input_keys(self) -> List[str]:
        """Return the input keys.

        :meta private:
        """
        return ["query", "history", "config", "response", "client"]

    @property
    def output_keys(self) -> List[str]:
        """
        Return the output keys

        :meta private:
        """
        return ["result"]

    def _should_continue(self, iterations: int, time_elapsed: float) -> bool:
        if self.max_iterations is not None and iterations >= self.max_iterations:
            return False
        if (
                self.max_execution_time is not None
                and time_elapsed >= self.max_execution_time
        ):
            return False

        return True

    @staticmethod
    def _should_abort(plan):
        if re.search("STOP", plan):
            return True
        return False

    @staticmethod
    def _should_continue_plan(plan) -> bool:
        if re.search("CONTINUE", plan):
            return True
        return False

    @staticmethod
    def _should_end(plan) -> bool:
        if re.search("Final Answer", plan):
            return True
        return False

    @staticmethod
    def _is_missing(plan) -> bool:
        if re.search("MISSING", plan):
            return True
        return False

    def _call(
            self,
            inputs: Dict[str, Any],
            run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> Dict[str, Any]:
        query = inputs['query']
        config = inputs['config']

        planner_history: List[Tuple[str, str]] = []
        action_selector_history: List[Tuple[str, str, str]] = []
        eval_input = f'User query: {query}\n'
        final_answer = ''
        iterations = 0
        time_elapsed = 0.0
        start_time = time.time()
        response = inputs['response']

        logger.info(f'Query: {query}')

        while self._should_continue(iterations, time_elapsed):

            # PLANNER
            planner_response = self.planner.invoke({"input": query,
                                                    "actions": self.action_spec,
                                                    "planner_history": planner_history,
                                                    "message_history": inputs['history'],
                                                    "config": config,
                                                    "response": response,
                                                    })
            response.agent_messages.append(planner_response)

            plan = planner_response.content
            logger.info(f"Planner: {plan}")
            eval_input += f'Plan step {iterations + 1}: {plan}\n'

            if self._should_abort(plan):
                final_answer = re.sub("STOP[^a-zA-Z0-9]*", "", plan).strip()
                break

            # ACTION SELECTOR
            # exec time is measure within action selector
            as_response = self.action_selector.invoke({"plan": plan,
                                                       "actions": self.action_spec,
                                                       "action_history": action_selector_history,
                                                       "message_history": inputs["history"],
                                                       "config": config,
                                                       })
            api_plan = as_response[-1].content  # Get the last message of the action selector as input for caller
            response.agent_messages.extend(as_response)  # Add all action selector messages
            logger.info(f'API Selector: {api_plan}')

            if self._is_missing(api_plan):
                planner_history.append((plan, api_plan))
                iterations += 1
                continue

            eval_input += f'API call {iterations + 1}: http://localhost:8000/invoke/{api_plan}\n'

            # CALLER
            c_time = time.time()
            caller_response = self.caller.invoke({"api_plan": api_plan,
                                                  "actions": self.action_spec,
                                                  "config": config,
                                                  "client": inputs["client"],
                                                  })
            caller_response.execution_time = time.time() - c_time
            execution_res = caller_response.content
            response.agent_messages.append(caller_response)
            logger.info(f'Caller: {execution_res}')
            action_selector_history.append((plan, api_plan, execution_res))
            eval_input += f'API response {iterations + 1}: {execution_res}\n'
            planner_history.append((plan, execution_res))

            # EVALUATOR
            e_time = time.time()
            eval_response = self._finished(eval_input, inputs['history'], config)
            eval_response.execution_time = time.time() - e_time
            response.agent_messages.append(eval_response)
            if re.match(r"FINISHED", eval_response.content):
                final_answer = re.sub(r"FINISHED", "", eval_response.content).strip()
                break

            iterations += 1
            time_elapsed = time.time() - start_time

        if final_answer == "":
            final_answer = "I am sorry, but I was unable to fulfill your request."

        response.content = final_answer
        response.iterations = iterations

        logger.info(f'Final Answer: {final_answer}')
        return {"result": response}
