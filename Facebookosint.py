#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CYBER OSINT X
=============
Advanced OSINT & Network Security Toolkit
Platforms : Android Termux / Pydroid 3 / Linux / Windows
Python    : 3.7+

Ethics & legality:
  - Only queries PUBLIC data sources.
  - Network stress tests default to loopback and require the user to
    confirm ownership/authorization of the target host.
  - Never fabricates results: if data is unavailable, it reports that.
"""

import os
import re
import json
import ssl
import time
import socket
import string
import random
import datetime
import ipaddress
import subprocess
import sys
import threading
from urllib.parse import urlparse

# ----------------------------------------------------------------------------
# BOOTSTRAP: automatic dependency installation (Termux / Pydroid friendly)
# ----------------------------------------------------------------------------
REQUIRED = {"requests": "requests", "phonenumbers": "phonenumbers"}

def ensure_deps():
    missing = []
    for mod, pkg in REQUIRED.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("[*] Installing missing dependencies:", ", ".join(missing))
        for pkg in missing:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            except Exception as e:
                print(f"[!] Could not install {pkg}: {e}")
                print("    On Termux:  pkg install python && pip install " + pkg)
                print("    On Pydroid: Menu -> Pip -> install " + pkg)
                sys.exit(1)

ensure_deps()

import requests
import phonenumbers
from phonenumbers import carrier as pncarrier
from phonenumbers import geocoder, timezone as pntz

# ----------------------------------------------------------------------------
# TERMINAL UI — red/black hacker theme
# ----------------------------------------------------------------------------
class UI:
    R  = "\033[91m"   # bright red
    D  = "\033[31m"   # dark red
    K  = "\033[90m"   # grey
    W  = "\033[97m"   # white
    Y  = "\033[93m"
    G  = "\033[92m"
    C  = "\033[96m"
    B  = "\033[0m"    # reset
    BG = "\033[41m"   # red background

    @staticmethod
    def _banner_lines():
        return [
            r"  ██████╗██╗   ██╗██████╗ ███████╗██████╗     ██████╗ ███████╗",
            r" ██╔════╝╚██╗ ██╔╝██╔══██╗██╔════╝██╔══██╗    ██╔══██╗██╔════╝",
            r" ██║      ╚████╔╝ ██████╔╝█████╗  ██████╔╝    ██████╔╝███████╗",
            r" ██║       ╚██╔╝  ██╔══██╗██╔══╝  ██╔══██╗    ██╔══██╗╚════██║",
            r" ╚██████╗   ██║   ██████╔╝███████╗██║  ██║    ██████╔╝███████║",
            r"  ╚═════╝   ╚═╝   ╚═════╝ ╚══════╝╚═╝  ╚═╝    ╚═════╝ ╚══════╝",
        ]

    @classmethod
    def banner(cls):
        os.system("cls" if os.name == "nt" else "clear")
        try:
            cols = os.get_terminal_size().columns
        except Exception:
            cols = 80
        print()
        for line in cls._banner_lines():
            print(cls.R + line.center(cols) + cls.B)
            time.sleep(0.05)
        print((cls.K + "  =" * 38 + cls.B).center(cols))
        print(cls.D + "  OSINT & NETWORK SECURITY TOOLKIT v1.0".center(cols) + cls.B)
        print(cls.K + "  public data only | no fabrication | authorized testing".center(cols) + cls.B)
        print()

    @staticmethod
    def loading(text="Loading", n=14, delay=0.03):
        for _ in range(n):
            for ch in r"|/-\\":
                sys.stdout.write(f"\r{UI.R}[{ch}]{UI.B} {text}...")
                sys.stdout.flush()
                time.sleep(delay)
        sys.stdout.write("\r" + " " * (len(text) + 16) + "\r")

    @staticmethod
    def progress(label, total, delay=0.01):
        width = 30
        for i in range(total + 1):
            pct = int(i / total * 100) if total else 100
            bar = "█" * int(width * i / total if total else width)
            sys.stdout.write(f"\r{UI.Y}{label}{UI.B} [{UI.R}{bar.ljust(width, '░')}{UI.B}] {pct:3d}%")
            sys.stdout.flush()
            time.sleep(delay)
        print()

    @staticmethod
    def title(text):
        print(f"\n{UI.BG}{UI.W} {text} {UI.B}\n")

    @staticmethod
    def ok(msg):    print(f"  {UI.G}[+]{UI.B} {msg}")
    @staticmethod
    def warn(msg): print(f"  {UI.Y}[!]{UI.B} {msg}")
    @staticmethod
    def err(msg):  print(f"  {UI.R}[x]{UI.B} {msg}")
    @staticmethod
    def info(msg): print(f"  {UI.C}[i]{UI.B} {msg}")
    @staticmethod
    def kv(k, v):  print(f"  {UI.D}{k:<26}{UI.B} {UI.W}{v}{UI.B}")

    @staticmethod
    def menu(options):
        for i, (name, _) in enumerate(options, 1):
            print(f"  {UI.R}[{i}]{UI.B} {UI.W}{name}{UI.B}")
        print(f"  {UI.R}[0]{UI.B} {UI.W}Exit{UI.B}")
        return input(f"\n  {UI.Y}choice>{UI.B} ").strip()

# ----------------------------------------------------------------------------
# REPORT SYSTEM — timestamped TXT/JSON export
# ----------------------------------------------------------------------------
class Report:
    DIR = "reports"

    @classmethod
    def save(cls, title, data: dict, as_json=True):
        os.makedirs(cls.DIR, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base = os.path.join(cls.DIR, f"{ts}_{re.sub(r'[^a-zA-Z0-9_-]', '_', title)}")
        lines = [f"CYBER OSINT X REPORT — {title}",
                 f"Generated: {datetime.datetime.now().isoformat()}",
                 "Sources: public data only; unavailable items marked.",
                 "=" * 60, ""]
        for k, v in data.items():
            lines.append(f"{k}:")
            if isinstance(v, dict):
                for kk, vv in v.items():
                    lines.append(f"  {kk}: {vv}")
            elif isinstance(v, list):
                for item in v:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"  {v}")
            lines.append("")
        txt_path = base + ".txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        UI.ok(f"Saved TXT report: {txt_path}")
        if as_json:
            json_path = base + ".json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({"title": title, "generated": datetime.datetime.now().isoformat(),
                           "data": data}, f, indent=2, default=str)
            UI.ok(f"Saved JSON report: {json_path}")

# ----------------------------------------------------------------------------
# MODULE 1 — WHATSAPP NUMBER INTELLIGENCE
# ----------------------------------------------------------------------------
class PhoneIntel:
    """International number intelligence via the 'phonenumbers' library
    (Google libphonenumber metadata). All data is static metadata, not
    live subscriber data. A live carrier/reputation lookup would require
    a keyed paid API, so those fields are reported as unavailable."""

    @classmethod
    def run(cls):
        UI.title("MODULE 1 — WHATSAPP NUMBER INTELLIGENCE")
        UI.info("Enter number in full international format, e.g. +14155552671")
        raw = input("  number> ").strip()
        if not raw:
            return
        try:
            num = phonenumbers.parse(raw, None)
        except phonenumbers.NumberParseException as e:
            UI.err(f"Parse failed: {e}")
            return

        if not phonenumbers.is_valid_number(num):
            UI.err("Not a valid number under E.164 / libphonenumber rules.")
            return

        UI.progress("Analyzing", 20)
        data = {
            "input": raw,
            "valid": True,
            "possible": phonenumbers.is_possible_number(num),
            "e164": phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164),
            "international": phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            "national": phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.NATIONAL),
            "country_code": num.country_code,
            "country": ", ".join(pntz.time_zones_for_number(num)) or "unknown",
            "region": geocoder.description_for_number(num, "en") or "unknown",
            "carrier_metadata": pncarrier.name_for_number(num, "en") or "unavailable (static metadata only)",
            "type": str(phonenumbers.number_type(num)).split(".")[-1],
        }
        data["in_whatsapp"] = "cannot be determined without WhatsApp's systems"

        UI.title("RESULT")
        for k, v in data.items():
            UI.kv(k, str(v))
        UI.warn("'carrier_metadata' is static libphonenumber metadata; actual live "
                "carrier assignment requires a keyed API and is omitted.")
        if input(f"  {UI.Y}Save report? [y/N]{UI.B} ").lower() == "y":
            Report.save(f"phone_{data['e164']}", data)

# ----------------------------------------------------------------------------
# MODULE 2 — FACEBOOK PROFILE INVESTIGATOR (public data only)
# ----------------------------------------------------------------------------
class FacebookOSINT:
    """Extracts what is publicly retrievable: URL validation, username,
    and OpenGraph metadata served in the anonymous HTML response.
    Facebook aggressively blocks bots and hides content from logged-out
    visitors — when that happens this module says so instead of guessing."""

    UA = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36")

    @staticmethod
    def parse(url):
        u = urlparse(url.strip() if "//" in url else "https://" + url.strip())
        if "facebook.com" not in (u.netloc or ""):
            return None, None
        path = u.path.strip("/").split("?")[0].split("/")[0]
        if path in ("profile.php",):
            q = dict(pair.split("=", 1) for pair in u.query.split("&") if "=" in pair)
            uid = q.get("id")
            return url.strip(), (f"profile_id:{uid}" if uid else None)
        return url.strip(), path or None

    @classmethod
    def run(cls):
        UI.title("MODULE 2 — FACEBOOK PROFILE INVESTIGATOR")
        raw = input("  profile URL> ").strip()
        url, ident = cls.parse(raw)
        if not url:
            UI.err("Not a facebook.com URL.")
            return
        UI.kv("Input URL", url)
        UI.kv("Public identifier", ident or "unavailable")

        UI.loading("Requesting public page")
        data = {"url": url, "identifier": ident or "unavailable"}
        try:
            r = requests.get(url, headers={"User-Agent": cls.UA, "Accept-Language": "en-US,en"},
                             timeout=20, allow_redirects=True)
            data["http_status"] = r.status_code
            data["final_url"] = r.url
            og = {}
            for m in re.finditer(r'<meta[^>]+property="og:([a-z_]+)"[^>]+content="([^"]*)"', r.text):
                og[m.group(1)] = m.group(2)
            data["public_metadata"] = og or "none exposed to anonymous visitors"
            if r.status_code in (301, 302) or "login" in r.url.lower():
                data["access"] = "redirected to login — no public data exposed"
            elif not og:
                data["access"] = "page fetched but exposes no public metadata to anonymous visitors"
        except requests.RequestException as e:
            data["http_status"] = "request failed"
            data["error"] = str(e)

        UI.title("RESULT")
        UI.kv("HTTP status", str(data.get("http_status")))
        if isinstance(data.get("public_metadata"), dict):
            for k, v in data["public_metadata"].items():
                UI.kv("og:" + k, v)
        else:
            UI.warn(str(data.get("public_metadata", data.get("error", "no data"))))
        UI.warn("Posts, friends, private activity: NOT accessible — Facebook gates "
                "these behind authentication; this toolkit will not bypass that.")
        if input(f"  {UI.Y}Save report? [y/N]{UI.B} ").lower() == "y":
            Report.save(f"fb_{ident or 'profile'}", data)

# ----------------------------------------------------------------------------
# MODULE 3 — NETWORK STRESS TESTING (own infrastructure only)
# ----------------------------------------------------------------------------
class StressTest:
    """Authorized load diagnostics: a bounded, rate-limited TCP connection
    tester (half-open connection count / handshake latency measurement)
    for measuring how your own server behaves under connection load.
    Default target is loopback. Not a DDoS tool; no spoofing, no
    amplification, no third-party targets."""

    @staticmethod
    def confirm(host):
        print(f"  {UI.Y}Target: {host}{UI.B}")
        a = input(f"  {UI.Y}Confirm you own/are authorized to test this host [yes/NO]{UI.B}: ").strip().lower()
        return a == "yes"

    @classmethod
    def run(cls):
        UI.title("MODULE 3 — NETWORK STRESS TESTING (AUTHORIZED ONLY)")
        host = input(f"  {UI.Y}Host (Enter = 127.0.0.1){UI.B}: ").strip() or "127.0.0.1"
        try:
            ip = socket.gethostbyname(host)
        except socket.gaierror:
            UI.err("DNS resolution failed.")
            return
        UI.kv("Resolved IP", ip)
        if ipaddress.ip_address(ip).is_loopback is False and not cls.confirm(host):
            UI.err("Authorization not confirmed. Aborting.")
            return

        try:
            port = int(input(f"  {UI.Y}Port [80]{UI.B}: ").strip() or 80)
            conns = int(input(f"  {UI.Y}Max concurrent connections [50]{UI.B}: ").strip() or 50)
            rounds = int(input(f"  {UI.Y}Test rounds [3]{UI.B}: ").strip() or 3)
        except ValueError:
            UI.err("Invalid number.")
            return
        conns = max(1, min(conns, 500)); rounds = max(1, min(rounds, 20))

        latencies, errors, lock = [], [], threading.Lock()
        def worker():
            try:
                t0 = time.time()
                s = socket.create_connection((ip, port), timeout=5)
                s.close()
                with lock: latencies.append((time.time() - t0) * 1000)
            except Exception as e:
                with lock: errors.append(str(e))

        UI.progress("Stress testing", rounds)
        for r in range(rounds):
            threads = [threading.Thread(target=worker) for _ in range(conns)]
            t0 = time.time()
            for t in threads: t.start()
            for t in threads: t.join()
            UI.info(f"Round {r+1}/{rounds}: {conns} conns in {time.time()-t0:.2f}s")
            time.sleep(1)

        if latencies:
            lat = sorted(latencies)
            UI.kv("Handshakes OK", str(len(lat)))
            UI.kv("Min / Avg / Max ms",
                  f"{lat[0]:.1f} / {sum(lat)/len(lat):.1f} / {lat[-1]:.1f}")
        if errors:
            UI.warn(f"{len(errors)} connection errors (server under load or refused): "
                    f"{errors[0]}{' ...' if len(errors) > 1 else ''}")
        data = {"target": f"{host} ({ip}:{port})", "rounds": rounds,
                "conns_per_round": conns, "successful": len(latencies),
                "errors": len(errors),
                "latency_ms": {"min": lat[0], "avg": sum(lat)/len(lat), "max": lat[-1]} if latencies else "none"}
        if input(f"  {UI.Y}Save report? [y/N]{UI.B} ").lower() == "y":
            Report.save(f"stress_{host}_{port}", data)

# ----------------------------------------------------------------------------
# MODULE 4 — SECURITY UTILITIES
# ----------------------------------------------------------------------------
class SecUtils:
    UA = "Mozilla/5.0 (compatible; CyberOsintX/1.0)"
    SEC_HEADERS = ["strict-transport-security", "content-security-policy",
                   "x-content-type-options", "x-frame-options",
                   "referrer-policy", "permissions-policy"]

    @classmethod
    def domain_ip(cls):
        UI.title("DOMAIN / IP INTELLIGENCE")
        target = input("  domain or IP> ").strip()
        try:
            ip = socket.gethostbyname(target)
        except socket.gaierror:
            ip = target if cls._is_ip(target) else None
        if not ip:
            UI.err("Unresolvable host."); return
        UI.kv("Resolved IP", ip)
        try:
            r = requests.get(f"http://ip-api.com/json/{ip}", timeout=15)
            j = r.json()
            for k in ("country", "city", "isp", "org", "as", "reverse", "timezone"):
                if j.get(k): UI.kv(k, str(j[k]))
            data = {"ip": ip, "geo_isp": j}
        except Exception as e:
            UI.warn(f"ip-api lookup failed: {e}")
            data = {"ip": ip}
        try:
            r = requests.get(f"https://rdap.org/ip/{ip}", timeout=15,
                             headers={"User-Agent": cls.UA})
            if r.status_code == 200:
                j = r.json()
                data["rdap_netname"] = j.get("name", "unavailable")
                UI.kv("RDAP netname", data["rdap_netname"])
        except Exception:
            UI.warn("RDAP lookup failed.")
        Report.save(f"domain_{target}", data) if input(f"  {UI.Y}Save? [y/N]{UI.B} ").lower() == "y" else None

    @staticmethod
    def _is_ip(s):
        try: ipaddress.ip_address(s); return True
        except ValueError: return False

    @classmethod
    def dns_records(cls):
        UI.title("DNS RECORD LOOKUP (via DNS-over-HTTPS)")
        domain = input("  domain> ").strip()
        data = {}
        for rtype in ("A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"):
            try:
                r = requests.get(f"https://dns.google/resolve?name={domain}&type={rtype}",
                                 timeout=10, headers={"User-Agent": cls.UA})
                ans = r.json().get("Answer", []) or []
                vals = [a.get("data", "") for a in ans]
                if vals:
                    data[rtype] = vals
                    UI.kv(rtype, ", ".join(vals[:5]) + (" ..." if len(vals) > 5 else ""))
            except Exception:
                pass
        if not data:
            UI.err("No records resolved.")
        if data and input(f"  {UI.Y}Save? [y/N]{UI.B} ").lower() == "y":
            Report.save(f"dns_{domain}", data)

    @classmethod
    def ssl_cert(cls):
        UI.title("SSL CERTIFICATE INSPECTION")
        host = input("  host:port [example.com:443]> ").strip() or "example.com:443"
        h, _, p = host.partition(":")
        p = p or "443"
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((h, int(p)), timeout=10) as sock:
                with ctx.wrap_socket(sock, server_hostname=h) as s:
                    cert = s.getpeercert()
            data = {"subject": dict(x[0] for x in cert["subject"]),
                    "issuer": dict(x[0] for x in cert["issuer"]),
                    "notBefore": cert["notBefore"], "notAfter": cert["notAfter"],
                    "serialNumber": cert["serialNumber"],
                    "SAN": [v for k, v in cert.get("subjectAltName", []) if k == "DNS"][:10]}
            UI.kv("Subject CN", data["subject"].get("commonName", "?"))
            UI.kv("Issuer", data["issuer"].get("organizationName", "?"))
            UI.kv("Valid until", data["notAfter"])
            UI.kv("SANs", ", ".join(data["SAN"]))
        except Exception as e:
            UI.err(f"TLS inspection failed: {e}"); data = {"error": str(e)}
        if input(f"  {UI.Y}Save? [y/N]{UI.B} ").lower() == "y":
            Report.save(f"ssl_{h}", data)

    @classmethod
    def http_headers(cls):
        UI.title("HTTP SECURITY HEADER AUDIT")
        url = input("  url> ").strip()
        if "//" not in url: url = "https://" + url
        try:
            r = requests.get(url, headers={"User-Agent": cls.UA}, timeout=15,
                             allow_redirects=True)
        except requests.RequestException as e:
            UI.err(f"Request failed: {e}"); return
        UI.kv("Status", f"{r.status_code} at {r.url}")
        low = {k.lower(): v for k, v in r.headers.items()}
        data = {"url": url, "status": r.status_code, "headers": dict(low)}
        for h in cls.SEC_HEADERS:
            if h in low: UI.ok(f"{h}: {low[h][:60]}")
            else:        UI.err(f"{h}: MISSING")
        if "server" in low: UI.kv("server", low["server"])
        if input(f"  {UI.Y}Save? [y/N]{UI.B} ").lower() == "y":
            Report.save(f"headers_{urlparse(url).netloc}", data)

# ----------------------------------------------------------------------------
# MODULE 5/6 — MAIN MENU
# ----------------------------------------------------------------------------
def main():
    UI.banner()
    while True:
        UI.title("MAIN MENU")
        opts = [
            ("WhatsApp Number Intelligence",        PhoneIntel.run),
            ("Facebook Profile Investigator (public data)", FacebookOSINT.run),
            ("Network Stress Testing (own infra)",  StressTest.run),
            ("Domain / IP Intelligence",            SecUtils.domain_ip),
            ("DNS Record Lookup",                   SecUtils.dns_records),
            ("SSL Certificate Inspection",          SecUtils.ssl_cert),
            ("HTTP Security Header Audit",          SecUtils.http_headers),
        ]
        try:
            c = UI.menu(opts)
        except (KeyboardInterrupt, EOFError):
            print("\n"); break
        if c == "0" or not c:
            print(UI.R + "  Stay ethical. Goodbye." + UI.B); break
        try:
            if c.isdigit() and 1 <= int(c) <= len(opts):
                opts[int(c) - 1][1]()
            else:
                UI.err("Invalid choice.")
        except KeyboardInterrupt:
            UI.warn("Interrupted.")
        except Exception as e:
            UI.err(f"Unhandled error: {e}")
        input(f"\n  {UI.K}press Enter to continue...{UI.B}")
        UI.banner()

if __name__ == "__main__":
    main()
