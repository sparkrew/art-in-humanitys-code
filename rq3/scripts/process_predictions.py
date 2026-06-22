import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# SETTINGS
DATA_DIR = Path("<PATH_TO_DATA_FOLDER>")
EXPERIMENT_DIR = Path("<PATH_TO_EXPERIMENT_OUTPUT_FOLDER>")
PREDICTIONS_FILE = EXPERIMENT_DIR / "predictions.json"
FIGURES_DIR = EXPERIMENT_DIR / "figures"
MANUAL_LABELS_FILE = DATA_DIR / "manual-sampling-25-artworks.json"

FILES_TO_REMOVE = [
    "empty_p5functions.json",
    "less_than_3_p5functions.json",
]

TOP_N = 25

ALLOWED_LABELS_BY_GROUP = {
    "entities": {
        "processed_audio",
        "processed_image",
        "processed_text",
        "synthesized_sound",
        "synthesized_text",
        "synthesized_image",
        "randomness",
    },
    "interaction": {"yes", "no"},
    "outcome": {"visual", "auditory", "static", "time_based"},
}


# PROCESS PREDICTIONS
def normalize_path(path) -> str:
    path = str(path)
    marker = "/artworks/src/"

    if marker in path:
        return path.split(marker, 1)[-1].lstrip("/")

    return path.lstrip("/")


files_to_remove = []
for filename in FILES_TO_REMOVE:
    file_path = DATA_DIR / filename

    if not file_path.exists():
        continue

    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    for item in data:
        if "artwork" in item:
            files_to_remove.append(normalize_path(item["artwork"]))

files_to_remove = set(files_to_remove)

with PREDICTIONS_FILE.open("r", encoding="utf-8") as file:
    raw_predictions = json.load(file)

clean_predictions = []

for item in raw_predictions:
    item["file_path"] = normalize_path(item["file_path"])

    if item["file_path"] in files_to_remove:
        continue

    labels = item.get("predicted_labels", {})

    for group in ["entities", "interaction", "outcome"]:
        values = labels.get(group, [])

        if values is None:
            values = []
        elif isinstance(values, str):
            values = [values]
        elif not isinstance(values, list):
            values = []

        labels[group] = [
            value
            for value in values
            if value in ALLOWED_LABELS_BY_GROUP[group]
        ]

    outcomes = set(labels["outcome"])

    if "static" in outcomes and "time_based" in outcomes:
        continue

    item["predicted_labels"] = labels
    item["label_combination"] = (
        f"entities={labels.get('entities', [])} | "
        f"interaction={labels.get('interaction', [])} | "
        f"outcome={labels.get('outcome', [])}"
    )

    clean_predictions.append(item)

with (EXPERIMENT_DIR / "clean_artworks_label_prediction.json").open("w", encoding="utf-8") as file:
    json.dump(clean_predictions, file, indent=2, ensure_ascii=False)


# PLOTS
def plot_label_group_counts(preds: list[dict], figures_dir: Path) -> None:
    label_groups = ["entities", "interaction", "outcome"]
    counts = {}

    for group in label_groups:
        counter = Counter()
        for pred in preds:
            labels = pred.get("predicted_labels", {}).get(group, [])
            counter.update(labels)
        counts[group] = counter

    total_files = len(preds)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for ax, group in zip(axes, label_groups):
        counter = counts[group]
        labels = list(counter.keys())
        values = list(counter.values())

        ax.bar(labels, values)
        ax.set_title(group)
        ax.set_ylabel("Number of files")
        ax.tick_params(axis="x", rotation=45)

    fig.suptitle(f"Predicted Labels Count Across {total_files} Files", fontsize=16)
    fig.tight_layout()

    figures_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figures_dir / "predicted_label_counts.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_label_combination_distribution(preds: list[dict], figures_dir: Path) -> None:
    label_counts = Counter(pred["label_combination"] for pred in preds)
    sorted_items = label_counts.most_common()

    labels = [item[0] for item in sorted_items]
    values = [item[1] for item in sorted_items]

    fig, ax = plt.subplots(figsize=(12, max(5, len(labels) * 0.35)))

    ax.barh(labels, values)
    ax.set_xlabel("Number of files")
    ax.set_ylabel("Label set")
    ax.set_title(f"Distribution of Concatenated Label Sets Across {len(preds)} Files")
    ax.invert_yaxis()

    fig.tight_layout()

    figures_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figures_dir / "label_combination_distribution.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def build_plot_data(preds: list[dict]) -> pd.DataFrame:
    rows = []

    for pred in preds:
        labels = pred["predicted_labels"]

        entities = labels.get("entities", [])
        interactions = labels.get("interaction", [])
        outcomes = labels.get("outcome", [])

        modality_outcomes = [
            x for x in outcomes
            if x in ["visual", "auditory"]
        ]

        axis_label = " | ".join([
            "entities=" + ", ".join(entities),
            "outcome=" + ", ".join(modality_outcomes),
        ])

        time_outcomes = [
            x for x in outcomes
            if x in ["static", "time_based"]
        ]

        for interaction in interactions:
            for time_outcome in time_outcomes:
                rows.append({
                    "axis_label": axis_label,
                    "color_group": f"interaction={interaction} | outcome={time_outcome}",
                })

    df_plot = pd.DataFrame(rows)

    if df_plot.empty:
        return pd.DataFrame()

    plot_data = pd.crosstab(
        df_plot["axis_label"],
        df_plot["color_group"],
    )

    plot_data["total"] = plot_data.sum(axis=1)

    plot_data = (
        plot_data
        .sort_values("total", ascending=False)
        .drop(columns="total")
    )

    return plot_data


