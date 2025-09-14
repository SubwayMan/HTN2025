import asyncio
import json
import dataclasses
import re
from typing import Optional, List, Tuple
from .fetcher import DataFetcher
from .milestones import generate_milestones, generate_milestones_with_heuristic
from .processor import MilestoneProcessor


def encode_payload(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def decode_payload(data: str) -> dict:
    # Strip "data: " prefix and any trailing newlines
    json_str = data.replace("data: ", "").strip()
    return json.loads(json_str)


class Pipeline:
    def __init__(self):
        self.PIPELINES = {}
        self.PIDToRepo = {}
        self.processors = {}  # Store processor instances per pipeline ID

    def add_process(self, pid):
        self.PIPELINES[pid] = asyncio.Queue()
        self.processors[pid] = (
            MilestoneProcessor()
        )  # Create new processor for each analysis

    def get_process(self, pid):
        return self.PIPELINES.get(pid)

    async def run_pipeline(self, pid: str, repo: str):
        p = self.PIPELINES[pid]
        processor = self.processors[pid]  # Get the processor for this pipeline
        try:
            df = DataFetcher()
            # Extract username/repo from URL using regex
            match = re.match(
                r"(?:https?://)?(?:www\.)?github\.com/([^/]+/[^/]+?)(?:\.git)?/?$", repo
            )
            if match:
                repo = match.group(1)

            repopath = self.PIDToRepo[pid] = df.fetch_github_repository(
                repo, "./workspace", use_https=True
            )
            # needed for merge picker strategy
            # commits = df.get_merge_commit_log(repopath)

            # first_commit = df.get_boundary_commit(repopath)
            # last_commit = df.get_boundary_commit(repopath, False)
            # commits = [first_commit] + commits
            # if last_commit.hash != commits[-1].hash:
            # commits.append(last_commit)

            async for milestone in generate_milestones_with_heuristic(45, df, repopath):
                # Send milestone info
                await p.put(
                    encode_payload(
                        {
                            "type": "milestone_start",
                            "payload": {"messages": milestone.messages},
                        }
                    )
                )

                # Process the milestone with AI
                try:
                    # Define callback to stream processing events
                    async def stream_event(event):
                        # Stream select processing events to frontend
                        if event.type == "run_item_stream_event":
                            if event.item.type == "message_output_item":
                                # Stream partial agent outputs
                                await p.put(
                                    encode_payload(
                                        {
                                            "type": "processing_update",
                                            "payload": {
                                                "message": "AI analyzing milestone..."
                                            },
                                        }
                                    )
                                )

                    result = await processor.process_milestone(milestone, stream_event)
                    await p.put(
                        encode_payload(
                            {"type": "milestone_analysis", "payload": result}
                        )
                    )
                except Exception as e:
                    await p.put(
                        encode_payload(
                            {"type": "milestone_error", "payload": {"error": str(e)}}
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
        finally:
            # Clean up processor after pipeline completes
            if pid in self.processors:
                del self.processors[pid]

    async def get_stream(self, pid: str):
        while True:
            event = await self.PIPELINES[pid].get()
            # Ensure the event is properly encoded as bytes for SSE
            if isinstance(event, str):
                yield event.encode('utf-8')
            else:
                yield event
            if decode_payload(event).get("type") == "end":
                break
