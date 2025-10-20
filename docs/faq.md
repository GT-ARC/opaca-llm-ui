# SAGE FAQ

## General Use

**What is SAGE and how does it work?**
SAGE is a platform that connects language model agents to OPACA services, enabling the assistant to fetch data, execute workflows, or control external systems by invoking defined tools.

**How do I connect to OPACA and why is it necessary?**
To connect, enter the OPACA URL (e.g., `http://localhost:8000`) along with your username and password, then click "Connect." This is necessary because OPACA provides the assistant with access to OPACA tools. Without connecting, the assistant cannot perform any tool-based operations.

**What is an interaction mode and how does it affect behavior?**
Interaction modes define how the assistant uses tools. Modes range from direct prompting to advanced, multi-step tool orchestration.

**Can I choose or see which AI model is being used?**
Yes, in most cases. You can view and select models in the configuration view. Some orchestration modes use predefined model combinations.

**Can I change the interaction mode during a conversation?**
Yes, you can switch modes at any time.

**What are the differences between interaction modes?**
 
- **Simple Prompt:** Direct language model prompt, no tools.
- **Tool LLM:** Two language model roles handle prompt and evaluate tool responses.
- **Self-Orchestrated:** The language model plans and executes multi-step tool calls.
- **Simple Tool Prompt:** Direct language model prompt using tool parameters.

**Can I use multiple interaction modes at once?**
No, only one mode can be active at a time. You can switch modes as needed.

## Tools and Services

**What are tools and services in OPACA?**
Tools are APIs or functions exposed by OPACA. The assistant can call them to perform tasks like querying databases, triggering actions, or controlling systems.

**How can I see which tools or services are available?**
Tools are loaded from the OPACA server when you connect. You can ask the assistant or view them in the interface (if supported).

**Can I guide the assistant to use a specific tool or parameters?**
Yes. If you know the tool schema, you can describe the tool and its parameters in your prompt. The assistant interprets this and executes the call.

**Why isn’t the assistant using a tool I know exists?**
The tool might be named differently, require missing parameters, or the assistant may not have chosen it. Try specifying the tool explicitly in your prompt.

**Why does the assistant sometimes call multiple tools?**
Complex queries may require multiple steps. The assistant can chain tool calls to gather intermediate data and complete the task.

**Can OPACA be used to control live systems?**
Yes, if those systems are connected as services. Use caution when enabling access to critical systems.

**Can I deploy my own tools or services to OPACA?**
Yes. If you have access to the OPACA platform, you can deploy custom OPACA agent containers and register new tools.

**Can I chain tools manually?**
Not directly through the UI. You can simulate chaining by prompting the assistant with follow-up instructions based on previous outputs, or by explicitly asking the assistant to use tools in a specific order.

## Prompts and Language Model Behavior

**What kind of prompts can I use?**
Natural language prompts describing your goal. You can check the Prompt Library for examples and templates.

**Where can I learn how to write better prompts?**
Use the Prompt Library, in-app tips, and official documentation for guidance.

**Can I see the tool requests the assistant is making?**
Yes, depending on the configuration. The assistant may show tool calls in its responses if transparency is enabled.

## Debugging and Transparency

**How can I understand what the assistant is doing behind the scenes?**
Tool calls and results are usually visible in the assistant’s messages. Developer mode or advanced settings may expose more logs.

**Can I save or export conversations?**
This depends on the platform. The current UI does not have a save function, but full history may be accessible via the backend’s API for developers.
