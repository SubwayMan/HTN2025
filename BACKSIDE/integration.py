import asyncio
import json
import dataclasses
from typing import Optional, List, Tuple


class PipelineState:
    """
    Per-pipeline append-only log with async notification.
    - events: list of (id_str, jsonable_dict)
    - cond: notifies waiters when a new event arrives or pipeline ends
    """

    def __init__(self):
        self.events: List[Tuple[str, dict]] = []
        self.done: bool = False
        self.error: Optional[str] = None
        self._next_seq: int = 1
        self._lock = asyncio.Lock()
        self._cond = asyncio.Condition()

    async def append(self, event: dict) -> str:
        async with self._lock:
            eid = str(self._next_seq)
            self._next_seq += 1
            self.events.append((eid, event))
        # notify outside the lock
        async with self._cond:
            self._cond.notify_all()
        return eid

    async def set_done(self):
        self.done = True
        async with self._cond:
            self._cond.notify_all()

    async def set_error(self, msg: str):
        self.error = msg
        self.done = True
        async with self._cond:
            self._cond.notify_all()

    def index_from_last_event_id(self, last_id: Optional[str]) -> int:
        """Map Last-Event-ID (string seq) to start index in events."""
        if not last_id:
            return 0
        try:
            seq = int(last_id)
        except ValueError:
            return 0
        # events are 1-based ids; list is 0-based
        # next unread index is seq (since last delivered was seq)
        return max(0, min(len(self.events), seq))


class Pipeline:
    def __init__(self):
        self.PIPELINES = {}

    def add_process(self, pid):
        self.PIPELINES[pid] = PipelineState()

    def get_process(self, pid):
        return self.PIPELINES.get(pid)

    async def run_pipeline(self, pid: str, repo: str):
        p = self.PIPELINES[pid]
        try:
            await p.append(
                {"type": "log", "payload": {"msg": "starting", "repo": repo}}
            )

            await p.append(
                {"type": "progress", "payload": {"stage": "scan", "percent": 10}}
            )
            await asyncio.sleep(0.3)

            # ... do real work here (clone, analyze, etc.) ...
            await p.append(
                {"type": "result", "payload": {"kind": "file_count", "value": 123}}
            )
            await asyncio.sleep(3)

            await p.append(
                {"type": "progress", "payload": {"stage": "done", "percent": 100}}
            )
            await asyncio.sleep(2)
            await p.set_done()
            await p.append({"type": "end", "payload": {"status": "done"}})
        except Exception as e:
            await p.append({"type": "error", "payload": {"msg": str(e)}})
            await p.set_error(str(e))
            await p.append(
                {"type": "end", "payload": {"status": "error", "error": str(e)}}
            )
