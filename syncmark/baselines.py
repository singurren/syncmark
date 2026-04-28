from __future__ import annotations

from dataclasses import dataclass

from .ecc import hamming74_decode, hamming74_encode
from .framing import add_crc, check_crc
from .utils import majority_bit


@dataclass
class BaselineDecodeResult:
    recovered_bits: list[int]
    crc_pass: bool
    recovered_payload_plus_crc: list[int]


def repeat_to_length(bits: list[int], length: int) -> list[int]:
    if not bits:
        raise ValueError("bits must not be empty")
    out: list[int] = []
    idx = 0
    while len(out) < length:
        out.append(bits[idx % len(bits)])
        idx += 1
    return out[:length]


def naive_position_decode(obs_bits: list[int], payload_len: int) -> list[int]:
    votes = {i: [] for i in range(payload_len)}
    for idx, bit in enumerate(obs_bits):
        votes[idx % payload_len].append(bit)
    return [majority_bit(votes[i], default=0) for i in range(payload_len)]


def repetition_encode(message_bits: list[int], text_length: int) -> list[int]:
    protected = add_crc(message_bits)
    return repeat_to_length(protected, text_length)


def repetition_decode(obs_bits: list[int], message_len: int) -> BaselineDecodeResult:
    payload_crc = naive_position_decode(obs_bits, message_len + 4)
    return BaselineDecodeResult(
        recovered_bits=payload_crc[:message_len],
        crc_pass=check_crc(payload_crc),
        recovered_payload_plus_crc=payload_crc,
    )


def hamming_baseline_encode(message_bits: list[int], text_length: int) -> tuple[list[int], int]:
    protected = add_crc(message_bits)
    # Pad protected bits to multiple of 4.
    pad = (-len(protected)) % 4
    padded = protected + [0] * pad
    encoded = hamming74_encode(padded)
    return repeat_to_length(encoded, text_length), len(protected)


def hamming_baseline_decode(obs_bits: list[int], protected_len: int, message_len: int) -> BaselineDecodeResult:
    encoded_majority = naive_position_decode(obs_bits, ((protected_len + 3) // 4) * 7)
    decoded = hamming74_decode(encoded_majority)
    decoded = decoded[:protected_len]
    return BaselineDecodeResult(
        recovered_bits=decoded[:message_len],
        crc_pass=check_crc(decoded),
        recovered_payload_plus_crc=decoded,
    )
