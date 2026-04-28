# 2026-04-28 Step 03: Real BiMark Pipeline Plumbing

## Purpose / 目的

Move beyond the BiMark-like simulator by adding the minimum hooks needed for real `WatermarkBimark` generation and detection with a SyncMark outer schedule.

从 BiMark-like 模拟器推进到真实 `WatermarkBimark` 管线，为 SyncMark outer schedule 增加最小生成与检测接口。

## What Was Done / 完成内容

- Added `--syncmark_outer`, `--syncmark_anchor_len`, and `--syncmark_key` to `bimark/generate_text_dump.py`.
- Generation now builds a SyncMark layout with `syncmark.framing.build_layout()` and passes it to `WatermarkBimark` as `schedule_mode="position_schedule"`.
- Generation records SyncMark metadata in `generation_params.json`, including `schedule_mode`, `schedule_bits`, anchor length, and key.
- Added `WatermarkDetector.extract_position_schedule_observed_bits()` to recover local observed bits from generated token ids under the position-schedule mode.
- Extended `bimark/detect_generation_text_dump.py` so SyncMark runs decode the same observed bitstream with both absolute position vote and `align_and_decode()`.
- Added `bimark/katana/SyncMark_BiMark_Real_Smoke.pbs` for the first real 20-50 sample Katana smoke test.
- Verified the changed files with `py_compile`.

- 给 `bimark/generate_text_dump.py` 增加了 `--syncmark_outer`、`--syncmark_anchor_len`、`--syncmark_key` 参数。
- 生成阶段现在使用 `syncmark.framing.build_layout()` 构造 SyncMark layout，并以 `schedule_mode="position_schedule"` 传给 `WatermarkBimark`。
- 生成阶段会在 `generation_params.json` 中记录 SyncMark 元数据，包括 `schedule_mode`、`schedule_bits`、anchor length 和 key。
- 给 `WatermarkDetector` 增加了 `extract_position_schedule_observed_bits()`，用于从 position-schedule 模式下的生成 token ids 中恢复 local observed bits。
- 扩展了 `bimark/detect_generation_text_dump.py`，使 SyncMark 检测在同一个 observed bitstream 上同时运行 absolute position vote 和 `align_and_decode()`。
- 新增 `bimark/katana/SyncMark_BiMark_Real_Smoke.pbs`，用于第一次真实 20-50 条 Katana smoke test。
- 已使用 `py_compile` 验证修改文件。

## Result / 结果

The following files compile successfully:

以下文件已通过编译检查：

```text
bimark/generate_text_dump.py
bimark/WatermarkBimark.py
bimark/detect_watermark_dump.py
bimark/detect_generation_text_dump.py
bimark/syncmark_support.py
```

The new generation mode is invoked as:

新的生成模式调用方式为：

```bash
uv run python -m bimark.generate_text_dump \
  --method bimark \
  --syncmark_outer \
  --ecc_method none \
  --message 1011001110001111
```

The new detection path is invoked on the generated output directory as:

新的检测路径在生成输出目录上调用：

```bash
uv run python -m bimark.detect_generation_text_dump \
  --data_dir <output_dir_name> \
  --detect
```

The PBS smoke job is:

PBS smoke 作业为：

```bash
qsub bimark/katana/SyncMark_BiMark_Real_Smoke.pbs
```

## What Was Achieved / 达成内容

The codebase now has the minimum real-pipeline path needed to test SyncMark framing and alignment against actual `WatermarkBimark` generation outputs.

代码库现在已经具备最小真实管线路径，可以用真实 `WatermarkBimark` 生成结果测试 SyncMark framing 与 alignment。

## Meaning / 结果含义

The previous BiMark-like simulator remains a diagnostic tool, but the next meaningful smoke test should use this real dump pipeline. This keeps the inner watermark signal identical to BiMark and changes only the outer bit schedule plus detector alignment.

之前的 BiMark-like 模拟器仍可作为诊断工具，但下一次有意义的 smoke test 应使用这条真实 dump 管线。这样可以保持内层水印信号等同于 BiMark，只改变外层 bit schedule 和 detector alignment。

## Next Step / 下一步

Run a 20-50 sample real BiMark smoke test. If model loading or generation requires GPU time, submit it through PBS instead of running it on the login node.

下一步运行 20-50 条样本的真实 BiMark smoke test。如果模型加载或生成需要 GPU 时间，应通过 PBS 提交，而不是在登录节点直接运行。
