# Legacy fixed-overhead progress sensitivity

Stage 3，2026-09-17。新增的是独立 control，不是替换 JB1，也不是确认恢复 CA-final 源码。
仅使 5 ms fixed overhead 进入 Prefill / Decode progress。使用冻结 JB1 的 `fixed_in_progress=True`；断言 queue overhead=0，intrinsic Prefill、blocking、profile、network、memory、SLA、tie-break 均不变。

复用 1634 个物理 reference records、3268 个 paired judgments；没有新 reference simulation。
所有 workload / scaled workload / partition / profile fingerprints、共同网格、point IDs、参考标签均核验。
每个标签从已有完整请求指标重新核算；Stage 2 raw 和冻结协议逐字节不变。完整清单与核验在 `results/formal/legacy_progress_sensitivity/source_manifest.json` 和 `integrity_checks.json`。

## Judgment：分层计数

| 配置 / SLA | variant | both safe | both unsafe | optimistic | conservative | 分母 |
|---|---|---|---|---|---|---|
| heterogeneous / tight-TPOT | raw | 209 | 1294 | 1 | 0 | 1504 |
| heterogeneous / tight-TPOT | legacy | 181 | 1295 | 0 | 28 | 1504 |
| heterogeneous / relaxed-TPOT (fixed TTFT) | raw | 656 | 436 | 8 | 404 | 1504 |
| heterogeneous / relaxed-TPOT (fixed TTFT) | legacy | 648 | 436 | 8 | 412 | 1504 |
| a100 / tight-TPOT | raw | 26 | 101 | 1 | 2 | 130 |
| a100 / tight-TPOT | legacy | 19 | 102 | 0 | 9 | 130 |
| a100 / relaxed-TPOT (fixed TTFT) | raw | 62 | 48 | 13 | 7 | 130 |
| a100 / relaxed-TPOT (fixed TTFT) | legacy | 58 | 52 | 9 | 11 | 130 |

总计 Raw O=23/C=413，Legacy O=17/C=460；53/3268 标签变化，全部 safe→unsafe。
Legacy both-safe=906、both-unsafe=1885，一致数2791/3268；它降低乐观分歧但增加保守分歧，不能称为统一改善。
异构分母包含两个单候选反向链路 anchor；decision 表仅六个五候选主场景。

## Capacity：沿用原共同网格

| variant | 有限误差 / 76 | 最小 gap | 中位数 | 最大 gap | no-safe | nonmonotone | right-censored |
|---|---|---|---|---|---|---|---|
| raw | 68 | -95.86% | 0.00% | 182.84% | 8 | 0 | 0 |
| legacy | 68 | -95.86% | -15.91% | 165.05% | 8 | 0 | 0 |

每个配置的 largest observed safe、nearest unsafe above、全序列、非单调/no-safe/右删失和相对 gap 都保留在 `summary.json` / `capacity.csv`。
Reference 仍有3个非单调配置、8个no-safe配置、0右删失。Legacy不另行细化网格；局部 gap 不能证明连续容量，控制变体的边界精度也不能自动继承Raw的2.5%目标。

## Decision：12 个主场景

Tight-TPOT：Raw和Legacy均6/6 winner agreement，所选partition都不变；Legacy推荐强度均低约2.14%。
Relaxed-TPOT (fixed TTFT)：Raw为0/6，Legacy为2/6；下表逐项保留所有正负变化。

| 负载 | Raw best → selected | Legacy best → selected | R best | Raw 类型 | Legacy 类型 | Raw 分区损失 | Legacy 分区损失 |
|---|---|---|---|---|---|---|---|
| h101 | [2] → 2 | [2] → 2 | [0] | strict best-set mismatch | strict best-set mismatch | 21.20% | 21.20% |
| h102 | [1, 2] → 1 | [2] → 2 | [0] | strict best-set mismatch | strict best-set mismatch | 8.30% | 14.07% |
| h103 | [2] → 2 | [2] → 2 | [0] | strict best-set mismatch | strict best-set mismatch | 12.19% | 12.19% |
| h104 | [2] → 2 | [0, 1, 2] → 0 | [0, 1] | strict best-set mismatch | agreement | 10.26% | 0.00% |
| h105 | [0, 1, 2] → 0 | [1, 2] → 1 | [1] | tie-break mismatch | agreement | 10.26% | 0.00% |
| h106 | [1, 2] → 1 | [1, 2] → 1 | [2] | tie-break mismatch | tie-break mismatch | 26.16% | 26.16% |

回答原审查问题：h101–h103 strict mismatch保留；h104不再strict且selected winner正确；h105 tie-break mismatch消失，h106保留。
h102反而由shift1转为shift2，reference rank从2降到4，分区损失8.30%→14.07%。
Relaxed场景平均分区损失 Raw 14.73% → Legacy 12.27%；均为六个描述性场景的等权平均。

## 解释

**Yes, but modified.** Reliability / decision transfer 现象并非完全由raw-progress造成，但具体winner、并列集合、错误数明显依赖实现语义。
不能说“6/6 relaxed选偏与实现无关”，也不能将legacy描述为普遍修复或已确认CA-final。
本对照只覆盖名义profiles；已有profile stress仍是Raw JB1结果，不能外推为Legacy stress结果。

复现：`python scripts/stage3_evidence.py legacy`（已有分组结果会校验后复用）；源码 `scripts/stage3_evidence.py`。无需额外reference runs。
