# OPACA FAQ

## General Use

**Q1: What is OPACA and how does it work?**  
A: OPACA is a platform that connects language model agents to backend services, enabling the assistant to fetch data, execute workflows, or control external systems by invoking defined tools.

**Q2: How do I connect to OPACA and why is it necessary?**  
A: To connect, enter the backend URL (e.g., `http://localhost:8000`) along with your username and password, then click "Connect." This is necessary because OPACA provides the assistant with access to backend tools. Without connecting, the assistant cannot perform any tool-based operations.

**Q3: What is an interaction mode and how does it affect behavior?**  
A: Interaction modes define how the assistant uses tools. Modes range from direct prompting to advanced, multi-step tool orchestration.

**Q4: Can I choose or see which AI model is being used?**  
A: Yes, in most cases. You can view and select models in the configuration view. Some orchestration modes use predefined model combinations.

**Q5: Can I change the interaction mode during a conversation?**  
A: Yes, you can switch modes at any time.

**Q6: What are the differences between interaction modes?**  
A:  
- **Simple Prompt:** Direct language model prompt, no tools.  
- **Tool LLM:** Two language model roles handle prompt and evaluate tool responses.  
- **Self-Orchestrated:** The language model plans and executes multi-step tool calls.  
- **Simple Tool Prompt:** Direct language model prompt using tool parameters.

**Q7: Can I use multiple interaction modes at once?**  
A: No, only one mode can be active at a time. You can switch modes as needed.

## Tools and Services

**Q8: What are tools and services in OPACA?**  
A: Tools are backend APIs or functions exposed by OPACA. The assistant can call them to perform tasks like querying databases, triggering actions, or controlling systems.

**Q9: How can I see which tools or services are available?**  
A: Tools are loaded from the OPACA server when you connect. You can ask the assistant or view them in the interface (if supported).

**Q10: Can I guide the assistant to use a specific tool or parameters?**  
A: Yes. If you know the tool schema, you can describe the tool and its parameters in your prompt. The assistant interprets this and executes the call.

**Q11: Why isn’t the assistant using a tool I know exists?**  
A: The tool might be named differently, require missing parameters, or the assistant may not have chosen it. Try specifying the tool explicitly in your prompt.

**Q12: Why does the assistant sometimes call multiple tools?**  
A: Complex queries may require multiple steps. The assistant can chain tool calls to gather intermediate data and complete the task.

**Q13: Can OPACA be used to control live systems?**  
A: Yes, if those systems are connected as services. Use caution when enabling access to critical systems.

**Q14: Can I deploy my own tools or services to OPACA?**  
A: Yes. If you have access to the backend, you can deploy custom OPACA agent containers and register new tools.

**Q15: Can I chain tools manually?**  
A: Not directly through the UI. You can simulate chaining by prompting the assistant with follow-up instructions based on previous outputs, or by explicitly asking the assistant to use tools in a specific order.

## Prompts and Language Model Behavior

**Q16: What kind of prompts can I use?**  
A: Natural language prompts describing your goal. You can check the Prompt Library for examples and templates.

**Q17: Where can I learn how to write better prompts?**  
A: Use the Prompt Library, in-app tips, and official documentation for guidance.

**Q18: Can I see the tool requests the assistant is making?**  
A: Yes, depending on the configuration. The assistant may show tool calls in its responses if transparency is enabled.

## Debugging and Transparency

**Q19: How can I understand what the assistant is doing behind the scenes?**  
A: Tool calls and results are usually visible in the assistant’s messages. Developer mode or advanced settings may expose more logs.

**Q20: Can I save or export conversations?**  
A: This depends on the platform. The current UI does not have a save function, but full history may be accessible via the backend’s API for developers.

---

# Top 5 FAQ

1. **What is OPACA and why do I need to connect to it?**  
   OPACA enables the assistant to use tools. Without connecting, tool-based actions cannot be performed.

2. **What are tools/services and how do I know which are available?**  
   Tools are backend APIs registered in OPACA. They are loaded automatically when connecting to a backend.

3. **What is the difference between the interaction modes?**  
   - Simple Prompt: Direct call to the language model.  
   - Tool LLM: Two language model roles to check tool results.  
   - Self-Orchestrated: Language model manages multiple steps and planning.  
   - Simple Tool Prompt: Direct call using the tool parameter.

4. **What prompts can I use and where can I learn more?**  
   Use natural language to describe what you want. Check the Prompt Library for examples and templates.

5. **Can I upload my own tools/services?**  
   Yes. If you have the backend URL and credentials, you can deploy and register new tools with OPACA.

