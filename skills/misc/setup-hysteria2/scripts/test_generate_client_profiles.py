import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("generate-client-profiles.py")


class ProfileGenerationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.env = root / ".env"
        self.profiles = root / "profiles"
        self.result = root / "result"
        key, cert = root / "key.pem", root / "cert.pem"
        subprocess.run(["openssl", "req", "-new", "-x509", "-nodes", "-newkey", "rsa:2048",
                        "-keyout", str(key), "-out", str(cert), "-days", "1", "-subj", "/CN=bing.com",
                        "-addext", "subjectAltName=DNS:bing.com"], check=True, capture_output=True)
        self.cert = cert.read_text()
        pin = hashlib.sha256(ssl.PEM_cert_to_DER_cert(self.cert)).hexdigest().upper()
        self.result.write_text("\n".join([
            "=== installed ===", "==== RESULT ====", "HY2_SERVER=192.0.2.2", "HY2_PORT=8443",
            "HY2_SNI=bing.com", "HY2_AUTH=TestAuthToken1234567890", f"HY2_PINSHA256={pin}",
            "HY2_CERT_BASE64=" + base64.b64encode(self.cert.encode()).decode(), "==== DONE ====", "",
        ]))

    def run_generator(self, *extra, env=None):
        return subprocess.run(["python3", str(SCRIPT), "--host", "192.0.2.2", "--port", "8443",
                               "--env-file", str(self.env), "--profiles-dir", str(self.profiles), *extra],
                              capture_output=True, text=True, env=env)

    def test_generates_private_verified_profiles_without_printing_secrets(self):
        self.assertEqual(self.run_generator().returncode, 0)
        result = self.run_generator("--result-file", str(self.result))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("TestAuthToken", result.stdout)
        mac = self.profiles / "hysteria2-192-0-2-2-udp8443.yaml"
        mobile = self.profiles / "sing-box-mt-192-0-2-2-udp8443.json"
        for p in (self.env, mac, mobile):
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.profiles.stat().st_mode & 0o777, 0o700)
        self.assertIn("server: 192.0.2.2:8443", mac.read_text())
        conf = json.loads(mobile.read_text())
        self.assertFalse(conf["outbounds"][0]["tls"]["insecure"])
        self.assertEqual(conf["outbounds"][0]["tls"]["certificate"], self.cert)
        self.assertEqual(conf["inbounds"][0]["type"], "tun")
        env = dict(line.split("=", 1) for line in self.env.read_text().splitlines())
        self.assertIn("pinSHA256=", env["HYSTERIA2_URL"])
        self.assertEqual(base64.b64decode(env["HYSTERIA2_SINGBOX_MT_CONFIG_BASE64"]), mobile.read_bytes())
        if shutil.which("sing-box"):
            check = subprocess.run(["sing-box", "check", "-c", str(mobile)], capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, "sing-box rejected generated iOS JSON")
        self.assertNotEqual(self.run_generator("--result-file", str(self.result)).returncode, 0)

    def test_mismatched_certificate_writes_nothing(self):
        text = re.sub(r"HY2_PINSHA256=[0-9A-F]+", "HY2_PINSHA256=" + "0" * 64, self.result.read_text())
        self.result.write_text(text)
        self.assertNotEqual(self.run_generator("--result-file", str(self.result)).returncode, 0)
        self.assertFalse(self.env.exists())
        self.assertFalse(self.profiles.exists())

    def test_existing_env_blocks_preflight(self):
        self.env.write_text("KEEP=1\n")
        self.assertNotEqual(self.run_generator().returncode, 0)
        self.assertEqual(self.env.read_text(), "KEEP=1\n")

    def test_unignored_env_in_git_repository_is_refused(self):
        subprocess.run(["git", "-C", self.tmp.name, "init", "-q"], check=True)
        isolated = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        self.assertNotEqual(self.run_generator(env=isolated).returncode, 0)
        self.assertFalse(self.env.exists())

    def test_symlink_profile_is_not_overwritten(self):
        self.profiles.mkdir()
        target = Path(self.tmp.name) / "keep"
        target.write_text("KEEP\n")
        (self.profiles / "sing-box-mt-192-0-2-2-udp8443.json").symlink_to(target)
        self.assertNotEqual(self.run_generator("--result-file", str(self.result)).returncode, 0)
        self.assertEqual(target.read_text(), "KEEP\n")
        self.assertFalse(self.env.exists())


if __name__ == "__main__":
    unittest.main()
