#!/usr/bin/env python3

import argparse
import math
import re
import subprocess
import sys

# --- Simple Score Configuration ---
# Tune these weights to prioritize what's important.
W_COMMITS = 1.0  # Weight for each commit in the range
W_FILES = 0.2  # Weight for each file that was changed
W_CHURN = 0.01  # Weight for each line added or deleted


def calculate_score(c1: str, c2: str) -> float:
    """Calculates a simple score based on commits, files, and churn."""

    num_commits = 0
    num_changed_files = 0
    total_churn = 0

    try:
        # 1. Get the number of commits
        cmd_commits = ["git", "rev-list", "--count", "--first-parent", f"{c1}..{c2}"]
        result = subprocess.check_output(cmd_commits, text=True)
        num_commits = int(result.strip())

        # 2. Get the number of unique changed files
        cmd_files = ["git", "diff", "--name-only", c1, c2]
        result = subprocess.check_output(cmd_files, text=True)
        changed_files = result.strip().split("\n")
        # Filter out empty strings if there are no changed files
        num_changed_files = len([f for f in changed_files if f])

        # 3. Get the total churn (insertions + deletions)
        cmd_churn = ["git", "diff", "--shortstat", c1, c2]
        result = subprocess.check_output(cmd_churn, text=True)
        insertions = deletions = 0
        ins_match = re.search(r"(\d+) insertion", result)
        del_match = re.search(r"(\d+) deletion", result)
        if ins_match:
            insertions = int(ins_match.group(1))
        if del_match:
            deletions = int(del_match.group(1))
        total_churn = insertions + deletions

    except subprocess.CalledProcessError as e:
        return 0

    # Apply the weighted formula
    score = (
        (W_COMMITS * num_commits)
        + (W_FILES * num_changed_files)
        + (W_CHURN * total_churn)
    )

    return score


def main():
    """Parses arguments and runs the scoring or bisection logic."""
    parser = argparse.ArgumentParser(
        description="Calculate a 'work score' between two commits or test against a limit for git bisect."
    )
    parser.add_argument("c1", help="The starting commit hash (the 'bad' commit).")
    parser.add_argument("c2", help="The ending commit hash (the one being tested).")
    parser.add_argument(
        "--limit",
        type=float,
        help="If provided, exit 0 if score <= limit (good), and 1 if score > limit (bad).",
    )

    args = parser.parse_args()

    score = calculate_score(args.c1, args.c2)

    if args.limit is not None:
        # Bisect Mode: Compare score and exit with a status code.
        print(
            f"Testing {args.c2[:7]}... Score: {score:.2f} / {args.limit}",
            file=sys.stderr,
        )
        if score > args.limit:
            sys.exit(1)  # "Fail" the test (this commit is 'bad' for bisect)
        else:
            sys.exit(0)  # "Pass" the test (this commit is 'good' for bisect)
    else:
        # Scoring Mode: Just print the score.
        print(f"{score:.2f}")


if __name__ == "__main__":
    main()
