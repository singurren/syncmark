from __future__ import annotations

"""Reference Hugging Face adapter for SyncMark.

This module is intentionally lightweight and research-oriented. It requires local
availability of a causal language model checkpoint and is not exercised in the
CPU-only preview shipped with this package. The goal is to make the project
immediately extensible once you or another agent have GPU access.
"""

from dataclasses import dataclass
from typing import Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from .framing import build_layout, bits_from_int
from .hashing import partition_bit


@dataclass
class HFGenerationConfig:
    model_name_or_path: str = "meta-llama/Llama-3.1-8B-Instruct"
    device: str = "cuda"
    temperature: float = 0.8
    top_p: float = 0.95
    max_new_tokens: int = 200
    delta: float = 1.5
    key: str = "syncmark-demo-key"
    partition_mode: str = "position"  # or 'prefix'


class SyncMarkCausalLM:
    def __init__(self, cfg: HFGenerationConfig):
        self.cfg = cfg
        self.tokenizer = AutoTokenizer.from_pretrained(cfg.model_name_or_path, use_fast=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(cfg.model_name_or_path).to(cfg.device)
        self.model.eval()

    @torch.no_grad()
    def generate(self, prompt: str, message: int | str, message_bits: Optional[int] = 16) -> str:
        if isinstance(message, str):
            bits = [int(ch) for ch in message.strip()]
        else:
            bits = bits_from_int(int(message), int(message_bits or 16))
        layout = build_layout(bits, self.cfg.max_new_tokens, anchor_len=6, key=self.cfg.key)

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.cfg.device)
        generated = inputs.input_ids[0].tolist()
        prompt_len = len(generated)
        for step in range(self.cfg.max_new_tokens):
            logits = self.model(input_ids=torch.tensor([generated], device=self.cfg.device)).logits[0, -1].float()
            target_bit = layout[step].expected_bit
            vocab_size = logits.shape[0]
            prefix = generated[prompt_len + max(0, step - 3) :]
            mask = torch.empty(vocab_size, dtype=torch.bool, device=self.cfg.device)
            for token_id in range(vocab_size):
                part = partition_bit(self.cfg.key, step, token_id, prefix_tokens=prefix, mode=self.cfg.partition_mode)
                mask[token_id] = bool(part == target_bit)
            logits[mask] += self.cfg.delta
            logits = logits / max(self.cfg.temperature, 1e-5)
            probs = torch.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1).item()
            generated.append(next_token)
        continuation = generated[prompt_len:]
        return self.tokenizer.decode(continuation, skip_special_tokens=True)

    def extract_observed_bits(self, continuation: str) -> list[int]:
        ids = self.tokenizer(continuation, add_special_tokens=False).input_ids
        obs: list[int] = []
        prefix: list[int] = []
        for pos, token_id in enumerate(ids):
            obs.append(partition_bit(self.cfg.key, pos, token_id, prefix_tokens=prefix, mode=self.cfg.partition_mode))
            prefix.append(token_id)
        return obs
