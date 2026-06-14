import json

all_origins_path = "/all_origins.json"
duplicates_path = "/duplicate_origins.json"
output_path = "/all_origins_non_duplicated.json"

# Load all_origins
with open(all_origins_path, "r") as f:
    all_origins = json.load(f)

# Load duplicate links
with open(duplicates_path, "r") as f:
    duplicates = json.load(f)

# Determine which links to remove
links_to_remove = set()

for repo, data in duplicates.items():
    links = data.get("original_links", [])
    if len(links) > 1:
        # keep the first link, remove the others
        links_to_remove.update(links[1:])

# Filter all_origins
filtered_origins = [
    entry for entry in all_origins
    if entry.get("origin") not in links_to_remove
]

# Write cleaned file
with open(output_path, "w") as f:
    json.dump(filtered_origins, f, indent=2)

print(f"Removed {len(all_origins) - len(filtered_origins)} duplicated entries.")
print(f"Cleaned file written to: {output_path}")