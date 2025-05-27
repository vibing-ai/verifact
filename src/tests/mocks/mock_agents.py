from typing import Any
from pydantic import BaseModel
from agents import Agent
import asyncio

class MockResult:
    def __init__(self, output: Any):
        self.output = output

    def final_output_as(self, _type):
        return self.output

class MockAgent(Agent):
    def __init__(self, output, name="MockAgent"):
        self._output = output
        self.handoffs = []
        self._name = name
        self.mcp_config = {"prompt": "mock-prompt"}
        self.mcp_servers = []
        self.tools = []
        self.input_guardrails = []
        self.output_guardrails = []
        self.model_settings = []

    async def process(self, input_data):
        return MockResult(self._output)

    @property
    def name(self):
        return self._name
