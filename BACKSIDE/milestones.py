from dataclasses import dataclass
import subprocess as sp
import re
from typing import Generator, List, Optional
from gitmodels import Commit, FileChange


shortened_rename_regex = re.compile(r"\{.+\s=>\s(.+)\}(.*)$")


@dataclass
class RawMilestone:
    """
    Class to represent a raw, unprocessed milestone.
    Fields:
    - Squashed commit messages (string)
    - Files changed & amount of insertions/deletions (list of FileDiff)
    """

    start_commit_hash: str
    end_commit_hash: str
    messages: List[str]
    changes: List[FileChange]
    _repo_path: str  # Store repo path for internal use

    def get_diff_for_file(self, file_path: str) -> Optional[str]:
        """Fetches the detailed, line-by-line diff for a specific file."""
        # Ensure the requested file is part of this milestone's changes
        if not any(fc.path == file_path for fc in self.changes):
            return None

        command = [
            "git",
            "diff",
            self.start_commit_hash,
            self.end_commit_hash,
            "--",
            file_path,  # '--' disambiguates path from branch names
        ]
        try:
            result = sp.run(
                command, cwd=self._repo_path, capture_output=True, text=True, check=True
            )
            return result.stdout
        except sp.CalledProcessError as e:
            print(f"Error getting diff for {file_path}: {e.stderr}")
            return None


def generate_milestones(commits: List[Commit]) -> Generator[RawMilestone]:
    n = len(commits)
    for i in range(1, n):
        yield get_milestone_data(commits[i - 1], commits[i])


def get_milestone_data(c1: Commit, c2: Commit) -> RawMilestone:
    """Runs git diff and parses the output to create a Milestone object."""
    start_hash = c1.hash
    end_hash = c2.hash
    repo_path = c1.repository

    numstat_command = [
        "git",
        "--no-pager",
        "diff",
        "--numstat",
        f"{start_hash}..{end_hash}",
    ]
    print(" ".join(numstat_command))

    result = sp.run(
        numstat_command, cwd=repo_path, capture_output=True, text=True, check=True
    )
    file_to_stats = {}  # dict to tuple of (insertions, deletions)

    for line in result.stdout.strip().split("\n"):
        if re.search(shortened_rename_regex, line):
            line = shortened_rename_regex.sub(r"\1\2", line)
        insertions, deletions, *extras = line.split()
        filename = extras[-1]
        file_to_stats[filename] = (int(insertions), int(deletions))

    command = [
        "git",
        "--no-pager",
        "diff",
        "--name-status",
        f"{start_hash}..{end_hash}",
    ]
    print(" ".join(command))
    # TODO: handle failure
    result = sp.run(command, cwd=repo_path, capture_output=True, text=True, check=True)

    lines = result.stdout.strip().split("\n")
    # TODO: handle empty diffs
    # if not lines or len(lines) < 2:
    # return None
    changes = []

    for line in lines:
        status, *files = line.split()
        filename = files[-1]
        changes.append(
            FileChange(
                status=status,
                path=filename,
                old_path=None,
                insertions=-1,
                deletions=-1,
            )
        )
        if status.startswith("R"):
            changes[-1].old_path = files[0]
        if file_to_stats.get(filename) is not None:
            ins, dels = file_to_stats.get(filename)
            changes[-1].insertions = ins
            changes[-1].deletions = dels

    # get commit messages
    commit_message_command = [
        "git",
        "--no-pager",
        "log",
        '--pretty=format:"%s"',
        f"{start_hash}..{end_hash}",
    ]

    result = sp.run(
        commit_message_command,
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )

    return RawMilestone(
        start_commit_hash=start_hash,
        end_commit_hash=end_hash,
        messages=result.stdout.split("\n")[::-1],
        changes=changes,
        _repo_path=repo_path,
    )
