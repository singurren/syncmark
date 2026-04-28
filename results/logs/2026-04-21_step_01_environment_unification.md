# 2026-04-21 Step 01: Root uv Environment Unification

## Purpose / 目的

Clarify that SyncMark and BiMark should run from one root `uv` environment, and document the Katana CUDA/module requirements for GPU jobs.

明确 SyncMark 与 BiMark 应统一使用根目录 `uv` 环境运行，并记录 Katana GPU 作业所需的 CUDA/module 约束。

## What Was Done / 完成内容

- Updated the root README to state that `uv sync` and `uv run ...` are executed from the repository root.
- Updated `bimark/README.md` so BiMark generation, detection, and analysis examples use root-level `uv run python ...` commands.
- Updated `docs/execution_protocol.md` to make root `pyproject.toml` and root `uv.lock` the single source of truth for runtime dependencies.
- Replaced the old unrelated PBS template with a SyncMark + BiMark GPU smoke template using `module load cuda/13.0.0`.
- Fixed `bimark/run_syncmark_bimark_smoke.py` so its default output directory is the repository-local `results/smoke/` directory.

- 已更新根目录 README，说明 `uv sync` 与 `uv run ...` 都从仓库根目录执行。
- 已更新 `bimark/README.md`，使 BiMark 生成、检测和分析示例统一使用根目录 `uv run python ...` 命令。
- 已更新 `docs/execution_protocol.md`，明确根目录 `pyproject.toml` 与根目录 `uv.lock` 是运行依赖的唯一准则。
- 已将旧的无关 PBS 模板替换为 SyncMark + BiMark GPU smoke 模板，并使用 `module load cuda/13.0.0`。
- 已修复 `bimark/run_syncmark_bimark_smoke.py`，使默认输出目录落在仓库内的 `results/smoke/`。

## Result / 结果

The root environment successfully ran a one-trial SyncMark + BiMark smoke test with a writable `uv` cache:

根环境已在可写 `uv` cache 下成功运行 1 trial 的 SyncMark + BiMark smoke test：

```bash
uv --cache-dir /tmp/uv-cache-syncmark run python -m bimark.run_syncmark_bimark_smoke --trials 1
```

Output files were written to:

输出文件已写入：

```text
results/smoke/2026-04-21_syncmark_bimark_smoke/smoke_metrics.csv
results/smoke/2026-04-21_syncmark_bimark_smoke/smoke_summary.csv
results/smoke/2026-04-21_syncmark_bimark_smoke/smoke_config.json
```

## What Was Achieved / 达成内容

Future runs now have one documented dependency entry point, one PBS template, and one result-output convention.

后续运行现在有统一的依赖入口、统一的 PBS 模板，以及统一的结果输出约定。

## Meaning / 结果含义

This reduces environment drift between `syncmark/`, `code/`, and `bimark/`, and makes GPU jobs match the current PyTorch CUDA 13.0 build.

这降低了 `syncmark/`、`code/` 与 `bimark/` 之间的环境漂移风险，并使 GPU 作业与当前 PyTorch CUDA 13.0 build 匹配。

## Next Step / 下一步

Run a 20-50 trial smoke test through `template.pbs` on a GPU node, then record the PBS job ID, CUDA visibility, and summary metrics in a new dated result note.

下一步是在 GPU 节点上通过 `template.pbs` 运行 20-50 trial smoke test，并在新的日期记录中写入 PBS job ID、CUDA 可见性和 summary metrics。
