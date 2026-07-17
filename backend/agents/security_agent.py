from .base_agent import BaseAgent


class SecurityAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="agent_security",
            description="Analyze code and infrastructure for security vulnerabilities. Performs threat modeling, secure code review, vulnerability assessment, and provides fixes. Use for security audits, vulnerability scanning, OWASP analysis, and secure code reviews."
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
                        "description": "Security task: 'audit' (review code for vulnerabilities), 'threat_model' (analyze architecture risks), 'remediate' (fix a specific vulnerability), or 'best_practices' (security checklist)"
                    },
                    "target": {
                        "type": "STRING",
                        "description": "The code, config, URL, or description to analyze"
                    },
                    "language": {
                        "type": "STRING",
                        "description": "Programming language (for code audits)"
                    }
                },
                "required": ["task", "target"]
            }
        }]

    async def execute(self, task: str = "", target: str = "",
                      language: str = "", **kwargs) -> dict:
        valid = ["audit", "threat_model", "remediate", "best_practices"]
        if task not in valid:
            return {"success": False, "error": f"Invalid task '{task}'. Valid: {', '.join(valid)}"}

        system_prompt = (
            "You are a senior application security engineer. "
            "You make developers write secure code without even realizing it. "
            "You are developer-first, empathetic, pragmatic. You know most security vulnerabilities "
            "are honest mistakes by talented developers who were never taught secure coding. "
            "You fix the system, not the person. You speak in code examples, not policy documents.\n\n"
            "Core expertise: OWASP Top 10, CWE Top 25, threat modeling (STRIDE/PASTA), "
            "SAST/DAST integration, secure code review, authentication/authorization patterns, "
            "cryptographic best practices, input validation, and data protection.\n\n"
            "Always provide specific, actionable fixes with code examples. "
            "Distinguish between 'fix before merge' (exploitable) and 'improve when possible' (hardening)."
        )

        prompts = {
            "audit": f"Perform a security audit of this {'code (' + language + ')' if language else 'target'}:\n\n{target}\n\nList each vulnerability with: severity, CWE reference, exploit impact, and specific fix code.",
            "threat_model": f"Perform threat modeling for:\n\n{target}\n\nUse STRIDE. Identify trust boundaries, data flows, attack surfaces. Produce actionable security requirements.",
            "remediate": f"Analyze this vulnerability and provide a fix:\n\n{target}\n\nExplain the root cause and provide the complete secure implementation.",
            "best_practices": f"Generate a security best practices checklist for:\n\n{target}\n\nCover authentication, authorization, input validation, data protection, logging, and dependencies."
        }

        result = await self.call_gemini(system_prompt, prompts.get(task, target), timeout=45)
        return {
            "success": result.get("success", False),
            "task": task,
            "target": target[:200],
            "result": result.get("content", ""),
            "error": result.get("error"),
        }
