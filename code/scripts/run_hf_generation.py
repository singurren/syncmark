#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from syncmark.hf_adapter import HFGenerationConfig, SyncMarkCausalLM


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate SyncMark-watermarked text with a local HF causal LM.")
    p.add_argument("--prompt", type=str, required=True)
    p.add_argument("--message", type=str, default="1011010010010110")
    p.add_argument("--model", type=str, default="meta-llama/Llama-3.1-8B-Instruct")
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--max_new_tokens", type=int, default=200)
    p.add_argument("--delta", type=float, default=1.5)
    p.add_argument("--out_text", type=Path, default=Path("results/generated_syncmark.txt"))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = HFGenerationConfig(
        model_name_or_path=args.model,
        device=args.device,
        max_new_tokens=args.max_new_tokens,
        delta=args.delta,
    )
    watermarker = SyncMarkCausalLM(cfg)
    text = watermarker.generate(args.prompt, args.message, message_bits=len(args.message))
    args.out_text.parent.mkdir(parents=True, exist_ok=True)
    args.out_text.write_text(text, encoding="utf-8")
    print(f"[OK] wrote {args.out_text}")


if __name__ == "__main__":
    main()
