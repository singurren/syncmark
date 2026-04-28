from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Optional

import pandas as pd

from .alignment import align_and_decode
from .baselines import (
    hamming_baseline_decode,
    hamming_baseline_encode,
    repetition_decode,
    repetition_encode,
)
from .channel import IDSChannelConfig, apply_ids_channel
from .framing import SyncMarkConfig, bits_from_int, build_layout
from .utils import bit_accuracy, exact_match


@dataclass
class TrialResult:
    method: str
    text_length: int
    attack_name: str
    trial: int
    bit_accuracy: float
    exact_recovery: float
    crc_pass: float
    observed_length: int
    edit_ratio: float


def _expected_edit_ratio(cfg: IDSChannelConfig) -> float:
    return cfg.p_sub + cfg.p_del + cfg.p_ins


def simulate_trial(method: str, message_bits: list[int], text_length: int, key: str, channel_cfg: IDSChannelConfig, seed: int) -> TrialResult:
    if method == "syncmark":
        layout = build_layout(message_bits, text_length, anchor_len=6, key=key)
        clean_stream = [slot.expected_bit for slot in layout]
        obs = apply_ids_channel(clean_stream, channel_cfg, seed=seed)
        decoded = align_and_decode(obs, layout, message_len=len(message_bits))
        recovered = decoded.recovered_bits
        crc_pass = float(decoded.crc_pass)
    elif method == "repetition":
        clean_stream = repetition_encode(message_bits, text_length)
        obs = apply_ids_channel(clean_stream, channel_cfg, seed=seed)
        decoded = repetition_decode(obs, message_len=len(message_bits))
        recovered = decoded.recovered_bits
        crc_pass = float(decoded.crc_pass)
    elif method == "hamming74":
        clean_stream, protected_len = hamming_baseline_encode(message_bits, text_length)
        obs = apply_ids_channel(clean_stream, channel_cfg, seed=seed)
        decoded = hamming_baseline_decode(obs, protected_len=protected_len, message_len=len(message_bits))
        recovered = decoded.recovered_bits
        crc_pass = float(decoded.crc_pass)
    else:
        raise ValueError(f"Unknown method: {method}")

    return TrialResult(
        method=method,
        text_length=text_length,
        attack_name="mixed_ids",
        trial=seed,
        bit_accuracy=bit_accuracy(recovered, message_bits),
        exact_recovery=exact_match(recovered, message_bits),
        crc_pass=crc_pass,
        observed_length=len(obs),
        edit_ratio=_expected_edit_ratio(channel_cfg),
    )


def benchmark_methods(
    methods: Iterable[str],
    text_lengths: Iterable[int],
    n_trials: int,
    channel_cfg: IDSChannelConfig,
    message_bits: Optional[list[int]] = None,
    key: str = "syncmark-demo-key",
) -> pd.DataFrame:
    methods = list(methods)
    text_lengths = list(text_lengths)
    if message_bits is None:
        message_bits = bits_from_int(0b1011010010010110, 16)

    rows = []
    for text_length in text_lengths:
        for method in methods:
            for trial in range(n_trials):
                row = simulate_trial(method, message_bits, text_length, key, channel_cfg, seed=1000 * text_length + 100 * len(method) + trial)
                rows.append(row.__dict__)
    return pd.DataFrame(rows)
