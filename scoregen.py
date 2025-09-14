#!/usr/bin/env python3

import argparse
import math
import os
import re
import subprocess
import sys

# --- Churn Weight Configuration ---
IMPORTANT_EXTENSIONS = {
    # Core Source
    ".py",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".java",
    ".kt",
    ".cs",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".go",
    ".rs",
    ".swift",
    ".rb",
    ".php",
}
IMPORTANT_EXT_WEIGHT = 20  # Boost for important file types
SETUP_EXTENSIONS = {
    # Build & Config
    ".yml",
    ".yaml",
    "Makefile",
    "Dockerfile",
    "pom.xml",
    "build.gradle",
    "pyproject.toml",
    "go.mod",
    "CMakeLists.txt",
    # Infra & Schema
    ".sql",
    ".proto",
    ".graphql",
    ".tf",
    ".hcl",
    ".json",
    ".config.ts",
    ".lock",
}
SETUP_WEIGHT = 0.04

DATA_EXTENSIONS = {
    # -- Images --
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".tiff",
    ".webp",
    ".psd",
    ".ai",
    ".svg",  # Can be large if complex
    # -- Audio --
    ".mp3",
    ".wav",
    ".flac",
    ".aac",
    ".ogg",
    ".m4a",
    # -- Video --
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".flv",
    ".wmv",
    # -- Documents & Archives --
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".rar",
    ".7z",
    ".iso",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    # -- Models & 3D Assets --
    ".obj",
    ".fbx",
    ".blend",
    ".dae",
    ".stl",
    ".glb",
    ".gltf",
    # -- Data & Databases --
    ".db",
    ".sqlite",
    ".mdb",
    ".accdb",
    ".csv",  # Can be very large
    ".parquet",
    ".hdf5",
    ".pkl",
    ".bin",
    ".dat",
    # -- Executables & Libraries --
    ".exe",
    ".dll",
    ".so",
    ".a",
    ".lib",
    # -- Fonts --
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
}

DATA_EXT_WEIGHT = 0.01


def calculate_score(c1: str, c2: str) -> float:
    """
    Calculates a churn-based score where churn is weighted by file type
    and historical change frequency.
    """
    total_weighted_churn = 0.0

    try:
        # Get per-file stats (insertions, deletions, path) for the range
        cmd_numstat = ["git", "diff", "--numstat", c1, c2]
        numstat_output = subprocess.check_output(cmd_numstat, text=True)

        for line in numstat_output.strip().split("\n"):
            if not line:
                continue

            parts = line.split("\t")
            insertions = int(parts[0]) if parts[0] != "-" else 0
            deletions = int(parts[1]) if parts[1] != "-" else 0
            file_path = parts[2]

            raw_churn = insertions + deletions
            # taper = 500
            # raw_churn = taper * math.tanh(raw_churn / taper)

            # --- Calculate the weight for this file's churn ---
            weight = 0.70

            # 1. Adjust weight based on file extension
            _, ext = os.path.splitext(file_path)
            filename = os.path.basename(file_path)
            if ext in IMPORTANT_EXTENSIONS or filename in IMPORTANT_EXTENSIONS:
                weight *= IMPORTANT_EXT_WEIGHT
            if ext in SETUP_EXTENSIONS or filename in SETUP_EXTENSIONS:
                weight *= SETUP_WEIGHT

            # 2. Adjust weight based on historical change frequency
            # Files changed more often in the past are considered more significant.
            cmd_history = [
                "git",
                "rev-list",
                "--count",
                "--first-parent",
                f"{c1}..{c2}",
                "--",
                file_path,
            ]
            history_count_str = subprocess.check_output(cmd_history, text=True).strip()
            history_count = int(history_count_str)

            # Use a log scale to create a modifier. A file changed once (history_count=1)
            # gets a small boost, while a file changed 100 times gets a larger one.
            # A file never changed before (history_count=0) gets no boost (log(1)=0).
            history_modifier = math.tanh(history_count / 1.7)

            # weight *= history_modifier
            # --- Apply final weight to this file's churn ---
            total_weighted_churn += raw_churn * weight

    except subprocess.CalledProcessError:

        return 0.0  # Return 0 if any git command fails

    return total_weighted_churn


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
