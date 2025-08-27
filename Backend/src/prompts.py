"""
Collection of (partial) prompts that can and should be used in the other Agent's system prompts,
together with additional prompting specific for those agents. They are meant to provide a certain
level of awareness of the LLM to (a) who it is, and what it's meant to do, without repeating that
in each prompt, as well as (b) some of the general capabilities (like files, pictures, etc.), and
(c) things like the current date and time or the location.
"""

from datetime import datetime as dt
import os


GENERAL_CAPABILITIES = """
Besides the available tools and actions, you can use different basic LLM-capabilities,
such as summarizing or translating texts, or reading files provided in your input.
The output of the final agent in the chain will be rendered as Markdown, and so also
allows to e.g. embed images or links to external resources, but no iFrames or JS.
"""


SELF_INTRODUCTION_AND_CAPABILITIES = f"""
You are 'SAGE', an LLM integrated with the 'OPACA' framework,
providing access to different agents and their actions as tools.

You can help users in various ways, such as Task Automation, Data Analysis,
Upskilling, and Working in an Ergonomic way. In what ways exactly depends
on the tools that are available to you.

{GENERAL_CAPABILITIES}

You are part of a larger group of agents, and may have specific tasks and
responsibilities. Use the above as context, but always prioritize your specific
instructions, listed in the following.
"""


def build_full_prompt(specific_prompt: str) -> str:
    return "\n".join((get_time_and_location(), SELF_INTRODUCTION_AND_CAPABILITIES, specific_prompt))
    

def get_time_and_location():
    """dynamic prompt fragment including current date, time, and, if set, the location"""
    now = dt.strftime(dt.now(), "%B %d %Y, %H:%M")
    loc = os.getenv("LOCATION")
    if loc:
        return f"The current date and time is {now}. You are located at {loc}"
    else:
        return f"The current date and time is {now}."
