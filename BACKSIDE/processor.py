from ast import arguments
from agents import Agent, function_tool, Runner, RunContextWrapper, ItemHelpers, set_default_openai_key, ModelSettings
from agents.extensions.models.litellm_model import LitellmModel
from datetime import datetime, timedelta
from dotenv import load_dotenv
from json import dumps, loads
import os
from pydantic import BaseModel
from statistics import median
from typing import Iterable, List

load_dotenv()

from .milestones import RawMilestone
from .gitmodels import FileChange


@function_tool
def get_time_stats(wrapper: RunContextWrapper[RawMilestone]):
    """Returns start time, end time, and duration of the milestone in human-readable format."""
    # times are stored as unix timestamps, convert to human readable format
    start_dt = datetime.fromtimestamp(wrapper.context.time_start)
    end_dt = datetime.fromtimestamp(wrapper.context.time_end)
    duration = end_dt - start_dt
    return {
        "time_start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "time_end": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "time_duration": str(duration)
    }

@function_tool
def get_message_stats(wrapper: RunContextWrapper[RawMilestone]):
    """Returns statistics about commit messages including count, total length, and median length."""
    message_lengths = [len(message) for message in wrapper.context.messages]
    total_length = sum(message_lengths) if message_lengths else 0
    median_length = median(message_lengths) if message_lengths else 0
    return {
        "num_messages": len(wrapper.context.messages),
        "total_message_length": total_length,
        "median_message_length": median_length
    }

@function_tool
def get_messages(wrapper: RunContextWrapper[RawMilestone]):
    """Returns a list of all commit messages in the milestone."""
    return wrapper.context.messages

@function_tool
def get_longest_n_messages(wrapper: RunContextWrapper[RawMilestone], n: int):
    """Returns the n longest commit messages sorted by length in descending order."""
    return sorted(wrapper.context.messages, key=len, reverse=True)[:n]

@function_tool
def get_file_change_stats(wrapper: RunContextWrapper[RawMilestone]):
    """Returns comprehensive statistics about file changes including counts by type and median changes."""
    changes = wrapper.context.changes
    modifications = [c for c in changes if c.status == "M"]
    insertions_mod = [c.insertions for c in modifications]
    deletions_mod = [c.deletions for c in modifications]
    return {
        "num_file_changes": len(changes),
        "total_insertions": sum(c.insertions for c in changes) if changes else 0,
        "total_deletions": sum(c.deletions for c in changes) if changes else 0,
        "num_modifications": len(modifications),
        "num_file_renames": sum(1 for c in changes if c.status.startswith("R")),
        "num_file_additions": sum(1 for c in changes if c.status == "A"),
        "num_file_deletions": sum(1 for c in changes if c.status == "D"),
        "median_insertion_per_file": median(insertions_mod) if insertions_mod else 0,
        "median_deletion_per_file": median(deletions_mod) if deletions_mod else 0,
    }

@function_tool
def get_file_changes(wrapper: RunContextWrapper[RawMilestone]):
    """Returns all file changes in the milestone with their status, paths, and line statistics."""
    return wrapper.context.changes

@function_tool
def get_file_changes_by_status(wrapper: RunContextWrapper[RawMilestone], status: str):
    """Returns file changes filtered by status type (A: add, M: modify, D: delete, R: rename)."""
    return [change for change in wrapper.context.changes if change.status.startswith(status)]

@function_tool
def get_top_n_file_changes(wrapper: RunContextWrapper[RawMilestone], n: int):
    """Returns the n top file changes sorted by weighted changes (insertions*2 + deletions) in descending order."""
    return sorted(wrapper.context.changes, key=lambda x: x.insertions*2 + x.deletions, reverse=True)[:n]

@function_tool
def get_file_diff(wrapper: RunContextWrapper[RawMilestone], file_path: str):
    """Returns the detailed line-by-line diff for a specific file (expensive operation)."""
    try:
        return wrapper.context.get_diff_for_file(file_path)
    except Exception as exc:
        return f"ERROR getting diff: {exc}"

class MilestoneSummary(BaseModel):
    title: str
    summary: str
    most_important_changes: List[str]

class MilestoneProcessor():
    def __init__(self):
        # set_default_openai_key(os.environ["OPENAI_API_KEY"])
        # cohere_api_key = os.environ["COHERE_API_KEY"]
        # cerebras_api_key = os.environ["CEREBRAS_API_KEY"]

        self.prev_summary = None
        self.prev_prev_summary = None

        with open(os.path.join(os.path.dirname(__file__), "prompt.txt"), "r") as f:
            prompt = f.read()
        self.overview_agent = Agent[RawMilestone](
            name="Milestone Summary Agent",
            instructions=prompt,
            tools=[
                get_time_stats,
                get_message_stats,
                get_messages,
                get_longest_n_messages,
                get_file_diff,
                get_file_change_stats,
                get_file_changes,
                get_top_n_file_changes,
                get_file_changes_by_status
            ],
            # output_type=MilestoneSummary,
            # model=LitellmModel(model="anthropic/claude-3-7-sonnet-20250219", api_key=os.environ["ANTHROPIC_API_KEY"])
            model=LitellmModel(
                model="cerebras/qwen-3-235b-a22b-instruct-2507",
                api_key=os.environ["CEREBRAS_API_KEY"]
            )
        )

    async def process_milestone(self, milestone: RawMilestone, event_callback=None):
        prompt = "you're hallucinating a tool call.analyze the current milestone"
        if self.prev_summary is not None:
            prompt += f", this is the previous summary: {self.prev_summary}"
        if self.prev_prev_summary is not None:
            prompt += f", this is the previous previous summary: {self.prev_prev_summary}"

        result = Runner.run_streamed(
            self.overview_agent,
            prompt,
            context=milestone,
            max_turns=30
        )

        async for event in result.stream_events():
            self.print_event(event)
            # Pass events to callback if provided
            if event_callback:
                await event_callback(event)

        # print("Here's final result: ", result)

        result_dict = loads(result.final_output)
        if self.prev_summary is not None:
            self.prev_prev_summary = self.prev_summary
        self.prev_summary = result_dict["summary"]

        print(result_dict)
        return result_dict


    def print_event(self, event):
        # Ignore raw responses event
        if event.type == "raw_response_event":
            return
        elif event.type == "agent_updated_stream_event":
            print(f"Agent updated: {event.new_agent.name}")
            return
        elif event.type == "run_item_stream_event":
            if event.item.type == "tool_call_item":
                pass#print("-- Tool was called")
            elif event.item.type == "tool_call_output_item":
                if isinstance(event.item.output, str):
                    pass#print(f"-- Tool output: {event.item.output[:500]}")
                elif isinstance(event.item.output, dict):
                    pass#print(f"-- Tool output: {str(event.item.output)[:500]}")
                elif isinstance(event.item.output, Iterable):
                    # For other iterables like lists, convert to string first
                    pass#print(f"-- Tool output: {str(list(event.item.output)[:10])}")
                else:
                    pass#print(f"-- Tool output: {event.item.output}")
            elif event.item.type == "message_output_item":
                pass#print(f"-- Message output:\n {ItemHelpers.text_message_output(event.item)}")
            else:
                pass

