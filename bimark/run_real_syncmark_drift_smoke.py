from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path

import torch
from transformers import AutoTokenizer

try:
    from .detect_watermark_dump import WatermarkDetector
    from .syncmark_support import decode_syncmark_alignment, decode_syncmark_position_vote
    from .utils import read_json_file, read_jsonl_file
except ImportError:
    from detect_watermark_dump import WatermarkDetector
    from syncmark_support import decode_syncmark_alignment, decode_syncmark_position_vote
    from utils import read_json_file, read_jsonl_file


@dataclass(frozen=True)
class AttackSpec:
    name: str
    p_del: float
    p_ins: float
    p_sub: float


def parse_attack_spec(raw: str) -> AttackSpec:
    parts = raw.split(":")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "attack spec must be name:p_del:p_ins:p_sub, for example delete10:0.10:0:0"
        )
    name, p_del, p_ins, p_sub = parts
    if not name:
        raise argparse.ArgumentTypeError("attack spec name must not be empty")
    try:
        values = [float(p_del), float(p_ins), float(p_sub)]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid attack probability in {raw!r}") from exc
    if any(value < 0.0 or value > 1.0 for value in values):
        raise argparse.ArgumentTypeError("attack probabilities must be in [0, 1]")
    return AttackSpec(name=name, p_del=values[0], p_ins=values[1], p_sub=values[2])


def parse_lengths(raw: str) -> list[int]:
    lengths = [int(part) for part in raw.split(",") if part.strip()]
    if not lengths or any(length <= 0 for length in lengths):
        raise argparse.ArgumentTypeError("lengths must be a comma-separated list of positive integers")
    return lengths


