from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path

import torch
from transformers import AutoTokenizer

from syncmark.alignment import AlignmentWeights, align_and_decode
from syncmark.framing import build_layout, check_crc
from syncmark.utils import bits_to_str, str_to_bits

try:
    from .detect_watermark_dump import WatermarkDetector
    from .run_real_syncmark_drift_smoke import AttackSpec, attack_token_ids, parse_attack_spec, parse_lengths
    from .syncmark_support import bit_accuracy, decode_syncmark_position_vote, majority_bit
    from .utils import read_json_file, read_jsonl_file
except ImportError:
    from detect_watermark_dump import WatermarkDetector
    from run_real_syncmark_drift_smoke import AttackSpec, attack_token_ids, parse_attack_spec, parse_lengths
    from syncmark_support import bit_accuracy, decode_syncmark_position_vote, majority_bit
    from utils import read_json_file, read_jsonl_file


@dataclass(frozen=True)
class WeightPreset:
    name: str
    weights: AlignmentWeights


def parse_anchor_lengths(raw: str) -> list[int]:
    values = [int(part) for part in raw.split(",") if part.strip()]
    if not values or any(value <= 0 for value in values):
        raise argparse.ArgumentTypeError("anchor lengths must be a comma-separated list of positive integers")
    return values


def default_attack_specs() -> list[AttackSpec]:
    return [
        AttackSpec("clean", 0.0, 0.0, 0.0),
        AttackSpec("delete5", 0.05, 0.0, 0.0),
        AttackSpec("delete10", 0.10, 0.0, 0.0),
        AttackSpec("delete15", 0.15, 0.0, 0.0),
        AttackSpec("insert5", 0.0, 0.05, 0.0),
        AttackSpec("insert10", 0.0, 0.10, 0.0),
        AttackSpec("mixed5", 0.025, 0.025, 0.0),
        AttackSpec("mixed10", 0.05, 0.05, 0.0),
    ]


def weight_presets() -> list[WeightPreset]:
    return [
        WeightPreset("current", AlignmentWeights(anchor_match=2.0, anchor_mismatch=-1.0, payload_match=0.35, gap=-2.0, anchor_gap=-2.5)),
        WeightPreset("default", AlignmentWeights()),
        WeightPreset("loose_gap", AlignmentWeights(anchor_match=2.0, anchor_mismatch=-1.0, payload_match=0.35, gap=-1.0, anchor_gap=-1.5)),
        WeightPreset("anchor_heavy", AlignmentWeights(anchor_match=3.0, anchor_mismatch=-2.0, payload_match=0.25, gap=-1.2, anchor_gap=-2.2)),
    ]


def decode_alignment_with_weights(
    obs_bits: list[int],
    message_bits: str,
    text_length: int,
    anchor_len: int,
    key: str,
    weights: AlignmentWeights,
) -> dict[str, object]:
    layout = build_layout(str_to_bits(message_bits), text_length=text_length, anchor_len=anchor_len, key=key)
    decoded = align_and_decode(list(map(int, obs_bits)), layout, message_len=len(message_bits), weights=weights)
    recovered = bits_to_str(decoded.recovered_bits)
    return {
        "recovered_bits": recovered,
        "bit_accuracy": bit_accuracy(message_bits, recovered),
        "exact_recovery": float(recovered == message_bits),
        "crc_pass": bool(decoded.crc_pass),
        "alignment_score": float(decoded.alignment_score),
        "n_aligned_payload_observations": int(decoded.n_aligned_payload_observations),
    }


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, int, int, str, str], list[dict[str, object]]] = {}
    for row in rows:
        key = (
            str(row["attack"]),
            int(row["length"]),
            int(row["anchor_len"]),
            str(row["weight_preset"]),
            str(row["decoder"]),
        )
        groups.setdefault(key, []).append(row)

    summary_rows: list[dict[str, object]] = []
    for (attack, length, anchor_len, weight_preset, decoder), group in sorted(groups.items()):
        hit_rates = [float(row["hit_rate"]) for row in group]
        exact = [float(row["exact_recovery"]) for row in group]
        crc = [float(row["crc_pass"] is True or str(row["crc_pass"]).lower() == "true") for row in group]
        summary_rows.append(
            {
                "attack": attack,
                "length": length,
                "anchor_len": anchor_len,
                "weight_preset": weight_preset,
                "decoder": decoder,
                "n": len(group),
                "mean_hit_rate": sum(hit_rates) / len(hit_rates),
                "mean_ber": 1.0 - (sum(hit_rates) / len(hit_rates)),
                "exact_rate": sum(exact) / len(exact),
                "crc_pass_rate": sum(crc) / len(crc),
            }
        )
    return summary_rows


