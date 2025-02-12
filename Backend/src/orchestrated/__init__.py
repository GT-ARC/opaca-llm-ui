"""
Self-orchestrated backend that assigns tasks to multiple specialized agents that are dynamically created based on the running opaca platform.
Each agent has specific capabilities and functions, coordinated by an orchestrator.
"""

from .backend import SelfOrchestratedBackend