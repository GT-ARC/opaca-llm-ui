import time
import re
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from langchain.callbacks.base import BaseCallbackManager
from langchain.chains.base import Chain
from langchain.callbacks.manager import CallbackManagerForChainRun

from langchain_community.utilities import RequestsWrapper

from .planner import Planner
from .action_selector import ActionSelector
from .caller import Caller
from .utils import OpacaLLM

logger = logging.getLogger()


class RestGPT(Chain):
    """Consists of an agent using tools."""

    llm: OpacaLLM
    action_spec: List
    planner: Planner
    action_selector: ActionSelector
    requests_wrapper: RequestsWrapper
    simple_parser: bool = False
    return_intermediate_steps: bool = False
    max_iterations: Optional[int] = 15
    max_execution_time: Optional[float] = None
    early_stopping_method: str = "force"

    def __init__(
            self,
            llm: OpacaLLM,
            action_spec: List,
            requests_wrapper: RequestsWrapper,
            caller_doc_with_response: bool = False,
            parser_with_example: bool = False,
            simple_parser: bool = False,
            callback_manager: Optional[BaseCallbackManager] = None,
            **kwargs: Any,
    ) -> None:

        planner = Planner(llm=llm)
        action_selector = ActionSelector(llm=llm, action_spec=action_spec)

        super().__init__(
            llm=llm, action_spec=action_spec, planner=planner, action_selector=action_selector,
            requests_wrapper=requests_wrapper, simple_parser=simple_parser, callback_manager=callback_manager, **kwargs
        )

    def save(self, file_path: Union[Path, str]) -> None:
        """Raise error - saving not supported for Agent Executors."""
        raise ValueError(
            "Saving not supported for RestGPT. "
            "If you are trying to save the agent, please use the "
            "`.save_agent(...)`"
        )

    @property
    def _chain_type(self) -> str:
        return "RestGPT"

    @property
    def input_keys(self) -> List[str]:
        """Return the input keys.

        :meta private:
        """
        return ["query"]

    @property
    def output_keys(self) -> List[str]:
        """Return the singular output key.

        :meta private:
        """
        return self.planner.output_keys

    def debug_input(self) -> str:
        print("Debug...")
        return input()

    def _should_continue(self, iterations: int, time_elapsed: float) -> bool:
        if self.max_iterations is not None and iterations >= self.max_iterations:
            return False
        if (
                self.max_execution_time is not None
                and time_elapsed >= self.max_execution_time
        ):
            return False

        return True

    def _return(self, output, intermediate_steps: list) -> Dict[str, Any]:
        self.callback_manager.on_agent_finish(
            output, color="green", verbose=self.verbose
        )
        final_output = output.return_values
        if self.return_intermediate_steps:
            final_output["intermediate_steps"] = intermediate_steps
        return final_output

    def _get_api_selector_background(self, planner_history: List[Tuple[str, str]]) -> str:
        if len(planner_history) == 0:
            return "No background"
        return "\n".join([step[1] for step in planner_history])

    def _should_continue_plan(self, plan) -> bool:
        if re.search("Continue", plan):
            return True
        return False

    def _should_end(self, plan) -> bool:
        if re.search("Final Answer", plan):
            return True
        return False

    def _call(
            self,
            inputs: Dict[str, Any],
            run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> Dict[str, Any]:
        query = inputs['query']

        planner_history: List[Tuple[str, str]] = []
        iterations = 0
        time_elapsed = 0.0
        start_time = time.time()

        logger.info(f'Planner: Run')
        plan = self.planner.invoke({"input": query, "history": planner_history})
        logger.info(f"Planner: {plan['result']}")
        """
        logger.info(f'API Selector: Run')
        action_plan = self.action_selector.invoke({"plan": plan,
                                                   "background": self._get_api_selector_background(planner_history)})
        logger.info(f'API Selector: {action_plan["result"]}')
        """

        while self._should_continue(iterations, time_elapsed):
            tmp_planner_history = [plan]
            action_selector_history: List[Tuple[str, str, str]] = []
            action_selector_background = self._get_api_selector_background(planner_history)
            action_plan = self.action_selector.invoke({"plan": plan,
                                                       "background": self._get_api_selector_background(planner_history)})
            action_plan = action_plan["result"]

            finished = re.match(r"No API call needed.(.*)", action_plan)
            break
            """
            if not finished:
                executor = Caller(llm=self.llm, action_spec=self.action_spec, simple_parser=self.simple_parser, requests_wrapper=self.requests_wrapper)
                execution_res = executor.run(action_plan=action_plan, background=action_selector_background)
            else:
                execution_res = finished.group(1)

            planner_history.append((plan, execution_res))
            action_selector_history.append((plan, action_plan, execution_res))

            plan = self.planner.run(input=query, history=planner_history)
            logger.info(f"Planner: {plan}")

            while self._should_continue_plan(plan):
                action_selector_background = self._get_api_selector_background(planner_history)
                action_plan = self.action_selector.run(plan=tmp_planner_history[0], background=action_selector_background, history=action_selector_history, instruction=plan)

                finished = re.match(r"No API call needed.(.*)", action_plan)
                if not finished:
                    executor = Caller(llm=self.llm, action_spec=self.action_spec, scenario=self.scenario, simple_parser=self.simple_parser, requests_wrapper=self.requests_wrapper)
                    execution_res = executor.run(action_plan=action_plan, background=action_selector_background)
                else:
                    execution_res = finished.group(1)

                planner_history.append((plan, execution_res))
                action_selector_history.append((plan, action_plan, execution_res))

                plan = self.planner.run(input=query, history=planner_history)
                logger.info(f"Planner: {plan}")
                """

            if self._should_end(plan):
                break

            iterations += 1
            time_elapsed = time.time() - start_time

        return {"result": action_plan}

    @staticmethod
    def test():
        return "test successful"
