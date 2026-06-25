import matplotlib.pyplot as plt
from matplotlib_venn import venn2, venn3
import numpy as np
from venn import venn
from matplotlib_venn import venn2
from utils import load_json
from matplotlib.patches import Circle

TOTAL_ARTWORKS = 17875

def print_venn_counts(name, only_visual, only_auditory, visual_and_auditory):
    total_quadrant = only_visual + only_auditory + visual_and_auditory

    print(f"\n{name}")
    print(f"  only visual:          {only_visual}  ({format_percentage(only_visual)})")
    print(f"  only auditory:        {only_auditory}  ({format_percentage(only_auditory)})")
    print(f"  visual and auditory:  {visual_and_auditory}  ({format_percentage(visual_and_auditory)})")
    print(f"  total quadrant:       {total_quadrant}  ({format_percentage(total_quadrant)})")

def format_percentage(value, total=TOTAL_ARTWORKS):
    percentage = (value / total) * 100
    return f"{percentage:.2f}%"

def move_label(label, dx=0, dy=0):
    if label:
        x, y = label.get_position()
        label.set_position((x + dx, y + dy))
        
def diagnose_labels(data):
    both_static_and_time_based = []
    neither_static_nor_time_based = []
    no_visual_no_auditory = []

    for item in data:
        file_path = item.get("file_path", "")
        predicted_labels = item.get("predicted_labels", {})
        outcome_label = predicted_labels.get("outcome", [])

        is_static = "static" in outcome_label
        is_time_based = "time_based" in outcome_label

        has_visual = "visual" in outcome_label
        has_auditory = "auditory" in outcome_label

        if is_static and is_time_based:
            both_static_and_time_based.append(file_path)

        if not is_static and not is_time_based:
            neither_static_nor_time_based.append(file_path)

        if not has_visual and not has_auditory:
            no_visual_no_auditory.append(file_path)

    print("\nLABEL DIAGNOSTICS")
    print(f"  both static and time_based:     {len(both_static_and_time_based)}")
    print(f"  neither static nor time_based:  {len(neither_static_nor_time_based)}")
    print(f"  no visual nor auditory:         {len(no_visual_no_auditory)}")

    return {
        "both_static_and_time_based": both_static_and_time_based,
        "neither_static_nor_time_based": neither_static_nor_time_based,
        "no_visual_no_auditory": no_visual_no_auditory,
    }

def plot_empty_quadrants(output_file=None):
    fig, ax = plt.subplots(figsize=(6, 6))

    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)

    ax.axhline(0, color="black", linewidth=1)
    ax.axvline(0, color="black", linewidth=1)

    ax.set_xticks([])
    ax.set_yticks([])

    ax.set_aspect("equal")

    ax.text(1.08, 0, "time_based", ha="left", va="center", fontsize=14)
    ax.text(0, 1.08, "interactive", ha="center", va="bottom", fontsize=14)
    ax.text(-1.08, 0, "static", ha="right", va="center", fontsize=14)
    ax.text(0, -1.08, "non-interactive", ha="center", va="top", fontsize=14)

    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, bbox_inches="tight", dpi=300)

    plt.show()


def plot_venn_diagram1(sets, output_file):
    colors = {
        "visual": "#FF0000",
        "auditory": "#3EC300",
    }
    plt.figure(figsize=(8, 6))
    
    venn(
        sets,
        cmap=[colors[label] for label in sets.keys()],
        fontsize=13,
        legend_loc="upper right"
    )
    plt.savefig(output_file,format="svg", dpi=300, bbox_inches="tight")
    

def plot_venn_diagram(sets, output_file, title=None, quadrant_name=""):
    visual_set = sets["visual"]
    auditory_set = sets["auditory"]

    only_visual = len(visual_set - auditory_set)
    only_auditory = len(auditory_set - visual_set)
    visual_and_auditory = len(visual_set & auditory_set)

    print_venn_counts(
        quadrant_name,
        only_visual,
        only_auditory,
        visual_and_auditory
    )
    
    fig, ax = plt.subplots(figsize=(7, 6))
    
    # -----------------------------
    # Case 1: No auditory artworks
    # -----------------------------
    if only_auditory == 0 and visual_and_auditory == 0:
        circle = Circle(
            (0.5, 0.5),
            0.35,
            color="#FF0000",
            alpha=0.65
        )

        ax.add_patch(circle)

        # Percentage inside the circle
        ax.text(
            0.5,
            0.5,
            format_percentage(len(visual_set)),
            ha="center",
            va="center",
            fontsize=40
        )

        # Label
        ax.text(
            0.5,
            0.35,
            "visual",
            ha="center",
            va="center",
            fontsize=40
        )

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect("equal")
        ax.axis("off")
        plt.savefig(f"circle_{output_file}", format="svg", dpi=300, bbox_inches="tight")
        return

    # -----------------------------
    # Case 2: Visual + auditory
    # -----------------------------
    
    v = venn2(
        subsets=(only_visual, only_auditory, visual_and_auditory),
        set_labels=("visual", "auditory"),
        set_colors=("#FF0000", "#3EC300"),
        alpha=0.65,
        ax=ax
    )

    # Replace numbers with percentages
    if v.get_label_by_id("10"):
        v.get_label_by_id("10").set_text(format_percentage(only_visual))
        #print(f"ONLY VISUAL => {format_percentage(only_visual)}")
    
    if v.get_label_by_id("01"):
        if only_auditory == 0:
            v.get_label_by_id('01').set_visible(False)
        else:
            v.get_label_by_id("01").set_text(format_percentage(only_auditory))
        #print(f"ONLY AUDITORY => {format_percentage(only_auditory)}")

    if v.get_label_by_id("11"):
        v.get_label_by_id("11").set_text(format_percentage(visual_and_auditory))
        #print(f"ONLY VISUAL AND AUDITORY => {format_percentage(visual_and_auditory)}")

    # Font size
    for label_id in ["10", "01", "11"]:
        label = v.get_label_by_id(label_id)
        if label:
            label.set_fontsize(40) # number
            #label.set_fontweight("bold")

    for label in v.set_labels:
        if label:
            label.set_fontsize(40) # text
            #label.set_fontweight("bold")

    visual_label = v.set_labels[0]
    auditory_label = v.set_labels[1]

    move_label(visual_label, dx=0.20, dy=0.50)
    move_label(auditory_label, dx=0.05, dy=-0.15)
    
    auditory_percentage = (only_auditory / TOTAL_ARTWORKS) * 100
    intersection_percentage = (visual_and_auditory / TOTAL_ARTWORKS) * 100

    if auditory_percentage < 2.0:
        move_label(v.get_label_by_id("01"), dx=0.40, dy=-0.20)

    # if intersection_percentage < 2.0:
    move_label(v.get_label_by_id("11"), dx=0.10, dy=0.00)


    plt.savefig(output_file, format="svg", dpi=300, bbox_inches="tight")
    plt.close()
    
