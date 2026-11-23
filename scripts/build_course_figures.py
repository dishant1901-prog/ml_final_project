#!/usr/bin/env python3
"""Build deterministic figures used by the course report."""

from pathlib import Path
import os
import shutil

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("SOURCE_DATE_EPOCH", "1767225600")
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache" / "matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np


OUT = ROOT / "course-report" / "figures"


def _style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "savefig.dpi": 220,
    })


def architecture():
    fig, ax = plt.subplots(figsize=(7.15, 1.85))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    boxes = [
        (0.15, 1.65, 1.65, 0.8, "Free inputs", "S1/S2 · DEM · OSM", "#dbeafe"),
        (2.10, 1.65, 1.65, 0.8, "Quality control", "same orbit · masks", "#e0f2fe"),
        (4.05, 1.65, 1.75, 0.8, "Hazard evidence", "water · change · unknown", "#fef3c7"),
        (6.15, 1.65, 1.65, 0.8, "Exposure + graph", "links · settlements", "#dcfce7"),
        (8.10, 1.65, 1.75, 0.8, "Evidence bundle", "map · GeoJSON · PDF", "#f3e8ff"),
        (4.05, 0.35, 1.75, 0.75, "Registered UNet", "optional; fail closed", "#fee2e2"),
        (6.15, 0.35, 1.65, 0.75, "Claim ledger", "path + checksum", "#ede9fe"),
        (8.10, 0.35, 1.75, 0.75, "Bilingual copilot", "cited EN/NE answers", "#fce7f3"),
    ]
    for x, y, w, h, title, sub, color in boxes:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.08",
                                    facecolor=color, edgecolor="#334155", linewidth=0.8))
        ax.text(x + w/2, y + h*0.64, title, ha="center", va="center", weight="bold")
        ax.text(x + w/2, y + h*0.29, sub, ha="center", va="center", fontsize=7, color="#334155")
    for x1, x2 in ((1.80, 2.10), (3.75, 4.05), (5.80, 6.15), (7.80, 8.10)):
        ax.annotate("", (x2, 2.05), (x1, 2.05), arrowprops={"arrowstyle": "->", "lw": 1, "color": "#475569"})
    ax.annotate("", (4.9, 1.65), (4.9, 1.10), arrowprops={"arrowstyle": "->", "lw": 1, "color": "#475569"})
    ax.annotate("", (6.15, 0.72), (5.80, 0.72), arrowprops={"arrowstyle": "->", "lw": 1, "color": "#475569"})
    ax.annotate("", (8.10, 0.72), (7.80, 0.72), arrowprops={"arrowstyle": "->", "lw": 1, "color": "#475569"})
    fig.tight_layout(pad=0.1)
    fig.savefig(OUT / "architecture.pdf", bbox_inches="tight", metadata={"Creator": "HimaRoad report build"})
    plt.close(fig)


def results():
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 2.25), gridspec_kw={"width_ratios": [1.12, 1]})
    metrics = ["Precision", "Recall", "IoU", "F1"]
    baseline = [0.8835, 0.6629, 0.6096, 0.7575]
    unet = [0.8008, 0.9457, 0.7656, 0.8672]
    x = np.arange(len(metrics))
    axes[0].bar(x - 0.18, baseline, 0.36, label="Rule baseline", color="#0f766e")
    axes[0].bar(x + 0.18, unet, 0.36, label="Selected UNet", color="#2563eb")
    axes[0].set_xticks(x, metrics)
    axes[0].set_ylim(0, 1.05)
    axes[0].set_ylabel("Score")
    axes[0].set_title("Kuro Siwo development set (not blind)")
    axes[0].legend(frameon=False, fontsize=7, loc="lower right")
    axes[0].grid(axis="y", alpha=0.2)

    events = ["Teesta", "Melamchi", "Chamoli"]
    positives = np.array([81, 970, 247])
    detected_rule = np.array([11, 13, 0])
    detected_unet = np.array([0, 0, 0])
    axes[1].barh(events, positives, color="#e2e8f0", label="Human-labelled new water")
    axes[1].barh(events, detected_rule, color="#f59e0b", label="Rule true positives")
    axes[1].scatter(detected_unet, events, color="#dc2626", marker="x", s=30, label="UNet true positives (0)")
    axes[1].set_xscale("symlog", linthresh=1)
    axes[1].set_xlabel("Pixels (symlog scale)")
    axes[1].set_title("Once-only Himalayan windows")
    axes[1].legend(frameon=False, fontsize=6.5, loc="lower right")
    axes[1].grid(axis="x", alpha=0.2)
    fig.tight_layout(pad=0.6)
    fig.savefig(OUT / "model-results.pdf", bbox_inches="tight", metadata={"Creator": "HimaRoad report build"})
    plt.close(fig)


def case_study():
    fig, ax = plt.subplots(figsize=(3.45, 2.15))
    labels = ["Broad cut-offs", "Strict cut-offs", "Likely links"]
    event = [22, 19, 16]
    control = [19, 0, 0]
    x = np.arange(len(labels))
    ax.bar(x - 0.18, event, 0.36, color="#dc2626", label="26 Aug event run")
    ax.bar(x + 0.18, control, 0.36, color="#94a3b8", label="10 Aug pre-event control")
    ax.set_xticks(x, labels, rotation=14, ha="right")
    ax.set_ylabel("Count")
    ax.set_title("Trishuli event/control sensitivity")
    ax.legend(frameon=False, fontsize=7)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout(pad=0.5)
    fig.savefig(OUT / "case-study.pdf", bbox_inches="tight", metadata={"Creator": "HimaRoad report build"})
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    _style()
    architecture()
    results()
    case_study()
    source = ROOT / "data" / "validation" / "ux-polished" / "desktop.png"
    dashboard = OUT / "dashboard.png"
    if source.is_file():
        shutil.copyfile(source, dashboard)
    elif dashboard.is_file():
        print(f"Using tracked validated interface capture: {dashboard}")
    else:
        raise SystemExit(
            f"Missing both raw and tracked validated interface captures: {source}, {dashboard}"
        )
    print(f"Built report figures in {OUT}")


if __name__ == "__main__":
    main()
