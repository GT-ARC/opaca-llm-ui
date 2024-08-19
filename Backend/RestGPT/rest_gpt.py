import time
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from langchain.chains.base import Chain
from langchain.callbacks.manager import CallbackManagerForChainRun
from langchain_core.language_models import BaseLLM
from langchain_openai import ChatOpenAI

from .planner import Planner
from .action_selector import ActionSelector
from .caller import Caller
from .evaluator import Evaluator

logger = logging.getLogger()


class RestGPT(Chain):
    """Consists of an agent using tools."""

    llm: BaseLLM | ChatOpenAI
    action_spec: List
    planner: Planner
    action_selector: ActionSelector
    caller: Caller
    evaluator: Evaluator
    max_iterations: Optional[int] = 5
    max_execution_time: Optional[float] = None
    debug_output: str = ""

    def __init__(
            self,
            llm: BaseLLM | ChatOpenAI,
            action_spec: List,
            **kwargs: Any,
    ) -> None:

        print(f'Initialized RestGPT with model type {type(llm)}')

        planner = Planner(llm=llm)
        action_selector = ActionSelector(llm=llm, action_spec=action_spec)
        caller = Caller(llm=llm, action_spec=action_spec)
        evaluator = Evaluator(llm=llm)

        super().__init__(
            llm=llm, action_spec=action_spec, planner=planner, action_selector=action_selector, caller=caller,
            evaluator=evaluator, **kwargs
        )

    def _finished(self, eval_input: str, history: List[Tuple[str, str]], slim_prompt: bool, examples: bool):
        return self.evaluator.invoke({"input": eval_input,
                                      "history": history,
                                      "slim_prompt": slim_prompt,
                                      "examples": examples
                                      })["result"]

    @property
    def _chain_type(self) -> str:
        return "Opaca-LLM"

    @property
    def input_keys(self) -> List[str]:
        """Return the input keys.

        :meta private:
        """
        return ["query", "history", "config"]

    @property
    def output_keys(self) -> List[str]:
        """
        Return the output keys

        :meta private:
        """
        return ["result", "debug"]

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

        self.debug_output += f'Query: {query}\n'
        logger.info(f'Query: {query}')

        while self._should_continue(iterations, time_elapsed):

            # PLANNER
            plan = self.planner.invoke({"input": query,
                                        "actions": self.action_spec,
                                        "planner_history": planner_history,
                                        "message_history": inputs['history'],
                                        "slim_prompt": config['slim_prompts']['planner'],
                                        "examples": config['examples']['planner']})
            plan = plan["result"]
            self.debug_output += f'Planner: {plan}\n'
            logger.info(f"Planner: {plan}")
            eval_input += f'Plan step {iterations + 1}: {plan}\n'

            if self._should_abort(plan):
                final_answer = re.sub("STOP", "", plan).strip()
                break

            # ACTION SELECTOR
            api_plan = self.action_selector.invoke({"plan": plan,
                                                    "actions": self.action_spec,
                                                    "history": action_selector_history,
                                                    "slim_prompt": config['slim_prompts']['action_selector'],
                                                    "examples": config['examples']['action_selector']})
            api_plan = api_plan["result"]
            self.debug_output += f'API Selector: {api_plan}\n'
            logger.info(f'API Selector: {api_plan}')

            if self._is_missing(api_plan):
                planner_history.append((plan, api_plan))
                iterations += 1
                continue

            eval_input += f'API call {iterations + 1}: http://localhost:8000/invoke/{api_plan}\n'

            # CALLER
            execution_res = self.caller.invoke({"api_plan": api_plan,
                                                "actions": self.action_spec,
                                                "examples": config['examples']['action_selector']})
            execution_res = execution_res["result"]
            self.debug_output += f'Caller: {execution_res}\n'
            logger.info(f'Caller: {execution_res}')
            action_selector_history.append((plan, api_plan, execution_res))
            eval_input += f'API response {iterations + 1}: {execution_res}\n'
            planner_history.append((plan, execution_res))

            # EVALUATOR
            eval_output = self._finished(eval_input,
                                         inputs['history'],
                                         config['slim_prompts']['planner'],
                                         config['examples']['planner'])
            if re.match(r"FINISHED", eval_output):
                final_answer = re.sub(r"FINISHED: ", "", eval_output).strip()
                break

            iterations += 1
            time_elapsed = time.time() - start_time

        if final_answer == "":
            final_answer = "I am sorry, but I was unable to fulfill your request."

        self.debug_output += f'Final Answer: {final_answer}\n'
        logger.info(f'Final Answer: {final_answer}')
        return {"result": final_answer, "debug": self.debug_output}
