#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create preview plots from synthetic benchmark CSV.")
    p.add_argument("--csv", type=Path, required=True)
    p.add_argument("--out_png", type=Path, default=Path("results/synthetic_preview.png"))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.csv)
    grouped = df.groupby(["method", "text_length"], as_index=False).agg(
        bit_accuracy=("bit_accuracy", "mean"),
        exact_recovery=("exact_recovery", "mean"),
        crc_pass=("crc_pass", "mean"),
    )

    fig = plt.figure(figsize=(9, 5.4))
    ax = fig.add_subplot(1, 1, 1)
    for method, sub in grouped.groupby("method"):
        sub = sub.sort_values("text_length")
        ax.plot(sub["text_length"], sub["exact_recovery"], marker="o", label=method)
    ax.set_xlabel("Text length (marked positions)")
    ax.set_ylabel("Exact message recovery")
    ax.set_title("Synthetic preview: synchronization-aware framing under IDS edits")
    ax.set_ylim(0.0, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(frameon=False)
    fig.tight_layout()
    args.out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out_png, dpi=200)
    print(f"[OK] wrote {args.out_png}")


if __name__ == "__main__":
    main()
