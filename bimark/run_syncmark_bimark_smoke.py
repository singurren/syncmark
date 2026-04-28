from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from syncmark.framing import build_layout

from .syncmark_support import (
    BiMarkLikeSignalConfig,
    apply_token_ids_attack,
    decode_message_hamming74,
    decode_message_position_vote,
    decode_syncmark_alignment,
    decode_syncmark_position_vote,
    extract_observed_bits_from_tokens,
    generate_bimark_like_tokens,
    hamming74_encode_bits,
    repeat_bits_to_length,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a small SyncMark + BiMark smoke test under token drift.")
    parser.add_argument("--trials", type=int, default=30)
    parser.add_argument("--message_bits", type=int, default=16)
    parser.add_argument("--text_length", type=int, default=160, help="Number of watermarked slots, excluding the warm-up prefix.")
    parser.add_argument("--anchor_len", type=int, default=6)
    parser.add_argument("--syncmark_key", type=str, default="syncmark-bimark-smoke")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--p_del", type=float, default=0.06)
    parser.add_argument("--p_ins", type=float, default=0.06)
    parser.add_argument("--p_sub", type=float, default=0.04)
    parser.add_argument("--vocab_size", type=int, default=4096)
    parser.add_argument("--window_size", type=int, default=2)
    parser.add_argument("--candidate_pool", type=int, default=256)
    parser.add_argument("--bias_strength", type=float, default=1.15)
    parser.add_argument("--seed_mode", choices=["position", "prefix"], default="position")
    parser.add_argument("--out_dir", type=Path, default=None)
    return parser.parse_args()


def random_bitstring(rng: np.random.Generator, n_bits: int) -> str:
    return "".join(str(int(bit)) for bit in rng.integers(0, 2, size=n_bits))


def build_out_dir(args: argparse.Namespace) -> Path:
    if args.out_dir is not None:
        return args.out_dir
    stamp = datetime.now().strftime("%Y-%m-%d_syncmark_bimark_smoke")
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / "results" / "smoke" / stamp


def main() -> None:
    args = parse_args()
    out_dir = build_out_dir(args).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = BiMarkLikeSignalConfig(
        vocab_size=args.vocab_size,
        window_size=args.window_size,
        bias_strength=args.bias_strength,
        candidate_pool=args.candidate_pool,
        seed_mode=args.seed_mode,
    )

    master_rng = np.random.default_rng(args.seed)
    rows: list[dict] = []

    for trial in range(args.trials):
        message_bits = random_bitstring(master_rng, args.message_bits)
        sync_layout = build_layout([int(bit) for bit in message_bits], text_length=args.text_length, anchor_len=args.anchor_len, key=args.syncmark_key)
        sync_schedule = "".join(str(slot.expected_bit) for slot in sync_layout)
        plain_schedule = repeat_bits_to_length(message_bits, args.text_length)
        ecc_schedule = repeat_bits_to_length(hamming74_encode_bits(message_bits), args.text_length)

        clean_plain = generate_bimark_like_tokens(plain_schedule, cfg, seed=args.seed + 1000 * trial + 1)
        clean_ecc = generate_bimark_like_tokens(ecc_schedule, cfg, seed=args.seed + 1000 * trial + 2)
        clean_sync = generate_bimark_like_tokens(sync_schedule, cfg, seed=args.seed + 1000 * trial + 3)

        attacked_plain = apply_token_ids_attack(clean_plain, p_del=args.p_del, p_ins=args.p_ins, p_sub=args.p_sub, vocab_size=args.vocab_size, seed=args.seed + 1000 * trial + 101)
        attacked_ecc = apply_token_ids_attack(clean_ecc, p_del=args.p_del, p_ins=args.p_ins, p_sub=args.p_sub, vocab_size=args.vocab_size, seed=args.seed + 1000 * trial + 102)
        attacked_sync = apply_token_ids_attack(clean_sync, p_del=args.p_del, p_ins=args.p_ins, p_sub=args.p_sub, vocab_size=args.vocab_size, seed=args.seed + 1000 * trial + 103)

        obs_plain = extract_observed_bits_from_tokens(attacked_plain, cfg)
        obs_ecc = extract_observed_bits_from_tokens(attacked_ecc, cfg)
        obs_sync = extract_observed_bits_from_tokens(attacked_sync, cfg)

        dec_plain = decode_message_position_vote(obs_plain, message_bits)
        dec_ecc = decode_message_hamming74(obs_ecc, message_bits)
        dec_sync_position = decode_syncmark_position_vote(obs_sync, message_bits, text_length=args.text_length, anchor_len=args.anchor_len, key=args.syncmark_key)
        dec_sync_align = decode_syncmark_alignment(obs_sync, message_bits, text_length=args.text_length, anchor_len=args.anchor_len, key=args.syncmark_key)

        trial_rows = {
            "bimark_position_vote": (dec_plain, len(attacked_plain), len(obs_plain)),
            "bimark_hamming74": (dec_ecc, len(attacked_ecc), len(obs_ecc)),
            "syncmark_position_vote": (dec_sync_position, len(attacked_sync), len(obs_sync)),
            "syncmark_alignment": (dec_sync_align, len(attacked_sync), len(obs_sync)),
        }

        for method, (decoded, attacked_len, observed_len) in trial_rows.items():
            rows.append(
                {
                    "trial": trial,
                    "method": method,
                    "message_bits": args.message_bits,
                    "text_length": args.text_length,
                    "anchor_len": args.anchor_len,
                    "bit_accuracy": decoded["bit_accuracy"],
                    "exact_recovery": decoded["exact_recovery"],
                    "crc_pass": decoded.get("crc_pass"),
                    "alignment_score": decoded.get("alignment_score"),
                    "clean_token_len": args.text_length + args.window_size,
                    "attacked_token_len": attacked_len,
                    "observed_bits_len": observed_len,
                    "recovered_bits": decoded["recovered_bits"],
                }
            )

    df = pd.DataFrame(rows)
    summary = (
        df.groupby("method", dropna=False)
        .agg(
            mean_bit_accuracy=("bit_accuracy", "mean"),
            mean_exact_recovery=("exact_recovery", "mean"),
            mean_crc_pass=("crc_pass", "mean"),
            mean_attacked_token_len=("attacked_token_len", "mean"),
            mean_observed_bits_len=("observed_bits_len", "mean"),
        )
        .reset_index()
        .sort_values(["mean_exact_recovery", "mean_bit_accuracy"], ascending=False)
    )

    metrics_path = out_dir / "smoke_metrics.csv"
    summary_path = out_dir / "smoke_summary.csv"
    config_path = out_dir / "smoke_config.json"

    df.to_csv(metrics_path, index=False)
    summary.to_csv(summary_path, index=False)
    config_path.write_text(
        json.dumps(
            {
                "trials": args.trials,
                "message_bits": args.message_bits,
                "text_length": args.text_length,
                "anchor_len": args.anchor_len,
                "syncmark_key": args.syncmark_key,
                "seed": args.seed,
                "attack": {"p_del": args.p_del, "p_ins": args.p_ins, "p_sub": args.p_sub},
                "signal": {
                    "vocab_size": args.vocab_size,
                    "window_size": args.window_size,
                    "candidate_pool": args.candidate_pool,
                    "bias_strength": args.bias_strength,
                    "seed_mode": args.seed_mode,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Smoke test summary:")
    print(summary.to_string(index=False))
    print(f"Saved metrics to {metrics_path}")
    print(f"Saved summary to {summary_path}")


if __name__ == "__main__":
    main()
