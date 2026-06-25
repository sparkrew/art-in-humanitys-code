import json
import os
import re
from collections import Counter
import matplotlib.pyplot as plt
from venn import venn
from utils import load_json

FONT_EXTENSIONS = {
    ".otf", ".ttf", ".woff", ".woff2", ".vlw"
}

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".jpe", ".jfif", ".gif", ".webp",
    ".bmp", ".svg", ".tiff", ".tif", ".ico", ".cur",
    ".psd", ".dds",
    ".glsl", ".frag", ".vert", ".obj"
}

SOUND_EXTENSIONS = {
    ".mp3", ".ogg", ".wav", ".m4a",
    ".aac", ".flac", ".aiff", ".mid", ".midi"
}

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".m4v", ".mov", ".webm", ".avi"
}

DATA_EXTENSIONS = {
    ".json", ".txt", ".csv", ".tsv", ".xml",
    ".db", ".xlsx"
}


def get_clean_extension(filename):
    """
    Extracts and normalizes the extension.

    It fixes cases like:
    - index.html  1 -> .html
    - sketch.js 1 -> .js
    - style.css 1 -> .css
    """
    filename = filename.strip()
    _, extension = os.path.splitext(filename)
    extension = extension.lower().strip()

    match = re.match(r"^\.[a-z0-9]+", extension)

    if match:
        return match.group(0)

    return ""


def get_asset_category(filename):
    extension = get_clean_extension(filename)
    if extension in FONT_EXTENSIONS:
        return "fonts"
    
    if extension in IMAGE_EXTENSIONS or extension in VIDEO_EXTENSIONS:
        return "image_video"

    if extension in SOUND_EXTENSIONS:
        return "sound"

    if extension in DATA_EXTENSIONS:
        return "data"

    return None


def save_other_extensions(data, output_file="other_asset_extensions.txt"):
    others_counter = Counter()
    for item in data:
        other_files = item.get("other", [])

        other_extensions_for_artwork = set()

        for filename in other_files:
            extension = get_clean_extension(filename)
            asset_category = get_asset_category(filename)

            if asset_category is None:
                continue

            if asset_category == "others":
                print("No here")
                if extension:
                    other_extensions_for_artwork.add(extension)
                else:
                    other_extensions_for_artwork.add("no_extension")

        for extension in other_extensions_for_artwork:
            print("HERE AGAIN")
            others_counter[extension] += 1

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("extension,# of artworks\n")

        for extension, count in others_counter.most_common():
            f.write(f"{extension},{count}\n")

    print(f"Saved other extensions to: {output_file}")

def count_libraries_per_artwork(data):
    """ For couting how many artworks use each library. 
    If an artwork has no libraries, it is counted as 'no_library'."""
    
    counter = Counter()
    for item in data:
        libraries = item.get("libraries", [])
        if not libraries:
            counter["no_library"] += 1
        else:
            unique_libraries = set(libraries) # Avoid counting the same library twice in the same artwork
            for library in unique_libraries:
                counter[library] += 1
    return counter

def count_assets_per_artwork(data):
    """ This method counts how many artworks use each type of asset. The 'other' field contains filenames.
    This function extracts file extensions. In the case of image files extension we group then as 'img' and it counts one,
    even if there are different files with different extensions."""
    counter = Counter()
    #artworks_with_assets = 0
    for item in data:
        other_files = item.get("other", [])

        asset_categories_for_artwork = set()

        for filename in other_files:
            asset_category = get_asset_category(filename)
            if asset_category is None:
                continue
            #artworks_with_assets += 1
            asset_categories_for_artwork.add(asset_category)
            #break
            

        for asset_category in asset_categories_for_artwork:
            counter[asset_category] += 1
    #print(f"Number of artworks with at least one asset: {artworks_with_assets}")
    return counter

def get_artworks_by_asset_category(data):
    """
    Returns a dictionary like:
    {
        "image_video": {artwork_id_1, artwork_id_2, ...},
        "data": {artwork_id_3, artwork_id_4, ...},
        ...
    }
    """

    asset_sets = {
        "image_video": set(),
        "data": set(),
        "sound": set(),
        "fonts": set()
    }

    for index, item in enumerate(data):
        artwork_id = item.get("id", index)
        other_files = item.get("other", [])

        categories_for_this_artwork = set()

        for filename in other_files:
            asset_category = get_asset_category(filename)

            if asset_category is None:
                continue

            categories_for_this_artwork.add(asset_category)

        for category in categories_for_this_artwork:
            asset_sets[category].add(artwork_id)

    return asset_sets

def plot_counter(counter, title, xlabel, ylabel, output_file=None, top_n=None, custom_order=None):
    """Plots a bar chart from a Counter and displays the count above each bar."""

    if custom_order is not None:
        most_common = [
            (label, counter.get(label, 0))
            for label in custom_order
        ]
    elif top_n is not None:
        most_common = counter.most_common(top_n)
    else:
        most_common = counter.most_common()

    labels = [item[0] for item in most_common]
    counts = [item[1] for item in most_common]

    plt.figure(figsize=(8, 6))
    bars = plt.bar(labels, counts,color="red")

    plt.title(title, fontsize=18)
    plt.xlabel(xlabel, fontsize=14)
    plt.ylabel(ylabel, fontsize=14)

    plt.xticks(rotation=45, ha="right")

    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            str(int(height)),
            ha="center",
            va="bottom",
            fontsize=10
        )

    plt.tight_layout()
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
    #plt.show()

def plot_venn(asset_sets, output_file=None):
    colors = {
        "image_video": "#FF0000",
        "data": "#337CA0",
        "sound": "#3EC300",
        "fonts": "#FFFC31"
    }

    fig, ax = plt.subplots(figsize=(6, 6))

    venn(
        asset_sets,
        cmap=[colors[label] for label in asset_sets.keys()],
        fontsize=20,
        legend_loc="upper right"
    )

    ax = plt.gca()
    ax.set_ylim(0.08, 1.25)

    if output_file:
        plt.savefig(output_file,format="svg", dpi=300, bbox_inches="tight")#, pad_inches=-0.05
    #plt.show()
    
def main():
    input_file = "found_artworks_clean_updated_libraries_clean.json" #"found_artworks_clean_updated_libraries.json" #"found_artworks_clean.json"
    input_file2 = "merged_artworks_llm_libraries_assets_code_lines.json"
    data = load_json(input_file2)

    #libraries_counter = count_libraries_per_artwork(data)
    assets_counter = count_assets_per_artwork(data)

    save_other_extensions(
        data,
        output_file="other_asset_extensions.txt"
    )

    #print("Libraries:")
    #for library, count in libraries_counter.most_common():
    #    print(f"{library}: {count}")

    print("\nAssets:")
    for asset, count in assets_counter.most_common():
        print(f"{asset}: {count}")

    plot_counter(
        assets_counter,
        title="Number of Artworks per Asset Type",
        xlabel="assets",
        ylabel="# of artworks",
        output_file="assets_vs_artworks.png")
    
    asset_sets = get_artworks_by_asset_category(data)

    print("Number of artworks per category:")
    for category, artworks in asset_sets.items():
        print(f"{category}: {len(artworks)}")

    artworks_with_at_least_one_category = set().union(*asset_sets.values())

    print(
        "Number of artworks that use at least one of the selected asset categories:", # 4994
        len(artworks_with_at_least_one_category)
    )


    plot_venn(
        asset_sets,
        output_file="assets_venn_diagram3.svg"
    )


if __name__ == "__main__":
    main()