def compare_summary(summary_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, int, int, str], dict[str, dict[str, object]]] = {}
    for row in summary_rows:
        key = (str(row["attack"]), int(row["length"]), int(row["anchor_len"]), str(row["weight_preset"]))
        grouped.setdefault(key, {})[str(row["decoder"])] = row

    comparisons: list[dict[str, object]] = []
    for (attack, length, anchor_len, weight_preset), decoders in sorted(grouped.items()):
        position = decoders.get("syncmark_position_vote")
        alignment = decoders.get("syncmark_alignment")
        if not position or not alignment:
            continue
        comparisons.append(
            {
                "attack": attack,
                "length": length,
                "anchor_len": anchor_len,
                "weight_preset": weight_preset,
                "n": alignment["n"],
                "position_hit_rate": position["mean_hit_rate"],
                "alignment_hit_rate": alignment["mean_hit_rate"],
                "hit_delta_alignment_minus_position": float(alignment["mean_hit_rate"]) - float(position["mean_hit_rate"]),
                "position_exact_rate": position["exact_rate"],
                "alignment_exact_rate": alignment["exact_rate"],
                "exact_delta_alignment_minus_position": float(alignment["exact_rate"]) - float(position["exact_rate"]),
                "alignment_crc_pass_rate": alignment["crc_pass_rate"],
            }
        )
    return comparisons


