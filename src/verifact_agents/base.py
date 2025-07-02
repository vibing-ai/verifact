"""Base interfaces for the agent system.

This module defines the core protocols and data structures for the agent system,
establishing a foundation for clean separation of concerns.
"""

from typing import Generic, Protocol, TypeVar

T_Input = TypeVar('T_Input')
T_Output = TypeVar('T_Output')

class Agent(Protocol, Generic[T_Input, T_Output]):
    """Base protocol for all agents."""
    async def process(self, input_data: T_Input) -> T_Output:
        """Process the input data and return a result."""
        ...

# Placeholder for future implementation
