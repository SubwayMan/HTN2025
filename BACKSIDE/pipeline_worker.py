import os
import json
import time
import tempfile
import subprocess
from redis import Redis  # sync client for simplicity

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = Redis.from_url(REDIS_URL, decode_responses=True)

JOB_QUEUE = "jobs:analysis"
STREAM_KEY = lambda pid: f"pipeline:{pid}:events"
STATUS_KEY = lambda pid: f"pipeline:{pid}:status"
ERR_KEY = lambda pid: f"pipeline:{pid}:error"


def emit(pid: str, event_type: str, payload: dict):
    ev = {"type": event_type, "payload": payload}
    r.xadd(STREAM_KEY(pid), {"json": json.dumps(ev)}, maxlen=10_000)


def run_pipeline(pipeline_id: str, repo: str):
    r.set(STATUS_KEY(pipeline_id), "running")
    try:
        emit(pipeline_id, "log", {"msg": "Cloning", "repo": repo})
        with tempfile.TemporaryDirectory() as tmp:
            # In your real pipeline you may do a shallow clone or use GitHub API
            subprocess.check_call(["git", "clone", "--depth", "1", repo, tmp])

            emit(pipeline_id, "progress", {"stage": "scan", "percent": 10})
            time.sleep(0.2)

            # Fake analysis steps for now
            emit(pipeline_id, "result", {"kind": "file_count", "value": 123})
            emit(pipeline_id, "progress", {"stage": "lint", "percent": 50})
            time.sleep(0.2)

            emit(
                pipeline_id,
                "result",
                {"kind": "lint_summary", "errors": 3, "warnings": 12},
            )
            emit(pipeline_id, "progress", {"stage": "done", "percent": 100})

        r.set(STATUS_KEY(pipeline_id), "done")
    except subprocess.CalledProcessError as e:
        r.set(STATUS_KEY(pipeline_id), "error")
        r.set(ERR_KEY(pipeline_id), f"clone failed: {e}")
        emit(pipeline_id, "error", {"msg": "clone failed", "detail": str(e)})
    except Exception as e:
        r.set(STATUS_KEY(pipeline_id), "error")
        r.set(ERR_KEY(pipeline_id), str(e))
        emit(pipeline_id, "error", {"msg": "unexpected", "detail": str(e)})


def main():
    print("Worker started. Waiting for jobs...")
    while True:
        # BRPOP blocks until a job arrives. Pair with RPUSH on the producer side.
        _, raw = r.brpop(JOB_QUEUE, timeout=0)
        job = json.loads(raw)
        pid = job["pipeline_id"]
        repo = job["repo"]
        run_pipeline(pid, repo)


if __name__ == "__main__":
    main()
