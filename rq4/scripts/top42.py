import json
from urllib.parse import urlparse
from collections import Counter, defaultdict

INPUT_PATH = 'input_data.json'  # Path to the input JSON file

def normalize_origin(origin: str) -> str:
    origin = origin.rstrip('/')
    if origin.endswith('.git'):
        origin = origin[:-4]
    if '://' not in origin:
        origin = 'git://' + origin
    return origin


def extract_contributor(origin: str):
    origin = normalize_origin(origin)
    parsed = urlparse(origin)

    host = parsed.hostname or 'unknown'
    path_parts = [p for p in parsed.path.split('/') if p]

    if host and 'github.com' in host and len(path_parts) >= 1:
        return path_parts[0], True 

    return host, False


with open(INPUT_PATH, 'r') as f:
    data = json.load(f)

all_contributor_repos = defaultdict(set)
github_contributor_repos = defaultdict(set)
for record in data:
    # Only live repos
    if not record.get('metadata', {}).get('live', False):
        continue
    origin = record.get('origin')
    if not origin:
        continue
    normalized_origin = normalize_origin(origin)
    contributor, is_github = extract_contributor(origin)
    if is_github:
        github_contributor_repos[contributor].add(normalized_origin)

github_contributors = Counter({
    contributor: len(repos)
    for contributor, repos in github_contributor_repos.items()
})

top42_github = github_contributors.most_common(42)

# Add the list of all repo URLs
github_output = [
    {
        "contributor": contributor,
        "unique_repo_count": count,
        "repo_links": sorted(list(github_contributor_repos[contributor]))
    }
    for contributor, count in top42_github
]

with open('top_42_contributors.json', 'w') as f:
    json.dump(github_output, f, indent=2)

print("\nsaved to 'top_42_contributors.json'")