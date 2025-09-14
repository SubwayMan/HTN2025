import asyncio
from agents import ItemHelpers
import json
import dataclasses
import re
from typing import Optional, List, Tuple
from .fetcher import DataFetcher
from .milestones import generate_milestones, generate_milestones_with_heuristic
from .processor import MilestoneProcessor
import os
import cohere


def encode_payload(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def decode_payload(data: str) -> dict:
    # Strip "data: " prefix and any trailing newlines
    json_str = data.replace("data: ", "").strip()
    return json.loads(json_str)


def get_tool_call_message(item) -> str:
    tool_name = item.raw_item.name

    tool_messages = {
        "get_time_stats": "Getting timeline information...",
        "get_message_stats": "Analyzing commit message statistics...",
        "get_messages": "Retrieving commit messages...",
        "get_longest_n_messages": "Finding longest commit messages...",
        "get_file_change_stats": "Calculating file change statistics...",
        "get_file_changes": "Analyzing file changes...",
        "get_file_changes_by_status": "Filtering file changes by type...",
        "get_top_n_file_changes": "Finding most significant file changes...",
        "get_file_diff": "Examining detailed file differences..."
    }

    return tool_messages.get(tool_name, f"Processing {tool_name}...")

class Pipeline:
    def __init__(self):
        self.PIPELINES = {}
        self.PIDToRepo = {}
        self.processors = {}  # Store processor instances per pipeline ID
        self.all_summaries = {}  # Store all summaries by pipeline ID

    def add_process(self, pid):
        self.PIPELINES[pid] = asyncio.Queue()
        self.processors[pid] = (
            MilestoneProcessor()
        )  # Create new processor for each analysis
        self.all_summaries[pid] = []  # Initialize summary list for this pipeline

    def get_process(self, pid):
        return self.PIPELINES.get(pid)

    def get_all_summaries(self, pid):
        """Get all summaries for a specific pipeline ID"""
        return self.all_summaries.get(pid, [])

    async def process_summaries_with_service(self, pid, service_func):
        """Process all summaries for a pipeline with a service function and return result"""
        summaries = self.get_all_summaries(pid)
        if not summaries:
            return None

        # Call the service function with all summaries
        try:
            result = await service_func(summaries)
            return result
        except Exception as e:
            print(f"Error processing summaries with service: {e}")
            return None

    async def cohere_summary_service(self, summaries):
        """Example service function - replace with your actual service integration"""
        co = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))

        response = co.chat(
            messages=[
                {
                    "role": "system",
                    "content": "You are given a list of summaries, each summary is for a section of a github project. Your job is to look across all these summaries and give a one-paragraph overview of the project. Touch upon purpose, technologies, type of project (long, hackathon, enterprise/personal) etc."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "HERE ARE THE SUMMARIES: " + "\n\n".join(str(s) for s in summaries)
                        }
                    ]
                }
            ],
            temperature=0.3,
            model="command-a-03-2025",
        )

        return response

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

            limit = 3
            a = 0

            async for milestone in generate_milestones_with_heuristic(
                4000.0, df, repopath
            ):
                a += 1
                if a >= limit:
                    break
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
                                                "message": ItemHelpers.text_message_output(event.item)
                                            },
                                        }
                                    )
                                )
                            
                            if event.item.type == "tool_call_item":
                                await p.put(
                                    encode_payload(
                                        {
                                            "type": "processing_update",
                                            "payload": {
                                                "message": get_tool_call_message(event.item)
                                            },
                                        }
                                    )
                                )

                    result = await processor.process_milestone(milestone, stream_event)

                    # Save summary to centralized list
                    self.all_summaries[pid].append(result)

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
                print("Processed milestone")
            print("Finished processing milestones")
            print(f"Total summaries collected: {len(self.all_summaries.get(pid, []))}")

            # Process all summaries with service after all milestones are complete
            try:
                final_result = await self.process_summaries_with_service(
                    pid, self.cohere_summary_service
                )
                if final_result:
                    # Extract text from Cohere response
                    summary_text = final_result.message.content[0].text
                    print(f"Generated final summary: {summary_text[:100]}...")
                    await p.put(
                        encode_payload(
                            {"type": "final_summary", "payload": {"text": summary_text}}
                        )
                    )
                else:
                    print("No final result from Cohere service")
            except Exception as e:
                await p.put(
                    encode_payload(
                        {"type": "service_error", "payload": {"error": str(e)}}
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
            # Clean up processor and summaries after pipeline completes
            if pid in self.processors:
                del self.processors[pid]
            if pid in self.all_summaries:
                del self.all_summaries[pid]

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
