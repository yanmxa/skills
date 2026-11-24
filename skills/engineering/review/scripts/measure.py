#!/usr/bin/env python3
"""Inventory measurements; run installed analyzers only with explicit opt-in."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from scope import collect

SOURCES = {".go", ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".rb", ".rs", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".php", ".swift", ".kt", ".scala", ".m", ".mm", ".lua"}


def measure(scope, run_tools=False, project_checks=False):
    root = Path(scope["root"])
    files = [name for name in scope["files"] if (root / name).is_file() and Path(name).suffix in SOURCES]
    results = []

    def run(metric, command, permitted, scope_kind="files"):
        item = {"metric": metric, "command": command, "scope": scope_kind}
        if not shutil.which(command[0]):
            item.update(status="UNMEASURED", reason="tool not installed; no automatic downloads")
        elif not permitted:
            item.update(status="NOT_RUN", reason="requires explicit opt-in")
        else:
            try:
                proc = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=120)
                output = proc.stdout + proc.stderr
                item.update(status="MEASURED" if proc.returncode == 0 else "FAILED",
                            exit_code=proc.returncode, output=output[:12000], truncated=len(output) > 12000)
            except (OSError, subprocess.TimeoutExpired):
                item.update(status="FAILED", reason="tool failed or exceeded 120 seconds")
        results.append(item)

    # Absolute paths preserve spaces, metacharacters and leading '-' filenames.
    paths = [str(root / name) for name in files]
    if paths:
        run("complexity", ["lizard", "--csv", *paths], run_tools)
        with tempfile.TemporaryDirectory(prefix="review-metrics-") as td:
            run("duplication", ["jscpd", "--reporters", "json", "--output", td, *paths], run_tools)
            if results[-1]["status"] == "MEASURED":
                report = Path(td) / "jscpd-report.json"
                if report.is_file():
                    try:
                        results[-1]["report"] = json.loads(report.read_text())
                    except (OSError, ValueError):
                        results[-1].update(status="FAILED", reason="invalid duplication report")
                else:
                    results[-1].update(status="FAILED", reason="analyzer produced no duplication report")
        python = [str(root / name) for name in files if name.endswith(".py")]
        if python:
            run("python dead-code candidates", ["vulture", *python], run_tools)
            run("python maintainability", ["radon", "mi", "-s", *python], run_tools)
        if any(name.endswith(".go") for name in files):
            run("go dead-code candidates", ["staticcheck", "-checks=U1000", "./..."], project_checks, "project")
            run("go coverage/tests", ["go", "test", "-cover", "./..."], project_checks, "project")
        if any(Path(name).suffix in {".js", ".jsx", ".ts", ".tsx"} for name in files):
            run("js/ts dead-code candidates", ["knip", "--no-progress"], project_checks, "project")
    mutation = [name for name in ("metron", "gremlins", "mutmut", "stryker", "cargo-mutants") if shutil.which(name)]
    return {"fingerprint": scope["fingerprint"], "files": files, "excluded": scope["excluded"],
            "results": results, "mutation_tools_available": mutation,
            "notice": "Measurement is not correctness proof. NOT_RUN/UNMEASURED/FAILED are never passes; mutation is not run."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", nargs="?")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--run-tools", action="store_true", help="run installed source analyzers after authorization")
    parser.add_argument("--project-checks", action="store_true", help="also allow project-wide checks/test execution (may have side effects)")
    parser.add_argument("--check", help="require the shared review fingerprint")
    parser.add_argument("--expect-head")
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    try:
        scope = collect(args.base, whole_tree=args.base is None, expected_head=args.expect_head, paths=args.path, require_clean=args.clean)
        if args.base is not None and not scope["files"] and not scope["excluded"]:
            raise ValueError("empty review scope")
        if args.check and scope["fingerprint"] != args.check:
            raise ValueError("review target changed; collect a fresh scope")
        report = measure(scope, args.run_tools, args.project_checks)
        after = collect(args.base, whole_tree=args.base is None, expected_head=args.expect_head, paths=args.path, require_clean=args.clean)
        if after["fingerprint"] != scope["fingerprint"]:
            raise ValueError("analyzer changed the review target; measurements are stale")
        if args.json:
            print(json.dumps(report, ensure_ascii=True, indent=2))
        else:
            print("fingerprint: " + report["fingerprint"])
            print(f"scope: {len(report['files'])} source files; {len(report['excluded'])} excluded paths")
            for item in report["results"]:
                print(f"{item['metric']}: {item['status']}")
                print("  command: " + json.dumps(item["command"]))
                if "output" in item:
                    print(item["output"])
                if "report" in item:
                    print(json.dumps(item["report"], ensure_ascii=True))
                if "reason" in item:
                    print("  " + item["reason"])
                if item.get("truncated"):
                    print("  output truncated; full findings not assessed")
            print(report["notice"])
        if any(item["status"] == "FAILED" for item in report["results"]):
            sys.exit(1)
    except (ValueError, OSError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
