from __future__ import annotations

from dataclasses import dataclass

from .utils import bit_accuracy, exact_match


@dataclass
class DecodeMetrics:
    bit_accuracy: float
    exact_recovery: float
    crc_pass: float


def compute_metrics(recovered: list[int], target: list[int], crc_pass: bool) -> DecodeMetrics:
    return DecodeMetrics(
        bit_accuracy=bit_accuracy(recovered, target),
        exact_recovery=exact_match(recovered, target),
        crc_pass=float(crc_pass),
    )
