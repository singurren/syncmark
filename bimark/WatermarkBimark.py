from transformers import LogitsProcessor
import torch
from typing import List
import numpy as np
try:
    from .utils import prf
except ImportError:
    from utils import prf
import random
import time
import os

seed = int(os.environ.get('GLOBAL_SEED', 42))

random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(seed)


class WatermarkBimark(LogitsProcessor):
    def __init__(
        self,
        tokenizer,
        device,
        vocab_size: int,
        top_k: int = 50,
        partition_seeds: list = list(range(10)),
        c_key: int = 530773,
        bit_idx_key: int = 283519,
        delta: List[float] = [1.0],
        window_size: int = 2,
        bits: str = '0',
        alpha: int = 1,
        schedule_mode: str = 'random_bit_index',
        schedule_bits: str | None = None,
    ):
        self.tokenizer = tokenizer
        self.vocab_size = vocab_size
        self.device = device
        self.top_k = top_k

        self.partition_masks = []
        if type(partition_seeds) is not list:
            partition_seeds = [partition_seeds]
        for key in partition_seeds:
            num_v0 = int(self.vocab_size * 0.5)
            rng = np.random.default_rng(key)
            mask = np.zeros(self.vocab_size, dtype=bool)
            mask[rng.choice(self.vocab_size, num_v0, replace=False)] = True
            mask = torch.tensor(mask).to(torch.bool).to(device)
            self.partition_masks.append(mask)

        if len(delta) == 1:
            self.delta_list = [delta[0]] * len(self.partition_masks)
        elif len(delta) == len(self.partition_masks):
            self.delta_list = delta
        else:
            raise ValueError(
                f"Length of prob_delta list ({len(delta)}) does not match "
                f"number of partition_seeds ({len(self.partition_masks)})."
            )
        print(f"WatermarkBimark initialized with deltas: {self.delta_list}")

        self.c_key = c_key
        self.bit_idx_key = bit_idx_key
        self.alpha = alpha
        self.window_size = window_size
        self.cnt = 0
        self.bits = bits
        self.schedule_mode = schedule_mode
        self.schedule_bits = schedule_bits or ""
        self.watermark_step = 0

        if self.schedule_mode not in {"random_bit_index", "position_schedule"}:
            raise ValueError("schedule_mode must be 'random_bit_index' or 'position_schedule'.")
        if self.schedule_mode == "position_schedule" and not self.schedule_bits:
            raise ValueError("schedule_bits must be provided when schedule_mode='position_schedule'.")

    def _resolve_target_bit(self, bit_idx_seed: int) -> int:
        if self.schedule_mode == "position_schedule":
            schedule_idx = min(self.watermark_step, len(self.schedule_bits) - 1)
            return int(self.schedule_bits[schedule_idx])

        rng_bit_idx = np.random.default_rng(bit_idx_seed)
        bit_idx = rng_bit_idx.integers(0, len(self.bits))
        return int(self.bits[bit_idx])

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
        begin = time.time()
        if self.cnt == 0:
            self.hist = [set() for _ in range(input_ids.shape[0])]
            self.watermark_step = 0

        if self.cnt < self.window_size:
            self.cnt += 1
            return scores

        score_topk = torch.topk(scores, self.top_k, dim=-1)
        prob_topk_values = torch.nn.functional.softmax(score_topk.values, dim=-1).to(self.device).to(torch.float32)
        prob_topk_indices = score_topk.indices

        self.cnt += 1

        alpha = torch.full((input_ids.shape[0], 1), self.alpha, dtype=torch.float32).to(self.device)
        inputs = input_ids.to(self.device)
        prefix = inputs[:, -self.window_size:]

        c_seed = prf(prefix, self.c_key)
        bit_idx_seed = prf(prefix, self.bit_idx_key)

        ops_stack = []
        skip_pos = []

        for batch_idx in range(prefix.size(0)):
            if prefix[batch_idx] in self.hist[batch_idx]:
                skip_pos.append(batch_idx)
            else:
                self.hist[batch_idx].add(prefix[batch_idx])

            rng_c = np.random.default_rng(c_seed[batch_idx])
            c_list = rng_c.integers(0, 2, size=len(self.partition_masks))
            bit = self._resolve_target_bit(bit_idx_seed[batch_idx])

            ops_list = []
            for c_value in c_list:
                if (c_value == 1 and bit == 0) or (c_value == 0 and bit == 1):
                    ops_list.append(1)
                else:
                    ops_list.append(-1)
            ops_stack.append(ops_list)

        ops_stack = torch.tensor(ops_stack).to(self.device)

        for layer_idx in range(len(self.partition_masks)):
            current_delta_val = self.delta_list[layer_idx]
            prob_delta = torch.full((input_ids.shape[0], 1), current_delta_val, dtype=torch.float32).to(self.device)

            top_k_mask = self.partition_masks[layer_idx][prob_topk_indices]
            p0 = torch.sum(prob_topk_values * top_k_mask, -1, keepdim=True)
            mask_p0 = (p0 < 1e-30) + (1 - p0 < 1e-30)

            delta = torch.max(torch.min(alpha / p0, 1 + prob_delta), torch.ones(prob_delta.shape).to(self.device)) - 1
            beta = torch.min(delta * p0 / (1 - p0), torch.ones(prob_delta.shape).to(self.device))

            delta[mask_p0 == 1] = 0
            beta[mask_p0 == 1] = 0
            delta[skip_pos] = 0
            beta[skip_pos] = 0

            delta = delta * ops_stack[:, layer_idx].unsqueeze(1)
            beta = beta * ops_stack[:, layer_idx].unsqueeze(1)
            delta = delta.expand(-1, prob_topk_values.shape[1])
            beta = beta.expand(-1, prob_topk_values.shape[1])

            prob_topk_values[top_k_mask == True] = prob_topk_values[top_k_mask == True] * (1 + delta)[top_k_mask == True]
            prob_topk_values[top_k_mask == False] = prob_topk_values[top_k_mask == False] * (1 - beta)[top_k_mask == False]

        prob = torch.zeros_like(scores, dtype=torch.float32).to(self.device)
        prob.scatter_(1, prob_topk_indices, prob_topk_values)
        new_scores = torch.log(prob).to(self.device)

        self.watermark_step += 1

        end = time.time()
        runtime = end - begin
        _ = runtime
        return new_scores
