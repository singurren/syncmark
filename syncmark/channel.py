from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class IDSChannelConfig:
    p_flip: float = 0.10
    p_sub: float = 0.05
    p_del: float = 0.04
    p_ins: float = 0.04
    bursty: bool = False
    burst_prob: float = 0.0
    burst_max_len: int = 3


def _flip(bit: int) -> int:
    return 1 - int(bit)


def apply_inner_noise(bits: list[int], p_flip: float, rng: random.Random) -> list[int]:
    out = []
    for bit in bits:
        out.append(_flip(bit) if rng.random() < p_flip else int(bit))
    return out


def apply_ids_channel(bits: list[int], cfg: IDSChannelConfig, seed: Optional[int] = None) -> list[int]:
    rng = random.Random(seed)
    corrupted = apply_inner_noise(bits, cfg.p_flip, rng)
    out: list[int] = []
    i = 0
    while i < len(corrupted):
        bit = corrupted[i]

        # Deletion
        if rng.random() < cfg.p_del:
            burst = 1
            if cfg.bursty and rng.random() < cfg.burst_prob:
                burst = rng.randint(1, cfg.burst_max_len)
            i += burst
            continue

        # Substitution
        if rng.random() < cfg.p_sub:
            bit = _flip(bit)
        out.append(bit)

        # Insertion after current symbol
        if rng.random() < cfg.p_ins:
            burst = 1
            if cfg.bursty and rng.random() < cfg.burst_prob:
                burst = rng.randint(1, cfg.burst_max_len)
            for _ in range(burst):
                out.append(rng.randint(0, 1))
        i += 1
    return out