def plot_full_stacked_distribution(
    plot_data: pd.DataFrame,
    total_files: int,
    figures_dir: Path,
) -> None:
    if plot_data.empty:
        return

    ax = plot_data.plot(
        kind="barh",
        stacked=True,
        figsize=(18, max(5, len(plot_data) * 0.35)),
    )

    fig = ax.get_figure()

    ax.set_xlabel("Number of files")
    ax.set_ylabel("Entity + visual/auditory outcome")
    ax.set_title(f"Distribution of Labels Across {total_files} Files")

    ax.legend(
        loc="upper right",
        bbox_to_anchor=(1, 0.90),
    )

    ax.invert_yaxis()
    fig.tight_layout()

    figures_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figures_dir / "label_distribution_stacked_full.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_top_label_groups_with_others(
    plot_data: pd.DataFrame,
    total_files: int,
    figures_dir: Path,
    top_n: int = 25,
) -> None:
    if plot_data.empty:
        return

    plot_data_with_total = plot_data.copy()
    plot_data_with_total["total"] = plot_data_with_total.sum(axis=1)
    plot_data_with_total = plot_data_with_total.sort_values("total", ascending=False)

    top_data = plot_data_with_total.head(top_n).drop(columns="total")
    other_data = plot_data_with_total.iloc[top_n:].drop(columns="total")

    if len(other_data) > 0:
        other_row = other_data.sum(axis=0).to_frame().T
        other_row.index = ["Others"]
        plot_data_top = pd.concat([top_data, other_row])
    else:
        plot_data_top = top_data

    ax = plot_data_top.plot(
        kind="barh",
        stacked=True,
        figsize=(12, max(5, len(plot_data_top) * 0.35)),
    )

    fig = ax.get_figure()

    ax.set_xlabel("Number of files")
    ax.set_ylabel("Entity + visual/auditory outcome")
    ax.set_title(f"Top {top_n} Label Groups + Others Across {total_files} Files")

    ax.legend(
        loc="upper right",
        bbox_to_anchor=(1, 0.75),
    )

    ax.invert_yaxis()
    fig.tight_layout()

    figures_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figures_dir / f"top_{top_n}_label_groups_with_others_stacked.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_top_label_groups_with_others_outline(
    plot_data: pd.DataFrame,
    total_files: int,
    figures_dir: Path,
    top_n: int = 25,
) -> None:
    if plot_data.empty:
        return

    plot_data_clean = plot_data.drop(columns=["total"], errors="ignore")

    totals = plot_data_clean.sum(axis=1)
    plot_data_sorted = plot_data_clean.loc[
        totals.sort_values(ascending=False).index
    ]

    top_data = plot_data_sorted.head(top_n)
    other_total = plot_data_sorted.iloc[top_n:].sum().sum()
    has_others = other_total > 0

    y_labels = list(top_data.index)
    if has_others:
        y_labels.append("Others")

    y = np.arange(len(y_labels))

    fig, ax = plt.subplots(
        figsize=(18, max(5, len(y_labels) * 0.35)),
    )

    left = np.zeros(len(top_data))

    for col in top_data.columns:
        values = top_data[col].values

        ax.barh(
            y[:len(top_data)],
            values,
            left=left,
            label=col,
        )

        left += values

    if has_others:
        ax.barh(
            y[-1],
            other_total,
            facecolor="none",
            edgecolor="black",
            linewidth=1.5,
        )

    ax.set_yticks(y)
    ax.set_yticklabels(y_labels)

    ax.set_xlabel("Number of files")
    ax.set_ylabel("Entity + visual/auditory outcome")
    ax.set_title(f"Top {top_n} Label Groups + Others Across {total_files} Files")

    ax.legend(
        loc="upper right",
        bbox_to_anchor=(1, 0.85),
    )

    ax.invert_yaxis()
    fig.tight_layout()

    figures_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figures_dir / f"top_{top_n}_label_groups_with_others_outline.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


# MANUAL COMPARISON

