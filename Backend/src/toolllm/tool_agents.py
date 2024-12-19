from typing import Dict, Any

from ..models import LLMAgent, AgentMessage

TOOL_GENERATOR_PROMPT = """You are a helpful ai assistant that plans solution to user queries with the help of 
tools. You can find those tools in the tool section. Do not generate optional 
parameters for those tools if the user has not explicitly told you to. 
Some queries require sequential calls with those tools. If other tool calls have been 
made already, you will receive the generated AI response of these tool calls. In that 
case you should continue to fulfill the user query with the additional knowledge. 
If you are unable to fulfill the user queries with the given tools, let the user know. 
You are only allowed to use those given tools. If a user asks about tools directly, 
answer them with the required information. Tools can also be described as services."""


class ToolGenerator(LLMAgent):

    def __init__(self, llm, **kwargs):
        super().__init__(
            name="Tool Generator",
            llm=llm,
            system_prompt=TOOL_GENERATOR_PROMPT,
            **kwargs
        )

    def invoke(self, inputs: Dict[str, Any]) -> AgentMessage:
        return super().invoke(inputs)


class ToolEvaluator(LLMAgent):

    def __init__(self, llm, **kwargs):
        super().__init__(
            name="Tool Evaluator",
            llm=llm,
            system_prompt="",
            **kwargs
        )

    def invoke(self, inputs: Dict[str, Any]) -> AgentMessage:
        self.input_variables = ['query', 'tool_names', 'parameters', 'results']
        self.message_template = ("A user had the following request: {query}\n"
                                 "You just used the tools {tool_names} with the following parameters: {parameters}\n"
                                 "The results were {results}\n"
                                 "Generate a response explaining the result to a user. Decide if the user request "
                                 "requires further tools by outputting 'CONTINUE' or 'FINISHED' at the end of your "
                                 "response.")

        return super().invoke(inputs)