def get_quadrant_set(data, quadrant):
    """
    quadrant example:
    ("interactive", "time_based")
    ("interactive", "static")
    ("non_interactive", "static")
    ("non_interactive", "time_based")
    """

    interaction_type, time_type = quadrant
    sets = {
        "visual": set(),
        "auditory": set()
    }
    for item in data:
        file_path = item.get("file_path", "")
        predicted_labels = item.get("predicted_labels", {})

        entities_label = predicted_labels.get("entities", [])
        interaction_label = predicted_labels.get("interaction", [])
        outcome_label = predicted_labels.get("outcome", [])
        
        is_interactive = interaction_label[0] == "yes"
        is_time_based = "time_based" in outcome_label
        is_static = "static" in outcome_label
        
        if interaction_type == "interactive" and not is_interactive:
            continue

        if interaction_type == "non_interactive" and is_interactive:
            continue

        if time_type == "time_based" and not is_time_based:
            continue

        if time_type == "static" and not is_static:
            continue
        
        has_image = "visual" in outcome_label
        has_sound = "auditory" in outcome_label
        
        if has_image:
            sets["visual"].add(file_path)
        if has_sound:
            sets["auditory"].add(file_path)
    
    return sets

def create_sets_and_plots(data):
    quadrants = {
        "q1_interactive_time_based": ("interactive", "time_based"),
        "q2_interactive_static": ("interactive", "static"),
        "q3_non_interactive_static": ("non_interactive", "static"),
        "q4_non_interactive_time_based": ("non_interactive", "time_based"),
    }

    all_quadrant_sets = {}
    
    
    for name, quadrant in quadrants.items():
        quadrant_sets = get_quadrant_set(data, quadrant)
        all_quadrant_sets[name] = quadrant_sets

        image_count = len(quadrant_sets["visual"])
        sound_count = len(quadrant_sets["auditory"])
        total_image_or_sound = len(
            quadrant_sets["visual"] | quadrant_sets["auditory"]
        )
        
        print(f"\n{name}")
        # print(f"visual: {len(quadrant_sets['visual'])}")
        # print(f"percentage: {format_percentage(image_count)}")
        # print(f"auditory: {len(quadrant_sets['auditory'])}")
        # print(f"percentage: {format_percentage(sound_count)}")
        # print(
        #     "total with image or sound:",
        #     len(quadrant_sets["visual"] | quadrant_sets["auditory"])
        # )
        # print(f"percentage: {format_percentage(total_image_or_sound)}")
        plot_venn_diagram(
            quadrant_sets,
            f"venn_diagram2_{name}.svg",
            name
        )
        
        # FROM clean_artworks_label_prediction1.json
        # q1_interactive_time_based
        # visual: 8063
        # auditory: 1962
        # total with image or sound: 8372
        # 
        # q2_interactive_static
        # visual: 213
        # auditory: 2
        # total with image or sound: 213
        # 
        # q3_non_interactive_static
        # visual: 2562
        # auditory: 0
        # total with image or sound: 2562
        # 
        # q4_non_interactive_time_based
        # visual: 4548
        # auditory: 255
        # total with image or sound: 4612

#----------------------------------------------------------------

        # FROM clean_artworks_label_prediction.json
        # q1_interactive_time_based
        # visual: 9393
        # percentage: 52.55%
        # auditory: 1913
        # percentage: 10.70%
        # total with image or sound: 9560
        # percentage: 53.48%
        # 
        # q2_interactive_static
        # visual: 1258
        # percentage: 7.04%
        # auditory: 0
        # percentage: 0.00%
        # total with image or sound: 1258
        # percentage: 7.04%
        # 
        # q3_non_interactive_static
        # visual: 2655
        # percentage: 14.85%
        # auditory: 0
        # percentage: 0.00%
        # total with image or sound: 2655
        # percentage: 14.85%
        # 
        # q4_non_interactive_time_based
        # visual: 4384
        # percentage: 24.53%
        # auditory: 130
        # percentage: 0.73%
        # total with image or sound: 4396
        # percentage: 24.59%

if __name__ == "__main__":
    input_file2 = "clean_artworks_label_prediction.json"
    data = load_json(input_file2)
    
    print(f"TOTAL_ARTWORKS = {TOTAL_ARTWORKS}")

    diagnose_labels(data)

    create_sets_and_plots(data)
    #plot_empty_quadrants("empty_quadrants2.svg")