import json
from collections import defaultdict
from urllib.parse import urlparse

INPUT_FILE = "/all_origins.json"
OUTPUT_FILE = "/duplicate_origins.json"


def normalize_origin(origin: str) -> str:
    """
    Ignore protocol differences (http, https, git, etc.)
    Remove 'git://' prefix
    Remove '.git' suffix
    """

    if "://" in origin:
        origin = origin.split("://", 1)[1]

    if origin.endswith(".git"):
        origin = origin[:-4]

    return origin.lower().strip()


def find_duplicates():
    with open(INPUT_FILE, "r") as f:
        data = json.load(f)

    counts = defaultdict(int)
    original_map = defaultdict(list)

    for record in data:
        origin = record.get("origin", "").strip()
        if not origin:
            continue

        norm = normalize_origin(origin)
        counts[norm] += 1
        original_map[norm].append(origin)

    duplicates = {}

    for norm, count in counts.items():
        if count > 1:
            duplicates[norm] = {
                "count": count,
                "original_links": list(set(original_map[norm]))
            }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(duplicates, f, indent=4)

    print(f"Total duplicated groups: {len(duplicates)}")


if __name__ == "__main__":
    find_duplicates()
