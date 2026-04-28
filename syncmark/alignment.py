from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .framing import Slot, check_crc
from .utils import majority_bit


@dataclass
class AlignmentResult:
    recovered_bits: list[int]
    recovered_payload_plus_crc: list[int]
    crc_pass: bool
    alignment_score: float
    observed_payload_votes: dict[int, list[int]]
    n_aligned_payload_observations: int


@dataclass
class AlignmentWeights:
    anchor_match: float = 2.5
    anchor_mismatch: float = -2.8
    payload_match: float = 0.35
    gap: float = -0.9
    anchor_gap: float = -1.8


MATCH = 1
DELETE = 2
INSERT = 3


def align_and_decode(obs_bits: list[int], layout: list[Slot], message_len: int, weights: Optional[AlignmentWeights] = None) -> AlignmentResult:
    if weights is None:
        weights = AlignmentWeights()
    n = len(layout)
    m = len(obs_bits)
    dp = np.full((n + 1, m + 1), -1e18, dtype=float)
    ptr = np.zeros((n + 1, m + 1), dtype=np.int8)
    dp[0, 0] = 0.0

    def delete_penalty(slot: Slot) -> float:
        return weights.anchor_gap if slot.slot_type == "anchor" else weights.gap

    for i in range(n + 1):
        for j in range(m + 1):
            cur = dp[i, j]
            if cur < -1e17:
                continue
            if i < n and j < m:
                slot = layout[i]
                if slot.slot_type == "anchor":
                    sc = weights.anchor_match if obs_bits[j] == slot.expected_bit else weights.anchor_mismatch
                else:
                    sc = weights.payload_match
                cand = cur + sc
                if cand > dp[i + 1, j + 1]:
                    dp[i + 1, j + 1] = cand
                    ptr[i + 1, j + 1] = MATCH
            if i < n:
                cand = cur + delete_penalty(layout[i])
                if cand > dp[i + 1, j]:
                    dp[i + 1, j] = cand
                    ptr[i + 1, j] = DELETE
            if j < m:
                cand = cur + weights.gap
                if cand > dp[i, j + 1]:
                    dp[i, j + 1] = cand
                    ptr[i, j + 1] = INSERT

    i, j = n, m
    votes: dict[int, list[int]] = {}
    while i > 0 or j > 0:
        move = ptr[i, j]
        if move == MATCH:
            slot = layout[i - 1]
            obs = obs_bits[j - 1]
            if slot.slot_type == "payload" and slot.message_index is not None:
                votes.setdefault(slot.message_index, []).append(obs)
            i -= 1
            j -= 1
        elif move == DELETE:
            i -= 1
        elif move == INSERT:
            j -= 1
        else:
            # Fallback for ties at initialization boundary.
            if i > 0:
                i -= 1
            elif j > 0:
                j -= 1

    if not votes:
        recovered_payload_crc = [0] * (message_len + 4)
    else:
        max_idx = max(votes)
        recovered_payload_crc = [majority_bit(votes.get(idx, []), default=0) for idx in range(max_idx + 1)]

    # Pad to expected length if the tail is missing.
    if len(recovered_payload_crc) < message_len + 4:
        recovered_payload_crc.extend([0] * (message_len + 4 - len(recovered_payload_crc)))
    recovered_payload_crc = recovered_payload_crc[: message_len + 4]

    crc_pass = check_crc(recovered_payload_crc)
    recovered = recovered_payload_crc[:message_len]
    n_obs = sum(len(v) for v in votes.values())
    return AlignmentResult(
        recovered_bits=recovered,
        recovered_payload_plus_crc=recovered_payload_crc,
        crc_pass=crc_pass,
        alignment_score=float(dp[n, m]),
        observed_payload_votes=votes,
        n_aligned_payload_observations=n_obs,
    )
