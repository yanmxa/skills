import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILLS = Path(__file__).resolve().parents[1] / "skills/engineering"
TARGET = SKILLS / "review/scripts/target.sh"
METRICS = SKILLS / "metrics/scripts/measure.sh"
REFS = SKILLS / "intent/scripts/refs.sh"


class ReviewHelpersTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="review-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Review Test")
        self.git("config", "user.email", "review@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", str(self.root / "no-hooks"))
        for name in ("module.py", "staged.py", "deleted.py"):
            (self.root / name).write_text("value = 1\n")
        self.git("add", ".")
        self.git("commit", "-qm", "baseline")
        self.git("checkout", "-qb", "work")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True).stdout

    def run_script(self, script, *args, env=None, cwd=None):
        return subprocess.run(["/bin/sh", str(script), *args], cwd=cwd or self.root,
                              capture_output=True, text=True, env=env)

    def scope(self):
        result = self.run_script(TARGET, "main", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_untracked_only_is_in_scope(self):
        (self.root / "new module.py").write_text("value = 2\n")
        scope = self.scope()
        self.assertIn("new module.py", scope["files"])
        self.assertIn("new module.py", scope["untracked"])

    def test_branch_index_worktree_and_deleted_share_one_scope(self):
        (self.root / "branch.py").write_text("value = 3\n")
        self.git("add", "branch.py")
        self.git("commit", "-qm", "branch change")
        (self.root / "staged.py").write_text("value = 4\n")
        self.git("add", "staged.py")
        (self.root / "module.py").write_text("value = 5\n")
        self.git("rm", "deleted.py")
        (self.root / "new.py").write_text("value = 6\n")
        self.assertEqual(set(self.scope()["files"]), {"branch.py", "staged.py", "module.py", "deleted.py", "new.py"})

    def test_fingerprint_detects_same_length_content_change(self):
        path = self.root / "new.py"
        path.write_text("value = 1\n")
        token = self.scope()["fingerprint"]
        self.assertEqual(self.run_script(TARGET, "main", "--check", token).returncode, 0)
        path.write_text("value = 2\n")
        self.assertNotEqual(self.run_script(TARGET, "main", "--check", token).returncode, 0)

    def test_index_content_is_not_lost_when_worktree_is_restored(self):
        path = self.root / "module.py"
        path.write_text("value = 2\n")
        self.git("add", "module.py")
        path.write_text("value = 1\n")
        scope = self.scope()
        self.assertIn("module.py", scope["files"])
        path.write_text("value = 3\n")
        self.git("add", "module.py")
        path.write_text("value = 1\n")
        self.assertNotEqual(scope["fingerprint"], self.scope()["fingerprint"])

    def test_credentials_and_symlinks_are_explicitly_unreviewed(self):
        (self.root / ".env").write_text("PASSWORD=do-not-display\n")
        self.git("add", "-f", ".env")  # isolate this case from the user's global .env ignore
        (self.root / "credentials.json").write_text('{"token":"do-not-display"}')
        (self.root / "linked.py").symlink_to(self.root / ".env")
        scope = self.scope()
        self.assertFalse(set(scope["files"]) & {".env", "credentials.json", "linked.py"})
        self.assertEqual({item["path"] for item in scope["excluded"]}, {".env", "credentials.json", "linked.py"})
        self.assertNotIn("do-not-display", json.dumps(scope))

    def test_ignored_files_are_not_reviewed(self):
        (self.root / ".gitignore").write_text("ignored.py\n")
        (self.root / "ignored.py").write_text("value = 2\n")
        self.assertNotIn("ignored.py", self.scope()["files"])

    def test_generated_diff_preserves_literal_metacharacter_path(self):
        name = "a *; echo no.py"
        (self.root / name).write_text("value = 2\n")
        self.git("add", name)
        scope = self.scope()
        args = shlex.split(scope["diff_commands"]["final"])
        self.assertIn(":(literal)" + name, args)
        result = subprocess.run(args, cwd=self.root, capture_output=True, text=True, check=True)
        self.assertIn("+value = 2", result.stdout)

    def test_nested_directory_uses_root_relative_paths(self):
        subdir = self.root / "nested"
        subdir.mkdir()
        (subdir / "new.py").write_text("value = 2\n")
        result = self.run_script(TARGET, "main", "--json", cwd=subdir)
        self.assertEqual(json.loads(result.stdout)["files"], ["nested/new.py"])

    def test_bad_base_and_empty_scope_fail(self):
        self.assertNotEqual(self.run_script(TARGET, "does-not-exist", "--json").returncode, 0)
        self.assertNotEqual(self.run_script(TARGET, "main", "--json").returncode, 0)

    def tool_env(self, source):
        folder = self.root / "tools"
        folder.mkdir()
        (folder / "git").symlink_to(shutil.which("git"))
        (folder / "python3").symlink_to(sys.executable)
        (folder / "dirname").symlink_to(shutil.which("dirname"))
        tool = folder / "lizard"
        tool.write_text(source)
        tool.chmod(0o700)
        return dict(os.environ, PATH=str(folder))

    def test_metrics_inventory_does_not_execute_tools(self):
        (self.root / "new file.py").write_text("value = 2\n")
        marker = self.root / "executed"
        env = self.tool_env(f'#!/bin/sh\nprintf yes > "{marker}"\n')
        result = self.run_script(METRICS, "main", "--json", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("new file.py", report["files"])
        self.assertEqual(report["results"][0]["status"], "NOT_RUN")
        self.assertFalse(marker.exists())

    def test_authorized_analyzer_failure_is_not_a_pass(self):
        (self.root / "new file.py").write_text("value = 2\n")
        env = self.tool_env("#!/bin/sh\nexit 7\n")
        result = self.run_script(METRICS, "main", "--json", "--run-tools", env=env)
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertEqual(report["results"][0]["status"], "FAILED")
        self.assertEqual(report["results"][0]["exit_code"], 7)
        self.assertIn(str((self.root / "new file.py").resolve()), report["results"][0]["command"])

    def test_excluded_manifest_drift_invalidates_review(self):
        (self.root / "new.py").write_text("value = 2\n")
        first = self.scope()["fingerprint"]
        hidden = self.root / "credentials.json"
        hidden.write_text('{"token":"not-for-review"}')
        added = self.scope()["fingerprint"]
        self.assertNotEqual(first, added)
        self.assertNotEqual(self.run_script(TARGET, "main", "--check", first).returncode, 0)
        hidden.unlink()
        self.assertNotEqual(self.run_script(TARGET, "main", "--check", added).returncode, 0)

    def test_exclusive_target_rejects_wrong_head_and_dirty_checkout(self):
        (self.root / "module.py").write_text("value = 2\n")
        self.git("add", "module.py")
        self.git("commit", "-qm", "selected change")
        self.assertNotEqual(self.run_script(TARGET, "main", "--expect-head", "main", "--clean").returncode, 0)
        self.assertEqual(self.run_script(TARGET, "HEAD~1", "--expect-head", "HEAD", "--clean").returncode, 0)
        (self.root / "local.py").write_text("value = 3\n")
        self.assertNotEqual(self.run_script(TARGET, "HEAD~1", "--expect-head", "HEAD", "--clean").returncode, 0)

    def test_path_filter_is_literal_and_shared_with_metrics(self):
        (self.root / "src").mkdir()
        (self.root / "src/new.py").write_text("value = 2\n")
        (self.root / "other.py").write_text("value = 3\n")
        target = self.run_script(TARGET, "main", "--path", "src", "--json")
        scope = json.loads(target.stdout)
        self.assertEqual(scope["files"], ["src/new.py"])
        result = self.run_script(METRICS, "main", "--path", "src", "--check", scope["fingerprint"], "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["files"], scope["files"])
        self.assertNotEqual(self.run_script(TARGET, "main", "--path", "../outside").returncode, 0)

    def test_refs_does_not_recommend_symlinked_rules_or_specs(self):
        with tempfile.TemporaryDirectory(prefix="review-outside-") as td:
            outside = Path(td)
            (outside / "untrusted_spec.md").write_text("Not a repository instruction.\n")
            (self.root / "AGENTS.md").symlink_to(outside / "untrusted_spec.md")
            (self.root / "docs").symlink_to(outside, target_is_directory=True)
            (self.root / "new.py").write_text("value = 2\n")
            result = self.run_script(REFS, "main")
            self.assertEqual(result.returncode, 0, result.stderr)
            rules = result.stdout.split("governing repository rules:\n", 1)[1].split("unreviewed symlink references:", 1)[0]
            self.assertNotIn("AGENTS.md", rules)
            self.assertIn("unreviewed symlink references:", result.stdout)
            self.assertNotIn("untrusted_spec.md", result.stdout)

    def test_large_files_are_disclosed_without_reading_content(self):
        (self.root / "large.dat").write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        scope = self.scope()
        self.assertNotIn("large.dat", scope["files"])
        self.assertIn("2 MiB", scope["excluded"][0]["reason"])

    def test_analyzer_mutation_invalidates_evidence_without_rollback(self):
        (self.root / "new.py").write_text("value = 2\n")
        env = self.tool_env(f'#!/bin/sh\nprintf "changed\\n" > "{self.root / "module.py"}"\n')
        result = self.run_script(METRICS, "main", "--run-tools", "--json", env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale", result.stderr)
        self.assertEqual((self.root / "module.py").read_text(), "changed\n")

    def test_refs_covers_untracked_paths_with_spaces(self):
        folder = self.root / "src nested"
        folder.mkdir()
        (folder / "AGENTS.md").write_text("Use explicit errors.\n")
        (folder / "new.py").write_text("value = 2\n")
        result = self.run_script(REFS, "main")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("src nested/AGENTS.md", result.stdout)


if __name__ == "__main__":
    unittest.main()
