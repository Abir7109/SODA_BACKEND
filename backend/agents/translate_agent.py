from .base_agent import BaseAgent


class TranslateAgent(BaseAgent):
    """Translation agent — translates text between languages.
    Supports all major languages. Non-blocking execution.
    """

    def __init__(self):
        super().__init__(
            name="agent_translate",
            description="Translate text between languages. Supports all major languages. Returns the translated text along with detected source language."
        )

    @property
    def tool_definitions(self) -> list:
        return [{
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "text": {
                        "type": "STRING",
                        "description": "The text to translate"
                    },
                    "target_language": {
                        "type": "STRING",
                        "description": "Target language (e.g. 'spanish', 'french', 'arabic', 'bengali'). Required."
                    },
                    "source_language": {
                        "type": "STRING",
                        "description": "Source language (optional — auto-detected if not provided)"
                    }
                },
                "required": ["text", "target_language"]
            }
        }]

    async def execute(self, text: str = "", target_language: str = "",
                      source_language: str = "", **kwargs) -> dict:
        if not text or not target_language:
            return {"success": False, "error": "Both text and target_language are required"}

        source = source_language if source_language else "auto-detected"
        system_prompt = (
            "You are a professional translator. Translate the given text accurately "
            "while preserving tone, meaning, and cultural nuances. "
            "Return ONLY the translated text."
        )
        user_prompt = (
            f"Translate the following text from {source} to {target_language}:\n\n"
            f"{text}\n\n"
            f"Return only the translated text."
        )

        result = await self.call_gemini(system_prompt, user_prompt, timeout=15)
        return {
            "success": result.get("success", False),
            "source_text": text,
            "translated_text": result.get("content", ""),
            "target_language": target_language,
            "source_language": source_language if source_language else "auto",
            "error": result.get("error"),
        }
