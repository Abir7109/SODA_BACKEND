from .base_agent import BaseAgent


class SocialAgent(BaseAgent):
    """Social media and trend analysis agent.
    Analyzes social media trends, generates post ideas, and provides
    content strategy recommendations.
    """

    def __init__(self):
        super().__init__(
            name="agent_social",
            description="Analyze social media trends, generate post ideas, create content strategies, or analyze engagement patterns. Use for social media planning, trend research, hashtag optimization, and content calendar suggestions."
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
                        "description": "Task type: 'trends', 'content_ideas', 'strategy', 'hashtags', 'engagement_tips', or 'post_analysis'"
                    },
                    "platform": {
                        "type": "STRING",
                        "description": "Social platform: 'twitter', 'instagram', 'linkedin', 'facebook', 'youtube', 'tiktok'"
                    },
                    "topic": {
                        "type": "STRING",
                        "description": "Topic, niche, or industry to focus on"
                    },
                    "details": {
                        "type": "STRING",
                        "description": "Additional context, current content, or specific requirements"
                    }
                },
                "required": ["task"]
            }
        }]

    async def execute(self, task: str = "", platform: str = "twitter",
                      topic: str = "", details: str = "", **kwargs) -> dict:
        system_prompt = (
            "You are a social media strategist and content expert. "
            "Provide actionable, platform-specific advice. "
            "Focus on current best practices and engagement optimization."
        )
        user_parts = [f"Platform: {platform}", f"Task: {task}"]
        if topic:
            user_parts.append(f"Topic: {topic}")
        if details:
            user_parts.append(f"Details: {details}")

        result = await self.call_gemini(system_prompt, "\n\n".join(user_parts), timeout=20)
        return {
            "success": result.get("success", False),
            "task": task,
            "platform": platform,
            "result": result.get("content", ""),
            "error": result.get("error"),
        }
