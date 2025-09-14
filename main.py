# app.py
import asyncio
import json
import uuid
from typing import Dict, List, Optional, Tuple
from fastapi import FastAPI, Form, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from BACKSIDE.integration import Pipeline
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    # pid = "bongnog"  # Commented out for unique IDs
    pipeline.add_process(pid)
    # fire-and-forget
    background.add_task(pipeline.run_pipeline, pid, repo)
    return {"id": pid}


@app.get("/analysis/{pid}")
async def analysis_sse(pid: str, request: Request):
    p = pipeline.get_process(pid)
    if not p:
        raise HTTPException(404, "Unknown analysis id")

    return StreamingResponse(
        pipeline.get_stream(pid),
        media_type="text/event-stream",
    )
