from __future__ import annotations

from typing import Iterable, List


def chunked(seq: Iterable[int], n: int) -> List[list[int]]:
    seq = list(seq)
    return [seq[i : i + n] for i in range(0, len(seq), n)]


def majority_bit(bits: list[int], default: int = 0) -> int:
    if not bits:
        return default
    ones = sum(bits)
    zeros = len(bits) - ones
    return 1 if ones >= zeros else 0


def bit_accuracy(a: list[int], b: list[int]) -> float:
    if len(a) != len(b):
        raise ValueError("Bit strings must have the same length.")
    if not a:
        return 1.0
    return sum(int(x == y) for x, y in zip(a, b)) / len(a)


def exact_match(a: list[int], b: list[int]) -> float:
    return float(a == b)


def bits_to_str(bits: Iterable[int]) -> str:
    return "".join(str(int(b)) for b in bits)


def str_to_bits(text: str) -> list[int]:
    clean = text.strip().replace(" ", "")
    if any(ch not in {"0", "1"} for ch in clean):
        raise ValueError("Bit string must contain only 0/1.")
    return [int(ch) for ch in clean]