if MANUAL_LABELS_FILE.exists():
    with MANUAL_LABELS_FILE.open("r", encoding="utf-8") as file:
        manual_data = json.load(file)

    predictions_by_path = {
        normalize_path(item["file_path"]): item
        for item in clean_predictions
    }

    manual_by_path = {
        normalize_path(item["file_path"]): item
        for item in manual_data
        if "manual_labels" in item
    }

    error_rows = []

    for file_path, manual_item in manual_by_path.items():
        prediction_item = predictions_by_path.get(file_path)

        if prediction_item is None:
            continue

        manual_labels = manual_item["manual_labels"]
        predicted_labels = prediction_item["predicted_labels"]

        missing_count = 0
        extra_count = 0
        missing_labels = []
        extra_labels = []

        for group in ["entities", "interaction", "outcome"]:
            manual_values = manual_labels.get(group, [])
            predicted_values = predicted_labels.get(group, [])

            if isinstance(manual_values, str):
                manual_values = [manual_values]
            if isinstance(predicted_values, str):
                predicted_values = [predicted_values]

            missing = set(manual_values) - set(predicted_values)
            extra = set(predicted_values) - set(manual_values)

            missing_count += len(missing)
            extra_count += len(extra)

            missing_labels.extend([f"{group}: {label}" for label in sorted(missing)])
            extra_labels.extend([f"{group}: {label}" for label in sorted(extra)])

        error_rows.append({
            "file_path": file_path,
            "missing_errors": missing_count,
            "extra_errors": extra_count,
            "total_errors": missing_count + extra_count,
            "missing_labels": missing_labels,
            "extra_labels": extra_labels,
        })

    errors_df = pd.DataFrame(error_rows)

    if not errors_df.empty:
        with (EXPERIMENT_DIR / "manual_prediction_errors.json").open("w", encoding="utf-8") as file:
            json.dump(errors_df.to_dict(orient="records"), file, indent=2, ensure_ascii=False)

        errors_plot = (
            errors_df
            .sort_values("total_errors", ascending=False)
            .set_index("file_path")[["missing_errors", "extra_errors"]]
        )

        ax = errors_plot.plot(
            kind="barh",
            stacked=True,
            figsize=(12, max(5, len(errors_plot) * 0.35)),
        )

        fig = ax.get_figure()
        ax.set_xlabel("Number of errors")
        ax.set_ylabel("File path")
        ax.set_title(f"Prediction Errors Across {len(errors_df)} Manual Files")
        fig.tight_layout()

        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(FIGURES_DIR / "manual_prediction_errors_stacked.png", dpi=300, bbox_inches="tight")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8, 5))

        ax.hist(
            errors_df["total_errors"],
            bins=range(errors_df["total_errors"].max() + 2),
            align="left",
            edgecolor="black",
        )

        ax.set_xlabel("Number of errors per file")
        ax.set_ylabel("Number of files")
        ax.set_title(f"Histogram of Prediction Errors Across {len(errors_df)} Files")
        ax.set_xticks(range(errors_df["total_errors"].max() + 1))

        fig.tight_layout()
        fig.savefig(FIGURES_DIR / "manual_prediction_errors_histogram.png", dpi=300, bbox_inches="tight")
        plt.close(fig)

    manual_paths = {
        normalize_path(item["file_path"])
        for item in manual_data
        if "manual_labels" in item
    }

    prediction_paths = {
        normalize_path(item["file_path"])
        for item in clean_predictions
    }

    missing_in_predictions = sorted(manual_paths - prediction_paths)

    without_manual_labels = [
        normalize_path(item["file_path"])
        for item in manual_data
        if "manual_labels" not in item
    ]


# RUN PLOTS
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

plot_label_group_counts(clean_predictions, FIGURES_DIR)
plot_label_combination_distribution(clean_predictions, FIGURES_DIR)

plot_data = build_plot_data(clean_predictions)

plot_full_stacked_distribution(
    plot_data=plot_data,
    total_files=len(clean_predictions),
    figures_dir=FIGURES_DIR,
)

plot_top_label_groups_with_others(
    plot_data=plot_data,
    total_files=len(clean_predictions),
    figures_dir=FIGURES_DIR,
    top_n=TOP_N,
)

plot_top_label_groups_with_others_outline(
    plot_data=plot_data,
    total_files=len(clean_predictions),
    figures_dir=FIGURES_DIR,
    top_n=TOP_N,
)

print("\nDone.")
print(f"Raw predictions: {len(raw_predictions)}")
print(f"Files removed by preprocessing filters: {len(raw_predictions) - len(clean_predictions)}")
print(f"Clean predictions: {len(clean_predictions)}")
print(f"JSON outputs saved in: {EXPERIMENT_DIR}")
print(f"PNG figures saved in: {FIGURES_DIR}")
