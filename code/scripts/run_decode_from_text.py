#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from syncmark.alignment import align_and_decode
from syncmark.framing import build_layout
from syncmark.hashing import partition_bit


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Decode SyncMark bits from a continuation text file.")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--message_bits", type=int, default=16)
    p.add_argument("--key", type=str, default="syncmark-demo-key")
    p.add_argument("--tokenizer_path", type=str, required=True, help="Tokenizer path compatible with the generated text.")
    p.add_argument("--partition_mode", choices=["position", "prefix"], default="position")
    return p.parse_args()


def main() -> None:
    from transformers import AutoTokenizer

    args = parse_args()
    tok = AutoTokenizer.from_pretrained(args.tokenizer_path, use_fast=True)
    text = args.input.read_text(encoding="utf-8")
    ids = tok(text, add_special_tokens=False).input_ids
    obs = []
    prefix = []
    for pos, token_id in enumerate(ids):
        obs.append(partition_bit(args.key, pos, token_id, prefix_tokens=prefix, mode=args.partition_mode))
        prefix.append(token_id)
    layout = build_layout([0] * args.message_bits, text_length=len(obs), anchor_len=6, key=args.key)
    decoded = align_and_decode(obs, layout, message_len=args.message_bits)
    print("Recovered bits:", "".join(str(b) for b in decoded.recovered_bits))
    print("CRC pass:", decoded.crc_pass)
    print("Alignment score:", decoded.alignment_score)


if __name__ == "__main__":
    main()
