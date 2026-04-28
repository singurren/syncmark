# Execution Protocol / 执行协议

## Scope / 适用范围

This document records the operating rules for continuing the SyncMark + BiMark research inside this repository.

本文记录了在本仓库内继续推进 SyncMark + BiMark 研究时需要遵守的执行规则。

For the canonical directory layout, see `docs/repository_structure.md`.

仓库目录结构以 `docs/repository_structure.md` 为准。

## Research Positioning / 研究定位

- `syncmark/`, `bimark/`, `code/`, `docs/`, and `AGENT_HANDOFF.md` form one root `uv` project.
- `syncmark/` is the core SyncMark package; `bimark/` is the BiMark baseline and real generation/detection pipeline to extend.
- The immediate goal is not full-cluster reproduction. The immediate goal is to validate whether SyncMark framing plus alignment improves robustness under synchronization drift before scaling out.

- 仓库根目录下的 `syncmark/`、`bimark/`、`code/`、`docs/`、`AGENT_HANDOFF.md` 现在构成一个统一的根目录 `uv` 项目。
- `syncmark/` 是核心 SyncMark 包；`bimark/` 是已有的 BiMark baseline 和后续真实生成与检测实验管线。
- 当前目标不是直接做全集群大复现，而是先验证 SyncMark 的 framing + alignment 在同步漂移攻击下是否带来稳定收益，再决定是否批量扩展。

## Working Sequence / 工作顺序

1. Read and maintain the thesis-story documents:
   - `docs/theory_spec_syncmark.md`
   - `docs/experimental_plan.md`
   - `AGENT_HANDOFF.md`
2. Re-validate the synthetic logic when needed, but do not treat synthetic preview numbers as thesis results.
3. First integration target:
   - connect `syncmark/framing.py` and `syncmark/alignment.py` to the BiMark pipeline,
   - run a 20-50 sample smoke test,
   - verify that alignment decoding is more stable than naive position vote or naive ECC under drift.
4. Only after the smoke test is convincing, prepare PBS jobs for larger Katana experiments.

1. 持续阅读并维护 thesis story 文档：
   - `docs/theory_spec_syncmark.md`
   - `docs/experimental_plan.md`
   - `AGENT_HANDOFF.md`
2. 需要时复验 synthetic 逻辑，但不得把 synthetic preview 结果当作论文最终结果。
3. 第一阶段集成目标：
   - 将 `syncmark/framing.py` 与 `syncmark/alignment.py` 接入 BiMark 管线，
   - 做 20-50 条样本的 smoke test，
   - 验证 alignment decoder 在 drift 攻击下比 naive position vote / naive ECC 更稳。
4. 只有当 smoke test 结论成立后，才进入 Katana 上的大规模 PBS 批处理实验。

## Environment Rules / 环境约束

- Use the root `uv` project to run both SyncMark and BiMark code. The root `pyproject.toml` and root `uv.lock` are the single source of truth for runtime dependencies.
- Do not create, sync, or document a separate `bimark/` virtual environment for normal runs. Treat any nested `bimark/pyproject.toml` or `bimark/uv.lock` as legacy metadata unless a future migration deliberately removes or repurposes them.
- Run `uv sync` and `uv run ...` from the repository root. Do not run these code paths as bare `python` outside a managed environment.
- Run cross-package smoke tests from the repository root, for example `uv run python -m bimark.run_syncmark_bimark_smoke --trials 20`.
- Avoid heavy computation on the Katana login node.
- If a task is long-running, write a PBS job script first and submit it with `qsub`.
- Start with CPU resources. Request `ngpus=1` or a GPU model only when the code path truly requires GPU execution.
- For GPU jobs using the current lockfile, load `cuda/13.0.0` before running PyTorch. The current root environment resolves to a CUDA 13.0 PyTorch build.
- Set `UV_CACHE_DIR` to a writable path such as `/tmp/${USER}/uv-cache` or a project-local cache before `uv sync` / `uv run`; the default scratch cache may be read-only in some sessions.
- Use `template.pbs` as the reference style for new job scripts.

- 运行 SyncMark 和 BiMark 代码时统一使用根目录 `uv` 项目。根目录 `pyproject.toml` 与根目录 `uv.lock` 是运行依赖的唯一准则。
- 常规运行不要在 `bimark/` 子目录创建、同步或记录独立虚拟环境。除非未来明确迁移，否则嵌套的 `bimark/pyproject.toml` 或 `bimark/uv.lock` 只视为历史元数据。
- 所有 `uv sync` 与 `uv run ...` 都从仓库根目录执行；不要在未托管环境中裸跑 `python`。
- 跨包 smoke test 从仓库根目录执行，例如 `uv run python -m bimark.run_syncmark_bimark_smoke --trials 20`。
- 不要在 Katana 登录节点做重计算。
- 只要任务会长时间运行，就先写 PBS 作业脚本，再用 `qsub` 提交。
- 默认先申请 CPU；只有代码路径明确依赖 GPU 时才申请 `ngpus=1` 或指定 `gpu_model`。
- 使用当前 lockfile 的 GPU 作业应先加载 `cuda/13.0.0`，因为当前根环境解析到 CUDA 13.0 版 PyTorch。
- 在执行 `uv sync` / `uv run` 前，将 `UV_CACHE_DIR` 指向可写路径，例如 `/tmp/${USER}/uv-cache` 或项目内 cache；部分会话中的默认 scratch cache 可能是只读的。
- 新 PBS 作业脚本的风格以 `template.pbs` 为参考。

## Result Logging Standard / 结果记录规范

All progress must be written to files under `./results/logs/` with date-based records.

所有工作进展都必须写入 `./results/logs/` 下按日期组织的记录文件。

Each step record must contain both Chinese and English, and must at minimum answer:

每一步记录都必须同时包含中文和英文，并至少回答以下内容：

- the purpose of the step / 这一步的目的
- what was done / 这一步做了什么
- what result was obtained / 这一步的结果是什么
- what was achieved / 达成了什么
- what the result means / 说明什么
- what the next step is / 后续步骤是什么

Recommended layout:

建议结构：

- one markdown file per dated step, for example `results/logs/2026-04-20_step_01.md`
- experiment outputs such as CSV or JSON should live under `results/` in a task-specific subdirectory
- keep the narrative file bilingual and the raw metrics machine-readable

- 每个步骤一份 markdown 记录，例如 `results/logs/2026-04-20_step_01.md`
- CSV、JSON 等实验原始输出应放在 `results/` 下按任务划分的子目录中
- 叙述性文件保持双语，原始指标文件保持机器可读

## Git Practice / Git 记录

- After code changes and document updates are complete, create a git commit.
- Sync to GitHub when network access and credentials permit.
- If push cannot be completed in the current environment, record the blocker and the local commit hash in the dated result file.

- 在代码修改和文档更新完成后，需要创建 git commit。
- 在网络和凭据允许的情况下同步到 GitHub。
- 如果当前环境无法完成 push，需要把阻塞原因和本地 commit hash 写入对应日期的结果文件中。
