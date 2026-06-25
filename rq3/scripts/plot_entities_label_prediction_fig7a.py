import json
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter
from utils import load_json, percentage


INPUT_FILE = "clean_artworks_label_prediction.json"

def count_entity_groups(data):
    """
    Counts the entities in 3 big groups:
    - synthesized: image, text, sound
    - processed: image, text, sound
    - randomness
    """
    counts = {
        "synthesized": {"image": 0, "text": 0, "sound": 0},
        "processed": {"image": 0, "text": 0, "sound": 0},
        "randomness": 0
    }

    for item in data:
        entities = item.get("predicted_labels", {}).get("material_and_process", [])

        # Use set to avoid counting duplicates inside the same artwork
        entities = set(entities)

        for entity in entities:
            if entity == "synthesized_image":
                counts["synthesized"]["image"] += 1
            elif entity == "synthesized_text":
                counts["synthesized"]["text"] += 1
            elif entity in {"synthesized_audio", "synthesized_sound"}:
                counts["synthesized"]["sound"] += 1

            elif entity == "processed_image":
                counts["processed"]["image"] += 1
            elif entity == "processed_text":
                counts["processed"]["text"] += 1
            elif entity in {"processed_audio", "processed_sound"}:
                counts["processed"]["sound"] += 1

            elif entity == "randomness":
                counts["randomness"] += 1

    return counts


def plot_entity_distribution(counts, output_file="entities_grouped_plot.png", ax=None,  shared_y_max=None, total=None):
    # Colors
    color_image = "#FF0000"
    color_text = "#337CA0"
    color_sound = "#3EC300"
    color_randomness = "#020122"

    synthesized_vals = counts["synthesized"]
    processed_vals = counts["processed"]
    randomness_val = counts["randomness"]

    # Values
    syn_image = synthesized_vals["image"]
    syn_text = synthesized_vals["text"]
    syn_sound = synthesized_vals["sound"]

    pro_image = processed_vals["image"]
    pro_text = processed_vals["text"]
    pro_sound = processed_vals["sound"]

    syn_total = 17198
    syn_pct = 96.16

    pro_total = 9067
    pro_pct = 46.86

    ran_total = 8871
    ran_pct = 44.70

    syn_label_y = 7800
    pro_label_y = 5600
    ran_label_y = 8700


    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 7.5), dpi=300)
    else:
        fig = ax.figure

    print("ENTRO A PLOT ENTITIES")
    # -------------------------
    # X positions
    # -------------------------
    bar_width = 0.20

    # synthesized group (total, image, text, sound)
    syn_center = 0
    syn_x = [
        syn_center - 1.5 * bar_width,
        syn_center - 0.47 * bar_width,
        syn_center + 0.57 * bar_width,
        syn_center + 1.61 * bar_width,
    ]

    # processed group (total, image, text, sound)
    pro_center = 0.92
    pro_x = [
        pro_center - 1.45 * bar_width,
        pro_center - 0.41 * bar_width,
        pro_center + 0.63 * bar_width,
        pro_center + 1.66 * bar_width,
    ]

    # randomness group
    ran_center = 1.56

    # -------------------------
    # Plot bars
    # -------------------------
    bars_syn = ax.bar(
        syn_x,
        [syn_total, syn_image, syn_text, syn_sound],
        width=bar_width,
        color=[color_randomness, color_image, color_text, color_sound]
    )
    
    bars_pro = ax.bar(
        pro_x,
        [pro_total, pro_image, pro_text, pro_sound],
        width=bar_width,
        color=[color_randomness, color_image, color_text, color_sound]
    )

    bar_ran = ax.bar(
        ran_center,
        randomness_val,
        width=bar_width,
        color=color_randomness
    )


    # -------------------------
    # Total labels above each group
    # -------------------------

    max_total = max(syn_total, pro_total)
    
    # -------------------------
    # X axis
    # -------------------------
    ax.set_xticks([syn_center, pro_center, ran_center])
    ax.set_xticklabels(["synthesized", "processed", "randomness"], fontsize=18)

    # limit the extra space
    ax.set_xlim(-0.55, 1.95)
    
    # -------------------------
    # Y axis / style
    # -------------------------
    # Express the y-axis as a percentage of the total number of artworks,
    # running from 0% to 100%.
    if total is None:
        total = max(syn_total, pro_total, ran_total)

    print(F"total => {total}")
    ax.set_ylim(0, total)
    ax.set_yticks(np.linspace(0, total, 6))
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=total))
    ax.tick_params(axis="y", labelsize=18)
    #ax.grid(axis="y", linestyle="--", alpha=0.25)
    ax.set_axisbelow(True)

    # Remove top and right borders
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Softer remaining borders
    ax.spines["left"].set_alpha(0.5)
    ax.spines["bottom"].set_alpha(0.5)
    
    print(f"synthesized total: {syn_total} ({percentage(syn_total, total):.2f}%)")
    print(f"synthesized image: {syn_image} ({percentage(syn_image, total):.2f}%)")
    print(f"synthesized text: {syn_text} ({percentage(syn_text, total):.2f}%)")
    print(f"synthesized sound: {syn_sound} ({percentage(syn_sound, total):.2f}%)")
    
    print(f"processed total: {pro_total} ({percentage(pro_total, total):.2f}%)")
    print(f"processed image: {pro_image} ({percentage(pro_image, total):.2f}%)")
    print(f"processed text: {pro_text} ({percentage(pro_text, total):.2f}%)")
    print(f"processed sound: {pro_sound} ({percentage(pro_sound, total):.2f}%)")
    
    print(f"randomness: {randomness_val} ({percentage(randomness_val, total):.2f}%)")

    # -------------------------
    # Legend
    # -------------------------
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, color=color_image, label="image"),
        plt.Rectangle((0, 0), 1, 1, color=color_text, label="text"),
        plt.Rectangle((0, 0), 1, 1, color=color_sound, label="sound"),
        plt.Rectangle((0, 0), 1, 1, color=color_randomness, label="total"),
    ]

    ax.legend(handles=legend_handles, fontsize=20)

    plt.tight_layout()
    if output_file is not None:
        print("SAVE ENTITY PLOT")
        plt.savefig(output_file, format="svg", dpi=300, bbox_inches="tight")

def main():
    data = load_json(INPUT_FILE)
    counts = count_entity_groups(data)

    print("Counts:")
    print(counts)
    # {'synthesized': {'image': 14797, 'text': 3588, 'sound': 1174}, 
    # 'processed': {'image': 5212, 'text': 1947, 'sound': 1589}, 
    # 'randomness': 7992}
    plot_entity_distribution(
        counts,
        output_file="entities_grouped_plot10.svg",
        total=len(data)
    )

# {'synthesized': {'image': 14797, 'text': 3588, 'sound': 1174}, 'processed': {'image': 5212, 'text': 1947, 'sound': 1589}, 'randomness': 7992}
# ENTRO A PLOT ENTITIES
# SAVE ENTITY PLOT
# PS C:\Users\Asus\Documents\vscode_projects\genart-classifier> python .\plot_entities_label_prediction.py
# Counts:
# {'synthesized': {'image': 14571, 'text': 3416, 'sound': 1223}, 'processed': {'image': 5529, 'text': 2281, 'sound': 1484}, 'randomness': 9431}
# {synthesized': {'image': 14603, 'text': 3363, 'sound': 1181}, 'processed': {'image': 5507, 'text': 2371, 'sound': 1504}, 'randomness': 8871}

if __name__ == "__main__":
    main()