from __future__ import annotations

import random
from pathlib import Path
from typing import Optional

HOMOGLYPHS = {
    "a": "а",  # Cyrillic a
    "e": "е",  # Cyrillic e
    "o": "ο",  # Greek omicron
    "p": "р",  # Cyrillic er
    "c": "с",  # Cyrillic es
    "x": "х",  # Cyrillic ha
}


def random_swap(text: str, rng: random.Random) -> str:
    if len(text) < 2:
        return text
    idx = rng.randint(0, len(text) - 2)
    chars = list(text)
    chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
    return "".join(chars)


def random_delete(text: str, rng: random.Random) -> str:
    if not text:
        return text
    idx = rng.randint(0, len(text) - 1)
    return text[:idx] + text[idx + 1 :]


def random_insert(text: str, rng: random.Random) -> str:
    idx = rng.randint(0, len(text))
    ch = rng.choice([" ", "-", ",", ".", "a", "e"])
    return text[:idx] + ch + text[idx:]


def random_homoglyph(text: str, rng: random.Random) -> str:
    candidates = [idx for idx, ch in enumerate(text) if ch.lower() in HOMOGLYPHS]
    if not candidates:
        return text
    idx = rng.choice(candidates)
    ch = text[idx]
    rep = HOMOGLYPHS[ch.lower()]
    if ch.isupper():
        rep = rep.upper()
    return text[:idx] + rep + text[idx + 1 :]


def compound_char_attack(text: str, n_ops: int = 5, seed: Optional[int] = None) -> str:
    rng = random.Random(seed)
    ops = [random_swap, random_delete, random_insert, random_homoglyph]
    attacked = text
    for _ in range(n_ops):
        attacked = rng.choice(ops)(attacked, rng)
    return attacked


def delete_random_words(text: str, frac: float = 0.1, seed: Optional[int] = None) -> str:
    rng = random.Random(seed)
    words = text.split()
    if not words:
        return text
    keep = []
    for w in words:
        if rng.random() >= frac:
            keep.append(w)
    return " ".join(keep) if keep else text
