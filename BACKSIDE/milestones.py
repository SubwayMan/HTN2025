import subprocess as sp
from typing import Generator, List, Optional
from gitmodels import Commit, FileChange


class RawMilestone:
    """
    Class to represent a raw, unprocessed milestone.
    Fields:
    - Squashed commit messages (string)
    - Files changed & amount of insertions/deletions (list of FileDiff)
    """

    start_commit_hash: str
    end_commit_hash: str
    summary: str
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

    def __init__(self) -> None:
        pass


def generate_milestones(commits: List[Commit]) -> Generator[RawMilestone]:
    milestones = []


def get_milestone_data(c1: Commit, c2: Commit) -> RawMilestone:
    """Runs git diff and parses the output to create a Milestone object."""
    # Use --numstat AND --name-status. Git prints numstat block first, then name-status.
    start_hash = c1.hash
    end_hash = c2.hash
    command = [
        "git",
        "diff",
        "--numstat",
        "--name-status",
        "-M",
        "--shortstat",
        start_hash,
        end_hash,
    ]

    repo_path = c1.repository
    # TODO: handle failure
    result = sp.run(command, cwd=repo_path, capture_output=True, text=True, check=True)

    lines = result.stdout.strip().split("\n")
    # TODO: handle empty diffs
    # if not lines or len(lines) < 2:
    # return None
    breakpoint()

    # --- PARSING LOGIC ---
    summary = lines[-1]

    # Separate the numstat lines from the name-status lines
    # There will be a blank line separating the blocks
    blank_line_index = lines.index("")
    numstat_lines = lines[:blank_line_index]
    name_status_lines = lines[blank_line_index + 1 : -1]

    # 1. Parse numstat to get insertions/deletions for each path
    stats_by_path = {}
    for line in numstat_lines:
        parts = line.split("\t")
        # Handle binary files which have '-' for insertions/deletions
        insertions = 0 if parts[0] == "-" else int(parts[0])
        deletions = 0 if parts[1] == "-" else int(parts[1])
        path = parts[2]
        stats_by_path[path] = {"insertions": insertions, "deletions": deletions}

    # 2. Parse name-status to get status and handle renames
    file_changes = []
    for line in name_status_lines:
        parts = line.split("\t")
        status_code = parts[0]

        insertions, deletions = 0, 0

        if status_code.startswith("R"):  # Handle renames
            status = "R"
            old_path = parts[1]
            path = parts[2]
            # For renames, the numstat path is the *new* path
            if path in stats_by_path:
                insertions = stats_by_path[path]["insertions"]
                deletions = stats_by_path[path]["deletions"]

            file_changes.append(
                FileChange(
                    status=status,
                    path=path,
                    old_path=old_path,
                    insertions=insertions,
                    deletions=deletions,
                )
            )
        else:  # Handle A, M, D
            status = status_code
            path = parts[1]
            if path in stats_by_path:
                insertions = stats_by_path[path]["insertions"]
                deletions = stats_by_path[path]["deletions"]

            file_changes.append(
                FileChange(
                    status=status, path=path, insertions=insertions, deletions=deletions
                )
            )
