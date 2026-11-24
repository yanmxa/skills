#!/usr/bin/env python3
"""Turn an SSH deployment result into private desktop and iPhone profiles.

Never print the password or share URL. The result file is a private, short-lived
file created by deploy-hysteria2-server.sh, not a log for later inspection.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
from urllib.parse import quote, urlencode


def destinations(host, port, env_file, profiles_dir):
    slug = f"{host.replace('.', '-').replace(':', '-')}-udp{port}"
    return (env_file, profiles_dir / f"hysteria2-{slug}.yaml",
            profiles_dir / f"sing-box-mt-{slug}.json")


def preflight(paths):
    env_file, desktop, mobile = paths
    for path in paths:
        if path.is_symlink() or path.exists():
            raise ValueError(f"refusing to overwrite existing path: {path}")
        if path.parent.is_symlink() or (path.parent.exists() and not path.parent.is_dir()):
            raise ValueError(f"unsafe output directory: {path.parent}")
    if not env_file.parent.is_dir():
        raise ValueError("the .env parent directory must already exist")
    # Credentials must never accidentally be added to a Git repository.
    repo = subprocess.run(["git", "-C", str(env_file.parent), "rev-parse", "--is-inside-work-tree"],
                          capture_output=True, text=True, check=False)
    if repo.returncode == 0 and repo.stdout.strip() == "true":
        ignored = subprocess.run(["git", "-C", str(env_file.parent), "check-ignore", "-q", str(env_file)],
                                 check=False)
        if ignored.returncode != 0:
            raise ValueError(f"add {env_file.name} to .gitignore before writing credentials")
    return desktop, mobile


def parse_result(text, host, port):
    match = re.search(r"^==== RESULT ====$([\s\S]*?)^==== DONE ====$", text, re.M)
    if not match:
        raise ValueError("missing complete server result block (server may need manual inspection)")
    fields = dict(re.findall(r"^(HY2_[A-Z0-9_]+)=(.*)$", match.group(1), re.M))
    required = {"HY2_PORT", "HY2_SNI", "HY2_AUTH", "HY2_PINSHA256", "HY2_CERT_BASE64"}
    if not required <= fields.keys() or fields["HY2_PORT"] != str(port):
        raise ValueError("incomplete result or unexpected server port")
    if not re.fullmatch(r"[A-Za-z0-9]{16,64}", fields["HY2_AUTH"]):
        raise ValueError("invalid password returned by server")
    if not re.fullmatch(r"[0-9A-Fa-f]{64}", fields["HY2_PINSHA256"]):
        raise ValueError("invalid certificate fingerprint")
    cert = base64.b64decode(fields["HY2_CERT_BASE64"], validate=True).decode("ascii")
    der = ssl.PEM_cert_to_DER_cert(cert)
    if hashlib.sha256(der).hexdigest().casefold() != fields["HY2_PINSHA256"].casefold():
        raise ValueError("server certificate does not match its reported fingerprint")
    return fields, cert


def build_profiles(host, port, fields, cert, template):
    sni, password, pin = (fields[key] for key in ("HY2_SNI", "HY2_AUTH", "HY2_PINSHA256"))
    if not re.fullmatch(r"[A-Za-z0-9.-]+", sni):
        raise ValueError("invalid SNI domain")
    server = f"{host}:{port}"
    desktop = template.replace("SERVER_HOST:PORT", server).replace("YOUR_AUTH_TOKEN", password).replace("YOUR_CERT_SHA256", pin)
    desktop = re.sub(r"(?m)^(\s*sni: )bing\.com", lambda m: m.group(1) + sni, desktop)
    if any(x in desktop for x in ("SERVER_HOST:PORT", "YOUR_AUTH_TOKEN", "YOUR_CERT_SHA256")):
        raise ValueError("client template was not fully populated")
    # Mobile: trust the actual server certificate, instead of relying on a
    # third-party URI importer to preserve pinSHA256 or enabling insecure TLS.
    tag = "hy2-" + host.replace(".", "-")
    mobile = {
        "log": {"level": "warn"},
        "dns": {"servers": [{"type": "tls", "tag": "remote", "server": "1.1.1.1", "detour": tag}],
                "final": "remote", "strategy": "ipv4_only"},
        "inbounds": [{"type": "tun", "tag": "tun-in", "address": ["172.19.0.1/30"],
                      "auto_route": True, "strict_route": True}],
        "outbounds": [{"type": "hysteria2", "tag": tag, "server": host, "server_port": port,
                       "password": password,
                       "tls": {"enabled": True, "server_name": sni, "insecure": False,
                               "certificate": cert}},
                      {"type": "direct", "tag": "direct"}],
        "route": {"rules": [{"action": "sniff"}, {"protocol": "dns", "action": "hijack-dns"}],
                  "final": tag, "auto_detect_interface": True},
    }
    mobile_json = json.dumps(mobile, ensure_ascii=False, indent=2) + "\n"
    uri = "hysteria2://" + quote(password, safe="") + "@" + server + "/?" + urlencode(
        {"sni": sni, "insecure": "1", "pinSHA256": pin}) + "#hy2-" + host
    env = "\n".join([
        "HYSTERIA2_SERVER=" + server,
        "HYSTERIA2_AUTH=" + password,
        "HYSTERIA2_SNI=" + sni,
        "HYSTERIA2_PIN_SHA256=" + pin,
        'HYSTERIA2_URL="' + uri + '"',
        "HYSTERIA2_CLIENT_CONFIG_BASE64=" + base64.b64encode(desktop.encode()).decode(),
        "HYSTERIA2_SINGBOX_MT_CONFIG_BASE64=" + base64.b64encode(mobile_json.encode()).decode(),
        "",
    ])
    return env, desktop, mobile_json


def save(paths, contents):
    created = []
    try:
        profiles = paths[1].parent
        if not profiles.exists():
            profiles.mkdir(parents=True, mode=0o700)
        for path, content in zip(paths, contents):
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(path, flags, 0o600)
            created.append(path)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
    except BaseException:
        for path in created:
            path.unlink()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--env-file", type=Path, required=True, help="new, Git-ignored .env FILE (not a directory)")
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--result-file", type=Path, help="private SSH result file; omitted for preflight")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9.-]+", args.host) or not 1 <= args.port <= 65535:
        parser.error("invalid host or UDP port")
    paths = destinations(args.host, args.port, args.env_file.absolute(), args.profiles_dir.expanduser().absolute())
    try:
        preflight(paths)
        if args.result_file is None:
            print("Output paths are available and the .env file is Git-ignored.")
            return
        text = args.result_file.read_text(encoding="utf-8")
        fields, cert = parse_result(text, args.host, args.port)
        template = (Path(__file__).parent / "config.yaml.template").read_text()
        contents = build_profiles(args.host, args.port, fields, cert, template)
        save(paths, contents)
        for path in paths:
            print(f"Saved (mode 600): {path}")
    except (ValueError, OSError) as error:
        # Never include the SSH result, password, or profile body in errors.
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
