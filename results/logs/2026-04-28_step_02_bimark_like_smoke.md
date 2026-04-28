# 2026-04-28 Step 02: BiMark-like SyncMark Smoke Test

## Purpose / 目的

Run the first 20-50 trial smoke test for the SyncMark-on-BiMark idea, using the current BiMark-like inner signal simulator, and check whether alignment decoding is more stable than naive position vote or Hamming(7,4) under insertion/deletion drift.

使用当前 BiMark-like 内层信号模拟器运行第一轮 20-50 trial smoke test，检查在 insertion/deletion drift 下，alignment decoding 是否比 naive position vote 或 Hamming(7,4) 更稳定。

## What Was Done / 完成内容

- Ran 30-trial no-attack diagnostics.
- Ran 30-trial drift diagnostics with default drift settings.
- Tuned the BiMark integration alignment weights to avoid over-aligning on noisy anchors in the no-attack case.
- Ran mild-drift checks at 160 and 300 slots.
- Ran anchor-length checks at 300 slots with `anchor_len=12` and `anchor_len=16`.
- Stored all CSV outputs under `results/smoke/`.

- 运行了 30 trial 的无攻击诊断。
- 使用默认 drift 设置运行了 30 trial 的插删漂移诊断。
- 调整了 BiMark 接入层的 alignment 权重，避免在无攻击情况下因 noisy anchors 过度错位。
- 在 160 和 300 slots 下运行了 mild drift 检查。
- 在 300 slots 下分别测试了 `anchor_len=12` 和 `anchor_len=16`。
- 所有 CSV 输出均保存在 `results/smoke/`。

## Result / 结果

The no-attack diagnostic initially showed that alignment could misalign even without edits:

无攻击诊断最初显示 alignment 在没有编辑攻击时也可能错位：

```text
results/smoke/2026-04-28_30trial_no_attack/
syncmark_position_vote mean_bit_accuracy = 0.9958
syncmark_alignment     mean_bit_accuracy = 0.9688
```

After using more conservative BiMark-side alignment weights, no-attack behavior matched the position decoder:

使用更保守的 BiMark-side alignment 权重后，无攻击行为与 position decoder 对齐：

```text
results/smoke/2026-04-28_30trial_no_attack_tuned/
syncmark_position_vote mean_bit_accuracy = 0.9958, exact_recovery = 0.9333
syncmark_alignment     mean_bit_accuracy = 0.9958, exact_recovery = 0.9333
```

However, under drift, SyncMark alignment did not beat the baselines:

但是在 drift 条件下，SyncMark alignment 没有超过 baselines：

```text
results/smoke/2026-04-28_30trial_drift_tuned/
bimark_hamming74       mean_bit_accuracy = 0.5875
bimark_position_vote   mean_bit_accuracy = 0.5688
syncmark_position_vote mean_bit_accuracy = 0.5458
syncmark_alignment     mean_bit_accuracy = 0.5396
```

Mild drift and longer text did not reverse the conclusion:

mild drift 和更长文本也没有扭转结论：

```text
results/smoke/2026-04-28_30trial_mild_drift_len300_tuned/
bimark_position_vote   mean_bit_accuracy = 0.7333
syncmark_position_vote mean_bit_accuracy = 0.6688
syncmark_alignment     mean_bit_accuracy = 0.6375
```

Longer anchors also did not help in this simulator:

更长 anchors 在该模拟器中也没有带来收益：

```text
results/smoke/2026-04-28_30trial_mild_drift_len300_anchor12/
syncmark_alignment mean_bit_accuracy = 0.6250

results/smoke/2026-04-28_30trial_mild_drift_len300_anchor16/
syncmark_alignment mean_bit_accuracy = 0.5917
```

## What Was Achieved / 达成内容

- Confirmed the root `uv` environment can run cross-package SyncMark/BiMark smoke tests.
- Fixed an alignment-weight issue that caused unnecessary no-attack misalignment.
- Produced a clear negative diagnostic: the current BiMark-like simulator does not yet demonstrate the intended SyncMark gain.

- 确认根目录 `uv` 环境可以运行跨包 SyncMark/BiMark smoke test。
- 修复了一个 alignment 权重问题，该问题会导致无攻击情况下不必要的错位。
- 得到了明确的否定性诊断：当前 BiMark-like 模拟器尚不能展示预期的 SyncMark 增益。

## Meaning / 结果含义

This smoke test should not be used as evidence that SyncMark improves BiMark. The current simulator is useful for plumbing and diagnostics, but it likely does not model the real BiMark detector's drift failure mode strongly enough. Plain position voting remains competitive in this toy setting, while anchors consume payload budget without recovering enough synchronization.

这轮 smoke test 不能作为 SyncMark 改进 BiMark 的证据。当前模拟器适合测试管线和诊断问题，但它很可能没有充分模拟真实 BiMark detector 的 drift failure mode。在这个 toy setting 中，普通 position voting 仍然很有竞争力，而 anchors 消耗了 payload 预算，却没有恢复足够同步信息。

## Next Step / 下一步

Move from the BiMark-like token simulator to the real BiMark dump pipeline:

从 BiMark-like token simulator 转向真实 BiMark dump 管线：

- Generate 20-50 short samples with real `WatermarkBimark` using root `uv`.
- Store the SyncMark layout bits used during generation.
- Extend detection to extract observed local BiMark bit votes from generated text.
- Compare absolute position vote against `align_and_decode()` on the same observed bitstream.
- Only if this real-pipeline smoke test shows separation should a PBS parameter sweep be prepared.

- 使用根目录 `uv` 和真实 `WatermarkBimark` 生成 20-50 条短文本。
- 保存生成时使用的 SyncMark layout bits。
- 扩展检测流程，从生成文本中提取真实的 local BiMark bit votes。
- 在同一个 observed bitstream 上比较 absolute position vote 与 `align_and_decode()`。
- 只有当这个真实管线 smoke test 显示差异后，才准备 PBS 扫参作业。
