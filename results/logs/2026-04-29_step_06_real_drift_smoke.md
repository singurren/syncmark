# 2026-04-29 Step 06: Real SyncMark-BiMark Drift Smoke

## Purpose / 目的

Add and run a small real-pipeline drift smoke test so the project can compare SyncMark position vote and SyncMark alignment after token-level insertion/deletion drift, rather than only on unattacked generated text.

增加并运行一个小规模真实管线 drift smoke test，使项目能够在 token-level insertion/deletion drift 之后比较 SyncMark position vote 与 SyncMark alignment，而不只是比较未攻击生成文本。

## What Was Done / 完成内容

- Added `bimark/run_real_syncmark_drift_smoke.py`.
- The script reads an existing real generation dump under `output_dump/`, tokenizes generated text, applies token-level drift attacks, extracts observed BiMark bits, and decodes with both SyncMark decoders.
- Added the drift smoke call to `bimark/katana/SyncMark_BiMark_Real_Smoke.pbs` after normal detection.
- Updated `docs/execution_protocol.md` to document the drift smoke command.
- Ran the script on the existing job `7773955` output directory `bimark_c4_gpt2_2026-04-28_18-59-26`.
- Copied the tracked summary artifacts to `results/smoke/2026-04-29_real_drift_smoke/`.

- 新增了 `bimark/run_real_syncmark_drift_smoke.py`。
- 该脚本读取 `output_dump/` 下已有真实生成结果，对生成文本做 tokenizer 编码，施加 token-level drift attack，提取 observed BiMark bits，并用两个 SyncMark decoder 解码。
- 在 `bimark/katana/SyncMark_BiMark_Real_Smoke.pbs` 的普通检测之后追加了 drift smoke 调用。
- 更新了 `docs/execution_protocol.md`，记录 drift smoke 命令。
- 在已有作业 `7773955` 的输出目录 `bimark_c4_gpt2_2026-04-28_18-59-26` 上运行了脚本。
- 将可追踪的 summary artifact 复制到 `results/smoke/2026-04-29_real_drift_smoke/`。

## Result / 结果

The command completed successfully:

命令已成功完成：

```bash
UV_CACHE_DIR=/tmp/${USER}/uv-cache uv run python -m bimark.run_real_syncmark_drift_smoke \
  --data_dir bimark_c4_gpt2_2026-04-28_18-59-26 \
  --max_items 20 \
  --target_lengths 25,50,100 \
  --seed 4242
```

It produced 456 row-level results and 24 summary rows:

它产出了 456 行逐样本结果和 24 行 summary：

```text
output_dump/bimark_c4_gpt2_2026-04-28_18-59-26/syncmark_drift_smoke_n20_seed4242.csv
output_dump/bimark_c4_gpt2_2026-04-28_18-59-26/syncmark_drift_smoke_n20_seed4242_summary.csv
output_dump/bimark_c4_gpt2_2026-04-28_18-59-26/syncmark_drift_smoke_n20_seed4242_metadata.json
```

Tracked copies:

已追踪副本：

```text
results/smoke/2026-04-29_real_drift_smoke/summary.csv
results/smoke/2026-04-29_real_drift_smoke/metadata.json
```

Key summary:

关键汇总：

```text
clean    L=100 vote_hit=0.9276 align_hit=0.8487 vote_exact=0.4737 align_exact=0.1053
delete10 L=100 vote_hit=0.5493 align_hit=0.5526 vote_exact=0.0000 align_exact=0.0000
insert10 L=100 vote_hit=0.5362 align_hit=0.5329 vote_exact=0.0000 align_exact=0.0000
mixed10  L=100 vote_hit=0.5461 align_hit=0.6776 vote_exact=0.0000 align_exact=0.0526
```

## What Was Achieved / 达成内容

The real generation pipeline now has a lightweight drift-attack detection stage. This closes the gap found in Step 05: the project no longer only validates clean generated text.

真实生成管线现在有了轻量级 drift-attack 检测阶段。这补上了 Step 05 中发现的缺口：项目不再只验证 clean generated text。

The first real drift smoke shows that alignment can help under some drift settings, especially `mixed10` at length 100, but it is not yet consistently better across all deletion/insertion settings.

第一次真实 drift smoke 显示 alignment 在部分 drift 设置下可能有帮助，尤其是 `mixed10` 的 length 100；但它还没有在所有 deletion/insertion 设置下稳定优于 position vote。

## Meaning / 结果含义

The thesis-relevant experimental path is now connected end-to-end, but the current SyncMark layout/alignment parameters are not yet strong enough to justify scaling to a full sweep. The clean-text result still favors position vote, which is expected. The attacked-text result is mixed, which means the next work should focus on decoder/layout calibration before expensive cluster experiments.

与 thesis 相关的实验路径现在已经端到端接通，但当前 SyncMark layout/alignment 参数还不足以支撑直接扩大到完整扫参。clean-text 结果仍然偏向 position vote，这是预期内的。attacked-text 结果是混合的，说明下一步应先做 decoder/layout 校准，而不是马上做昂贵的大规模集群实验。

## Next Step / 下一步

Tune the real-pipeline alignment decoder and framing choices on small smoke runs. Immediate candidates are anchor length, alignment weights, target prefix lengths, and attack strengths. After a small setting shows stable gains under deletion/insertion drift, submit a new PBS smoke and only then prepare larger sweeps.

下一步应在小规模 smoke run 上调试真实管线的 alignment decoder 和 framing 选择。优先候选项包括 anchor length、alignment weights、target prefix lengths 和 attack strengths。只有当某个小设置在 deletion/insertion drift 下表现出稳定收益后，再提交新的 PBS smoke，之后才准备更大规模扫参。
