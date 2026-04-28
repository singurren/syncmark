#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from syncmark.channel import IDSChannelConfig
from syncmark.simulation import benchmark_methods


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run synthetic short-text SyncMark benchmarks.")
    p.add_argument("--out_csv", type=Path, default=Path("results/synthetic_metrics.csv"))
    p.add_argument("--trials", type=int, default=400)
    p.add_argument("--lengths", type=int, nargs="+", default=[80, 120, 160, 240, 320])
    p.add_argument("--p_flip", type=float, default=0.10)
    p.add_argument("--p_sub", type=float, default=0.05)
    p.add_argument("--p_del", type=float, default=0.04)
    p.add_argument("--p_ins", type=float, default=0.04)
    p.add_argument("--bursty", action="store_true")
    p.add_argument("--burst_prob", type=float, default=0.20)
    p.add_argument("--burst_max_len", type=int, default=3)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    channel_cfg = IDSChannelConfig(
        p_flip=args.p_flip,
        p_sub=args.p_sub,
        p_del=args.p_del,
        p_ins=args.p_ins,
        bursty=args.bursty,
        burst_prob=args.burst_prob,
        burst_max_len=args.burst_max_len,
    )
    df = benchmark_methods(
        methods=["repetition", "hamming74", "syncmark"],
        text_lengths=args.lengths,
        n_trials=args.trials,
        channel_cfg=channel_cfg,
    )
    df.to_csv(args.out_csv, index=False)
    print(f"[OK] wrote {args.out_csv}")
    print(df.groupby(["method", "text_length"])[["bit_accuracy", "exact_recovery", "crc_pass"]].mean().round(3))


if __name__ == "__main__":
    main()
