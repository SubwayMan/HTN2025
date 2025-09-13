import subprocess as sp
import string
import random
import os
from gitmodels import Commit

default_cloning_depth = 300


def generate_slug(length=12):
    """Generate a random alphanumeric slug of specified length."""
    characters = string.ascii_letters + string.digits  # a-z, A-Z, 0-9
    return "".join(random.choice(characters) for _ in range(length))


class RepoNotFoundException(Exception):
    pass


class DataFetcher:
    """
    Class for obtaining data from Github.
    Return
    """

    def fetch_github_repository(
        self, repo: str, workspace_path: str, depth: int = default_cloning_depth
    ):
        slug = generate_slug()
        path = os.path.join(workspace_path, slug)
        url = f"git@github.com:{repo}.git"
        command = [
            "git",
            "clone",
            "--filter=blob:none",
            f"--depth={depth}",
            "--no-checkout",
            url,
            path,
        ]
        try:
            result = sp.run(command, capture_output=True, text=True, check=True)
            if not os.path.exists(path):
                print("Failed to execute command. Stdout:")
                print(result.stdout)
                print("Stderr:")
                print(result.stderr)
                raise RepoNotFoundException
            return path
        except sp.CalledProcessError:
            raise RepoNotFoundException(f"Failed to find repository {repo}.")

    def get_commit_log(self):
        pass
