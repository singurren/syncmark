from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .hashing import anchor_bits
from .utils import chunked


@dataclass
class Slot:
    index: int
    slot_type: str  # 'anchor' or 'payload'
    expected_bit: Optional[int]
    message_index: Optional[int]
    cycle: int
    offset_in_cycle: int


@dataclass
class SyncMarkConfig:
    message_bits: int = 16
    text_length: int = 200
    anchor_len: int = 6
    key: str = "syncmark-demo-key"


def bits_from_int(value: int, n_bits: int) -> list[int]:
    if value < 0:
        raise ValueError("value must be non-negative")
    return [(value >> i) & 1 for i in range(n_bits - 1, -1, -1)]


def int_from_bits(bits: list[int]) -> int:
    out = 0
    for bit in bits:
        out = (out << 1) | int(bit)
    return out


def crc4(bits: list[int]) -> list[int]:
    """A tiny checksum suitable for short-message prototype experiments.

    This is not intended as a cryptographic primitive. It serves only as a low-
    cost integrity check in the reference implementation.
    """
    weights = [1, 2, 3, 5]
    acc = 0
    for idx, bit in enumerate(bits):
        if bit:
            acc ^= weights[idx % len(weights)]
    return bits_from_int(acc % 16, 4)


def add_crc(bits: list[int]) -> list[int]:
    return bits + crc4(bits)


def check_crc(bits_with_crc: list[int]) -> bool:
    if len(bits_with_crc) < 4:
        return False
    payload, checksum = bits_with_crc[:-4], bits_with_crc[-4:]
    return crc4(payload) == checksum


def build_layout(message_bits: list[int], text_length: int, anchor_len: int, key: str) -> list[Slot]:
    """Build a repeated anchor+payload layout of exactly ``text_length`` slots.

    Each cycle contains a unique anchor pattern followed by the full payload+
    checksum. The message is repeated as many times as needed to cover the target
    text length, which is suitable for finite-length short-text experiments.
    """
    protected_bits = add_crc(message_bits)
    cycle_payload_len = len(protected_bits)
    cycle_len = anchor_len + cycle_payload_len
    n_cycles = max(1, (text_length + cycle_len - 1) // cycle_len)
    slots: list[Slot] = []
    slot_idx = 0
    for cycle in range(n_cycles):
        a_bits = anchor_bits(key, cycle, anchor_len)
        for offset, bit in enumerate(a_bits):
            slots.append(
                Slot(
                    index=slot_idx,
                    slot_type="anchor",
                    expected_bit=bit,
                    message_index=None,
                    cycle=cycle,
                    offset_in_cycle=offset,
                )
            )
            slot_idx += 1
        for offset, bit in enumerate(protected_bits):
            slots.append(
                Slot(
                    index=slot_idx,
                    slot_type="payload",
                    expected_bit=bit,
                    message_index=offset,
                    cycle=cycle,
                    offset_in_cycle=anchor_len + offset,
                )
            )
            slot_idx += 1
        if slot_idx >= text_length:
            break
    return slots[:text_length]


def cycle_summary(message_bits: list[int], text_length: int, anchor_len: int, key: str) -> dict:
    protected_bits = add_crc(message_bits)
    cycle_len = anchor_len + len(protected_bits)
    n_cycles = max(1, (text_length + cycle_len - 1) // cycle_len)
    return {
        "message_len": len(message_bits),
        "checksum_len": 4,
        "cycle_len": cycle_len,
        "num_cycles": n_cycles,
        "anchor_len": anchor_len,
        "effective_repetitions_per_payload_bit": n_cycles,
        "anchor_rate": anchor_len / cycle_len,
    }
