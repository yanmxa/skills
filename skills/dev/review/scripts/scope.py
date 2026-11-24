#!/usr/bin/env python3
"""One review scope for branch, index, worktree and untracked files. Never edits Git."""
import argparse
import fnmatch
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys


SECRET_PATTERNS = (".env", ".env.*", "*.key", "*.pem", "*.p12", "*.pfx", "secrets.*", "credentials.*",
                   "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa", "*_private.*", "*_secret.*")


def git(*args):
    result = subprocess.run(["git", *args], capture_output=True)
    if result.returncode:
        raise ValueError("git command failed: " + " ".join(args[:2]))
    return result.stdout


def collect(base=None, whole_tree=False, expected_head=None, paths=None, require_clean=False):
    root = Path(git("rev-parse", "--show-toplevel").decode().strip())
    head = git("rev-parse", "HEAD").decode().strip()
    if require_clean and git("status", "--porcelain", "-z", "--untracked-files=all"):
        raise ValueError("exclusive PR/commit review requires a clean checkout; local changes were not included")
    if expected_head:
        expected = git("rev-parse", "--verify", "--end-of-options", expected_head + "^{commit}").decode().strip()
        if expected != head:
            raise ValueError("requested head is not this checkout; use an approved isolated checkout first")
    selected = []
    for name in paths or []:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("--path must be repository-relative without '..'")
        selected.append(path.as_posix().rstrip("/") or ".")
    if base is None:
        for candidate in ("@{upstream}", "main", "HEAD~1", "HEAD"):
            probe = subprocess.run(["git", "rev-parse", "--verify", candidate + "^{commit}"], capture_output=True)
            if probe.returncode == 0:
                base = candidate
                break
    resolved = git("rev-parse", "--verify", "--end-of-options", base + "^{commit}").decode().strip()
    merge = git("merge-base", resolved, head).decode().strip()
    prefix = ["-C", str(root)]
    layers = ((merge, head), ("--cached", head), ())
    changed = set()
    for layer in layers:
        changed.update(p for p in git(*prefix, "diff", "--name-only", "--no-renames", "-z", *layer).split(b"\0") if p)
    untracked = set(p for p in git(*prefix, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0") if p)
    changed.update(untracked)
    if whole_tree:
        changed.update(p for p in git(*prefix, "ls-files", "-z").split(b"\0") if p)
    included, excluded = [], []
    digest = hashlib.sha256(json.dumps([merge, head, whole_tree, sorted(selected), require_clean]).encode())
    for raw in sorted(changed):
        name = raw.decode("utf-8", errors="surrogateescape")
        if selected and not any(item == "." or name == item or name.startswith(item + "/") for item in selected):
            continue
        path = root / name
        reason = None
        if any(fnmatch.fnmatch(part.lower(), pattern) for part in path.relative_to(root).parts for pattern in SECRET_PATTERNS):
            reason = "credential-like path"
        elif "\n" in name or "\r" in name:
            reason = "newline in filename"
        elif any((root.joinpath(*path.relative_to(root).parts[:i])).is_symlink()
                 for i in range(1, len(path.relative_to(root).parts) + 1)):
            reason = "symlink (not followed)"
        elif path.is_file() and path.stat().st_size > 2 * 1024 * 1024:
            reason = "file exceeds 2 MiB; explicit inspection required"
        if reason:
            excluded.append({"path": name, "reason": reason})
            digest.update(raw + b"\0excluded\0" + reason.encode())
            digest.update(b"link" if path.is_symlink() else b"file" if path.exists() else b"deleted")
            continue
        included.append(name)
        digest.update(raw + b"\0")
        if path.is_file():
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        else:
            digest.update(b"<deleted>")
    literal = [":(literal)" + name for name in included]
    commands = {}
    if literal:
        for label, layer in (("final", (merge,)), ("staged", ("--cached", head)), ("unstaged", ())):
            args = ["git", *prefix, "diff", "--no-ext-diff", "--no-textconv", *layer, "--", *literal]
            commands[label] = shlex.join(args)
            # Include staging changes even when the worktree was restored to HEAD.
            digest.update(git(*args[1:]))
    return {"root": str(root), "base_ref": base, "base": merge, "head": head, "paths": selected,
            "whole_tree": whole_tree, "clean": require_clean,
            "fingerprint": digest.hexdigest(), "files": included,
            "untracked": [p.decode("utf-8", errors="surrogateescape") for p in sorted(untracked) if p.decode("utf-8", errors="surrogateescape") in included],
            "excluded": excluded, "diff_commands": commands}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", nargs="?")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--files", action="store_true")
    parser.add_argument("--all", action="store_true", help="whole tree, for standalone metrics")
    parser.add_argument("--check", help="fail if the review fingerprint changed")
    parser.add_argument("--expect-head", help="require the requested PR/commit head to be checked out")
    parser.add_argument("--path", action="append", default=[], help="limit to a repository-relative file/directory")
    parser.add_argument("--clean", action="store_true", help="reject local changes for an exclusive PR/commit review")
    args = parser.parse_args()
    try:
        scope = collect(args.base, args.all, args.expect_head, args.path, args.clean)
        if not scope["files"] and not scope["excluded"]:
            raise ValueError("empty review scope")
        if args.check and args.check != scope["fingerprint"]:
            raise ValueError("review target changed; collect a fresh scope and re-review")
        if args.json:
            print(json.dumps(scope, ensure_ascii=True, indent=2))
        elif args.files:
            print("\n".join(scope["files"]))
        else:
            print(f"base: {scope['base']}\nhead: {scope['head']}\nfingerprint: {scope['fingerprint']}")
            print("files (branch + staged + unstaged + untracked):")
            for name in scope["files"]:
                print("  " + name)
            for entry in scope["excluded"]:
                print(f"unreviewed: {entry['path']} ({entry['reason']})")
            for label, command in scope["diff_commands"].items():
                print(f"{label} diff: {command}")
            print("Read included untracked files separately: Git diff does not contain them.")
            print("Before reporting, rerun with --check <fingerprint> and the same base and target flags.")
    except (ValueError, OSError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
