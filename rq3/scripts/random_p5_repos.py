import json
import random
from urllib.parse import urlparse

INPUT_FILE = "/spark/output_results_deduplicated_no_none.json"
OUTPUT_FILE = "selected_origins_p5.txt"
TARGET_FILENAME = "p5.js"
# TARGET_SAMPLE_SIZE = 1000  # Target number of samples

# Uncomment the line below to use a fixed percentage instead of targeting a sample size
FIXED_PERCENTAGE = 1  # Use 1% of total repositories


def is_github_url(url):
    """
    Check if a URL is from github.com
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower() in ("github.com", "www.github.com")
    except Exception:
        return False


def extract_github_username(origin_url):
    """
    Extract GitHub username from a URL like:
    https://github.com/username/repo
    """
    try:
        path_parts = urlparse(origin_url).path.strip("/").split("/")
        if len(path_parts) >= 2:
            return path_parts[0]
    except Exception:
        pass
    return None


# Load JSON array
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

filtered = []

for obj in data:
    # Handle metadata == None
    metadata = obj.get("metadata")
    if not isinstance(metadata, dict):
        continue

    # Only select "live": true entries
    if metadata.get("live") != True:
        continue

    matched_files = metadata.get("matched_files")

    # Handle matched_files == None or not a list
    if not isinstance(matched_files, list):
        continue

    if any(
        isinstance(f, dict) and f.get("file_name") == TARGET_FILENAME
        for f in matched_files
    ):
        origin = obj.get("origin")
        if not isinstance(origin, str):
            continue

        # Filter for GitHub URLs only
        if not is_github_url(origin):
            continue

        username = extract_github_username(origin)
        if username:
            filtered.append((username, origin))

# Total count of all live GitHub repos with p5.js
total_all_repos = len(filtered)

# Calculate target sample size based on percentage or fixed target
if 'FIXED_PERCENTAGE' in globals():
    target_sample = int(total_all_repos * (FIXED_PERCENTAGE / 100.0))
    print(f"Using fixed percentage: {FIXED_PERCENTAGE}%")
# else:
#     target_sample = TARGET_SAMPLE_SIZE
#     print(f"Using target sample size: {TARGET_SAMPLE_SIZE}")

# Now select repositories ensuring unique GitHub usernames
selected_origins = []
seen_usernames = set()

# Shuffle to randomize selection
random.shuffle(filtered)

for username, origin in filtered:
    if username not in seen_usernames:
        selected_origins.append(origin)
        seen_usernames.add(username)
        
        # Stop when we reach target sample size
        if len(selected_origins) >= target_sample:
            break

# Write line-separated output
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    for origin in selected_origins:
        f.write(origin + "\n")

print(f"Total live GitHub repos with {TARGET_FILENAME}: {total_all_repos}")
print(f"Target sample from percentage/size: {target_sample}")
print(f"Unique GitHub users selected: {len(selected_origins)}")
print(f"Wrote {len(selected_origins)} origins to {OUTPUT_FILE}")
