import subprocess as sp
import string
import random
import os
from gitmodels import Commit
from typing import Optional

default_cloning_depth = 310


def generate_slug(length=12):
    """Generate a random alphanumeric slug of specified length."""
    characters = string.ascii_letters + string.digits  # a-z, A-Z, 0-9
    return "".join(random.choice(characters) for _ in range(length))


class RepoNotFoundException(Exception):
    pass


class FailedGitLogException(Exception):
    pass


class FailedLogParseException(Exception):
    pass


class EmptyRepositoryException(Exception):
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
            empty_repo_check = ["git", "rev-list", "-n", "1", "--all"]
            try:
                sp.run(empty_repo_check, check=True)
            except sp.CalledProcessError:
                raise EmptyRepositoryException(f"Repo {repo} is empty.")
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

    def get_boundary_commit(self, repository: str, first: bool = True) -> Commit:
        """Finds the very first (oldest) or last (newest) commit of a branch."""
        # --reverse finds the oldest commit first. Without it, we get the newest.

        format_string = "%x1e%H%x1f%P%x1f%an%x1f%at%x1f%ct%x1f%s"
        command = [
            "git",
            "--no-pager",
            "log",
            "-n",
            "1",
            f'--pretty=format:"{format_string}"',
        ]
        if first:
            try:
                # STEP 1: Run the inner command to get the root commit hash
                rev_list_command = ["git", "rev-list", "--max-parents=0", "HEAD"]
                rev_list_result = sp.run(
                    rev_list_command,
                    cwd=repository,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                root_hash = rev_list_result.stdout.strip()
                if not root_hash:
                    raise EmptyRepositoryException("No root commit found.")

                command = [
                    "git",
                    "--no-pager",
                    "show",
                    root_hash,
                    f'--pretty=format:"{format_string}"',
                    "--no-patch",
                ]
            except sp.CalledProcessError as e:
                raise FailedGitLogException(f"Failed to get root hash: {e.stderr}")

        print(" ".join(command))
        try:
            result = sp.run(
                command,
                cwd=repository,
                capture_output=True,
                text=True,
                check=True,
            )
            try:
                output = result.stdout.split("\x1e")[1]

                chash, parents_str, aname, adate, cdate, subject = output.strip().split(
                    "\x1f"
                )
                commit = Commit(
                    hash=chash,
                    parent_hashes=parents_str.split(),
                    author_name=aname,
                    author_date_unix=int(adate),
                    committer_date_unix=int(cdate),
                    subject=subject,
                )
                return commit
            except ValueError:
                raise FailedLogParseException(
                    f"Failed to parse output of following command:\n{' '.join(command)}\nin folder {repository}\noutput:\n{result.stdout.strip()}"
                )
        except sp.CalledProcessError as e:
            raise FailedGitLogException(
                f"Failed to execute following command:\n{' '.join(command)}\nin folder {repository}\n\nstdout:\n{e.stdout}\n\nstderr:{e.stderr}"
            )
