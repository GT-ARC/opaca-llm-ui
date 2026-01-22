"""
Collection of (partial) prompts that can and should be used in the other Agent's system prompts,
together with additional prompting specific for those agents. They are meant to provide a certain
level of awareness of the LLM to (a) who it is, and what it's meant to do, without repeating that
in each prompt, as well as (b) some of the general capabilities (like files, pictures, etc.), and
(c) things like the current date and time or the location.
"""

from datetime import datetime as dt
import os


def build_full_prompt(specific_prompt: str) -> str:
    SELF_INTRODUCTION_AND_CAPABILITIES = f"""
    You are part of an LLM Assistant called \"SAGE\". {get_time_and_location()} Following are your 
    individual tasks:
    """
    return "\n".join((SELF_INTRODUCTION_AND_CAPABILITIES, specific_prompt))
    

def get_time_and_location():
    """dynamic prompt fragment including current date, time, and, if set, the location"""
    now = dt.strftime(dt.now(), "%B %d %Y, %H:%M")
    loc = os.getenv("LOCATION")
    if loc:
        return f"The current date and time is {now}. You are located at {loc}."
    else:
        return f"The current date and time is {now}."
