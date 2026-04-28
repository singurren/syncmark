# Repository Structure / 仓库结构

This repository is organized as one root `uv` project. Run `uv sync` and `uv run ...` from the repository root unless a document explicitly says otherwise.

本仓库按一个根目录 `uv` 项目组织。除非文档明确说明，否则都从仓库根目录执行 `uv sync` 和 `uv run ...`。

## Source Code / 源代码

- `syncmark/`
  - Core SyncMark Python package.
  - Contains framing, alignment, IDS-channel simulation, metrics, attacks, and the Hugging Face adapter.
  - This is the source of truth for SyncMark logic.
- `bimark/`
  - BiMark baseline code and SyncMark-on-BiMark integration experiments.
  - Keep real BiMark generation and detection code here.
  - `generate_text_dump.py` and `detect_generation_text_dump.py` include the real SyncMark-on-BiMark smoke path via `--syncmark_outer`.
  - Vendored from `https://github.com/singurren/LLM_with_watermark.git` at source commit `a8e41022ecd099b5859807d69ec815b601d7f03c`.
  - The nested BiMark git metadata was removed on 2026-04-28 so the root SyncMark repository can record cross-package research changes atomically.
  - `bimark/pyproject.toml` and `bimark/uv.lock` are legacy metadata; normal runs use the root `pyproject.toml` and root `uv.lock`.
- `code/scripts/`
  - Command-line experiment scripts and demos that call the root packages.
- `code/configs/`
  - Example experiment configuration files.

- `syncmark/`
  - 核心 SyncMark Python 包。
  - 包含 framing、alignment、IDS 信道模拟、指标、攻击和 Hugging Face adapter。
  - 这是 SyncMark 逻辑的唯一准则。
- `bimark/`
  - BiMark baseline 代码，以及 SyncMark 接入 BiMark 的实验代码。
  - 真实 BiMark 生成与检测管线保留在这里。
  - `generate_text_dump.py` 和 `detect_generation_text_dump.py` 通过 `--syncmark_outer` 提供真实 SyncMark-on-BiMark smoke 路径。
  - 来源为 `https://github.com/singurren/LLM_with_watermark.git`，原始 commit 为 `a8e41022ecd099b5859807d69ec815b601d7f03c`。
  - 2026-04-28 已移除嵌套 BiMark git 元数据，使根目录 SyncMark 仓库可以原子化记录跨包研究改动。
  - `bimark/pyproject.toml` 和 `bimark/uv.lock` 属于历史元数据；常规运行使用根目录 `pyproject.toml` 和根目录 `uv.lock`。
- `code/scripts/`
  - 调用根目录包的命令行实验脚本和 demo。
- `code/configs/`
  - 示例实验配置。

## Documentation / 文档

- `README.md`
  - Project entry point and quick-start notes.
- `AGENT_HANDOFF.md`
  - Continuation plan for future researchers or agents.
- `docs/theory_spec_syncmark.md`
  - Thesis-story theory specification.
- `docs/experimental_plan.md`
  - Experiment matrix and baseline plan.
- `docs/execution_protocol.md`
  - Operational rules for `uv`, Katana/PBS, result logging, and git practice.
- `docs/repository_structure.md`
  - This file.

- `README.md`
  - 项目入口和快速开始说明。
- `AGENT_HANDOFF.md`
  - 给后续研究者或 agent 的接续计划。
- `docs/theory_spec_syncmark.md`
  - thesis story 的理论定义。
- `docs/experimental_plan.md`
  - 实验矩阵和 baseline 计划。
- `docs/execution_protocol.md`
  - `uv`、Katana/PBS、结果记录和 git 规则。
- `docs/repository_structure.md`
  - 本文件。

## Results / 结果输出

Use only `results/` for generated artifacts. Do not recreate a separate `result/` directory.

所有生成物统一放在 `results/`。不要再创建单独的 `result/` 目录。

- `results/logs/`
  - Dated bilingual progress records.
- `results/smoke/`
  - Small smoke-test metrics and configs.
- `results/synthetic_*`
  - Existing synthetic preview artifacts.

- `results/logs/`
  - 按日期记录的双语进展日志。
- `results/smoke/`
  - 小规模 smoke test 的指标和配置。
- `results/synthetic_*`
  - 已有 synthetic preview 产物。

## Generated/Local State / 本地生成状态

These paths are local environment or generated cache state and should not be treated as research artifacts:

以下路径属于本地环境或生成缓存，不应视为研究产物：

- `.venv/`
- `.uv-cache/`
- `__pycache__/`
- `*.egg-info/`
- `bimark/output_dump/`
- `bimark/out/`
