"""
This module configures the root logger as soon as the application is loaded.

"""

import logging

class ColoredFormatter(logging.Formatter):
    """
    Custom logging formatter that logs output colorful
    """

    # Define agent-specific colors
    AGENT_COLORS = {
        # Tool-llm
        "Tool Generator": "\x1b[31;20m",  # Dim Red
        "Tool Evaluator": "\x1b[33;20m",  # Dim Yellow
        "Output Generator": "\x1b[32;20m", # Dim Green

        # Simple Roles
        "system": "\x1b[93m",  # Light Yellow
        "assistant": "\x1b[94m",  # Light Blue
        "user": "\x1b[97m",  # Light White

        # Orchestration
        "Orchestrator": "\x1b[93m", # bright red
        "AgentPlanner": "\x1b[95m", # bright magenta
        "WorkerAgent": "\x1b[96m", # bright cyan
        "AgentEvaluator": "\x1b[94m", # bright blue
        "OverallEvaluator": "\x1b[92m", # bright green
        "IterationAdvisor": "\x1b[35m", # magenta
    }

    def format(self, record: logging.LogRecord):
        agent_name = getattr(record, "agent_name", None)
        color = self.AGENT_COLORS.get(agent_name, "\x1b[38;20m") # Default = Dim White
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        if agent_name is None:
            base = f"{timestamp} [{record.levelname}] {record.module} {record.funcName} -"
        else:
            base = f"{timestamp} [{record.levelname}] {agent_name} -"

        # Split messages into lines to make colorful logging work in docker
        message_lines = record.getMessage().splitlines()
        formatted_lines = [
            f"{color}{base} {message_lines[0]}\x1b[0m",
        ] + [
            f"{color}{' ' * len(base)} {line}\x1b[0m"
            for line in message_lines[1:]
        ]
        return "\n".join(formatted_lines)


# Reduce logging level for httpx
logging.getLogger("httpx").setLevel(logging.WARNING)

# configure root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create colorful logging handler for agent messages
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(ColoredFormatter())

# Attach handler to root logger
logger.addHandler(console_handler)