def attack_token_ids(tokens: list[int], spec: AttackSpec, vocab_size: int, rng: random.Random) -> list[int]:
    attacked: list[int] = []
    for token in tokens:
        if rng.random() < spec.p_ins:
            attacked.append(rng.randrange(vocab_size))
        if rng.random() < spec.p_del:
            continue
        out_token = int(token)
        if rng.random() < spec.p_sub:
            out_token = rng.randrange(vocab_size)
        attacked.append(out_token)
    if rng.random() < spec.p_ins:
        attacked.append(rng.randrange(vocab_size))
    return attacked


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, int, str], list[dict[str, object]]] = {}
    for row in rows:
        key = (str(row["attack"]), int(row["length"]), str(row["decoder"]))
        groups.setdefault(key, []).append(row)

    summary: list[dict[str, object]] = []
    for (attack, length, decoder), group in sorted(groups.items()):
        hit_rates = [float(row["hit_rate"]) for row in group]
        exact = [float(row["exact_recovery"]) for row in group]
        observed_lens = [int(row["observed_bits_len"]) for row in group]
        attacked_lens = [int(row["attacked_token_len"]) for row in group]
        summary.append(
            {
                "attack": attack,
                "length": length,
                "decoder": decoder,
                "n": len(group),
                "mean_hit_rate": sum(hit_rates) / len(hit_rates),
                "mean_ber": 1.0 - (sum(hit_rates) / len(hit_rates)),
                "exact_rate": sum(exact) / len(exact),
                "mean_observed_bits_len": sum(observed_lens) / len(observed_lens),
                "mean_attacked_token_len": sum(attacked_lens) / len(attacked_lens),
            }
        )
    return summary


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"no rows to write for {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run token-level drift attacks on a real SyncMark+BiMark dump.")
    parser.add_argument("--data_dir", required=True, help="Directory name under output_dump/")
    parser.add_argument("--max_items", type=int, default=50)
    parser.add_argument("--target_lengths", type=parse_lengths, default=parse_lengths("25,50,100"))
    parser.add_argument("--seed", type=int, default=4242)
    parser.add_argument(
        "--attack_spec",
        type=parse_attack_spec,
        action="append",
        default=None,
        help="Repeatable name:p_del:p_ins:p_sub spec. Defaults to clean/delete10/insert10/mixed10.",
    )
    args = parser.parse_args()

    attack_specs = args.attack_spec or [
        AttackSpec("clean", 0.0, 0.0, 0.0),
        AttackSpec("delete10", 0.10, 0.0, 0.0),
        AttackSpec("insert10", 0.0, 0.10, 0.0),
        AttackSpec("mixed10", 0.05, 0.05, 0.0),
    ]

    base = Path("output_dump") / args.data_dir
    params = read_json_file(str(base / "generation_params.json"))
    content = read_jsonl_file(str(base / "generation_text.jsonl"))

    if not params.get("syncmark_outer", False) and params.get("schedule_mode") != "position_schedule":
        raise SystemExit("This drift smoke expects a SyncMark outer / position_schedule generation dump.")

    tokenizer = AutoTokenizer.from_pretrained(params["model_name"])
    tokenizer.pad_token = tokenizer.eos_token

    vocab_size = int(params["vocab_size"])
    seeds = params.get("partition_seeds", [0])
    weights = params.get("prob_delta", [1.0])
    if not isinstance(weights, list):
        weights = [weights]
    if len(weights) == 1 and len(seeds) > 1:
        weights = weights * len(seeds)

    detector = WatermarkDetector(
        tokenizer,
        vocab_size,
        window_size=int(params.get("window_size", 2)),
        gamma=0.5,
    )

    original_msg = params.get("original_message", "")
    anchor_len = int(params.get("syncmark_anchor_len", 6))
    syncmark_key = params.get("syncmark_key", "syncmark-bimark-real")
    c_key = int(params.get("c_key", 8214793))

    rows: list[dict[str, object]] = []
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
            if not attacked_tokens:
                continue

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
                decoded_rows = {
                    "syncmark_position_vote": decode_syncmark_position_vote(
                        obs_bits,
                        original_msg,
                        text_length=target_len,
                        anchor_len=anchor_len,
                        key=syncmark_key,
                    ),
                    "syncmark_alignment": decode_syncmark_alignment(
                        obs_bits,
                        original_msg,
                        text_length=target_len,
                        anchor_len=anchor_len,
                        key=syncmark_key,
                    ),
                }
                for decoder_name, decoded in decoded_rows.items():
                    rows.append(
                        {
                            "item_idx": item_idx,
                            "prompt_idx": item.get("prompt_idx", ""),
                            "attack": spec.name,
                            "p_del": spec.p_del,
                            "p_ins": spec.p_ins,
                            "p_sub": spec.p_sub,
                            "length": target_len,
                            "decoder": decoder_name,
                            "hit_rate": decoded["bit_accuracy"],
                            "ber": 1.0 - float(decoded["bit_accuracy"]),
                            "exact_recovery": decoded["exact_recovery"],
                            "crc_pass": decoded.get("crc_pass"),
                            "observed_bits_len": len(obs_bits),
                            "clean_token_len": len(clean_tokens),
                            "attacked_token_len": len(attacked_tokens),
                        }
                    )

    if not rows:
        raise SystemExit("No drift smoke rows were produced.")

    suffix = f"n{args.max_items}_seed{args.seed}"
    result_path = base / f"syncmark_drift_smoke_{suffix}.csv"
    summary_path = base / f"syncmark_drift_smoke_{suffix}_summary.csv"
    metadata_path = base / f"syncmark_drift_smoke_{suffix}_metadata.json"

    summary_rows = summarize(rows)
    write_csv(result_path, rows)
    write_csv(summary_path, summary_rows)
    metadata_path.write_text(
        json.dumps(
            {
                "data_dir": args.data_dir,
                "max_items": args.max_items,
                "target_lengths": args.target_lengths,
                "seed": args.seed,
                "skipped_items": skipped,
                "attack_specs": [spec.__dict__ for spec in attack_specs],
                "result_csv": str(result_path),
                "summary_csv": str(summary_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote rows: {len(rows)} -> {result_path}")
    print(f"Wrote summary: {len(summary_rows)} -> {summary_path}")
    print(f"Wrote metadata: {metadata_path}")


if __name__ == "__main__":
    main()
