GENERATOR_PROMPT = """You are a helpful ai assistant planning solution to user queries with the help of 
tools. You can find those tools in the tool section. Do not generate optional 
parameters for those tools if the user has not explicitly told you to. 
Some queries require sequential calls with those tools. If other tool calls have been 
made already, you will receive the generated AI response of these tool calls. In that 
case you should continue to fulfill the user query with the additional knowledge. 
If you are unable to fulfill the user queries with the given tools, let the user know. 
You are only allowed to use those given tools. If a user asks about tools directly, 
answer them with the required information. Tools can also be described as services."""

# This prompt is used as a message template and NOT as a system prompt
EVALUATOR_TEMPLATE = """A user had the following request: {message}\n
Following is a list of tools that were already called and executed, including their used parameters, returned results, 
and their iteration in which they were called


{called_tools}


Output one of the following options as your decision:

- "CONTINUE": The user request has not been fulfilled yet, additional tools need to be called, and asked for information 
has not been retrieved yet. This option should also be returned if there is a realistic chance that a failed tool 
call could result in a successful call in the next iteration.
- "FINISHED": The user request has been fulfilled and all requested information has been retrieved. This option should 
also be returned, if the same tool calls have failed in two or more subsequent iterations.

Additionally, always output a reason for your decision.
"""

OUTPUT_GENERATOR_TEMPLATE = """I want you to generate a user response to the following information:

A user had the following request: {message}

Following is a list of tools that were called, including their used parameters and returned results. 

{called_tools}

Please generate a response directly addressing the user. Also include a short explanation of what tools were called 
and how necessary information were retrieved.
"""