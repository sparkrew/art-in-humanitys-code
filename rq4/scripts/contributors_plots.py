import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import plotly.express as px
import os

# Config
EXCEL_PATH = "42_contributors.xlsx"
OUTDIR = "figures"
SHEET_NAME = 0 

# Order
PURPOSE_ORDER = ["art", "CS edu", "art edu"]

# Utils functions
def norm_col(s: str) -> str:
    """Normalize column names to avoid issues with spaces/case."""
    s = str(s).strip()
    s = re.sub(r"\s+", " ", s)
    return s

def to_bool_active(x) -> bool:
    """Convert the common values of Active to boolean.
    Treats NaN as False."""
    if pd.isna(x):
        return False
    s = str(x).strip().lower()
    return s in {"1", "true", "yes", "y", "active", "activo", "sí", "si"}

def safe_mkdir(path: str):
    os.makedirs(path, exist_ok=True)

def save_all_formats(fig, basepath_no_ext: str, dpi=300):
    fig.savefig(basepath_no_ext + ".pdf", bbox_inches="tight")
    fig.savefig(basepath_no_ext + ".svg", bbox_inches="tight")
    fig.savefig(basepath_no_ext + ".png", dpi=dpi, bbox_inches="tight")

def plot_contributors(df, types_present):
    df = df.copy()
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 14,
        "axes.titlesize": 18,
        "axes.labelsize": 18,
    })
    # Colors
    org_dark_blue = "#020122"
    org_mid_blue = "#337CA0"
    org_light_blue = "#73B3D3"

    user_dark_red = "#FF0000"
    user_mid_red = "#FF5C5C"
    user_light_red = "#FFADAD"

    required_cols = {
        "Username",
        "Purpose",
        "Number_repos",
        "org_or_user",
        "Active_bool",
        "Years_since_creation"
    }

    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing columns in dataframe for plot4: {missing}\n"
            f"Columns detected: {list(df.columns)}"
        )

    def get_text_color(background_color):
        """
        Returns white text for dark colors and black text for light colors.
        Uses relative luminance.
        """
        r, g, b = mcolors.to_rgb(background_color)
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        if luminance < 0.5:
            return "white"
        return "black"

    def assign_color_group(row):
        """Color classification"""
        is_org = str(row["org_or_user"]).strip().lower() == "org"
        is_active = bool(row["Active_bool"])
        years = pd.to_numeric(row["Years_since_creation"], errors="coerce")

        if is_org:
            if not is_active:
                return "org_light_blue"
            elif pd.notna(years) and years >= 10:
                return "org_dark_blue"
            else:
                return "org_mid_blue"
        else:
            if not is_active:
                return "user_light_red"
            elif pd.notna(years) and years >= 10:
                return "user_dark_red"
            else:
                return "user_mid_red"

    df["color_group"] = df.apply(assign_color_group, axis=1)
    color_order = [
        "org_dark_blue",
        "org_mid_blue",
        "org_light_blue",
        "user_dark_red",
        "user_mid_red",
        "user_light_red",
    ]
    color_map = {
        "org_dark_blue": org_dark_blue,
        "org_mid_blue": org_mid_blue,
        "org_light_blue": org_light_blue,
        "user_dark_red": user_dark_red,
        "user_mid_red": user_mid_red,
        "user_light_red": user_light_red,
    }

    fig, ax = plt.subplots(figsize=(17, 18), dpi=300)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    x_positions = range(len(types_present))
    bar_width = 0.95

    max_total = 0

    for i, purpose in enumerate(types_present):
        sub = df[df["Purpose"] == purpose].copy()

        if sub.empty:
            continue

        sub["color_group"] = pd.Categorical(
            sub["color_group"],
            categories=color_order,
            ordered=True
        )

        sub = sub.sort_values(
            by=["color_group", "Number_repos", "Username"],
            ascending=[True, False, True]
        )

        bottom = 0

        for _, row in sub.iterrows():
            height = row["Number_repos"]

            if height <= 0:
                continue

            color = color_map[row["color_group"]]
            text_color = get_text_color(color)

            ax.bar(
                i,
                height,
                bottom=bottom,
                width=bar_width,
                color=color,
                edgecolor="white",
                linewidth=1.0
            )

            # Text inside each rectangle/bar segment
            ax.text(
                i,
                bottom + height / 2,
                str(row["Username"]),
                ha="center",
                va="center",
                fontsize=20,
                color=text_color,
                weight="semibold",
                clip_on=True
            )

            bottom += height

        max_total = max(max_total, bottom)

    # Axes
    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(
        types_present,
        rotation=18,
        fontsize=22,
        ha="right"
    )
    ax.tick_params(axis="y", labelsize=36)
    ax.tick_params(axis="x", labelsize=36)
    ax.set_ylim(0, max_total * 1.10 if max_total > 0 else 1)
    ax.grid(axis="y", linestyle="--", alpha=0.15)
    ax.set_axisbelow(True)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    # Legend section
    legend_handles = [
        Patch(facecolor=org_dark_blue, edgecolor="white", label="Org ≥ 10 years"),
        Patch(facecolor=user_dark_red, edgecolor="white", label="User ≥ 10 years"),
        Patch(facecolor=org_mid_blue, edgecolor="white", label="Org < 10 years"),
        Patch(facecolor=user_mid_red, edgecolor="white", label="User < 10 years"),
        Patch(facecolor=org_light_blue, edgecolor="white", label="Org non-active"),
        Patch(facecolor=user_light_red, edgecolor="white", label="User non-active"),
    ]
    ax.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.10),
        ncol=3,
        frameon=False,
        fontsize=30,
        handlelength=1.5,
        handleheight=1.2,
        columnspacing=1.8
    )

    plt.tight_layout()
    plt.savefig(f"{OUTDIR}/plot.png", dpi=300, bbox_inches="tight")
    plt.savefig(f"{OUTDIR}/plot.pdf", bbox_inches="tight")
    plt.savefig(f"{OUTDIR}/plot.svg", bbox_inches="tight")
    plt.close()

def main():
    # Loading the data
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME, engine="openpyxl")
    df.columns = [norm_col(c) for c in df.columns]

    required = {"Username", "Purpose", "Number_repos", "Active", "URL", "Created_in", "org_or_user"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in Excel: {missing}\nColumns detected: {list(df.columns)}")

    # Basic cleaning and type conversion
    df["Purpose"] = df["Purpose"].astype(str).str.strip()
    df["Username"] = df["Username"].astype(str).str.strip()
    df["Number_repos"] = pd.to_numeric(df["Number_repos"], errors="coerce").fillna(0).astype(int)
    df["Active_bool"] = df["Active"].apply(to_bool_active)
    df["URL"] = df["URL"].astype(str).str.strip()
    df["Created_in"] = pd.to_numeric(df["Created_in"], errors="coerce")
    df["Years_since_creation"] = 2026 - df["Created_in"]
    df["org_or_user"] = df["org_or_user"].astype(str).str.strip().str.lower()

    types_present = ['CS edu', 'art edu', 'art']
    print(f"Types in data (in order): {types_present}")
    types_present += [t for t in sorted(df["Purpose"].unique()) if t not in types_present]

    safe_mkdir(OUTDIR)
    plot_contributors(df, types_present)
 

if __name__ == "__main__":
    main()