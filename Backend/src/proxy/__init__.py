"""
Different backends relaying the messages directly to some other domain-specific LLMs
running at DAI-Labor/GT-ARC.
"""

from .proxy_backends import KnowledgeBackend, DataAnalysisBackend
