import asyncio
import json
import os
from typing import Dict, Any, List, Tuple
from pathlib import Path
from tqdm.asyncio import tqdm

from openai import AsyncOpenAI
from opaca_client import OpacaClient
from utils import openapi_to_functions

# Configuration
DEFAULT_MODEL = "gpt-4o-2024-11-20"
DEFAULT_OUTPUT_FILE = "agents_tools.json"

SYSTEM_PROMPT = """
You are an expert at analyzing software agents and their capabilities.
Your goal is to create comprehensive summaries of agents and their functions for an orchestration agent.
This orchestration agent should be able to assign tasks to the right agent based on the user's request.
To do this, you need to create extreamly precise and comprehensive summaries of the agents and their functions 
so that the orchestration agent can easily understand the capabilities of each agent.
Keep in mind that the summaries should be as precise and to the point as possible.
"""

AGENT_ANALYSIS_PROMPT = """Analyze the following agent and its functions to provide a comprehensive summary of its capabilities.
Focus on:
1. The agent's overall purpose/objective
2. A concise summary of how its functions work together
3. A detailed description of what the agent should be used for

Agent Name: {agent_name}
Available Functions:
{functions}

You should only provide the summary, not the agent name or functions.
The summary should be a single paragraph that is easy to read and understand.
The paragraph should only contain 1-3 sentences and be extreamly precise.

Keep descriptions clear, specific, and focused on their exact capabilities."""

INSTRUCTIONS_SYSTEM_PROMPT = """You are an expert at writing precise instructions for agents.
Your goal is to create detailed instructions for an agent and on how it should behave.
These instructions should be passed to the actual worker agent.
Therefore, it should be clear how the agent should achieve certain goals and tasks."""

AGENT_INSTRUCTIONS_PROMPT = """Based on the following agent information, create detailed instructions for this agent and on how it should behave.
Include specific details about how to use each function effectively.

Agent Name: {agent_name}

Previous Analysis:
{summary}

Available Functions:
{functions}

Keep all of the best practices on writing precise agent instructions in mind.
The goal would be to pass these instructions to the actual worker agent.
Therefore, it should be clear how the agent should achieve certain goals and tasks.
Aditionally, all the instructions should be written in an imperative "You should..." format.
Be as short and as precise as possible while still providing ALL the necessary information."""

async def analyze_agent_with_gpt(
    client: AsyncOpenAI,
    agent_name: str,
    functions: List[Dict],
    detailed_functions: List[Dict],
    model: str = DEFAULT_MODEL
) -> tuple[str, str]:
    """
    Use GPT-4 to analyze an agent's capabilities and generate a summary.
    Returns a tuple of (agent_name, summary)
    """
    # Get detailed function information for this agent
    agent_detailed_functions = [
        f for f in detailed_functions 
        if f["function"]["name"].startswith(f"{agent_name}--")
    ]
    
    # Format function information for the prompt
    function_details = []
    for func in agent_detailed_functions:
        name = func["function"]["name"].split("--")[1]
        desc = func["function"]["description"] or "No description available"
        params = func["function"]["parameters"]["properties"].get("requestBody", {}).get("properties", {})
        required = func["function"]["parameters"]["properties"].get("requestBody", {}).get("required", [])
        
        param_str = ""
        if params:
            param_str = "\nParameters:"
            for param_name, param_info in params.items():
                required_str = " (required)" if param_name in required else ""
                param_str += f"\n  - {param_name}{required_str}: {param_info.get('type', 'unknown type')}"
        
        function_details.append(f"- {name}: {desc}{param_str}")
    
    prompt = AGENT_ANALYSIS_PROMPT.format(
        agent_name=agent_name,
        functions="\n".join(function_details)
    )
    
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    
    return agent_name, response.choices[0].message.content

