import asyncio
import json
import os
import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime

from google import genai
from google.genai import types

SUB_AGENT_KEY = os.getenv("SUB_AGENT_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
SUB_AGENT_MODEL = "models/gemini-2.5-flash-latest"


class BaseAgent(ABC):
    """Base class for all SODA sub-agents.
    
    Each agent runs independently using a separate Gemini API key
    (SUB_AGENT_GEMINI_API_KEY) so it doesn't consume the main quota.
    Agents execute as asyncio tasks and return results that are
    injected into the main conversation via inject_text().
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self._client = None
        self._last_call = 0.0
        self._call_count = 0
        self._error_count = 0

    @property
    @abstractmethod
    def tool_definitions(self) -> list:
        """Return function declaration dicts for Gemini tool list."""
        pass

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(
                http_options={"api_version": "v1beta"},
                api_key=SUB_AGENT_KEY,
            )
        return self._client

    async def call_gemini(self, system_prompt: str, user_prompt: str,
                          timeout: int = 30) -> dict:
        """Call Gemini with the sub-agent key. Returns parsed response."""
        self._call_count += 1
        self._last_call = time.time()
        client = self._get_client()
        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=SUB_AGENT_MODEL,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.3,
                        max_output_tokens=4096,
                    ),
                ),
                timeout=timeout,
            )
            text = response.text.strip() if response and response.text else ""
            return {"success": True, "content": text}
        except asyncio.TimeoutError:
            self._error_count += 1
            return {"success": False, "error": f"Agent {self.name} timed out after {timeout}s"}
        except Exception as e:
            self._error_count += 1
            return {"success": False, "error": f"Agent {self.name} error: {str(e)}"}

    async def call_gemini_json(self, system_prompt: str, user_prompt: str,
                               timeout: int = 30) -> dict:
        """Call Gemini and parse JSON response."""
        result = await self.call_gemini(system_prompt, user_prompt, timeout)
        if not result.get("success"):
            return result
        try:
            data = json.loads(result["content"])
            return {"success": True, "data": data}
        except (json.JSONDecodeError, TypeError) as e:
            return {"success": False, "error": f"JSON parse failed: {e}", "raw": result["content"]}

    def get_stats(self) -> dict:
        return {
            "name": self.name,
            "calls": self._call_count,
            "errors": self._error_count,
            "last_call": datetime.fromtimestamp(self._last_call).isoformat() if self._last_call else None,
        }

    @abstractmethod
    async def execute(self, **kwargs) -> dict:
        """Execute the agent's primary function. Override in subclass."""
        pass

    def to_tool_dict(self) -> dict:
        """Convert this agent to a Gemini function declaration."""
        tools = self.tool_definitions
        return tools[0] if tools else None
