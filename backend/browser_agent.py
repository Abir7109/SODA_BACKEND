"""
browser-use integration for SODA.

Wraps the browser-use library (https://github.com/browser-use/browser-use)
to give SODA clean, precise browser control via an AI agent that can
navigate, click, type, and extract data from real web pages.

Uses Gemini as the LLM backbone (free tier via GOOGLE_API_KEY).
"""

import asyncio
import os
import sys
import logging
import time
from typing import Optional

logger = logging.getLogger("soda.browser_agent")

# Lazy imports — only loaded when first task runs
_Agent = None
_Browser = None
_BrowserConfig = None
_ChatGoogle = None


def _ensure_deps():
    """Lazily import browser-use and langchain dependencies."""
    global _Agent, _Browser, _BrowserConfig, _ChatGoogle
    if _Agent is not None:
        return True
    try:
        from browser_use import Agent, Browser, BrowserConfig
        from langchain_google_genai import ChatGoogleGenerativeAI
        _Agent = Agent
        _Browser = Browser
        _BrowserConfig = BrowserConfig
        _ChatGoogle = ChatGoogleGenerativeAI
        return True
    except ImportError as e:
        logger.error(
            f"browser-use not installed. Run: pip install browser-use langchain-google-genai\n"
            f"Import error: {e}"
        )
        return False


def _build_llm():
    """Build the Gemini LLM for browser-use."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No GOOGLE_API_KEY or GEMINI_API_KEY found. "
            "Set one in your .env for browser-use to work."
        )
    # Ensure langchain sees the key
    os.environ["GOOGLE_API_KEY"] = api_key
    return _ChatGoogle(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.0,
    )


class BrowserAgent:
    """
    Singleton browser-use agent for SODA.

    Usage:
        agent = BrowserAgent.get_instance()
        result = await agent.run_task("Go to github.com and find the trending repos")
    """

    _instance: Optional["BrowserAgent"] = None

    def __init__(self):
        self._browser: Optional[object] = None
        self._last_task_time: float = 0.0
        self._task_count: int = 0

    @classmethod
    def get_instance(cls) -> "BrowserAgent":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def run_task(
        self,
        task: str,
        max_steps: int = 15,
        timeout_seconds: int = 120,
    ) -> dict:
        """
        Execute a browser task using browser-use.

        Args:
            task: Natural language description of what to do in the browser.
            max_steps: Maximum agent steps (clicks, navigations, etc).
            timeout_seconds: Hard timeout for the entire task.

        Returns:
            {
                "success": bool,
                "result": str,        # Final agent response
                "steps_taken": int,
                "duration_seconds": float,
                "error": str | None,
            }
        """
        if not _ensure_deps():
            return {
                "success": False,
                "result": "",
                "steps_taken": 0,
                "duration_seconds": 0,
                "error": "browser-use not installed. Run: pip install browser-use langchain-google-genai",
            }

        start_time = time.time()
        self._task_count += 1

        try:
            llm = _build_llm()

            # Configure browser: connect to existing Chrome via CDP if available,
            # otherwise launch a new headless instance.
            cdp_url = os.getenv("BROWSER_CDP_URL", "")
            if cdp_url:
                browser_config = _BrowserConfig(
                    cdp_url=cdp_url,
                    disable_security=True,
                )
                logger.info(f"[browser-use] Connecting to existing Chrome at {cdp_url}")
            else:
                browser_config = _BrowserConfig(
                    headless=True,
                    disable_security=True,
                    extra_chromium_args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
                logger.info("[browser-use] Launching new headless Chrome instance")

            self._browser = _Browser(config=browser_config)

            agent = _Agent(
                task=task,
                llm=llm,
                browser=self._browser,
                max_actions_per_step=3,
            )

            # Run with timeout
            final_result = await asyncio.wait_for(
                agent.run(max_steps=max_steps),
                timeout=timeout_seconds,
            )

            duration = time.time() - start_time
            self._last_task_time = time.time()

            # Extract the final answer from the agent result
            result_text = ""
            steps_taken = 0
            if final_result:
                if hasattr(final_result, "final_result"):
                    result_text = final_result.final_result() or ""
                elif hasattr(final_result, "result"):
                    result_text = str(final_result.result)
                else:
                    result_text = str(final_result)

                if hasattr(final_result, "steps"):
                    steps_taken = len(final_result.steps)

            logger.info(
                f"[browser-use] Task completed in {duration:.1f}s, "
                f"{steps_taken} steps, result length={len(result_text)}"
            )

            return {
                "success": True,
                "result": result_text,
                "steps_taken": steps_taken,
                "duration_seconds": round(duration, 2),
                "error": None,
            }

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.warning(f"[browser-use] Task timed out after {duration:.1f}s")
            return {
                "success": False,
                "result": "",
                "steps_taken": 0,
                "duration_seconds": round(duration, 2),
                "error": f"Browser task timed out after {timeout_seconds}s. The task may be too complex — try breaking it into smaller steps.",
            }

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[browser-use] Task failed: {e}", exc_info=True)
            return {
                "success": False,
                "result": "",
                "steps_taken": 0,
                "duration_seconds": round(duration, 2),
                "error": f"Browser task failed: {str(e)}",
            }

        finally:
            # Clean up browser
            try:
                if self._browser:
                    await self._browser.close()
                    self._browser = None
            except Exception:
                self._browser = None

    async def close(self):
        """Clean up the browser instance."""
        try:
            if self._browser:
                await self._browser.close()
                self._browser = None
        except Exception:
            self._browser = None

    def get_status(self) -> dict:
        """Get current agent status."""
        return {
            "active": self._browser is not None,
            "total_tasks": self._task_count,
            "last_task_time": self._last_task_time,
        }


# Module-level convenience
async def run_browser_task(task: str, max_steps: int = 15, timeout_seconds: int = 120) -> dict:
    """Run a browser task via the singleton BrowserAgent."""
    agent = BrowserAgent.get_instance()
    return await agent.run_task(task, max_steps=max_steps, timeout_seconds=timeout_seconds)
