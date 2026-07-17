from .base_agent import BaseAgent


class DataAgent(BaseAgent):
    """Data extraction, transformation, and analysis agent.
    Processes structured and unstructured data in the background.
    """

    def __init__(self):
        super().__init__(
            name="agent_data",
            description="Extract, transform, analyze, or visualize data. Handles CSV/JSON parsing, data cleaning, format conversion, statistical analysis, and generating insights from datasets. Pass the data and describe what you need."
        )

    @property
    def tool_definitions(self) -> list:
        return [{
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "task": {
                        "type": "STRING",
                        "description": "What to do: 'extract', 'transform', 'analyze', 'convert', 'validate', or 'visualize'"
                    },
                    "data": {
                        "type": "STRING",
                        "description": "The input data as a string (CSV, JSON, text, etc.)"
                    },
                    "format": {
                        "type": "STRING",
                        "description": "Target format for conversion: 'json', 'csv', 'markdown', 'html'"
                    },
                    "instructions": {
                        "type": "STRING",
                        "description": "Specific instructions for what to do with the data"
                    }
                },
                "required": ["task"]
            }
        }]

    async def execute(self, task: str = "", data: str = "", format: str = "",
                      instructions: str = "", **kwargs) -> dict:
        system_prompt = (
            "You are a data processing expert. Handle data extraction, "
            "transformation, analysis, and conversion tasks accurately. "
            "Always preserve data integrity and provide clear output."
        )
        user_parts = [f"Task: {task}"]
        if data:
            user_parts.append(f"Input data:\n{data[:5000]}")
        if format:
            user_parts.append(f"Target format: {format}")
        if instructions:
            user_parts.append(f"Instructions: {instructions}")

        result = await self.call_gemini(system_prompt, "\n\n".join(user_parts), timeout=45)
        return {
            "success": result.get("success", False),
            "task": task,
            "result": result.get("content", ""),
            "error": result.get("error"),
        }
