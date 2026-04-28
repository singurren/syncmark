from __future__ import annotations

import hashlib
import hmac
from typing import Iterable


DEFAULT_HASH_K = 3


def _to_bytes(items: Iterable[int | str]) -> bytes:
    parts: list[bytes] = []
    for item in items:
        if isinstance(item, str):
            parts.append(item.encode("utf-8"))
        else:
            parts.append(str(int(item)).encode("ascii"))
        parts.append(b"|")
    return b"".join(parts)


def prf_bytes(key: str, *items: int | str, n_bytes: int = 32) -> bytes:
    msg = _to_bytes(items)
    digest = hmac.new(key.encode("utf-8"), msg, hashlib.sha256).digest()
    if n_bytes <= len(digest):
        return digest[:n_bytes]
    out = bytearray(digest)
    counter = 0
    while len(out) < n_bytes:
        counter += 1
        out.extend(hmac.new(key.encode("utf-8"), msg + counter.to_bytes(4, "big"), hashlib.sha256).digest())
    return bytes(out[:n_bytes])


def prf_bit(key: str, *items: int | str) -> int:
    return prf_bytes(key, *items, n_bytes=1)[0] & 1


def anchor_bits(key: str, cycle: int, anchor_len: int) -> list[int]:
    buf = prf_bytes(key, "anchor", cycle, n_bytes=max(1, (anchor_len + 7) // 8))
    bits: list[int] = []
    for byte in buf:
        for shift in range(8):
            bits.append((byte >> shift) & 1)
            if len(bits) == anchor_len:
                return bits
    return bits[:anchor_len]


def partition_bit(key: str, position: int, token_id: int, prefix_tokens: list[int] | None = None, mode: str = "position") -> int:
    """Return the secret partition membership of a token at a generation position.

    Parameters
    ----------
    key:
        Secret key.
    position:
        Token index within the generated continuation.
    token_id:
        Vocabulary id of the chosen token.
    prefix_tokens:
        Optional prefix token ids used when mode='prefix'.
    mode:
        'position' for robust, alignment-friendly partitioning;
        'prefix' for a BiMark/KGW-style context-dependent variant.
    """
    if mode not in {"position", "prefix"}:
        raise ValueError("mode must be 'position' or 'prefix'.")
    if mode == "position":
        return prf_bit(key, "part", position, token_id)
    prefix_tokens = prefix_tokens or []
    tail = prefix_tokens[-DEFAULT_HASH_K:]
    return prf_bit(key, "part", position, token_id, *tail)
