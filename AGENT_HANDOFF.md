# AGENT HANDOFF

This file is the quickest way for another AI agent or collaborator to continue the project without re-deriving the plan.

See also:
- `docs/execution_protocol.md` for Katana/PBS, `uv`, result logging, and git-record rules.
- `results/logs/` for dated bilingual progress records.

Environment rule: run both SyncMark and BiMark through the root `uv` project. Do not sync or document a separate `bimark/` environment for normal runs.

## Project objective

Develop and evaluate **SyncMark**, a synchronization-aware multi-bit watermarking framework for short and edited LLM-generated text.

## Why this direction was chosen

The previous COMP9991 report found that simply adding ECC or layer-wise delta scheduling on top of BiMark did not improve short-text robustness. The key insight is that realistic edits create **position drift** and **tokenization drift**, so the effective channel is not well approximated by independent bit flips. That motivates an outer layer that restores synchronization before payload decoding.

## Immediate tasks

### Stage A: theory validation (already scaffolded)

- Read `docs/theory_spec_syncmark.md`.
- Run the synthetic benchmark:

```bash
uv sync
uv run python code/scripts/run_synthetic_benchmark.py \
  --out_csv results/synthetic_metrics.csv \
  --trials 400 \
  --lengths 120 160 240 320 400 \
  --p_flip 0.05 --p_sub 0.02 --p_del 0.02 --p_ins 0.02

uv run python code/scripts/make_preview_plots.py \
  --csv results/synthetic_metrics.csv \
  --out_png results/synthetic_preview.png
```

Success criterion for Stage A:
- SyncMark beats repetition and naive Hamming under insertion/deletion/substitution settings.

### Stage B: reproduce full LLM baselines

Priority order:
1. Your own BiMark implementation from COMP9991.
2. MajorMark.
3. DERMARK.
4. MirrorMark.
5. XMark.

Minimum benchmark setting:
- message bits: 8 / 16 / 32
- output lengths: 100 / 150 / 200 / 300
- tasks: news-like continuation, instruction following, low-entropy/code-like stress test

### Stage C: integrate SyncMark outer layer with a real inner watermark

Best path:
- Keep the outer frame/alignment logic from this package.
- Replace the reference inner marker with BiMark-style or another lower-distortion inner embedding scheme.
- Compare:
  - inner only
  - inner + naive ECC
  - inner + SyncMark outer layer

### Stage D: attacks

Required attacks:
- token deletion
- token insertion
- token substitution
- sentence paraphrase
- character-level typo/swap/homoglyph/unicode perturbation

Stretch attacks:
- adaptive paraphrase or RL-based removal
- local edit localization benchmark

## Important code files

- `syncmark/framing.py`
  - anchor+payload cycle design and checksum
- `syncmark/alignment.py`
  - alignment-aware decoder
- `syncmark/channel.py`
  - synthetic IDS channel
- `syncmark/hf_adapter.py`
  - reference end-to-end LM integration
- `code/scripts/run_synthetic_benchmark.py`
  - main synthetic benchmark runner

## What not to do

- Do **not** treat the synthetic results as thesis results.
- Do **not** spend most of the 9993 time building diffusion watermarking first.
- Do **not** compare methods under mismatched message length or text length budgets.
- Do **not** ignore character-level attacks.

## Publication strategy

Most realistic target sequence:
1. internal thesis report or lab preprint,
2. ARR / Findings-style NLP submission,
3. watermarking/security workshop if full benchmark is not ready in time.

## Decision rule after first full experiments

If SyncMark outer layer improves exact recovery under insertion/deletion and char-level attacks while keeping quality close to the inner baseline, continue on the AR track.

If gains disappear after replacing the reference inner watermark with a real low-distortion method, then the bottleneck is not synchronization and the project should pivot to detector-side statistics or edit localization instead.
