import asyncio
from datetime import datetime
import os
import shutil

from BACKSIDE.fetcher import DataFetcher
from BACKSIDE.milestones import get_milestone_data
from BACKSIDE.processor import MilestoneProcessor


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


def print_unix_timestamp(timestamp):
    dt_object = datetime.fromtimestamp(timestamp)

    formatted_date = dt_object.strftime("%Y-%m-%d %H:%M:%S")

    print(formatted_date)


testrepo = "patrick-gu/toot"
d = DataFetcher()
empty_directory("./workspace")
repo = d.fetch_github_repository(testrepo, "./workspace", use_https=True)
commits = d.get_commit_log(repo)
first_commit = d.get_boundary_commit(repo)
last_commit = d.get_boundary_commit(repo, False)
commits = [first_commit] + commits
if last_commit.hash != commits[-1].hash:
    commits.append(last_commit)

milestone = get_milestone_data(commits[5], commits[10])
for dc in milestone.changes:
    print(dc)
for message in milestone.messages:
    print(message)

print("Milestone start:")
print_unix_timestamp(milestone.time_start)
print("Milestone end:")
print_unix_timestamp(milestone.time_end)

async def main():
    processor = MilestoneProcessor([milestone])
    await processor.process_all_milestones()

asyncio.run(main())


# paths = [a.path for a in milestone.changes]
# while True:
#     command, *args = input().split()
#     if command == "list":
#         print(paths)
#     elif command == "diff":
#         filename = args[0]
#         print(milestone.get_diff_for_file(filename))


