"""Count art programming environments from SWH_signals in generative_art_dataset.json."""

import re
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

EXT_TO_ENV = {
    ".js": "p5.js",
    ".cpp": "openFrameworks",
    ".h": "openFrameworks",
    ".pde": "Processing",
    ".scd": "supercollider",
    ".toe": "TouchDesigner",
    ".tox": "TouchDesigner",
    ".ndbx": "nodebox",
    ".v4p": "vvvv",
}

SIGNAL_RE = re.compile(r'"SWH_signals"\s*:\s*\{\s*"enum"\s*:\s*\[([^\]]*)\]')
EXT_RE = re.compile(r'"(\.[^"]+)"')


def main():
    path = Path(__file__).parent / "generative_art_dataset.json"
    if not path.exists():
        sys.exit(f"File not found: {path}")

    env_counts = Counter()

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = SIGNAL_RE.search(line)
            if not m:
                continue
            inner = m.group(1).strip()
            if not inner:
                continue
            exts = set(EXT_RE.findall(inner))
            envs = {EXT_TO_ENV[e] for e in exts if e in EXT_TO_ENV}
            if len(envs) == 1:
                env_counts[envs.pop()] += 1
            elif len(envs) > 1:
                env_counts["more than one"] += 1

    for env, count in env_counts.most_common():
        print(f"{env} - {count}")

    return env_counts


def donut_chart(env_counts):
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 15,
        }
    )

    labels = ["p5.js", "Processing", "openFrameworks", "more than one", "others"]
    named = {"p5.js", "Processing", "openFrameworks", "more than one"}
    others = sum(c for env, c in env_counts.items() if env not in named)
    counts = [
        env_counts.get("p5.js", 0),
        env_counts.get("Processing", 0),
        env_counts.get("openFrameworks", 0),
        env_counts.get("more than one", 0),
        others,
    ]
    colors = ["#337ca0", "#FF0000", "#3EC300", "#FFFC31", "#020122"]
    total = sum(counts)

    annot_labels = [
        f"{name}  ({count / total * 100:.1f}%)\n{count:,}"
        for name, count in zip(labels, counts)
    ]

    _, ax = plt.subplots(figsize=(8, 5))
    wedges, _ = ax.pie(
        counts,
        colors=colors,
        wedgeprops=dict(width=0.4, edgecolor="white"),
        startangle=90,
    )

    anchor_ang = [(w.theta1 + w.theta2) / 2.0 for w in wedges]
    anchor_ang[0] = 330.0

    order = sorted(
        range(len(anchor_ang)),
        key=lambda i: np.sin(np.deg2rad(anchor_ang[i])),
        reverse=True,
    )
    text_x = 1.5
    label_ys = np.linspace(0.95, -0.95, len(order))

    for ty, i in zip(label_ys, order):
        rad = np.deg2rad(anchor_ang[i])
        ax.annotate(
            annot_labels[i],
            xy=(np.cos(rad), np.sin(rad)),
            xytext=(text_x, ty),
            ha="left",
            va="center",
            fontsize=13,
            arrowprops=dict(
                arrowstyle="-",
                color="0.5",
                lw=0.9,
                shrinkA=2,
                shrinkB=6,
            ),
        )

    ax.text(
        0,
        0.08,
        f"{total / 1_000_000:.2f}M".replace(".", ","),
        ha="center",
        va="center",
        fontsize=22,
        fontweight="bold",
    )
    ax.text(
        0,
        -0.14,
        "Repos",
        ha="center",
        va="center",
        fontsize=16,
    )
    ax.set_aspect("equal")
    ax.set_xlim(-1.3, 3.4)
    ax.set_ylim(-1.4, 1.4)
    out = Path(__file__).parent / "art_envs_donut.svg"
    # plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.savefig(out, format="svg", bbox_inches="tight")
    # plt.savefig("figure.svg", bbox_inches="tight")
    print(f"Saved to {out}")
    plt.show()


if __name__ == "__main__":
    env_counts = main()
    donut_chart(env_counts)
