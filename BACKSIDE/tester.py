from fetcher import DataFetcher
import os
import shutil
from milestones import get_milestone_data


def empty_directory(directory_path):
    """
    Deletes all files and subdirectories within the specified directory.

    Args:
        directory_path (str): The path to the directory to be emptied.
    """
    if not os.path.exists(directory_path):
        print(f"Directory not found: {directory_path}")
        return

    # Iterate over all entries in the directory
    for entry in os.listdir(directory_path):
        full_path = os.path.join(directory_path, entry)
        if os.path.isfile(full_path) or os.path.islink(full_path):
            os.unlink(full_path)  # Remove the file or link
        elif os.path.isdir(full_path):
            shutil.rmtree(full_path)  # Remove the subdirectory and its contents


testrepo = "patrick-gu/toot"
d = DataFetcher()
empty_directory("../workspace")
repo = d.fetch_github_repository(testrepo, "../workspace")
commits = d.get_commit_log(repo)[::-1]
first_commit = d.get_boundary_commit(repo)
last_commit = d.get_boundary_commit(repo, False)
commits = [first_commit] + commits
if last_commit.hash != commits[-1].hash:
    commits.append(last_commit)

milestone = get_milestone_data(commits[1], commits[2])
for dc in milestone.changes:
    print(dc)
for message in milestone.messages:
    print(message)
