import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SETUP = Path(__file__).resolve().parents[1] / "skills/misc/setup-macos/scripts/setup-macos.sh"


class SetupLayoutTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="setup-layout-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.bundle = self.root / "checkout with spaces"
        self.setup = self.bundle / "setup-macos/scripts/setup-macos.sh"
        self.setup.parent.mkdir(parents=True)
        shutil.copyfile(SETUP, self.setup)

    def run_setup(self):
        return subprocess.run(
            ["/bin/bash", str(self.setup), "--components", "git"],
            cwd=self.root,
            env=dict(os.environ, HOME=str(self.root)),
            capture_output=True,
            text=True,
        )

    def test_runs_sibling_component_from_another_working_directory(self):
        component = self.bundle / "setup-git/scripts/setup-git.sh"
        component.parent.mkdir(parents=True)
        component.write_text("printf 'ran bundled component\\n'\n")
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ran bundled component\n", result.stdout)

    def test_missing_component_fails_instead_of_reporting_setup_complete(self):
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing component script for git", result.stderr)
        self.assertNotIn("Setup Complete", result.stdout)
