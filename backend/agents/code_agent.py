from .base_agent import BaseAgent


class CodeAgent(BaseAgent):
    """Code generation, review, analysis, and debugging agent.
    Uses its own Gemini quota so main loop is not blocked.
    """

    def __init__(self):
        super().__init__(
            name="agent_code",
            description="Generate, review, analyze, debug, or explain code. Handles programming questions, code reviews, bug finding, refactoring suggestions, and writing code snippets in any language. Returns the code with explanation."
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
                        "description": "The coding task: 'generate', 'review', 'debug', 'explain', 'refactor', or 'convert'"
                    },
                    "language": {
                        "type": "STRING",
                        "description": "Programming language (e.g. 'python', 'javascript', 'typescript', 'rust')"
                    },
                    "code": {
                        "type": "STRING",
                        "description": "The code to review, debug, explain, or refactor (optional for generate tasks)"
                    },
                    "requirements": {
                        "type": "STRING",
                        "description": "Description of what the code should do (for generate/refactor tasks)"
                    }
                },
                "required": ["task"]
            }
        }]

    async def execute(self, task: str = "", language: str = "python",
                      code: str = "", requirements: str = "", **kwargs) -> dict:
        valid_tasks = ["generate", "review", "debug", "explain", "refactor", "convert"]
        if task not in valid_tasks:
            return {"success": False, "error": f"Invalid task '{task}'. Valid: {', '.join(valid_tasks)}"}

        system_prompt = (
            f"You are an expert {language} developer. "
            f"Provide clear, production-quality {language} code with explanations. "
            f"Focus on correctness, readability, and best practices."
        )
        if task == "generate":
            user_prompt = f"Write {language} code for:\n{requirements}\n\nInclude a brief explanation of the approach."
        elif task == "review":
            user_prompt = f"Review this {language} code for bugs, style issues, and improvements:\n\n{code}"
        elif task == "debug":
            user_prompt = f"Debug this {language} code. Find and fix the issues:\n\n{code}"
        elif task == "explain":
            user_prompt = f"Explain this {language} code in detail:\n\n{code}"
        elif task == "refactor":
            user_prompt = f"Refactor this {language} code to be cleaner and more maintainable. Requirements: {requirements}\n\nCode:\n{code}"
        elif task == "convert":
            user_prompt = f"Convert this code to {language}:\n\n{code}"
        else:
            return {"success": False, "error": f"Unknown task: {task}"}

        result = await self.call_gemini(system_prompt, user_prompt, timeout=45)
        return {
            "success": result.get("success", False),
            "task": task,
            "language": language,
            "result": result.get("content", ""),
            "error": result.get("error"),
        }
