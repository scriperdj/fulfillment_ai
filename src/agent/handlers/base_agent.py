"""
Base Agent Class (Stretch Goal)
Provides common interface for all specialized agents
"""

import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents"""

    def __init__(self, agent_name: str, agent_type: str):
        """
        Initialize base agent
        Args:
            agent_name: Unique agent identifier
            agent_type: Agent type (shipment, customer, refund, escalation)
        """
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.conversation_history = []
        self.state = {}

    @abstractmethod
    async def handle(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a deviation/task
        Args:
            context: Order and deviation context
        Returns:
            Resolution output
        """
        pass

    async def add_to_history(self, role: str, content: str) -> None:
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_state(self) -> Dict[str, Any]:
        """Get agent state"""
        return {
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "history_length": len(self.conversation_history),
            "state": self.state,
        }

    def reset_state(self) -> None:
        """Reset agent state"""
        self.conversation_history = []
        self.state = {}
        logger.info(f"Reset state for {self.agent_name}")
