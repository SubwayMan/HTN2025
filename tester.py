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

# Create evenly spaced milestones
num_commits = len(commits)
target_milestones = min(10, num_commits - 1)  # Can't have more milestones than commit pairs

milestones = []
if target_milestones > 0:
    # Calculate the base size and remainder for distribution
    base_size = num_commits // target_milestones
    remainder = num_commits % target_milestones

    start_idx = 0
    for i in range(target_milestones):
        # Add 1 to the first 'remainder' milestones to distribute extra commits
        milestone_size = base_size + (1 if i < remainder else 0)
        end_idx = start_idx + milestone_size - 1

        # Ensure we don't go out of bounds
        if end_idx >= num_commits:
            end_idx = num_commits - 1


        print(f"Start idx: {start_idx}, End idx: {end_idx}")
        milestone = get_milestone_data(commits[start_idx], commits[end_idx])
        milestones.append(milestone)

        # Move start to next position (non-overlapping)
        start_idx = end_idx + 1

        # Stop if we've covered all commits
        if start_idx >= num_commits:
            break

# Print information about all milestones
for i, milestone in enumerate(milestones):
    print(f"\n--- Milestone {i+1} ---")
    # for dc in milestone.changes:
    #     print(dc)
    for message in milestone.messages:
        print(message)

    print("Milestone start:")
    print_unix_timestamp(milestone.time_start)
    print("Milestone end:")
    print_unix_timestamp(milestone.time_end)

async def main():
    processor = MilestoneProcessor()

    for m in milestones[:5]:
        await processor.process_milestone(m)

asyncio.run(main())


# paths = [a.path for a in milestone.changes]
# while True:
#     command, *args = input().split()
#     if command == "list":
#         print(paths)
#     elif command == "diff":
#         filename = args[0]
#         print(milestone.get_diff_for_file(filename))


