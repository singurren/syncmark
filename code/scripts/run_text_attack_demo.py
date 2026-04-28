#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from syncmark.attacks import compound_char_attack, delete_random_words


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Apply lightweight text attacks to a text file.")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--mode", choices=["char", "word_delete"], default="char")
    p.add_argument("--n_ops", type=int, default=6)
    p.add_argument("--frac", type=float, default=0.12)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    text = args.input.read_text(encoding="utf-8")
    if args.mode == "char":
        attacked = compound_char_attack(text, n_ops=args.n_ops, seed=args.seed)
    else:
        attacked = delete_random_words(text, frac=args.frac, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(attacked, encoding="utf-8")
    print(f"[OK] wrote {args.output}")


if __name__ == "__main__":
    main()
