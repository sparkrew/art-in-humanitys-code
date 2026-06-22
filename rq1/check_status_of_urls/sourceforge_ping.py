#!/usr/bin/env python3
"""Extract SourceForge origins from the large origins dump, transform them into
canonical SourceForge project URLs, and HTTP-ping each to record online/offline."""

import json
import re
import os
import sys
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_FILE = os.path.join(HERE, "all_origins_final_version.json")
SOURCEFORGE_JSON = os.path.join(HERE, "sourceforge.json")
PING_RESULTS_JSON = os.path.join(HERE, "sourceforge_ping_results.json")

ORIGIN_RE = re.compile(r'"origin":\s*"(https://git\.code\.sf\.net/p/[^"]+)"')

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
TIMEOUT = 20


def transform(origin):
    """git.code.sf.net/p/<project>/<repo> -> sourceforge.net/projects/<project>/"""
    url = origin.replace("git.code.sf.net/p", "sourceforge.net/projects")
    # Drop the trailing repository segment, keep canonical project page.
    url = url.rstrip("/")
    url = url.rsplit("/", 1)[0]
    return url + "/"


def extract_origins():
    """Stream the line-delimited dump and pull out sourceforge origins (ordered, unique)."""
    seen = set()
    entries = []
    with open(SOURCE_FILE, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "git.code.sf.net/p" not in line:
                continue
            for origin in ORIGIN_RE.findall(line):
                if origin in seen:
                    continue
                seen.add(origin)
                entries.append({"origin": origin, "public_url": transform(origin)})
    return entries


def ping(url, user_agent=USER_AGENT):
    """Simple HTTP GET ping. Returns (status_code_or_None, online_bool)."""
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.status < 400
    except urllib.error.HTTPError as e:
        return e.code, e.code < 400
    except Exception:  # network/url failures => offline
        return None, False


def repo_liveness(origin):
    """Authoritative liveness check via the git smart-HTTP endpoint.

    sourceforge.net project pages sit behind a Cloudflare JS challenge that
    returns 403 for every automated request (live or dead alike), so it cannot
    tell us if a project exists. The git.code.sf.net info/refs endpoint is not
    challenge-protected and returns 200 for a live repo, 404 for a missing one.
    """
    refs_url = origin.rstrip("/") + "/info/refs?service=git-upload-pack"
    req = urllib.request.Request(
        refs_url, method="GET", headers={"User-Agent": "git/2.39.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.status == 200
    except urllib.error.HTTPError as e:
        return e.code, False
    except Exception:
        return None, False


def main():
    print(f"Extracting sourceforge origins from {SOURCE_FILE} ...")
    entries = extract_origins()
    print(f"Found {len(entries)} sourceforge origins.")

    with open(SOURCEFORGE_JSON, "w", encoding="utf-8") as fh:
        json.dump(entries, fh, indent=2, ensure_ascii=False)
    print(f"Wrote {SOURCEFORGE_JSON}")

    print("\nPinging transformed URLs (and verifying repo liveness) ...")
    results = []
    online = 0
    blocked = 0
    for i, entry in enumerate(entries, 1):
        url = entry["public_url"]
        # 1) Ping the transformed public_url as requested.
        pub_status, _ = ping(url)
        if pub_status == 403:
            blocked += 1
        # 2) Authoritative liveness via the non-challenged git endpoint.
        repo_status, is_online = repo_liveness(entry["origin"])
        online += 1 if is_online else 0
        state = "online" if is_online else "offline"
        print(
            f"[{i:3}/{len(entries)}] {state:7} "
            f"(public_url:{pub_status} repo:{repo_status}) {url}"
        )
        results.append(
            {
                "origin": entry["origin"],
                "public_url": url,
                "public_url_status": pub_status,
                "repo_status": repo_status,
                "online": is_online,
            }
        )

    with open(PING_RESULTS_JSON, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    offline = len(entries) - online
    print(f"\nWrote {PING_RESULTS_JSON}")
    print(f"Summary: {online} online, {offline} offline, {len(entries)} total.")
    print(
        f"Note: {blocked}/{len(entries)} public_url pings returned 403 "
        "(Cloudflare bot challenge on sourceforge.net project pages). "
        "online/offline is determined by the git info/refs endpoint."
    )


if __name__ == "__main__":
    main()
