from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Commit:
    """
    class to encode a singular git commit.
    properties:
    - hash
    - date/time of creation
    - message
    """

    hash: str
    parent_hashes: List[str]
    author_name: str
    author_date_unix: int
    committer_date_unix: int
    subject: str
    repository: str


@dataclass
class FileChange:
    """Represents a single file change within a milestone."""

    status: str
    path: str
    old_path: Optional[str] = None
    insertions: int = 0
    deletions: int = 0