def rank_configs(comparisons: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[int, str], list[dict[str, object]]] = {}
    for row in comparisons:
        if str(row["attack"]) == "clean":
            continue
        key = (int(row["anchor_len"]), str(row["weight_preset"]))
        groups.setdefault(key, []).append(row)

    ranked: list[dict[str, object]] = []
    for (anchor_len, weight_preset), group in sorted(groups.items()):
        hit_deltas = [float(row["hit_delta_alignment_minus_position"]) for row in group]
        exact_deltas = [float(row["exact_delta_alignment_minus_position"]) for row in group]
        positive_hit = [delta > 0.0 for delta in hit_deltas]
        ranked.append(
            {
                "anchor_len": anchor_len,
                "weight_preset": weight_preset,
                "n_cells": len(group),
                "mean_hit_delta": sum(hit_deltas) / len(hit_deltas),
                "mean_exact_delta": sum(exact_deltas) / len(exact_deltas),
                "positive_hit_delta_rate": sum(positive_hit) / len(positive_hit),
                "min_hit_delta": min(hit_deltas),
                "max_hit_delta": max(hit_deltas),
            }
        )
    ranked.sort(key=lambda row: (float(row["mean_hit_delta"]), float(row["mean_exact_delta"]), float(row["positive_hit_delta_rate"])), reverse=True)
    return ranked


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"no rows to write for {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Grid search real SyncMark+BiMark drift decoder settings.")
    parser.add_argument("--data_dir", required=True, help="Directory name under output_dump/")
    parser.add_argument("--max_items", type=int, default=20)
    parser.add_argument("--target_lengths", type=parse_lengths, default=parse_lengths("50,100,150"))
    parser.add_argument("--anchor_lens", type=parse_anchor_lengths, default=None)
    parser.add_argument("--allow_anchor_mismatch", action="store_true")
    parser.add_argument("--seed", type=int, default=5151)
    parser.add_argument("--output_prefix", default=None)
    parser.add_argument("--attack_spec", type=parse_attack_spec, action="append", default=None)
    args = parser.parse_args()

    attack_specs = args.attack_spec or default_attack_specs()
    presets = weight_presets()

    base = Path("output_dump") / args.data_dir
    params = read_json_file(str(base / "generation_params.json"))
    content = read_jsonl_file(str(base / "generation_text.jsonl"))
    if not params.get("syncmark_outer", False) and params.get("schedule_mode") != "position_schedule":
        raise SystemExit("This grid expects a SyncMark outer / position_schedule generation dump.")
    generated_anchor_len = int(params.get("syncmark_anchor_len", 6))
    anchor_lens = args.anchor_lens or [generated_anchor_len]
    mismatched_anchor_lens = [value for value in anchor_lens if value != generated_anchor_len]
    if mismatched_anchor_lens and not args.allow_anchor_mismatch:
        raise SystemExit(
            "Cannot validly scan anchor lengths on an existing dump because the generated schedule is fixed. "
            f"This dump was generated with syncmark_anchor_len={generated_anchor_len}; "
            f"mismatched requested values were {mismatched_anchor_lens}. "
            "Regenerate text for each anchor length, or pass --allow_anchor_mismatch for diagnostic-only analysis."
        )

    tokenizer = AutoTokenizer.from_pretrained(params["model_name"])
    tokenizer.pad_token = tokenizer.eos_token

    vocab_size = int(params["vocab_size"])
    seeds = params.get("partition_seeds", [0])
    weights = params.get("prob_delta", [1.0])
    if not isinstance(weights, list):
        weights = [weights]
    if len(weights) == 1 and len(seeds) > 1:
        weights = weights * len(seeds)

    detector = WatermarkDetector(tokenizer, vocab_size, window_size=int(params.get("window_size", 2)), gamma=0.5)
    original_msg = params.get("original_message", "")
    syncmark_key = params.get("syncmark_key", "syncmark-bimark-real")
    c_key = int(params.get("c_key", 8214793))

    observations: list[dict[str, object]] = []
    skipped = 0
    for item_idx, item in enumerate(content[: args.max_items]):
        text = item.get("generation_text", "")
        if not text:
            skipped += 1
            continue
        clean_tokens = tokenizer.encode(text, add_special_tokens=False)
        if not clean_tokens:
            skipped += 1
            continue
        for spec_idx, spec in enumerate(attack_specs):
            rng = random.Random(args.seed + item_idx * 1009 + spec_idx * 9176)
            attacked_tokens = attack_token_ids(clean_tokens, spec, vocab_size=vocab_size, rng=rng)
            token_tensor = torch.tensor(attacked_tokens, dtype=torch.long)
            for target_len in args.target_lengths:
                if len(token_tensor) < target_len:
                    continue
                current_tokens = token_tensor[:target_len]
                obs_bits = detector.extract_position_schedule_observed_bits(
                    detect_gen_tokens=current_tokens,
                    partition_seeds=seeds,
                    c_key=c_key,
                    weight=weights,
                )
                observations.append(
                    {
                        "item_idx": item_idx,
                        "prompt_idx": item.get("prompt_idx", ""),
                        "attack": spec.name,
                        "p_del": spec.p_del,
                        "p_ins": spec.p_ins,
                        "p_sub": spec.p_sub,
                        "length": target_len,
                        "clean_token_len": len(clean_tokens),
                        "attacked_token_len": len(attacked_tokens),
                        "obs_bits": obs_bits,
                    }
                )

    rows: list[dict[str, object]] = []
    for obs in observations:
        obs_bits = obs["obs_bits"]
        if not isinstance(obs_bits, list):
            continue
        for anchor_len in anchor_lens:
            position_decoded = decode_syncmark_position_vote(
                obs_bits,
                original_msg,
                text_length=int(obs["length"]),
                anchor_len=anchor_len,
                key=syncmark_key,
            )
            for preset in presets:
                decoded_rows = {
                    "syncmark_position_vote": position_decoded,
                    "syncmark_alignment": decode_alignment_with_weights(
                        obs_bits,
                        original_msg,
                        text_length=int(obs["length"]),
                        anchor_len=anchor_len,
                        key=syncmark_key,
                        weights=preset.weights,
                    ),
                }
                for decoder_name, decoded in decoded_rows.items():
                    rows.append(
                        {
                            "item_idx": obs["item_idx"],
                            "prompt_idx": obs["prompt_idx"],
                            "attack": obs["attack"],
                            "p_del": obs["p_del"],
                            "p_ins": obs["p_ins"],
                            "p_sub": obs["p_sub"],
                            "length": obs["length"],
                            "anchor_len": anchor_len,
                            "weight_preset": preset.name,
                            "decoder": decoder_name,
                            "hit_rate": decoded["bit_accuracy"],
                            "ber": 1.0 - float(decoded["bit_accuracy"]),
                            "exact_recovery": decoded["exact_recovery"],
                            "crc_pass": decoded.get("crc_pass"),
                            "observed_bits_len": len(obs_bits),
                            "clean_token_len": obs["clean_token_len"],
                            "attacked_token_len": obs["attacked_token_len"],
                        }
                    )

    if not rows:
        raise SystemExit("No grid rows were produced.")

    prefix = args.output_prefix or f"syncmark_drift_grid_n{args.max_items}_seed{args.seed}"
    rows_path = base / f"{prefix}.csv"
    summary_path = base / f"{prefix}_summary.csv"
    comparison_path = base / f"{prefix}_comparison.csv"
    ranking_path = base / f"{prefix}_ranking.csv"
    metadata_path = base / f"{prefix}_metadata.json"

    summary_rows = summarize(rows)
    comparison_rows = compare_summary(summary_rows)
    ranking_rows = rank_configs(comparison_rows)
    write_csv(rows_path, rows)
    write_csv(summary_path, summary_rows)
    write_csv(comparison_path, comparison_rows)
    write_csv(ranking_path, ranking_rows)
    metadata_path.write_text(
        json.dumps(
            {
                "data_dir": args.data_dir,
                "max_items": args.max_items,
                "target_lengths": args.target_lengths,
                "anchor_lens": anchor_lens,
                "generated_anchor_len": generated_anchor_len,
                "allow_anchor_mismatch": args.allow_anchor_mismatch,
                "seed": args.seed,
                "skipped_items": skipped,
                "attack_specs": [spec.__dict__ for spec in attack_specs],
                "weight_presets": [
                    {
                        "name": preset.name,
                        "weights": preset.weights.__dict__,
                    }
                    for preset in presets
                ],
                "rows_csv": str(rows_path),
                "summary_csv": str(summary_path),
                "comparison_csv": str(comparison_path),
                "ranking_csv": str(ranking_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote rows: {len(rows)} -> {rows_path}")
    print(f"Wrote summary: {len(summary_rows)} -> {summary_path}")
    print(f"Wrote comparison: {len(comparison_rows)} -> {comparison_path}")
    print(f"Wrote ranking: {len(ranking_rows)} -> {ranking_path}")
    print(f"Wrote metadata: {metadata_path}")
    print("Top ranked configs:")
    for row in ranking_rows[:5]:
        print(row)


if __name__ == "__main__":
    main()
