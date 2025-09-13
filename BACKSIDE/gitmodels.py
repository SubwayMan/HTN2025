from dataclasses import dataclass
from typing import List


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


@dataclass
class FileRename:
    """
    class to represent the action of renaming a file in git.
    """


@dataclass
class FileDiff:
    """
    Class that contains top-level file diff info and can be used to fetch more information.
    """

    filename: str
    insertions: int
    deletions: int
    renames: List[FileRename]
