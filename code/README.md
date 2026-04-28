# SyncMark reference code

This repository contains two complementary parts:

1. **A fully runnable synthetic simulator** for the insertion-deletion-substitution (IDS) channel.
2. **A reference Hugging Face integration** for end-to-end generation and decoding once you have a local causal language model checkpoint.

## Why the repo is structured this way

Your COMP9991 report showed that simply adding ECC on top of a multi-bit watermark can dilute the per-bit statistical signal in short texts and fail to improve recovery in practice. The purpose of this codebase is to isolate a different failure mode: **synchronization loss under editing attacks**.

The synthetic simulator is therefore the fastest way to validate the central hypothesis before spending GPU time on full LLM experiments.

## Core idea

- Baseline 1 (`repetition`): repeat payload bits and decode by position only.
- Baseline 2 (`hamming74`): add a standard block code, but still decode by position only.
- Proposed (`syncmark`): insert per-cycle anchor bits, then use alignment-aware decoding to recover the payload after insertions/deletions/substitutions.

## Quick start

```bash
uv run python code/scripts/run_synthetic_benchmark.py \
  --out_csv results/synthetic_metrics.csv \
  --trials 400 \
  --lengths 80 120 160 240 320 \
  --p_flip 0.10 --p_sub 0.05 --p_del 0.04 --p_ins 0.04 --bursty

uv run python code/scripts/make_preview_plots.py \
  --csv results/synthetic_metrics.csv \
  --out_png results/synthetic_preview.png
```

## Interpreting the synthetic results

The synthetic benchmark is **not** the final paper result. It is a design-validation tool that should answer:

- Does synchronization-aware framing help when edit operations create drift?
- Is the gain still present after paying the anchor overhead?
- Under the same short-text budget, does naive ECC still underperform due to redundancy dilution?

If the answers are yes, that justifies moving to the full LLM stage.

## Running the LLM stage later

The provided `syncmark/hf_adapter.py` and `code/scripts/run_hf_generation.py` assume that:

- a compatible causal LM is locally accessible,
- you have GPU memory for autoregressive decoding,
- you want a research prototype rather than a productionized watermarking API.

Example:

```bash
uv run python code/scripts/run_hf_generation.py \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --device cuda \
  --prompt "Write a 200-token news brief about AI regulation in Australia." \
  --message 1011010010010110 \
  --max_new_tokens 200 \
  --out_text results/generated_syncmark.txt
```

## Important caveats

- The reference inner watermark is deliberately simple so that the synchronization contribution is easy to study.
- For the actual 9993 thesis, you should compare the outer sync layer against **BiMark** and, if possible, against **DERMARK**, **MajorMark**, **MirrorMark**, and **XMark**.
- The current HF prototype marks each generated position. For the final system, replacing the inner layer with your BiMark implementation is recommended.
