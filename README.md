# COMP9993 research package: SyncMark

This package is designed so that you can hand it to a supervisor, collaborator, or AI agent and start work immediately.

## What is inside

- `proposal/COMP9993_Research_Proposal.docx` and `.pdf`
  - A polished proposal suitable for supervisor discussion and 9993 planning.
- `docs/literature_map_2025_2026.md`
  - Curated paper map from foundations to the newest 2025-2026 work.
- `docs/paper_links.csv`
  - Machine-readable paper list with URLs and short notes.
- `docs/theory_spec_syncmark.md`
  - Full theoretical framing of the proposed method.
- `docs/experimental_plan.md`
  - Complete experiment matrix, baselines, metrics, datasets, and ablations.
- `docs/expected_results_and_conclusions.md`
  - Pre-registered expected outcomes and interpretation guide.
- `docs/paper_outline.md`
  - Suggested paper structure and figure plan.
- `docs/repository_structure.md`
  - Canonical repository layout and artifact-location rules.
- `AGENT_HANDOFF.md`
  - Step-by-step continuation plan for another researcher or AI agent.
- `syncmark/`
  - Core SyncMark package: framing, alignment, synthetic channel, metrics, and Hugging Face adapter.
- `bimark/`
  - BiMark baseline and the SyncMark-on-BiMark integration experiments.
- `code/`
  - Experiment scripts and example configs.
- `results/`
  - Generated experiment outputs, synthetic previews, smoke-test metrics, and dated bilingual progress logs.
- `previous_work/COMP9991_Report_ZhanMa.pdf`
  - Your prior report for continuity.

## Research direction in one sentence

The proposal pivots from "more naive ECC on top of multi-bit watermarking" to a more precise question:

**Can short-text multi-bit LLM watermark recovery be improved by treating post-editing as a synchronization problem, not just a bit-flip problem?**

## Recommended first actions

1. Read the proposal.
2. Read `docs/theory_spec_syncmark.md`.
3. Run the synthetic benchmark through the root `uv` project to validate the synchronization hypothesis.
4. Replace the reference inner watermark with your BiMark implementation and reproduce the main benchmark.
5. Add strong real-world attacks, especially character-level attacks and paraphrasing.

## Execution notes

- The repository is now managed as one root `uv` project:

```bash
uv sync
uv run python code/scripts/run_synthetic_benchmark.py --trials 50
uv run python -m bimark.run_syncmark_bimark_smoke --trials 20
```

- Run `uv sync` and `uv run ...` from the repository root. For Katana GPU jobs, set a writable `UV_CACHE_DIR` and load the CUDA module matching the current PyTorch build:

```bash
export UV_CACHE_DIR="/tmp/${USER}/uv-cache"
module load cuda/13.0.0
```

- The active execution workflow, Katana/PBS constraints, and step-recording rules are documented in `docs/execution_protocol.md`.
- Ongoing dated bilingual work logs should be written under `results/logs/`.

## Important honesty note

The `results/` folder contains **synthetic channel-model previews**, not final LLM benchmark numbers. They are included to validate the central mechanism before spending GPU budget on full model experiments.
