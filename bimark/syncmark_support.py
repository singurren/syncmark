from __future__ import annotations

from dataclasses import dataclass, field
import csv
import hashlib
import math
import random
from typing import Sequence

from syncmark.alignment import AlignmentWeights, align_and_decode
from syncmark.framing import build_layout, check_crc
from syncmark.utils import bits_to_str, str_to_bits


@dataclass
class BiMarkLikeSignalConfig:
    vocab_size: int = 4096
    window_size: int = 2
    partition_seeds: tuple[int, ...] = tuple(range(10))
    c_key: int = 8214793
    bias_strength: float = 1.15
    candidate_pool: int = 256
    seed_mode: str = "position"
    partition_masks: list[list[bool]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.seed_mode not in {"position", "prefix"}:
            raise ValueError("seed_mode must be 'position' or 'prefix'.")
        self.partition_masks = []
        for key in self.partition_seeds:
            rng = random.Random(key)
            selected = set(rng.sample(range(self.vocab_size), self.vocab_size // 2))
            self.partition_masks.append([token_id in selected for token_id in range(self.vocab_size)])


def bimark_prf(prefix: Sequence[int], secret_key: int) -> int:
    seed_str = "".join(str(int(item)) for item in prefix) + str(int(secret_key))
    digest = hashlib.sha256(seed_str.encode("utf-8")).hexdigest()
    return int(digest, 16) % (2**32)


def hamming74_encode_block(nibble: int) -> int:
    d1 = (nibble >> 3) & 1
    d2 = (nibble >> 2) & 1
    d3 = (nibble >> 1) & 1
    d4 = nibble & 1
    p1 = d1 ^ d2 ^ d4
    p2 = d1 ^ d3 ^ d4
    p3 = d2 ^ d3 ^ d4
    return (d1 << 6) | (d2 << 5) | (d3 << 4) | (d4 << 3) | (p1 << 2) | (p2 << 1) | p3


def hamming74_encode_bits(bitstring: str) -> str:
    padded = bitstring
    if len(padded) % 4 != 0:
        padded += "0" * (4 - len(padded) % 4)
    encoded = []
    for idx in range(0, len(padded), 4):
        encoded.append(f"{hamming74_encode_block(int(padded[idx:idx + 4], 2)):07b}")
    return "".join(encoded)


def hamming74_decode_block(val7: int) -> int:
    d1 = (val7 >> 6) & 1
    d2 = (val7 >> 5) & 1
    d3 = (val7 >> 4) & 1
    d4 = (val7 >> 3) & 1
    p1 = (val7 >> 2) & 1
    p2 = (val7 >> 1) & 1
    p3 = val7 & 1

    s1 = p1 ^ d1 ^ d2 ^ d4
    s2 = p2 ^ d1 ^ d3 ^ d4
    s3 = p3 ^ d2 ^ d3 ^ d4
    syndrome = s1 | (s2 << 1) | (s3 << 2)

    if syndrome == 3:
        d1 ^= 1
    elif syndrome == 5:
        d2 ^= 1
    elif syndrome == 6:
        d3 ^= 1
    elif syndrome == 7:
        d4 ^= 1

    return (d1 << 3) | (d2 << 2) | (d3 << 1) | d4


def hamming74_decode_bits(encoded_bits: str, target_len_bits: int) -> str:
    decoded: list[str] = []
    for idx in range(0, len(encoded_bits), 7):
        chunk = encoded_bits[idx:idx + 7]
        if len(chunk) < 7:
            break
        decoded.append(f"{hamming74_decode_block(int(chunk.replace('x', '0'), 2)):04b}")
    return "".join(decoded)[:target_len_bits]


def repeat_bits_to_length(bitstring: str, length: int) -> str:
    if not bitstring:
        raise ValueError("bitstring must not be empty")
    repeats = (length + len(bitstring) - 1) // len(bitstring)
    return (bitstring * repeats)[:length]


def majority_bit(bits: Sequence[int], default: int = 0) -> int:
    if not bits:
        return default
    ones = sum(int(bit) for bit in bits)
    zeros = len(bits) - ones
    return 1 if ones >= zeros else 0


def bit_accuracy(reference: str, recovered: str) -> float:
    if len(reference) != len(recovered):
        raise ValueError("bit strings must have the same length")
    if not reference:
        return 1.0
    hits = sum(int(a == b) for a, b in zip(reference, recovered))
    return hits / len(reference)


def _seed_context(prefix: Sequence[int], position: int, cfg: BiMarkLikeSignalConfig) -> list[int]:
    if cfg.seed_mode == "position":
        return [position]
    return list(prefix)


def _c_list(prefix: Sequence[int], position: int, cfg: BiMarkLikeSignalConfig) -> list[int]:
    context = _seed_context(prefix, position, cfg)
    seed = bimark_prf(context, cfg.c_key)
    rng = random.Random(seed)
    return [rng.randrange(2) for _ in cfg.partition_masks]


def _prefer_in_mask(c_value: int, target_bit: int) -> bool:
    return int(c_value) != int(target_bit)


def infer_observed_bit(token_id: int, prefix: Sequence[int], position: int, cfg: BiMarkLikeSignalConfig) -> int:
    c_values = _c_list(prefix, position, cfg)
    votes: list[int] = []
    for c_value, mask in zip(c_values, cfg.partition_masks):
        in_mask = bool(mask[int(token_id)])
        if (c_value == 1 and in_mask) or (c_value == 0 and not in_mask):
            votes.append(0)
        else:
            votes.append(1)
    return majority_bit(votes, default=0)


def sample_token_for_target_bit(prefix: Sequence[int], position: int, target_bit: int, cfg: BiMarkLikeSignalConfig, rng: random.Random) -> int:
    c_values = _c_list(prefix, position, cfg)
    candidates = [rng.randrange(cfg.vocab_size) for _ in range(cfg.candidate_pool)]
    scores: list[float] = []
    for token_id in candidates:
        token_score = 0.0
        for c_value, mask in zip(c_values, cfg.partition_masks):
            prefer_in_mask = _prefer_in_mask(c_value, target_bit)
            in_mask = bool(mask[token_id])
            if in_mask == prefer_in_mask:
                token_score += 1.0
        scores.append(token_score)

    max_score = max(scores)
    weights = [math.exp(cfg.bias_strength * (score - max_score)) for score in scores]
    weight_sum = sum(weights)
    draw = rng.random() * weight_sum
    running = 0.0
    for token_id, weight in zip(candidates, weights):
        running += weight
        if running >= draw:
            return token_id
    return candidates[-1]


def generate_bimark_like_tokens(target_bits: str, cfg: BiMarkLikeSignalConfig, seed: int) -> list[int]:
    rng = random.Random(seed)
    tokens = [rng.randrange(cfg.vocab_size) for _ in range(cfg.window_size)]
    for position, ch in enumerate(target_bits):
        prefix = tokens[-cfg.window_size:]
        token_id = sample_token_for_target_bit(prefix, position, int(ch), cfg, rng)
        tokens.append(token_id)
    return [int(token) for token in tokens]


def apply_token_ids_attack(tokens: Sequence[int], p_del: float, p_ins: float, p_sub: float, vocab_size: int, seed: int) -> list[int]:
    rng = random.Random(seed)
    attacked: list[int] = []
    for token in tokens:
        if rng.random() < p_ins:
            attacked.append(rng.randrange(vocab_size))
        if rng.random() < p_del:
            continue
        token_out = int(token)
        if rng.random() < p_sub:
            token_out = rng.randrange(vocab_size)
        attacked.append(token_out)
    if rng.random() < p_ins:
        attacked.append(rng.randrange(vocab_size))
    return attacked


def extract_observed_bits_from_tokens(tokens: Sequence[int], cfg: BiMarkLikeSignalConfig) -> list[int]:
    token_list = [int(token) for token in tokens]
    if len(token_list) <= cfg.window_size:
        return []
    observed: list[int] = []
    for token_idx in range(cfg.window_size, len(token_list)):
        position = token_idx - cfg.window_size
        prefix = token_list[token_idx - cfg.window_size:token_idx]
        observed.append(infer_observed_bit(token_list[token_idx], prefix, position, cfg))
    return observed


def decode_repeated_positions(obs_bits: Sequence[int], codeword_len: int) -> str:
    if codeword_len <= 0:
        raise ValueError("codeword_len must be positive")
    votes = {idx: [] for idx in range(codeword_len)}
    for position, bit in enumerate(obs_bits):
        votes[position % codeword_len].append(int(bit))
    return bits_to_str([majority_bit(votes[idx], default=0) for idx in range(codeword_len)])


def decode_message_position_vote(obs_bits: Sequence[int], message_bits: str) -> dict:
    recovered = decode_repeated_positions(obs_bits, len(message_bits))
    return {
        "recovered_bits": recovered,
        "bit_accuracy": bit_accuracy(message_bits, recovered),
        "exact_recovery": float(recovered == message_bits),
        "crc_pass": None,
        "alignment_score": None,
    }


def decode_message_hamming74(obs_bits: Sequence[int], message_bits: str) -> dict:
    encoded_bits = hamming74_encode_bits(message_bits)
    recovered_encoded = decode_repeated_positions(obs_bits, len(encoded_bits))
    recovered = hamming74_decode_bits(recovered_encoded, len(message_bits))
    return {
        "recovered_bits": recovered,
        "bit_accuracy": bit_accuracy(message_bits, recovered),
        "exact_recovery": float(recovered == message_bits),
        "crc_pass": None,
        "alignment_score": None,
    }


def decode_syncmark_position_vote(obs_bits: Sequence[int], message_bits: str, text_length: int, anchor_len: int, key: str) -> dict:
    layout = build_layout(str_to_bits(message_bits), text_length=text_length, anchor_len=anchor_len, key=key)
    votes = {idx: [] for idx in range(len(message_bits) + 4)}
    for position, bit in enumerate(obs_bits[:len(layout)]):
        slot = layout[position]
        if slot.slot_type == "payload" and slot.message_index is not None:
            votes[slot.message_index].append(int(bit))
    recovered_payload = [majority_bit(votes[idx], default=0) for idx in range(len(message_bits) + 4)]
    recovered_message = bits_to_str(recovered_payload[:len(message_bits)])
    return {
        "recovered_bits": recovered_message,
        "bit_accuracy": bit_accuracy(message_bits, recovered_message),
        "exact_recovery": float(recovered_message == message_bits),
        "crc_pass": bool(check_crc(recovered_payload)),
        "alignment_score": None,
    }


def decode_syncmark_alignment(obs_bits: Sequence[int], message_bits: str, text_length: int, anchor_len: int, key: str) -> dict:
    layout = build_layout(str_to_bits(message_bits), text_length=text_length, anchor_len=anchor_len, key=key)
    weights = AlignmentWeights(
        anchor_match=2.0,
        anchor_mismatch=-1.0,
        payload_match=0.35,
        gap=-2.0,
        anchor_gap=-2.5,
    )
    decoded = align_and_decode(list(map(int, obs_bits)), layout, message_len=len(message_bits), weights=weights)
    recovered = bits_to_str(decoded.recovered_bits)
    return {
        "recovered_bits": recovered,
        "bit_accuracy": bit_accuracy(message_bits, recovered),
        "exact_recovery": float(recovered == message_bits),
        "crc_pass": bool(decoded.crc_pass),
        "alignment_score": float(decoded.alignment_score),
        "n_aligned_payload_observations": int(decoded.n_aligned_payload_observations),
    }


def write_csv(path, rows: Sequence[dict], fieldnames: Sequence[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
