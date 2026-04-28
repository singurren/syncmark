from __future__ import annotations

from .utils import chunked


# Hamming(7,4) matrices encoded manually for short-message baselines.


def hamming74_encode(bits: list[int]) -> list[int]:
    if len(bits) % 4 != 0:
        raise ValueError("Hamming(7,4) requires a multiple of 4 bits.")
    out: list[int] = []
    for d1, d2, d3, d4 in chunked(bits, 4):
        p1 = d1 ^ d2 ^ d4
        p2 = d1 ^ d3 ^ d4
        p3 = d2 ^ d3 ^ d4
        out.extend([p1, p2, d1, p3, d2, d3, d4])
    return out


def _syndrome(block: list[int]) -> int:
    b = block
    s1 = b[0] ^ b[2] ^ b[4] ^ b[6]
    s2 = b[1] ^ b[2] ^ b[5] ^ b[6]
    s3 = b[3] ^ b[4] ^ b[5] ^ b[6]
    return s1 + 2 * s2 + 4 * s3


def hamming74_decode(bits: list[int]) -> list[int]:
    if len(bits) % 7 != 0:
        raise ValueError("Hamming(7,4) requires a multiple of 7 bits.")
    out: list[int] = []
    for block in chunked(bits, 7):
        block = list(block)
        syn = _syndrome(block)
        if syn:
            pos = syn - 1
            if 0 <= pos < 7:
                block[pos] ^= 1
        out.extend([block[2], block[4], block[5], block[6]])
    return out
