# app.py
import asyncio
import json
import uuid
from typing import Dict, List, Optional, Tuple
from fastapi import FastAPI, Form, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from BACKSIDE.integration import Pipeline

app = FastAPI()

pipeline = Pipeline()


def sse_frame(data: dict, event_id: Optional[str] = None) -> bytes:
    payload = json.dumps(data, separators=(",", ":"))
    parts = []
    if event_id:
        parts.append(f"id: {event_id}\n")
    parts.append(f"data: {payload}\n\n")
    return "".join(parts).encode("utf-8")


@app.post("/begin-analysis")
async def begin_analysis(background: BackgroundTasks, repo: str = Form(...)):
    pid = str(uuid.uuid4())
    pid = "bongnog"
    pipeline.add_process(pid)
    # fire-and-forget
    background.add_task(pipeline.run_pipeline, pid, repo)
    return {"id": pid}


@app.get("/analysis/{pid}")
async def analysis_sse(pid: str, request: Request):
    p = pipeline.get_process(pid)
    if not p:
        raise HTTPException(404, "Unknown analysis id")

    # Support replay and resume:
    #  - If client sends Last-Event-ID header, start *after* that id.
    #  - Otherwise, start from the beginning.
    last_event_id = request.headers.get("last-event-id")

    async def gen():
        # 1) Replay buffered events
        idx = p.index_from_last_event_id(last_event_id)
        while idx < len(p.events):
            if await request.is_disconnected():
                return
            eid, evt = p.events[idx]
            yield sse_frame(evt, eid)
            idx += 1

        # 2) Tail new events until done and buffer is drained
        while True:
            if await request.is_disconnected():
                return

            # If there are new buffered events, flush them without waiting
            while idx < len(p.events):
                eid, evt = p.events[idx]
                yield sse_frame(evt, eid)
                idx += 1

            # If pipeline is done and all buffered events are sent, exit
            if p.done and idx >= len(p.events):
                return

            # Otherwise wait for more events or completion
            async with p._cond:
                try:
                    await asyncio.wait_for(p._cond.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    # loop back to check done/disconnect/new events
                    pass

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
