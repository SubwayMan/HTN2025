import asyncio
import json
import dataclasses
from typing import Optional, List, Tuple
from .fetcher import DataFetcher
from .milestones import generate_milestones
from .processor import MilestoneProcessor

processor = MilestoneProcessor()


def encode_payload(data: dict) -> str:
    return f"data: {json.dumps(data)}"


def decode_payload(data: str) -> dict:
    return json.loads(data[6:])


class Pipeline:
    def __init__(self):
        self.PIPELINES = {}
        self.PIDToRepo = {}

    def add_process(self, pid):
        self.PIPELINES[pid] = asyncio.Queue()

    def get_process(self, pid):
        return self.PIPELINES.get(pid)

    async def run_pipeline(self, pid: str, repo: str):
        p = self.PIPELINES[pid]
        try:
            df = DataFetcher()
            repopath = self.PIDToRepo[pid] = df.fetch_github_repository(
                repo, "./workspace"
            )
            commits = df.get_commit_log(repopath)

            first_commit = df.get_boundary_commit(repopath)
            last_commit = df.get_boundary_commit(repopath, False)
            commits = [first_commit] + commits
            if last_commit.hash != commits[-1].hash:
                commits.append(last_commit)

            async for milestone in generate_milestones(commits):
                await p.put(
                    encode_payload(
                        {
                            "type": "milestone",
                            "payload": {"messages": milestone.messages},
                        }
                    )
                )

            await p.put(encode_payload({"type": "end", "payload": {"status": "done"}}))
        except Exception as e:
            await p.put(encode_payload({"type": "error", "payload": {"msg": str(e)}}))
            await p.put(
                encode_payload(
                    {"type": "end", "payload": {"status": "error", "error": str(e)}}
                )
            )

    async def get_stream(self, pid: str):
        while True:
            event = await self.PIPELINES[pid].get()
            yield event
            if decode_payload(event).get("type") == "end":
                break
