from dataclasses import dataclass
import subprocess as sp
from typing import Generator, List, Optional
from gitmodels import Commit, FileChange


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
    milestones = []


def get_milestone_data(c1: Commit, c2: Commit) -> RawMilestone:
    """Runs git diff and parses the output to create a Milestone object."""
    start_hash = c1.hash
    end_hash = c2.hash
    command = [
        "git",
        "--no-pager",
        "diff",
        "--name-status",
        f"{start_hash}..{end_hash}",
    ]
    print(" ".join(command))
    repo_path = c1.repository
    # TODO: handle failure
    result = sp.run(command, cwd=repo_path, capture_output=True, text=True, check=True)

    lines = result.stdout.strip().split("\n")
    # TODO: handle empty diffs
    # if not lines or len(lines) < 2:
    # return None
    changes = []

    for line in lines:
        status, *files = line.split()
        changes.append(
            FileChange(
                status=status,
                path=files[-1],
                old_path=None,
                insertions=-1,
                deletions=-1,
            )
        )
        if status.startswith("R"):
            changes[-1].old_path = files[0]

    return RawMilestone(
        start_commit_hash=start_hash,
        end_commit_hash=end_hash,
        messages=[],
        changes=changes,
        _repo_path=repo_path,
    )
