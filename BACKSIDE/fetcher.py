import subprocess as sp
import string
import random
import os
from gitmodels import Commit

default_cloning_depth = 310


def generate_slug(length=12):
    """Generate a random alphanumeric slug of specified length."""
    characters = string.ascii_letters + string.digits  # a-z, A-Z, 0-9
    return "".join(random.choice(characters) for _ in range(length))


class RepoNotFoundException(Exception):
    pass


class FailedGitLogException(Exception):
    pass


class DataFetcher:
    """
    Class for obtaining data from Github.
    Return
    """

    def fetch_github_repository(
        self, repo: str, workspace_path: str, depth: int = default_cloning_depth
    ):
        """
        Clones a github repository into a workspace folder.
        repo: username/project example: 'SubwayMan/htn2025'
        workspace_path: the folder in which the project will be cloned.
        depth: cloning depth.
        returns: file path to cloned folder.
        """
        slug = generate_slug()
        path = os.path.join(workspace_path, slug)
        while os.path.exists(path):
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

    def get_commit_log(self, repository: str):
        format_string = "%x1e%H%x1f%P%x1f%an%x1f%at%x1f%ct%x1f%s"
        git_cmd = [
            "git",
            "--no-pager",
            "log",
            "--first-parent",
            "--merges",
            "--date=unix",
            f'--pretty=format:"{format_string}"',
        ]

        result = None
        print("Grabbing commits...")
        try:
            result = sp.run(
                git_cmd, cwd=repository, capture_output=True, text=True, check=True
            )
            commits = []
            print("Length of output:", len(result.stdout.split("\n")))

            command_content = result.stdout.split("\x1e")[1:]
            for record in command_content:
                try:
                    # Unpack the new committer date field
                    chash, parents_str, aname, adate, cdate, subject = (
                        record.strip().split("\x1f")
                    )
                    commit = Commit(
                        hash=chash,
                        parent_hashes=parents_str.split(),
                        author_name=aname,
                        author_date_unix=int(adate),
                        committer_date_unix=int(cdate),
                        subject=subject,
                    )
                    commits.append(commit)
                except ValueError:
                    print(f"Warning: Could not parse record: {record}")
                    continue

            return commits

        except sp.CalledProcessError:
            raise FailedGitLogException(
                f"Failed to run following command:\n{' '.join(git_cmd)}\nin directory {repository}"
            )
