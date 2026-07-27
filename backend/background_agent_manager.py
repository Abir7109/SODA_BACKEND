import asyncio
import logging
import os
import time
import uuid
from typing import Optional

logger = logging.getLogger("soda.bg_agent_manager")

MAX_OUTPUT_LINES = 500


class BackgroundTask:
    def __init__(self, task_id: str, prompt: str, workdir: str = ""):
        self.task_id = task_id
        self.prompt = prompt
        self.workdir = workdir or os.getcwd()
        self._process: Optional[asyncio.subprocess.Process] = None
        self._output: list[str] = []
        self._started_at: Optional[float] = None
        self._finished_at: Optional[float] = None
        self._exit_code: Optional[int] = None
        self._phase = "pending"

    @property
    def status(self) -> dict:
        return {
            "task_id": self.task_id,
            "phase": self._phase,
            "prompt": self.prompt[:200],
            "output": "\n".join(self._output[-50:]),
            "output_lines": len(self._output),
            "elapsed": round(time.time() - self._started_at, 1) if self._started_at else 0,
            "exit_code": self._exit_code,
            "finished": self._finished_at is not None,
        }

    async def start(self):
        self._started_at = time.time()
        self._phase = "running"
        # ponytail: uses npx opencode --prompt; add --model flag if specific model needed
        cmd = ["npx", "opencode", "--prompt", self.prompt]
        logger.info(f"[bg:{self.task_id}] Starting: {' '.join(cmd)}")
        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=self.workdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        asyncio.create_task(self._read_output())
        asyncio.create_task(self._wait_exit())

    async def _read_output(self):
        while True:
            line = await self._process.stdout.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            self._output.append(text)
            if len(self._output) > MAX_OUTPUT_LINES:
                self._output = self._output[-MAX_OUTPUT_LINES:]

    async def _wait_exit(self):
        self._exit_code = await self._process.wait()
        self._finished_at = time.time()
        self._phase = "completed" if self._exit_code == 0 else "failed"
        logger.info(f"[bg:{self.task_id}] Done (exit={self._exit_code}, {self.status['elapsed']}s)")
        cb = BackgroundAgentManager._on_complete.pop(self.task_id, None)
        if cb:
            cb(self.status)

    async def kill(self):
        if self._process and self._process.returncode is None:
            self._process.kill()
            self._phase = "killed"
            self._finished_at = time.time()


class BackgroundAgentManager:
    _tasks: dict[str, BackgroundTask] = {}
    _on_complete: dict[str, callable] = {}

    @classmethod
    async def spawn(cls, prompt: str, workdir: str = "", on_complete: callable = None) -> dict:
        task_id = f"bg-{uuid.uuid4().hex[:12]}"
        task = BackgroundTask(task_id, prompt, workdir)
        cls._tasks[task_id] = task
        if on_complete:
            cls._on_complete[task_id] = on_complete
        await task.start()
        return task.status

    @classmethod
    def get_status(cls, task_id: str) -> Optional[dict]:
        task = cls._tasks.get(task_id)
        if not task:
            return None
        return task.status

    @classmethod
    async def kill(cls, task_id: str) -> Optional[dict]:
        task = cls._tasks.get(task_id)
        if not task:
            return None
        await task.kill()
        return task.status

    @classmethod
    def list_tasks(cls) -> list[dict]:
        return [t.status for t in cls._tasks.values()]

    @classmethod
    def cleanup_old(cls, max_age: float = 3600):
        now = time.time()
        to_del = []
        for tid, task in cls._tasks.items():
            if task._finished_at and (now - task._finished_at) > max_age:
                to_del.append(tid)
        for tid in to_del:
            del cls._tasks[tid]
