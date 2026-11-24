#!/usr/bin/env python3
"""Discover references without following repository-controlled symlinks."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

from scope import collect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", nargs="?")
    parser.add_argument("--expect-head")
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--check")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    try:
        scope = collect(args.base, expected_head=args.expect_head, paths=args.path, require_clean=args.clean)
        if not scope["files"] and not scope["excluded"]:
            raise ValueError("empty review scope")
        if args.check and scope["fingerprint"] != args.check:
            raise ValueError("review target changed")
        root = Path(scope["root"])
        rejected = set()

        def safe(path):
            parts = path.relative_to(root).parts
            if any(root.joinpath(*parts[:i]).is_symlink() for i in range(1, len(parts) + 1)):
                rejected.add(path.relative_to(root).as_posix())
                return False
            return path.is_file()

        rules = set()
        for name in scope["files"]:
            directory = (root / name).parent
            while True:
                for filename in ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md"):
                    path = directory / filename
                    if safe(path):
                        rules.add(path.relative_to(root).as_posix())
                if directory == root:
                    break
                directory = directory.parent
        for filename in ("CONTRIBUTING.md", "CODING_STANDARDS.md", "STYLE.md", "CONVENTIONS.md"):
            if safe(root / filename):
                rules.add(filename)
        specs = set()
        for directory in ("docs", "specs", ".scratch", "doc"):
            folder = root / directory
            if folder.is_symlink():
                rejected.add(directory)
                continue
            for pattern in ("*.md", "*/*.md", "*/*/*.md", "*.txt"):
                for path in folder.glob(pattern):
                    if safe(path):
                        specs.add(path.relative_to(root).as_posix())
        result = subprocess.run(["git", "-C", str(root), "log", scope["base"] + ".." + scope["head"], "--pretty=%B"],
                                capture_output=True, text=True, check=True)
        issues = sorted(set(re.findall(r"(?<!\w)(?:#\d+|!\d+|[A-Z][A-Z0-9]+-\d+)\b", result.stdout)))
        print("fingerprint: " + scope["fingerprint"])
        for heading, values in (("issue references", issues), ("candidate specs", sorted(specs)[:10]),
                                ("governing repository rules", sorted(rules)), ("unreviewed symlink references", sorted(rejected))):
            print(heading + ":")
            print("\n".join("  " + item for item in values) or "  none")
        print("Read only safe references. Host-provided user instructions are separate from repository-controlled links.")
        print("Quote the actual requirement/rule; missing specs and truncated candidate lists are not passing checks.")
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
