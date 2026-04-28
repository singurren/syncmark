"""SyncMark research reference implementation.

This package contains a lightweight synchronization-aware multi-bit watermarking
framework for short and edited LLM-generated text.

The code is intended for research prototyping and ablation studies. It contains
both a synthetic IDS-channel simulator (fully runnable in CPU-only settings)
and a reference Hugging Face adapter for end-to-end generation once a causal LM
checkpoint is available locally.
"""

from .framing import SyncMarkConfig, build_layout, bits_from_int, int_from_bits
from .simulation import benchmark_methods

__all__ = [
    "SyncMarkConfig",
    "build_layout",
    "bits_from_int",
    "int_from_bits",
    "benchmark_methods",
]
