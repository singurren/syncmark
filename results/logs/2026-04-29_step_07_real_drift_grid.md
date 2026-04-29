# 2026-04-29 Step 07: Real Drift Grid Calibration

## Purpose / 目的

Calibrate SyncMark alignment settings on an existing real BiMark generation dump before launching another GPU generation job or a larger PBS sweep.

在提交新的 GPU 生成作业或更大规模 PBS sweep 之前，先在已有真实 BiMark 生成 dump 上校准 SyncMark alignment 设置。

## What Was Done / 完成内容

- Added `bimark/run_real_syncmark_drift_grid.py`.
- Reused the existing job `7773955` output directory `bimark_c4_gpt2_2026-04-28_18-59-26`; no text was regenerated.
- Added a guard that prevents invalid anchor-length scanning on an existing dump unless `--allow_anchor_mismatch` is explicitly set. The generated schedule in this dump used `syncmark_anchor_len=6`, so the valid calibration uses anchor length `6` only.
- Swept alignment weight presets `current`, `default`, `loose_gap`, and `anchor_heavy`.
- Swept target prefix lengths `50,100,150`.
- Swept token-level attacks `clean`, `delete5`, `delete10`, `delete15`, `insert5`, `insert10`, `mixed5`, and `mixed10`.
- Archived summary outputs under `results/smoke/2026-04-29_real_drift_grid/`.

- 新增了 `bimark/run_real_syncmark_drift_grid.py`。
- 复用了已有作业 `7773955` 的输出目录 `bimark_c4_gpt2_2026-04-28_18-59-26`；没有重新生成文本。
- 增加了保护逻辑：除非显式设置 `--allow_anchor_mismatch`，否则不允许在已有 dump 上做无效的 anchor-length 扫描。本 dump 生成时使用 `syncmark_anchor_len=6`，因此合法校准只使用 anchor length `6`。
- 扫描了 alignment weight presets `current`、`default`、`loose_gap` 和 `anchor_heavy`。
- 扫描了 target prefix lengths `50,100,150`。
- 扫描了 token-level attacks `clean`、`delete5`、`delete10`、`delete15`、`insert5`、`insert10`、`mixed5` 和 `mixed10`。
- 将 summary 输出归档到 `results/smoke/2026-04-29_real_drift_grid/`。

## Result / 结果

The command completed successfully:

命令已成功完成：

```bash
UV_CACHE_DIR=/tmp/${USER}/uv-cache uv run python -m bimark.run_real_syncmark_drift_grid \
  --data_dir bimark_c4_gpt2_2026-04-28_18-59-26 \
  --max_items 20 \
  --target_lengths 50,100,150 \
  --output_prefix syncmark_drift_grid_valid_anchor6_n20_seed5151 \
  --seed 5151
```

It produced:

它产出了：

```text
row-level rows: 3336
summary rows: 184
comparison rows: 92
ranking rows: 4
```

Tracked outputs:

已追踪输出：

```text
results/smoke/2026-04-29_real_drift_grid/summary.csv
results/smoke/2026-04-29_real_drift_grid/comparison.csv
results/smoke/2026-04-29_real_drift_grid/ranking.csv
results/smoke/2026-04-29_real_drift_grid/metadata.json
```

Ranked alignment weight configurations over attacked cells, excluding `clean`:

排除 `clean` 后，在 attacked cells 上的 alignment weight 配置排名：

```text
anchor_len=6, weight_preset=loose_gap,    mean_hit_delta=+0.0460, positive_hit_delta_rate=0.70
anchor_len=6, weight_preset=current,      mean_hit_delta=+0.0354, positive_hit_delta_rate=0.65
anchor_len=6, weight_preset=default,      mean_hit_delta=+0.0239, positive_hit_delta_rate=0.65
anchor_len=6, weight_preset=anchor_heavy, mean_hit_delta=+0.0103, positive_hit_delta_rate=0.50
```

For the valid best candidate, `anchor_len=6` and `loose_gap`:

对合法的当前最佳候选 `anchor_len=6`、`loose_gap`：

```text
clean:    mean_hit_delta=-0.1875, positive_rate=0.00
delete5:  mean_hit_delta=+0.0773, positive_rate=0.67
delete10: mean_hit_delta=+0.0219, positive_rate=0.67
delete15: mean_hit_delta=+0.1036, positive_rate=1.00
insert5:  mean_hit_delta=+0.0526, positive_rate=0.67
insert10: mean_hit_delta=+0.0307, positive_rate=0.67
mixed5:   mean_hit_delta=+0.0406, positive_rate=0.67
mixed10:  mean_hit_delta=+0.0143, positive_rate=0.67
```

## What Was Achieved / 达成内容

The project now has a low-cost calibration script that can search valid decoder settings on existing real generation dumps.

项目现在拥有一个低成本校准脚本，可以在已有真实生成 dump 上搜索合法的 decoder 设置。

The first valid calibration found a concrete candidate setting for the existing dump: generated `anchor_len=6` with `loose_gap` alignment weights.

第一次合法校准为已有 dump 找到了一个具体候选设置：生成时的 `anchor_len=6` 搭配 `loose_gap` alignment weights。

## Meaning / 结果含义

The current evidence is stronger than Step 06 but still limited. With the valid generated `anchor_len=6`, alignment is positive on most deletion and light insertion cells, but weaker on `insert10` and only mixed on the stronger drift settings.

当前证据比 Step 06 更强，但仍然有限。在合法的生成 `anchor_len=6` 下，alignment 在多数 deletion 和轻度 insertion cells 上为正，但在 `insert10` 上较弱，在更强 drift 设置上表现仍然混合。

The earlier diagnostic observation that other anchor lengths may look better on this dump is not valid evidence, because anchor length changes alter the generated schedule bits. Anchor length must be evaluated by regenerating text with that anchor length.

此前在该 dump 上看到其他 anchor length 可能更好的现象不能作为有效证据，因为 anchor length 改变会改变生成时的 schedule bits。anchor length 必须通过使用对应 anchor length 重新生成文本来评估。

## Next Step / 下一步

Run one new small GPU smoke that regenerates text with a candidate alternative anchor length, starting with `syncmark_anchor_len=8`, and compare it against the existing `anchor_len=6` result. Keep the grid guard in place so existing dumps are only used for valid decoder-weight calibration.

下一步应提交一个新的小规模 GPU smoke，用候选 alternative anchor length 重新生成文本，先从 `syncmark_anchor_len=8` 开始，并与已有 `anchor_len=6` 结果比较。保留 grid guard，确保已有 dump 只用于合法的 decoder-weight 校准。
