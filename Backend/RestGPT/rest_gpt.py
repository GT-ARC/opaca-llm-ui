import time
import re
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from langchain.callbacks.base import BaseCallbackManager
from langchain.chains.base import Chain
from langchain.callbacks.manager import CallbackManagerForChainRun

from langchain_community.utilities import RequestsWrapper

from .planner import Planner
from .action_selector import ActionSelector
from .caller import Caller
from .evaluator import Evaluator
from .utils import OpacaLLM

logger = logging.getLogger()


class RestGPT(Chain):
    """Consists of an agent using tools."""

    llm: OpacaLLM
    action_spec: List
    planner: Planner
    action_selector: ActionSelector
    evaluator: Evaluator
    requests_wrapper: RequestsWrapper
    simple_parser: bool = False
    return_intermediate_steps: bool = False
    max_iterations: Optional[int] = 5
    max_execution_time: Optional[float] = None
    early_stopping_method: str = "force"
    request_headers: Dict = None

    def __init__(
            self,
            llm: OpacaLLM,
            action_spec: List,
            requests_wrapper: RequestsWrapper,
            caller_doc_with_response: bool = False,
            parser_with_example: bool = False,
            simple_parser: bool = False,
            callback_manager: Optional[BaseCallbackManager] = None,
            request_headers: Dict = None,
            **kwargs: Any,
    ) -> None:

        planner = Planner(llm=llm)
        action_selector = ActionSelector(llm=llm, action_spec=action_spec)
        evaluator = Evaluator(llm=llm)

        super().__init__(
            llm=llm, action_spec=action_spec, planner=planner, action_selector=action_selector, evaluator=evaluator,
            requests_wrapper=requests_wrapper, simple_parser=simple_parser, callback_manager=callback_manager,
            request_headers=request_headers, **kwargs
        )

    def save(self, file_path: Union[Path, str]) -> None:
        """Raise error - saving not supported for Agent Executors."""
        raise ValueError(
            "Saving not supported for RestGPT. "
            "If you are trying to save the agent, please use the "
            "`.save_agent(...)`"
        )

    def _finished(self, eval_input: str):
        return self.evaluator.invoke({"input": eval_input})["result"]

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
        action_selector_history: List[Tuple[str, str, str]] = []
        eval_input = f'User query: {query}\n'
        final_answer = ''
        iterations = 0
        time_elapsed = 0.0
        start_time = time.time()

        logger.info(f'Planner: Run with query: {query}')

        while self._should_continue(iterations, time_elapsed):
            plan = self.planner.invoke({"input": query, "actions": self.action_spec, "history": planner_history})
            plan = plan["result"]
            logger.info(f"Planner: {plan}")
            eval_input += f'Plan step {iterations + 1}: {plan}\n'

            api_plan = self.action_selector.invoke({"plan": plan,
                                                    "actions": self.action_spec,
                                                    "history": action_selector_history})
            api_plan = api_plan["result"]
            eval_input += f'API call {iterations + 1}: http://localhost:8000/invoke/{api_plan}\n'

            executor = Caller(llm=self.llm, action_spec=self.action_spec, simple_parser=self.simple_parser,
                              requests_wrapper=self.requests_wrapper, request_headers=self.request_headers)
            execution_res = executor.invoke({"api_plan": api_plan})
            execution_res = execution_res["result"]
            logger.info(f'Caller: {execution_res}')
            action_selector_history.append((plan, api_plan, execution_res))
            eval_input += f'API response {iterations + 1}: {execution_res}\n'
            planner_history.append((plan, execution_res))
            eval_output = self._finished(eval_input)
            if re.match(r"FINISHED", eval_output):
                final_answer = re.sub(r"FINISHED: ", "", eval_output).strip()
                break

            """
            plan = self.planner.invoke({"input": query, "actions": self.action_spec, "history": planner_history})
            plan = plan["result"]
            logger.info(f"Planner: {plan}")
            while self._should_continue_plan(plan):
                api_plan = self.action_selector.invoke({"plan": tmp_planner_history[0], "history": action_selector_history, "instruction": plan})
                api_plan = api_plan["result"]

                finished = re.match(r"No API call needed.(.*)", api_plan)
                if not finished:
                    executor = Caller(llm=self.llm, action_spec=self.action_spec, simple_parser=self.simple_parser, requests_wrapper=self.requests_wrapper)
                    execution_res = executor.invoke({"api_plan": api_plan})
                    execution_res = execution_res["result"]
                else:
                    execution_res = finished.group(1)

                planner_history.append((plan, execution_res))
                action_selector_history.append((plan, api_plan, execution_res))

                plan = self.planner.invoke({"input": query, "history": planner_history})
                plan = plan["result"]
                logger.info(f"Planner: {plan}")
            """

            iterations += 1
            time_elapsed = time.time() - start_time

        if final_answer == "":
            final_answer = "I am sorry, but I was unable to fulfill your request."

        logger.info(f'Final Answer: {final_answer}')
        return {"result": final_answer}
