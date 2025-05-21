"""Base interfaces for the agent system.

This module defines the core protocols and data structures for the agent system,
establishing a foundation for clean separation of concerns.
"""

from typing import Generic, Protocol, TypeVar

# Define a generic input and output type for agents
T_Input = TypeVar("T_Input")
T_Output = TypeVar("T_Output")


class Agent(Protocol, Generic[T_Input, T_Output]):
    """Base protocol for all agents in the system.

    This protocol defines the minimal interface that all agents must implement.
    Specific agent types will extend this with more specialized interfaces.
    """

    async def process(self, input_data: T_Input) -> T_Output:
        """Process the input data and return a result.

        Args:
            input_data: The input data to process

        Returns:
            The processed output data
        """
        ...
