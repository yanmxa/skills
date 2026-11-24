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


DIRECT_DOMAINS = (
    # WeChat, Tencent, and payment/CDN domains used by WeChat.
    "qq.com", "wechat.com", "wechatpay.cn", "weixin.com", "weixinbridge.com",
    "servicewechat.com", "qpic.cn", "qlogo.cn", "gtimg.com", "tenpay.com",
    # Search and maps.
    "baidu.com", "bdstatic.com", "bdimg.com", "amap.com", "autonavi.com",
    # Shopping, payments, and local services.
    "taobao.com", "tmall.com", "alipay.com", "alipayobjects.com", "alicdn.com",
    "jd.com", "jdstatic.com", "360buyimg.com", "pinduoduo.com", "yangkeduo.com",
    "meituan.com", "meituan.net", "dianping.com",
    # Social, news, and video.
    "douyin.com", "douyincdn.com", "douyinpic.com", "bilibili.com", "bilivideo.com",
    "hdslb.com", "xiaohongshu.com", "xhscdn.com", "weibo.com", "sina.com.cn",
    "sinaimg.cn", "zhihu.com", "zhimg.com", "163.com", "126.com", "netease.com",
    "iqiyi.com", "qiyi.com", "youku.com", "ykimg.com",
)


def destinations(host, port, env_file, profiles_dir):
    slug = f"{host.replace('.', '-').replace(':', '-')}-udp{port}"
    return (env_file, profiles_dir / f"hysteria2-{slug}.yaml",
            profiles_dir / f"clash-mi-{slug}.yaml")


def preflight(paths):
    if not paths[0].parent.is_dir():
        raise ValueError("the .env parent directory must already exist")
    for path in paths:
        if path.is_symlink() or path.exists():
            raise ValueError(f"refusing to overwrite existing path: {path}")
        if path.parent.is_symlink() or (path.parent.exists() and not path.parent.is_dir()):
            raise ValueError(f"unsafe output directory: {path.parent}")
        # Every profile contains the password, not just the dotenv output.
        directory = next(parent for parent in path.parents if parent.is_dir())
        repo = subprocess.run(["git", "-C", str(directory), "rev-parse", "--is-inside-work-tree"],
                              capture_output=True, text=True, check=False)
        if repo.returncode == 0 and repo.stdout.strip() == "true":
            ignored = subprocess.run(["git", "-C", str(directory), "check-ignore", "-q", "--", str(path)],
                                     check=False)
            if ignored.returncode != 0:
                raise ValueError(f"use a Git-ignored output path for {path.name}")


def parse_result(text, port):
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
    return fields


def build_clash_mi(host, port, sni, password, pin):
    # JSON-quoted strings are valid YAML scalars and keep numeric passwords as text.
    fingerprint = ":".join(pin[i:i + 2].upper() for i in range(0, len(pin), 2))
    china_dns = json.dumps("https://dns.alidns.com/dns-query#DIRECT")
    dns_domains = ("geosite:cn", "+.cn", *("+." + domain for domain in DIRECT_DOMAINS))
    dns_policy = "\n".join(f"    {json.dumps(domain)}: {china_dns}" for domain in dns_domains)
    direct_rules = "\n".join(f"  - DOMAIN-SUFFIX,{domain},DIRECT" for domain in DIRECT_DOMAINS)
    return f"""# Clash Mi / Mihomo. Contains a private proxy password.
mode: rule
allow-lan: false
log-level: warning

proxies:
  - name: HY2
    type: hysteria2
    server: {json.dumps(host)}
    port: {port}
    password: {json.dumps(password)}
    sni: {json.dumps(sni)}
    fingerprint: {json.dumps(fingerprint)}
    skip-cert-verify: false

# The app manages the iOS VPN tunnel. Keep resolver traffic on the matching path.
dns:
  enable: true
  enhanced-mode: fake-ip
  fake-ip-filter:
    - geosite:private
    - '+.local'
    - '+.lan'
  default-nameserver:
    - 223.5.5.5
  proxy-server-nameserver:
    - {china_dns}
  nameserver:
    - 'https://1.1.1.1/dns-query#HY2'
  direct-nameserver:
    - {china_dns}
  direct-nameserver-follow-policy: true
  nameserver-policy:
    'geosite:private': system
    '+.local': system
    '+.lan': system
{dns_policy}

rules:
{direct_rules}
  - DOMAIN-SUFFIX,local,DIRECT
  - DOMAIN-SUFFIX,lan,DIRECT
  - DOMAIN-SUFFIX,cn,DIRECT
  - GEOSITE,private,DIRECT
  - GEOSITE,cn,DIRECT
  - IP-CIDR,10.0.0.0/8,DIRECT,no-resolve
  - IP-CIDR,127.0.0.0/8,DIRECT,no-resolve
  - IP-CIDR,169.254.0.0/16,DIRECT,no-resolve
  - IP-CIDR,172.16.0.0/12,DIRECT,no-resolve
  - IP-CIDR,192.168.0.0/16,DIRECT,no-resolve
  - IP-CIDR6,fc00::/7,DIRECT,no-resolve
  - IP-CIDR6,fe80::/10,DIRECT,no-resolve
  - GEOIP,CN,DIRECT,no-resolve
  - MATCH,HY2
"""


def build_profiles(host, port, fields, template):
    sni, password, pin = (fields[key] for key in ("HY2_SNI", "HY2_AUTH", "HY2_PINSHA256"))
    if not re.fullmatch(r"[A-Za-z0-9.-]+", sni):
        raise ValueError("invalid SNI domain")
    server = f"{host}:{port}"
    desktop = template.replace("SERVER_HOST:PORT", server).replace("YOUR_AUTH_TOKEN", password).replace("YOUR_CERT_SHA256", pin)
    desktop = re.sub(r"(?m)^(\s*sni: )bing\.com", lambda m: m.group(1) + sni, desktop)
    if any(x in desktop for x in ("SERVER_HOST:PORT", "YOUR_AUTH_TOKEN", "YOUR_CERT_SHA256")):
        raise ValueError("client template was not fully populated")
    mobile_yaml = build_clash_mi(host, port, sni, password, pin)
    uri = "hysteria2://" + quote(password, safe="") + "@" + server + "/?" + urlencode(
        {"sni": sni, "insecure": "1", "pinSHA256": pin}) + "#hy2-" + host
    env = "\n".join([
        "HYSTERIA2_SERVER=" + server,
        "HYSTERIA2_AUTH=" + password,
        "HYSTERIA2_SNI=" + sni,
        "HYSTERIA2_PIN_SHA256=" + pin,
        'HYSTERIA2_URL="' + uri + '"',
        "HYSTERIA2_CLIENT_CONFIG_BASE64=" + base64.b64encode(desktop.encode()).decode(),
        "HYSTERIA2_CLASH_MI_CONFIG_BASE64=" + base64.b64encode(mobile_yaml.encode()).decode(),
        "",
    ])
    return env, desktop, mobile_yaml


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
        fields = parse_result(text, args.port)
        template = (Path(__file__).parent / "config.yaml.template").read_text()
        contents = build_profiles(args.host, args.port, fields, template)
        save(paths, contents)
        for path in paths:
            print(f"Saved (mode 600): {path}")
    except (ValueError, OSError) as error:
        # Never include the SSH result, password, or profile body in errors.
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
