import asyncio
import time
import uuid
from datetime import datetime
from typing import Optional

# Module-level singleton
_global_orchestrator = None

from agents import (
    BaseAgent,
    WebSearchAgent,
    NewsAgent,
    WikipediaAgent,
    WebpageAgent,
    ResearchAgent,
    CodeAgent,
    DataAgent,
    MonitorAgent,
    SocialAgent,
    TranslateAgent,
    SummarizerAgent,
)


class AgentTask:
    """Represents a background agent task with status tracking."""

    def __init__(self, agent_name: str, task_id: str, params: dict):
        self.agent_name = agent_name
        self.task_id = task_id
        self.params = params
        self.status = "pending"  # pending -> running -> completed/failed
        self.result = None
        self.error = None
        self.created_at = time.time()
        self.completed_at = None

    def mark_running(self):
        self.status = "running"

    def mark_completed(self, result: dict):
        self.status = "completed"
        self.result = result
        self.completed_at = time.time()

    def mark_failed(self, error: str):
        self.status = "failed"
        self.error = error
        self.completed_at = time.time()

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "agent": self.agent_name,
            "status": self.status,
            "params": self.params,
            "result": self.result,
            "error": self.error,
        }


class AgentOrchestrator:
    """Manages registration, dispatch, and lifecycle of all sub-agents.
    
    Agents run as asyncio tasks and return results that are injected
    into the main Gemini conversation via inject_text() on the next turn.
    The orchestrator holds a callback so the AudioLoop can receive results.
    """

    def __init__(self, inject_callback=None):
        self._agents: dict[str, BaseAgent] = {}
        self._tasks: dict[str, AgentTask] = {}
        self._completed_tasks: list[AgentTask] = []
        self._max_completed = 50
        self._inject_callback = inject_callback
        self._register_defaults()

    def set_inject_callback(self, callback):
        self._inject_callback = callback

    def _register_defaults(self):
        """Register all built-in sub-agents."""
        self.register(WebSearchAgent())
        self.register(NewsAgent())
        self.register(WikipediaAgent())
        self.register(WebpageAgent())
        self.register(ResearchAgent())
        self.register(CodeAgent())
        self.register(DataAgent())
        self.register(MonitorAgent())
        self.register(SocialAgent())
        self.register(TranslateAgent())
        self.register(SummarizerAgent())

    def register(self, agent: BaseAgent):
        """Register an agent by name."""
        self._agents[agent.name] = agent
        print(f"[AgentOrchestrator] Registered agent: {agent.name}")

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        return self._agents.get(name)

    def get_all_agents(self) -> dict[str, BaseAgent]:
        return dict(self._agents)

    def get_agent_tools(self) -> list:
        """Return all agent tool definitions for Gemini's tool list."""
        tools = []
        for name, agent in sorted(self._agents.items()):
            td = agent.tool_definitions
            if td:
                tools.extend(td)
        return tools

    def get_task(self, task_id: str) -> Optional[AgentTask]:
        return self._tasks.get(task_id)

    def get_pending_results(self) -> list[dict]:
        """Get completed tasks that haven't been delivered yet."""
        results = []
        for task in self._completed_tasks[:]:
            if task.status == "completed" and task.result:
                results.append(task.to_dict())
                self._completed_tasks.remove(task)
        return results

    async def dispatch(self, agent_name: str, **params) -> dict:
        """Dispatch a task to an agent synchronously (waits for result).
        
        Used for tools that need immediate results (the old blocking pattern).
        For true non-blocking, use dispatch_background().
        """
        agent = self._agents.get(agent_name)
        if not agent:
            return {"success": False, "error": f"Unknown agent: {agent_name}"}
        try:
            result = await agent.execute(**params)
            return result
        except Exception as e:
            return {"success": False, "error": f"Agent {agent_name} crashed: {str(e)}"}

    async def dispatch_background(self, agent_name: str, **params) -> str:
        """Fire-and-forget: dispatch to agent in background task.
        
        Returns task_id immediately. Result is injected via callback
        when the agent completes.
        """
        agent = self._agents.get(agent_name)
        if not agent:
            return None
        task_id = str(uuid.uuid4())[:8]
        task = AgentTask(agent_name, task_id, params)
        self._tasks[task_id] = task
        asyncio.create_task(self._run_agent_task(agent, task))
        return task_id

    async def _run_agent_task(self, agent: BaseAgent, task: AgentTask):
        """Run agent in background and deliver result via callback."""
        task.mark_running()
        try:
            result = await agent.execute(**task.params)
            if result.get("success"):
                task.mark_completed(result)
                summary = self._make_summary(agent.name, result)
                if self._inject_callback and summary:
                    await self._inject_callback(summary)
            else:
                task.mark_failed(result.get("error", "Unknown error"))
                if self._inject_callback:
                    await self._inject_callback(
                        f"[Background agent {agent.name} failed: {result.get('error', 'Unknown error')}]"
                    )
        except Exception as e:
            task.mark_failed(str(e))
            if self._inject_callback:
                await self._inject_callback(
                    f"[Background agent {agent.name} crashed: {str(e)}]"
                )
        self._completed_tasks.append(task)
        if len(self._completed_tasks) > self._max_completed:
            self._completed_tasks = self._completed_tasks[-self._max_completed:]

    def _make_summary(self, agent_name: str, result: dict) -> str:
        """Create a concise text summary of agent results for injection."""
        if agent_name == "agent_search":
            items = result.get("results", [])
            if not items:
                return f"[Search for '{result.get('query', '')}' returned no results.]"
            lines = [f"[Web search results for: {result.get('query', '')}]"]
            for i, r in enumerate(items[:5], 1):
                lines.append(f"  {i}. {r.get('title', '')} — {r.get('snippet', '')[:150]}")
            return "\n".join(lines)

        elif agent_name == "agent_news":
            articles = result.get("articles", [])
            if not articles:
                return f"[No news found for '{result.get('query', '')}'.]"
            lines = [f"[News briefing for: {result.get('query', '')}]"]
            for a in articles[:5]:
                lines.append(f"  • {a.get('title', '')} ({a.get('source', '')})")
            return "\n".join(lines)

        elif agent_name == "agent_wikipedia":
            if result.get("success"):
                return f"[Wikipedia: {result.get('title', '')} — {result.get('description', '')}\n{result.get('extract', '')[:500]}]"
            return f"[Wikipedia lookup failed: {result.get('error', '')}]"

        elif agent_name == "agent_browse":
            if result.get("success"):
                content = result.get("content", "")
                return f"[Webpage content from {result.get('url', '')} ({result.get('content_length', 0)} chars):\n{content[:800]}]"
            return f"[Webpage fetch failed: {result.get('error', '')}]"

        elif agent_name == "agent_research":
            parts = [f"[Research summary for: {result.get('topic', '')}]"]
            sr = result.get("search_results", [])
            if sr:
                parts.append(f"Found {len(sr)} search results.")
            news = result.get("news", [])
            if news:
                parts.append(f"Found {len(news)} news articles.")
            synthesis = result.get("synthesis", "")
            if synthesis:
                parts.append(f"\n{synthesis[:800]}")
            return "\n".join(parts)

        elif agent_name == "agent_code":
            if result.get("success"):
                r = result.get("result", "")
                return f"[Code task '{result.get('task')}' ({result.get('language')}) complete:\n{r[:600]}]"
            return f"[Code task failed: {result.get('error', '')}]"

        elif agent_name == "agent_data":
            if result.get("success"):
                return f"[Data task '{result.get('task')}' complete:\n{result.get('result', '')[:500]}]"
            return f"[Data task failed: {result.get('error', '')}]"

        elif agent_name == "agent_translate":
            if result.get("success"):
                return f"[Translation to {result.get('target_language')}: {result.get('translated_text', '')[:200]}]"
            return f"[Translation failed: {result.get('error', '')}]"

        elif agent_name == "agent_summarize":
            if result.get("success"):
                return f"[Summary ({result.get('style')}): {result.get('summary', '')[:500]}]"
            return f"[Summarization failed: {result.get('error', '')}]"

        elif agent_name == "agent_social":
            if result.get("success"):
                return f"[Social media analysis ({result.get('platform')}):\n{result.get('result', '')[:500]}]"
            return f"[Social analysis failed: {result.get('error', '')}]"

        elif agent_name == "agent_monitor":
            if result.get("success"):
                return f"[Monitor check: {result.get('target', '')} — {result.get('summary', result.get('status_code', 'OK'))}]"
            return f"[Monitor check failed: {result.get('target', '')} — {result.get('error', '')}]"

        return f"[Agent {agent_name} completed.]"

    def get_agent_summary(self) -> list[dict]:
        """Get status of all agents for display."""
        return [
            {
                "name": name,
                "description": agent.description,
                "stats": agent.get_stats(),
            }
            for name, agent in sorted(self._agents.items())
        ]

    def get_task_summary(self) -> list[dict]:
        """Get status of recent tasks."""
        active = [t.to_dict() for t in self._tasks.values() if t.status in ("pending", "running")]
        recent = [t.to_dict() for t in self._completed_tasks[-10:]]
        return {"active": active, "recent": recent}


# ── Module-level helpers for tools.py import ──

def get_global_orchestrator():
    global _global_orchestrator
    if _global_orchestrator is None:
        _global_orchestrator = AgentOrchestrator()
    return _global_orchestrator


def get_agent_tool_defs():
    """Return all agent tool definitions for inclusion in Gemini's tool list."""
    return get_global_orchestrator().get_agent_tools()
