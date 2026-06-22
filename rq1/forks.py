import requests
import time
import json
import re
import os
import ijson
from itertools import cycle
from datetime import datetime


origins_file = "remove_manpages/all_origins_final_version.json"
tokens_file = "tokens.txt"
output_file = "forks/all_origins_forks.jsonl"
checkpoint_file = "forks/all_origins_forks.checkpoint"

BATCH_SIZE = 50
MAX_RETRIES = 5
REQUEST_TIMEOUT = 10
LAST_REQUEST_TIME = 0
MIN_DELAY = 0.3   # seconds (≈ 3 req/sec, safe)

GITHUB_API = "https://api.github.com/repos/{}"

def validate_tokens(tokens):
    for t in tokens:
        r = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {t}"}
        )
        print(t[:6], r.status_code)

def load_tokens(path):
    with open(path, "r") as f:
        tokens = [line.strip() for line in f if line.strip()]
    if not tokens:
        raise ValueError("No tokens found!")
    return tokens

tokens = load_tokens(tokens_file)
token_cycle = cycle(tokens)

# rate limit reset tracking
token_reset_times = {token: 0 for token in tokens}

validate_tokens(tokens)

processed_origins = set()
if os.path.exists(checkpoint_file):
    print("[CHECKPOINT] Loading checkpoint...")
    with open(checkpoint_file, "r") as f:
        for line in f:
            processed_origins.add(line.strip())

# cache repos (VERY IMPORTANT optimization)
repo_cache = {}


def extract_github_repo(origin_url):
    patterns = [
        r"github\.com[:/](.+?/.+?)(?:\.git)?$",
    ]
    for p in patterns:
        m = re.search(p, origin_url)
        if m:
            return m.group(1)
    return None


def get_next_token():
    while True:
        now = time.time()

        # try every token once
        for _ in range(len(tokens)):
            token = next(token_cycle)

            if now >= token_reset_times[token]:
                return token

        # all exhausted
        next_reset = min(token_reset_times.values())
        sleep_time = max(0, next_reset - now) + 1

        print(f"[WAIT] All tokens exhausted. Sleeping {sleep_time:.1f}s...")
        time.sleep(sleep_time)


def github_request(repo):
    # cache hit
    if repo in repo_cache:
        return repo_cache[repo]

    for attempt in range(MAX_RETRIES):
        token = get_next_token()
        headers = {"Authorization": f"token {token}"}

        try:

            global LAST_REQUEST_TIME

            now = time.time()
            elapsed = now - LAST_REQUEST_TIME

            if elapsed < MIN_DELAY:
                time.sleep(MIN_DELAY - elapsed)

            response = requests.get(
                GITHUB_API.format(repo),
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )

            LAST_REQUEST_TIME = time.time()

            if response.status_code == 200:
                data = response.json()
                repo_cache[repo] = data
                return data

            elif response.status_code == 404:
                repo_cache[repo] = None
                return None

            elif response.status_code == 401:
                print(f"[401] Invalid/expired token detected: {token[:6]}... rotating")

                # temporarily disable this token for a while
                token_reset_times[token] = time.time() + 300

                continue

            elif response.status_code == 403:
                text = response.text.lower()

                
                if "rate limit" in text:
                    reset_time = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
                    token_reset_times[token] = reset_time
                    print(f"[RATE LIMIT] until {datetime.fromtimestamp(reset_time)}")
                    continue

                
                elif "abuse" in text:
                    print(f"[ABUSE LIMIT] backing off for {repo}")
                    time.sleep(30)
                    return None   

                
                elif "blocked" in text:
                    print(f"[BLOCKED] {repo} (TOS)")
                    return None 

            
                else:
                    print(f"[403 UNKNOWN] {repo}")
                    print(response.text[:200])
                    return None 
            else:
                print(f"[WARN] Status {response.status_code} for {repo}")
                time.sleep(2)

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] {e}")
            time.sleep(5)

    print(f"[FAILED] Giving up on {repo}")
    repo_cache[repo] = None
    return None



processed_count = 0
fork_count = 0
non_fork_count = 0

batch = []

def flush_batch():
    if not batch:
        return
    with open(output_file, "a") as f:
        for record in batch:
            f.write(json.dumps(record) + "\n")
    batch.clear()



with open(origins_file, "r") as f:
    parser = ijson.items(f, "item")

    for obj in parser:
        origin_url = obj.get("origin")

        if not origin_url:
            continue

        live = obj.get("metadata", {}).get("live", True)

        if not live:
            continue

        if origin_url in processed_origins:
            continue

        repo = extract_github_repo(origin_url)

        is_fork = None
        parent = None

        if repo:
            data = github_request(repo)

            if data:
                is_fork = data.get("fork", False)

                if is_fork:
                    fork_count += 1
                    parent_info = data.get("parent", {})
                    parent = {
                        "full_name": parent_info.get("full_name"),
                        "html_url": parent_info.get("html_url"),
                    }
                else:
                    non_fork_count += 1

        # add fields
        obj["is_fork"] = is_fork
        obj["parent"] = parent

        batch.append(obj)
        processed_origins.add(origin_url)

        # checkpoint immediately
        with open(checkpoint_file, "a") as cf:
            cf.write(origin_url + "\n")

        processed_count += 1

        if processed_count % 10 == 0:
            print(f"[PROGRESS] {processed_count} processed")

        # batch flush
        if len(batch) >= BATCH_SIZE:
            flush_batch()

# final flush
flush_batch()



print(f"Processed: {processed_count}")
print(f"Forks: {fork_count}")
print(f"Not forks: {non_fork_count}")