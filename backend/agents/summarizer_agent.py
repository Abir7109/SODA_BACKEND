from .base_agent import BaseAgent


class SummarizerAgent(BaseAgent):
    """Summarization agent — condenses long text into concise summaries.
    Supports different summary styles and lengths.
    """

    def __init__(self):
        super().__init__(
            name="agent_summarize",
            description="Summarize long text, articles, documents, or conversations. Returns a concise summary in the requested style and length. Use when the user wants a quick overview of lengthy content."
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
                        "description": "The full text to summarize"
                    },
                    "style": {
                        "type": "STRING",
                        "description": "Summary style: 'concise' (1-2 sentences), 'normal' (short paragraph), 'detailed' (multi-paragraph with key points)"
                    },
                    "focus": {
                        "type": "STRING",
                        "description": "Optional focus area — what aspect to emphasize (e.g. 'key arguments', 'technical details', 'action items', 'decisions')"
                    }
                },
                "required": ["text"]
            }
        }]

    async def execute(self, text: str = "", style: str = "normal",
                      focus: str = "", **kwargs) -> dict:
        if not text:
            return {"success": False, "error": "No text provided for summarization"}

        style_guides = {
            "concise": "ONE paragraph of 1-2 sentences. Capture only the single most important point.",
            "normal": "A brief summary of 3-5 sentences covering the main points.",
            "detailed": "A thorough summary with key points, supporting details, and conclusions. Use bullet points for clarity.",
        }
        style_guide = style_guides.get(style, style_guides["normal"])
        system_prompt = (
            "You are a professional summarizer. Condense information "
            "while preserving accuracy, key facts, and important nuance. "
            "Do not add information not present in the original text."
        )
        user_prompt = f"Summarize the following text.\nStyle: {style_guide}"
        if focus:
            user_prompt += f"\nFocus area: {focus}"
        user_prompt += f"\n\n---\n{text[:8000]}"

        result = await self.call_gemini(system_prompt, user_prompt, timeout=20)
        return {
            "success": result.get("success", False),
            "style": style,
            "summary": result.get("content", ""),
            "original_length": len(text),
            "error": result.get("error"),
        }
