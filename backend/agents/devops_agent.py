from .base_agent import BaseAgent


class DevOpsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="agent_devops",
            description="Automate infrastructure, design CI/CD pipelines, manage deployments, and optimize cloud operations. Handles Docker, Kubernetes, Terraform, CI/CD, monitoring, scaling, and disaster recovery planning."
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
                        "description": "DevOps task: 'pipeline' (design CI/CD), 'infra' (infrastructure as code), 'deploy' (deployment strategy), 'monitor' (monitoring/alerting), or 'incident' (incident response playbook)"
                    },
                    "target": {
                        "type": "STRING",
                        "description": "Project or service description"
                    },
                    "tech_stack": {
                        "type": "STRING",
                        "description": "Technology stack (e.g. 'docker, kubernetes, aws, github actions')"
                    },
                    "context": {
                        "type": "STRING",
                        "description": "Current setup, requirements, or constraints"
                    }
                },
                "required": ["task", "target"]
            }
        }]

    async def execute(self, task: str = "", target: str = "",
                      tech_stack: str = "", context: str = "", **kwargs) -> dict:
        valid = ["pipeline", "infra", "deploy", "monitor", "incident"]
        if task not in valid:
            return {"success": False, "error": f"Invalid task '{task}'. Valid: {', '.join(valid)}"}

        system_prompt = (
            "You are a senior DevOps engineer who automates everything. "
            "You specialize in infrastructure automation, CI/CD pipeline development, and cloud operations. "
            "You streamline workflows, ensure reliability, and implement scalable deployment strategies "
            "that eliminate manual processes and reduce operational overhead.\n\n"
            f"Technology focus: {tech_stack or 'general cloud infrastructure'}.\n\n"
            "Core expertise: Infrastructure as Code (Terraform/CloudFormation/CDK), "
            "CI/CD (GitHub Actions/GitLab CI/Jenkins), container orchestration (Docker/Kubernetes), "
            "zero-downtime deployments (blue-green/canary/rolling), monitoring (Prometheus/Grafana/Datadog), "
            "auto-scaling, disaster recovery, and cost optimization.\n\n"
            "Every solution must include monitoring, alerting, and automated rollback capability. "
            "Design for reliability first, cost second."
        )

        prompts = {
            "pipeline": f"Design a CI/CD pipeline for:\n\nTarget: {target}\nStack: {tech_stack}\nContext: {context}\n\nProvide: pipeline stages diagram, tool choices with justifications, security scanning integration, deployment strategy, and rollback procedure.",
            "infra": f"Design infrastructure as code for:\n\nTarget: {target}\nStack: {tech_stack}\nContext: {context}\n\nProvide: architecture diagram text, resource list, Terraform/CDK code skeleton, networking setup, and cost estimate.",
            "deploy": f"Design a deployment strategy for:\n\nTarget: {target}\nStack: {tech_stack}\nContext: {context}\n\nProvide: strategy recommendation (blue-green/canary/rolling), step-by-step deployment flow, health check configuration, and rollback procedure.",
            "monitor": f"Design monitoring and alerting for:\n\nTarget: {target}\nStack: {tech_stack}\nContext: {context}\n\nProvide: key metrics and SLOs, dashboard layout, alert rules with severity, log aggregation setup, and on-call rotation recommendation.",
            "incident": f"Create an incident response playbook for:\n\nTarget: {target}\nStack: {tech_stack}\nContext: {context}\n\nProvide: detection criteria, severity classification, response steps by role, communication template, and post-mortem process."
        }

        result = await self.call_gemini(system_prompt, prompts.get(task, target), timeout=45)
        return {
            "success": result.get("success", False),
            "task": task,
            "target": target[:200],
            "result": result.get("content", ""),
            "error": result.get("error"),
        }
