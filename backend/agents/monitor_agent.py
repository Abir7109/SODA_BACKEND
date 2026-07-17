import time

from .base_agent import BaseAgent


class MonitorAgent(BaseAgent):
    """Background monitoring agent — watches for changes, checks conditions,
    and reports back. Runs as a fire-and-forget background task.
    """

    def __init__(self):
        super().__init__(
            name="agent_monitor",
            description="Monitor a URL, website, or condition in the background and report changes. Use for recurring checks, price monitoring, availability watching, or periodic status checks. Runs non-blocking — results delivered when available."
        )

    @property
    def tool_definitions(self) -> list:
        return [{
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "target": {
                        "type": "STRING",
                        "description": "What to monitor — URL, keyword, or condition description"
                    },
                    "check_type": {
                        "type": "STRING",
                        "description": "Type of check: 'webpage' (check page content), 'status' (check if site is up), 'change' (check for changes), 'keyword' (search for keyword on page)"
                    },
                    "condition": {
                        "type": "STRING",
                        "description": "Specific condition to check for (e.g. 'price below $50', 'keyword appears', 'status code 200')"
                    }
                },
                "required": ["target"]
            }
        }]

    async def execute(self, target: str = "", check_type: str = "status",
                      condition: str = "", **kwargs) -> dict:
        if not target:
            return {"success": False, "error": "No target specified"}

        if check_type == "status":
            import httpx
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    start = time.time()
                    resp = await client.get(target)
                    elapsed = round(time.time() - start, 2)
                    return {
                        "success": True,
                        "target": target,
                        "status_code": resp.status_code,
                        "response_time_ms": int(elapsed * 1000),
                        "online": resp.status_code < 500,
                        "summary": f"Site responded with {resp.status_code} in {elapsed}s",
                    }
            except Exception as e:
                return {"success": False, "target": target, "error": str(e), "online": False}

        elif check_type in ("webpage", "change", "keyword"):
            from .webpage_agent import WebpageAgent
            wa = WebpageAgent()
            page = await wa.execute(url=target)
            if not page.get("success"):
                return {"success": False, "target": target, "error": page.get("error", "Failed to fetch page")}

            content = page.get("content", "")
            if condition and condition.lower() in content.lower():
                return {
                    "success": True,
                    "target": target,
                    "condition_met": True,
                    "condition": condition,
                    "preview": content[:500],
                }

            if check_type == "keyword" and condition:
                count = content.lower().count(condition.lower())
                return {
                    "success": True,
                    "target": target,
                    "keyword": condition,
                    "occurrences": count,
                    "found": count > 0,
                }

            return {
                "success": True,
                "target": target,
                "content_preview": content[:1000],
                "content_length": len(content),
            }

        return {"success": False, "error": f"Unknown check_type: {check_type}"}