async def generate_agent_instructions(
    client: AsyncOpenAI,
    agent_name: str,
    summary: str,
    functions: List[Dict],
    detailed_functions: List[Dict],
    model: str = DEFAULT_MODEL
) -> tuple[str, str]:
    """
    Generate detailed instructions for using an agent and its functions.
    Returns a tuple of (agent_name, instructions)
    """
    # Get detailed function information for this agent
    agent_detailed_functions = [
        f for f in detailed_functions 
        if f["function"]["name"].startswith(f"{agent_name}--")
    ]
    
    # Format function information for the prompt
    function_details = []
    for func in agent_detailed_functions:
        name = func["function"]["name"].split("--")[1]
        desc = func["function"]["description"] or "No description available"
        params = func["function"]["parameters"]["properties"].get("requestBody", {}).get("properties", {})
        required = func["function"]["parameters"]["properties"].get("requestBody", {}).get("required", [])
        
        param_str = ""
        if params:
            param_str = "\nParameters:"
            for param_name, param_info in params.items():
                required_str = " (required)" if param_name in required else ""
                param_str += f"\n  - {param_name}{required_str}: {param_info.get('type', 'unknown type')}"
        
        function_details.append(f"- {name}: {desc}{param_str}")
    
    prompt = AGENT_INSTRUCTIONS_PROMPT.format(
        agent_name=agent_name,
        summary=summary,
        functions="\n".join(function_details)
    )
    
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": INSTRUCTIONS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    
    return agent_name, response.choices[0].message.content

async def get_agents_tools(
    url: str,
    user: str = None,
    pwd: str = None,
    model: str = DEFAULT_MODEL,
    output_file: str = DEFAULT_OUTPUT_FILE
) -> Dict[str, Any]:
    """
    Connects to OPACA platform and retrieves all agents and their tools.
    Returns a dictionary with two formats:
    1. agents_simple: Simple mapping of agent names to their function names and summaries
    2. agents_detailed: Detailed OpenAPI spec of all functions with parameters

    Args:
        url: The URL of the OPACA platform
        user: Optional username for authentication
        pwd: Optional password for authentication
        model: The OpenAI model to use for analysis (default: DEFAULT_MODEL)
        output_file: Path to save the JSON output (default: DEFAULT_OUTPUT_FILE)
    """
    client = OpacaClient()
    status = await client.connect(url, user, pwd)
    if status != 200:
        raise Exception(f"Failed to connect to OPACA platform. Status code: {status}")

    # Get simple agent->functions mapping
    agents_simple = await client.get_actions()
    num_agents = len(agents_simple)
    print(f"\nFound {num_agents} agents in the OPACA platform")

    # Get detailed OpenAPI spec
    actions_spec = await client.get_actions_with_refs()
    
    # Transform to OpenAI function format for easier consumption
    functions, error_msg = openapi_to_functions(actions_spec, use_agent_names=True)
    if error_msg:
        print(f"Warnings during transformation:\n{error_msg}")

    # Initialize OpenAI client
    openai_client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )

    print(f"\nCreating agent summaries using model: {model}")
    
    # Create tasks for parallel processing of summaries
    summary_tasks = [
        analyze_agent_with_gpt(openai_client, agent_name, agent_functions, functions, model)
        for agent_name, agent_functions in agents_simple.items()
    ]
    
    # Process all agents in parallel with progress bar
    summaries = await tqdm.gather(*summary_tasks, desc="Generating agent summaries")
    
    # Create a dictionary of agent summaries
    agent_summaries = {agent_name: summary for agent_name, summary in summaries}
    
    print(f"\nGenerating detailed instructions for each agent")
    
    # Create tasks for parallel processing of instructions
    instruction_tasks = [
        generate_agent_instructions(
            openai_client,
            agent_name,
            agent_summaries[agent_name],
            agents_simple[agent_name],
            functions,
            model
        )
        for agent_name in agents_simple.keys()
    ]
    
    # Process all instruction generations in parallel
    #instructions = await tqdm.gather(*instruction_tasks, desc="Generating agent instructions")
    
    # Convert results to dictionary
    agents_with_summaries = {
        agent_name: {
            "functions": agents_simple[agent_name],
            "summary": agent_summaries[agent_name],
            #"instructions": instruction
        }
        for agent_name in agent_summaries.keys() #, instruction in instructions
    }

    result = {
        "agents_simple": agents_with_summaries,
        "agents_detailed": functions
    }

    # Save to JSON file
    output_path = Path(output_file)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\nFinished generating summaries and instructions for {num_agents} agents")
    print(f"Writing agent details to: {output_path.absolute()}")

    return result

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate summaries of OPACA agents and their functions")
    parser.add_argument("--url", default="http://10.42.6.107:8000", help="OPACA platform URL")
    parser.add_argument("--user", help="Username for authentication")
    parser.add_argument("--pwd", help="Password for authentication")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model to use for analysis")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help="Output JSON file path")
    
    args = parser.parse_args()

    try:
        await get_agents_tools(
            url=args.url,
            user=args.user,
            pwd=args.pwd,
            model=args.model,
            output_file=args.output
        )
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 