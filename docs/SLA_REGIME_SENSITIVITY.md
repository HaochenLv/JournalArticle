# SLA-regime sensitivity: technical evidence

## 1. Frozen protocol

Stage 4是Stage 3之后设计的 controlled parameter sensitivity study，使用同一组六个held-out workloads，不是新的独立held-out generalization test。48 workload-SLA条件不是48独立workloads。仅改变八组TTFT/TPOT阈值；没有新增模型、GPU、network、workload、profile stress、候选或算法。

See [protocol](SLA_SENSITIVITY_PROTOCOL.md), config/sla_sensitivity_protocol.json and protocol_snapshot.json. Canonical hash: `ac61d6e30a9b19823bf8ff595feaf7bdf935ebd72206a712ab001e4968dc3f8b`. Protocol freeze commit `b85816c` precedes every new SLA outcome. Eight fixed pairs, five shifts, two semantics and original link assignments are unchanged. No prior monotonic outcome assumption.

## 2. Source version

Stage 3 source: `69a6b175b5be6788b6448f23edbf1366c1f626c3`; initial HEAD exactly matched and worktree was clean. JB1是journal明确指定的lightweight SLA-aware evaluator；Legacy是implementation-semantic sensitivity control。已撤回且从未公开/出版的AICCC稿不是prior publication。本阶段不寻找所谓final implementation。已accepted的 Evaluator-Guided SLA-Aware Layer Partitioning for Heterogeneous LLM Pipelines 是应区分的prior work；5-shift、evaluator-as-score和原partition search不是journal新增贡献。新增价值仅为SLA-regime sensitivity evidence。

Original launcher was unavailable; bundled Python3.12.14 uses existing networkx3.2.1/matplotlib3.8.4 packages. Host hardware configuration matches Stage 3. Portability source checks and every old-SLA evaluator field except runtime reproduce; original physical points are not rerun. Environment is saved without personal local paths.

## 3. Reused physical points

All1,450 primary-group records are read-only. Per-request aligned TTFT and max per-token TPOT are thresholded via formal_core.reference_details; no overhead is added. The old two-SLA labels (8,700 E/R/control comparisons) and24 semantic decision records including reference score vectors/best sets reproduce. Every new SLA actually calls journal_baseline.evaluate.

## 4. New physical points

复用1,450个原physical points，未重跑这些HELIX点。新增unique physical points=600，成功=600，physical attempts=600，retry=0，timeout=0，最终failed=0。Evaluator实际保存32,800次重新调用结果，其中原grid23,200次、新grid9,600次。Reference分类16,400次；Raw/Legacy共享物理真值。

Killable600s attempts, at most one same-input retry, original memory-aware scheduler ceiling12/budget24GiB/reserve6GiB. Full per-token metrics and input fingerprints are in reference/*.json.gz. Per-attempt journals are retained. No failed point becomes unsafe.

## 5. Refinement process

Union of all both-direction verdict transitions over5 candidates×8 SLA×3 models. Width>2.5% proposes round(sqrt(lower*upper),10); priority descending log width then lower endpoint. Every addition applies to five candidates and all SLA/semantics. Max24 additions/workload, six rounds and720 unique physical points overall. Original intensity range unchanged. Exact round plans, witnesses and unselected intervals are in refinement_history.json. Verification replays every selection against its prior grid.

## 6. Grid sizes before/after

| 负载 | 原grid | 最终grid | 新增强度 | 新增物理点 | 有新增轮数 | 未解决interval | 停止原因 |
|---|---|---|---|---|---|---|---|
| h101 | 51 | 75 | 24 | 120 | 4 | 12 | 24-intensity budget |
| h102 | 53 | 77 | 24 | 120 | 3 | 6 | 24-intensity budget |
| h103 | 46 | 70 | 24 | 120 | 6 | 0 | no unresolved transition |
| h104 | 41 | 52 | 11 | 55 | 6 | 0 | no unresolved transition |
| h105 | 49 | 73 | 24 | 120 | 3 | 9 | 24-intensity budget |
| h106 | 50 | 63 | 13 | 65 | 5 | 0 | no unresolved transition |

## 7. Judgment results

存在明显但非单调的变化。六个TPOT下Raw O依次为1、1、2、2、23、8，C为0、50、0、139、803、600（每格分母2050）；Legacy O为0、0、0、0、23、8，C为26、76、24、163、804、608。0.6→1.2时保守分歧下降，5→10时O和C同时下降。Raw在1.2仅2个O点，却包含h102的实际推荐；低总体分歧计数不能替代输出点检查。

| TTFT / TPOT (s) | 语义 | both-safe | both-unsafe | O | C | paired |
|---|---|---|---|---|---|---|
| 5.2 / 0.3 | raw | 217 | 1832 | 1 | 0 | 2050 |
| 5.2 / 0.3 | legacy | 191 | 1833 | 0 | 26 | 2050 |
| 5.2 / 0.6 | raw | 217 | 1782 | 1 | 50 | 2050 |
| 5.2 / 0.6 | legacy | 191 | 1783 | 0 | 76 | 2050 |
| 5.2 / 1.2 | raw | 275 | 1773 | 2 | 0 | 2050 |
| 5.2 / 1.2 | legacy | 251 | 1775 | 0 | 24 | 2050 |
| 5.2 / 2.4 | raw | 275 | 1634 | 2 | 139 | 2050 |
| 5.2 / 2.4 | legacy | 251 | 1636 | 0 | 163 | 2050 |
| 5.2 / 5 | raw | 672 | 552 | 23 | 803 | 2050 |
| 5.2 / 5 | legacy | 671 | 552 | 23 | 804 | 2050 |
| 5.2 / 10 | raw | 966 | 476 | 8 | 600 | 2050 |
| 5.2 / 10 | legacy | 958 | 476 | 8 | 608 | 2050 |
| 4.68 / 1.2 | raw | 161 | 1888 | 1 | 0 | 2050 |
| 4.68 / 1.2 | legacy | 142 | 1889 | 0 | 19 | 2050 |
| 4.68 / 10 | raw | 663 | 1068 | 0 | 319 | 2050 |
| 4.68 / 10 | legacy | 656 | 1068 | 0 | 326 | 2050 |

raw.csv has one row per point/SLA/semantic. `point_record` resolves to `points/<group>/<point_record>.json.gz`, containing full input fingerprints and first complete evaluator violation sets; this avoids repeating large ledgers sixteen times. No compact-adapter ordering is interpreted as physical causality. Counts are adaptive-sample descriptions.

## 8. Capacity results

没有贯穿所有SLA/候选的同一误差方向。Raw在0.3/0.6/1.2/2.4的相对gap中位数均为0，但0.6已有5个负gap，2.4已有10个负gap且最小达−99.81%；正gap在这些阈值仍存在。TPOT5的27个有定义候选gap全部为负，中位−95.08%；到10中位回升至−75.00%。Legacy在较紧TPOT通常更保守，而5/10的gap中位数与Raw相同。240条去重后的reference候选/SLA序列（并非独立随机样本）保留38个no-safe、23个nonmonotone、0个right-censored；不能把中位数或最大safe当成连续安全容量。

| TTFT / TPOT | 语义 | 有定义gap | 负 / 零 / 正 | 最小 | 中位 | 最大 |
|---|---|---|---|---|---|---|
| 5.2 / 0.3 | raw | 27 | 0 / 26 / 1 | 0.00% | 0.00% | 2.19% |
| 5.2 / 0.3 | legacy | 27 | 26 / 1 / 0 | -8.30% | -2.14% | 0.00% |
| 5.2 / 0.6 | raw | 27 | 5 / 21 / 1 | -22.89% | 0.00% | 2.19% |
| 5.2 / 0.6 | legacy | 27 | 26 / 1 / 0 | -24.54% | -2.14% | 0.00% |
| 5.2 / 1.2 | raw | 27 | 0 / 25 / 2 | 0.00% | 0.00% | 2.19% |
| 5.2 / 1.2 | legacy | 27 | 24 / 3 / 0 | -8.30% | -2.14% | 0.00% |
| 5.2 / 2.4 | raw | 27 | 10 / 15 / 2 | -99.81% | 0.00% | 2.19% |
| 5.2 / 2.4 | legacy | 27 | 24 / 3 / 0 | -99.83% | -2.14% | 0.00% |
| 5.2 / 5 | raw | 27 | 27 / 0 / 0 | -97.93% | -95.08% | -87.50% |
| 5.2 / 5 | legacy | 27 | 27 / 0 / 0 | -97.93% | -95.08% | -87.77% |
| 5.2 / 10 | raw | 27 | 27 / 0 / 0 | -95.86% | -75.00% | -60.60% |
| 5.2 / 10 | legacy | 27 | 27 / 0 / 0 | -95.86% | -75.00% | -60.60% |
| 4.68 / 1.2 | raw | 20 | 0 / 19 / 1 | 0.00% | 0.00% | 2.19% |
| 4.68 / 1.2 | legacy | 20 | 19 / 1 / 0 | -8.30% | -2.14% | 0.00% |
| 4.68 / 10 | raw | 20 | 20 / 0 / 0 | -86.95% | -76.04% | -47.79% |
| 4.68 / 10 | legacy | 20 | 20 / 0 / 0 | -87.23% | -76.04% | -47.79% |

capacity.csv and summary.json retain all480 semantic/candidate/SLA entries, including complete E/R sequences (null for missing), largest safe, nearest unsafe above, no-safe, right-censoring, nonmonotonicity, all transition intervals, local bracket width and unresolved flag. Reference sequences repeat under both semantic labels for comparison; there are240 distinct reference candidate/SLA sequences. No continuous-capacity theorem is claimed.

## 9. Decision results

最终网格上，最早的Raw mismatch出现在TPOT1.2的h102，是best sets有交集但tie-break选出−1、reference-best仅−2的情况；2.4继续保留。首个strict mismatch出现在2.4的h101和h105（两种语义均如此）。h103在5开始strict；h106在5开始tie-break；h104 Raw到10才strict，而Legacy在TTFT5.2的六个TPOT均agreement。出现/消失/再出现并存，不存在本实验支持的统一critical TPOT阈值。

| 负载 | 语义 | 5.2 / 0.3 | 5.2 / 0.6 | 5.2 / 1.2 | 5.2 / 2.4 | 5.2 / 5 | 5.2 / 10 | 4.68 / 1.2 | 4.68 / 10 |
|---|---|---|---|---|---|---|---|---|---|
| h101 | raw | A | A | A | S | A | S | A | S |
| h101 | legacy | A | A | A | S | A | S | A | S |
| h102 | raw | A | A | T | T | A | S | N | N |
| h102 | legacy | A | A | A | A | A | S | N | N |
| h103 | raw | A | A | A | A | S | S | A | S |
| h103 | legacy | A | A | A | A | S | S | A | S |
| h104 | raw | A | A | A | A | A | S | A | S |
| h104 | legacy | A | A | A | A | A | A | A | T |
| h105 | raw | A | A | A | S | T | T | A | T |
| h105 | legacy | A | A | A | S | T | A | A | A |
| h106 | raw | A | A | A | A | T | T | N | N |
| h106 | legacy | A | A | A | A | T | T | N | N |

Tie-break is smallest |shift|, then negative. Best-set overlap does not itself mean selected agreement. Competition rank, best sets and loss remain explicit. Code legend: A agreement, S strict mismatch, T tie-break mismatch, N abstention/no-safe recommendation, R no-safe reference, F incomplete reference.

## 10. Operating-point results

两层损失在中间SLA仍显著不同。TPOT5时Raw和Legacy的平均分区损失仅2.43%，平均运行点损失却为94.90%（范围90.57%–97.93%）；h101、h102、h104虽然选对分区，运行点损失分别94.97%、95.86%、95.58%。TPOT2.4的h105分区损失19.48%，Raw运行点损失99.79%。更关键的是h102在TPOT1.2/2.4：Raw的B=L=0.0108340444，S=0.0106018931，partition loss=2.14%，allocation=−2.14%，所以算术operating loss=0%；但所选shift−1的该点有3/54请求违反TPOT，safe loss=100%。Legacy选shift−2，同一推荐强度实际safe，safe loss=0%。

| TTFT / TPOT | 语义 | 平均分区loss | 平均运行点loss | 平均安全运行点loss | 定义分母(分区/运行/安全) | unsafe推荐 | 弃权 |
|---|---|---|---|---|---|---|---|
| 5.2 / 0.3 | raw | 0.00% | 0.00% | 0.00% | 6/6/6 | 0 | 0 |
| 5.2 / 0.3 | legacy | 0.00% | 2.14% | 2.14% | 6/6/6 | 0 | 0 |
| 5.2 / 0.6 | raw | 0.00% | 3.81% | 3.81% | 6/6/6 | 0 | 0 |
| 5.2 / 0.6 | legacy | 0.00% | 5.88% | 5.88% | 6/6/6 | 0 | 0 |
| 5.2 / 1.2 | raw | 0.36% | 0.00% | 16.67% | 6/6/6 | 1 | 0 |
| 5.2 / 1.2 | legacy | 0.00% | 1.79% | 1.79% | 6/6/6 | 0 | 0 |
| 5.2 / 2.4 | raw | 4.99% | 27.14% | 43.81% | 6/6/6 | 1 | 0 |
| 5.2 / 2.4 | legacy | 4.63% | 28.35% | 28.35% | 6/6/6 | 0 | 0 |
| 5.2 / 5 | raw | 2.43% | 94.90% | 95.82% | 6/6/6 | 1 | 0 |
| 5.2 / 5 | legacy | 2.43% | 94.90% | 95.82% | 6/6/6 | 1 | 0 |
| 5.2 / 10 | raw | 14.73% | 79.98% | 80.67% | 6/6/6 | 1 | 0 |
| 5.2 / 10 | legacy | 12.27% | 80.04% | 80.73% | 6/6/6 | 1 | 0 |
| 4.68 / 1.2 | raw | 0.00% | 0.00% | 0.00% | 4/4/4 | 0 | 2 |
| 4.68 / 1.2 | legacy | 0.00% | 2.14% | 2.14% | 4/4/4 | 0 | 2 |
| 4.68 / 10 | raw | 10.13% | 72.80% | 72.80% | 4/4/4 | 0 | 2 |
| 4.68 / 10 | legacy | 7.56% | 72.91% | 72.91% | 4/4/4 | 0 | 2 |

| 负载 | SLA | 语义 | 违反请求 / 总数 | fraction | 最大TTFT超限(s) | 最大TPOT超限(s) | 类型 |
|---|---|---|---|---|---|---|---|
| h102 | TTFT5.2_TPOT1.2 | raw | 3 / 54 | 5.56% | 0 | 3.54843 | TPOT only |
| h102 | TTFT5.2_TPOT2.4 | raw | 3 / 54 | 5.56% | 0 | 2.34843 | TPOT only |
| h106 | TTFT5.2_TPOT5 | raw | 7 / 49 | 14.29% | 0.0292473 | 0.236598 | both |
| h106 | TTFT5.2_TPOT5 | legacy | 7 / 49 | 14.29% | 0.0292473 | 0.236598 | both |
| h106 | TTFT5.2_TPOT10 | raw | 1 / 49 | 2.04% | 0.0292473 | 0 | TTFT only |
| h106 | TTFT5.2_TPOT10 | legacy | 1 / 49 | 2.04% | 0.0292473 | 0 | TTFT only |

Full96-row decisions and operating points follow. B=0 quantities are undefined. Partition loss and operating loss are not additive; partition+allocation is operating loss. Safety-adjusted usable load is0 for an unsafe recommendation or abstention, with no inference about unqueried or lower loads.

| 负载 | SLA | 语义 | E best → selected | R best | 类型 | R rank | B | S | L | 分区loss | 运行点loss | allocation | R-safe(L) | safe loss |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| h101 | TTFT5.2_TPOT0.3 | raw | [-2] → -2 | [-2] | A | 1 | 0.00993486 | 0.00993486 | 0.00993486 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h101 | TTFT5.2_TPOT0.3 | legacy | [-2] → -2 | [-2] | A | 1 | 0.00993486 | 0.00993486 | 0.00972198 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h101 | TTFT5.2_TPOT0.6 | raw | [-2] → -2 | [-2] | A | 1 | 0.00993486 | 0.00993486 | 0.00993486 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h101 | TTFT5.2_TPOT0.6 | legacy | [-2] → -2 | [-2] | A | 1 | 0.00993486 | 0.00993486 | 0.00972198 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h101 | TTFT5.2_TPOT1.2 | raw | [-2] → -2 | [-2] | A | 1 | 0.00993486 | 0.00993486 | 0.00993486 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h101 | TTFT5.2_TPOT1.2 | legacy | [-2] → -2 | [-2] | A | 1 | 0.00993486 | 0.00993486 | 0.00972198 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h101 | TTFT5.2_TPOT2.4 | raw | [-2] → -2 | [0, 1, 2] | S | 4 | 0.0269087 | 0.0246754 | 0.00993486 | 8.30% | 63.08% | 54.78% | True | 63.08% |
| h101 | TTFT5.2_TPOT2.4 | legacy | [-2] → -2 | [0, 1, 2] | S | 4 | 0.0269087 | 0.0246754 | 0.00972198 | 8.30% | 63.87% | 55.57% | True | 63.87% |
| h101 | TTFT5.2_TPOT5 | raw | [-2, -1, 0, 1, 2] → 0 | [0] | A | 1 | 13.1931 | 13.1931 | 0.663982 | 0.00% | 94.97% | 94.97% | True | 94.97% |
| h101 | TTFT5.2_TPOT5 | legacy | [-2, -1, 0, 1, 2] → 0 | [0] | A | 1 | 13.1931 | 13.1931 | 0.663982 | 0.00% | 94.97% | 94.97% | True | 94.97% |
| h101 | TTFT5.2_TPOT10 | raw | [2] → 2 | [0] | S | 4 | 13.1931 | 10.3961 | 4.096 | 21.20% | 68.95% | 47.75% | True | 68.95% |
| h101 | TTFT5.2_TPOT10 | legacy | [2] → 2 | [0] | S | 4 | 13.1931 | 10.3961 | 4.096 | 21.20% | 68.95% | 47.75% | True | 68.95% |
| h101 | TTFT4.68_TPOT1.2 | raw | [-2] → -2 | [-2] | A | 1 | 0.00993486 | 0.00993486 | 0.00993486 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h101 | TTFT4.68_TPOT1.2 | legacy | [-2] → -2 | [-2] | A | 1 | 0.00993486 | 0.00993486 | 0.00972198 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h101 | TTFT4.68_TPOT10 | raw | [2] → 2 | [0] | S | 3 | 9.53323 | 7.84469 | 4.096 | 17.71% | 57.03% | 39.32% | True | 57.03% |
| h101 | TTFT4.68_TPOT10 | legacy | [2] → 2 | [0] | S | 3 | 9.53323 | 7.84469 | 4.096 | 17.71% | 57.03% | 39.32% | True | 57.03% |
| h102 | TTFT5.2_TPOT0.3 | raw | [-2] → -2 | [-2] | A | 1 | 0.00835419 | 0.00835419 | 0.00835419 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h102 | TTFT5.2_TPOT0.3 | legacy | [-2] → -2 | [-2] | A | 1 | 0.00835419 | 0.00835419 | 0.00817518 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h102 | TTFT5.2_TPOT0.6 | raw | [-2] → -2 | [-2] | A | 1 | 0.010834 | 0.010834 | 0.00835419 | 0.00% | 22.89% | 22.89% | True | 22.89% |
| h102 | TTFT5.2_TPOT0.6 | legacy | [-2] → -2 | [-2] | A | 1 | 0.010834 | 0.010834 | 0.00817518 | 0.00% | 24.54% | 24.54% | True | 24.54% |
| h102 | TTFT5.2_TPOT1.2 | raw | [-2, -1] → -1 | [-2] | T | 2 | 0.010834 | 0.0106019 | 0.010834 | 2.14% | 0.00% | -2.14% | False | 100.00% |
| h102 | TTFT5.2_TPOT1.2 | legacy | [-2] → -2 | [-2] | A | 1 | 0.010834 | 0.010834 | 0.010834 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h102 | TTFT5.2_TPOT2.4 | raw | [-2, -1] → -1 | [-2] | T | 2 | 0.010834 | 0.0106019 | 0.010834 | 2.14% | 0.00% | -2.14% | False | 100.00% |
| h102 | TTFT5.2_TPOT2.4 | legacy | [-2] → -2 | [-2] | A | 1 | 0.010834 | 0.010834 | 0.010834 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h102 | TTFT5.2_TPOT5 | raw | [-2, -1, 0, 1, 2] → 0 | [0, 1] | A | 1 | 8.74201 | 8.74201 | 0.362039 | 0.00% | 95.86% | 95.86% | True | 95.86% |
| h102 | TTFT5.2_TPOT5 | legacy | [-2, -1, 0, 1, 2] → 0 | [0, 1] | A | 1 | 8.74201 | 8.74201 | 0.362039 | 0.00% | 95.86% | 95.86% | True | 95.86% |
| h102 | TTFT5.2_TPOT10 | raw | [1, 2] → 1 | [0] | S | 2 | 9.74198 | 8.93344 | 2.48883 | 8.30% | 74.45% | 66.15% | True | 74.45% |
| h102 | TTFT5.2_TPOT10 | legacy | [2] → 2 | [0] | S | 4 | 9.74198 | 8.37138 | 2.48883 | 14.07% | 74.45% | 60.38% | True | 74.45% |
| h102 | TTFT4.68_TPOT1.2 | raw | [] → None | [] | N | None | 0 | undefined | undefined | undefined | undefined | undefined | None | undefined |
| h102 | TTFT4.68_TPOT1.2 | legacy | [] → None | [] | N | None | 0 | undefined | undefined | undefined | undefined | undefined | None | undefined |
| h102 | TTFT4.68_TPOT10 | raw | [] → None | [] | N | None | 0 | undefined | undefined | undefined | undefined | undefined | None | undefined |
| h102 | TTFT4.68_TPOT10 | legacy | [] → None | [] | N | None | 0 | undefined | undefined | undefined | undefined | undefined | None | undefined |
| h103 | TTFT5.2_TPOT0.3 | raw | [-2] → -2 | [-2] | A | 1 | 0.00835419 | 0.00835419 | 0.00835419 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h103 | TTFT5.2_TPOT0.3 | legacy | [-2] → -2 | [-2] | A | 1 | 0.00835419 | 0.00835419 | 0.00817518 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h103 | TTFT5.2_TPOT0.6 | raw | [-2] → -2 | [-2] | A | 1 | 0.00835419 | 0.00835419 | 0.00835419 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h103 | TTFT5.2_TPOT0.6 | legacy | [-2] → -2 | [-2] | A | 1 | 0.00835419 | 0.00835419 | 0.00817518 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h103 | TTFT5.2_TPOT1.2 | raw | [-2] → -2 | [-2] | A | 1 | 0.00835419 | 0.00835419 | 0.00835419 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h103 | TTFT5.2_TPOT1.2 | legacy | [-2] → -2 | [-2] | A | 1 | 0.00835419 | 0.00835419 | 0.00817518 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h103 | TTFT5.2_TPOT2.4 | raw | [-2] → -2 | [-2] | A | 1 | 0.00835419 | 0.00835419 | 0.00835419 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h103 | TTFT5.2_TPOT2.4 | legacy | [-2] → -2 | [-2] | A | 1 | 0.00835419 | 0.00835419 | 0.00817518 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h103 | TTFT5.2_TPOT5 | raw | [1, 2] → 1 | [0] | S | 2 | 9.74198 | 9.53323 | 0.918891 | 2.14% | 90.57% | 88.42% | True | 90.57% |
| h103 | TTFT5.2_TPOT5 | legacy | [1, 2] → 1 | [0] | S | 2 | 9.74198 | 9.53323 | 0.918891 | 2.14% | 90.57% | 88.42% | True | 90.57% |
| h103 | TTFT5.2_TPOT10 | raw | [2] → 2 | [0] | S | 3 | 9.74198 | 8.55469 | 2.83425 | 12.19% | 70.91% | 58.72% | True | 70.91% |
| h103 | TTFT5.2_TPOT10 | legacy | [2] → 2 | [0] | S | 3 | 9.74198 | 8.55469 | 2.83425 | 12.19% | 70.91% | 58.72% | True | 70.91% |
| h103 | TTFT4.68_TPOT1.2 | raw | [-2] → -2 | [-2] | A | 1 | 0.00835419 | 0.00835419 | 0.00835419 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h103 | TTFT4.68_TPOT1.2 | legacy | [-2] → -2 | [-2] | A | 1 | 0.00835419 | 0.00835419 | 0.00817518 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h103 | TTFT4.68_TPOT10 | raw | [2] → 2 | [0] | S | 3 | 7.19361 | 6.59657 | 1.7984 | 8.30% | 75.00% | 66.70% | True | 75.00% |
| h103 | TTFT4.68_TPOT10 | legacy | [2] → 2 | [0] | S | 3 | 7.19361 | 6.59657 | 1.7984 | 8.30% | 75.00% | 66.70% | True | 75.00% |
| h104 | TTFT5.2_TPOT0.3 | raw | [-2] → -2 | [-2] | A | 1 | 0.0035125 | 0.0035125 | 0.0035125 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h104 | TTFT5.2_TPOT0.3 | legacy | [-2] → -2 | [-2] | A | 1 | 0.0035125 | 0.0035125 | 0.00343724 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h104 | TTFT5.2_TPOT0.6 | raw | [-2] → -2 | [-2] | A | 1 | 0.0035125 | 0.0035125 | 0.0035125 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h104 | TTFT5.2_TPOT0.6 | legacy | [-2] → -2 | [-2] | A | 1 | 0.0035125 | 0.0035125 | 0.00343724 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h104 | TTFT5.2_TPOT1.2 | raw | [-2] → -2 | [-2] | A | 1 | 0.0035125 | 0.0035125 | 0.0035125 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h104 | TTFT5.2_TPOT1.2 | legacy | [-2] → -2 | [-2] | A | 1 | 0.0035125 | 0.0035125 | 0.00343724 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h104 | TTFT5.2_TPOT2.4 | raw | [-2] → -2 | [-2] | A | 1 | 0.0035125 | 0.0035125 | 0.0035125 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h104 | TTFT5.2_TPOT2.4 | legacy | [-2] → -2 | [-2] | A | 1 | 0.0035125 | 0.0035125 | 0.00343724 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h104 | TTFT5.2_TPOT5 | raw | [1, 2] → 1 | [0, 1] | A | 1 | 6.74101 | 6.74101 | 0.297914 | 0.00% | 95.58% | 95.58% | True | 95.58% |
| h104 | TTFT5.2_TPOT5 | legacy | [1, 2] → 1 | [0, 1] | A | 1 | 6.74101 | 6.74101 | 0.297914 | 0.00% | 95.58% | 95.58% | True | 95.58% |
| h104 | TTFT5.2_TPOT10 | raw | [2] → 2 | [0, 1] | S | 3 | 6.74101 | 6.04908 | 1.21775 | 10.26% | 81.94% | 71.67% | True | 81.94% |
| h104 | TTFT5.2_TPOT10 | legacy | [0, 1, 2] → 0 | [0, 1] | A | 1 | 6.74101 | 6.74101 | 1.19165 | 0.00% | 82.32% | 82.32% | True | 82.32% |
| h104 | TTFT4.68_TPOT1.2 | raw | [-2] → -2 | [-2] | A | 1 | 0.0035125 | 0.0035125 | 0.0035125 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h104 | TTFT4.68_TPOT1.2 | legacy | [-2] → -2 | [-2] | A | 1 | 0.0035125 | 0.0035125 | 0.00343724 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h104 | TTFT4.68_TPOT10 | raw | [2] → 2 | [1] | S | 3 | 6.45522 | 5.79262 | 1.21775 | 10.26% | 81.14% | 70.87% | True | 81.14% |
| h104 | TTFT4.68_TPOT10 | legacy | [0, 1, 2] → 0 | [1] | T | 2 | 6.45522 | 6.18154 | 1.19165 | 4.24% | 81.54% | 77.30% | True | 81.54% |
| h105 | TTFT5.2_TPOT0.3 | raw | [-2] → -2 | [-2] | A | 1 | 0.00911031 | 0.00911031 | 0.00911031 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h105 | TTFT5.2_TPOT0.3 | legacy | [-2] → -2 | [-2] | A | 1 | 0.00911031 | 0.00911031 | 0.00891509 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h105 | TTFT5.2_TPOT0.6 | raw | [-2] → -2 | [-2] | A | 1 | 0.00911031 | 0.00911031 | 0.00911031 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h105 | TTFT5.2_TPOT0.6 | legacy | [-2] → -2 | [-2] | A | 1 | 0.00911031 | 0.00911031 | 0.00891509 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h105 | TTFT5.2_TPOT1.2 | raw | [-2] → -2 | [-2] | A | 1 | 0.00911031 | 0.00911031 | 0.00911031 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h105 | TTFT5.2_TPOT1.2 | legacy | [-2] → -2 | [-2] | A | 1 | 0.00911031 | 0.00911031 | 0.00891509 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h105 | TTFT5.2_TPOT2.4 | raw | [-2] → -2 | [1, 2] | S | 5 | 4.27735 | 3.44431 | 0.00911031 | 19.48% | 99.79% | 80.31% | True | 99.79% |
| h105 | TTFT5.2_TPOT2.4 | legacy | [-2] → -2 | [1, 2] | S | 5 | 4.27735 | 3.44431 | 0.00891509 | 19.48% | 99.79% | 80.32% | True | 99.79% |
| h105 | TTFT5.2_TPOT5 | raw | [-2, -1, 0, 1, 2] → 0 | [1] | T | 2 | 41.5843 | 37.3158 | 0.861078 | 10.26% | 97.93% | 87.66% | True | 97.93% |
| h105 | TTFT5.2_TPOT5 | legacy | [-2, -1, 0, 1, 2] → 0 | [1] | T | 2 | 41.5843 | 37.3158 | 0.861078 | 10.26% | 97.93% | 87.66% | True | 97.93% |
| h105 | TTFT5.2_TPOT10 | raw | [0, 1, 2] → 0 | [1] | T | 2 | 41.5843 | 37.3158 | 5.08665 | 10.26% | 87.77% | 77.50% | True | 87.77% |
| h105 | TTFT5.2_TPOT10 | legacy | [1, 2] → 1 | [1] | A | 1 | 41.5843 | 41.5843 | 5.08665 | 0.00% | 87.77% | 87.77% | True | 87.77% |
| h105 | TTFT4.68_TPOT1.2 | raw | [-2] → -2 | [-2] | A | 1 | 0.00911031 | 0.00911031 | 0.00911031 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h105 | TTFT4.68_TPOT1.2 | legacy | [-2] → -2 | [-2] | A | 1 | 0.00911031 | 0.00911031 | 0.00891509 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h105 | TTFT4.68_TPOT10 | raw | [0, 1, 2] → 0 | [1] | T | 2 | 23.1705 | 22.1881 | 5.08665 | 4.24% | 78.05% | 73.81% | True | 78.05% |
| h105 | TTFT4.68_TPOT10 | legacy | [1, 2] → 1 | [1] | A | 1 | 23.1705 | 23.1705 | 5.08665 | 0.00% | 78.05% | 78.05% | True | 78.05% |
| h106 | TTFT5.2_TPOT0.3 | raw | [1] → 1 | [1] | A | 1 | 0.00835419 | 0.00835419 | 0.00835419 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h106 | TTFT5.2_TPOT0.3 | legacy | [1] → 1 | [1] | A | 1 | 0.00835419 | 0.00835419 | 0.00817518 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h106 | TTFT5.2_TPOT0.6 | raw | [1] → 1 | [1] | A | 1 | 0.00835419 | 0.00835419 | 0.00835419 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h106 | TTFT5.2_TPOT0.6 | legacy | [1] → 1 | [1] | A | 1 | 0.00835419 | 0.00835419 | 0.00817518 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h106 | TTFT5.2_TPOT1.2 | raw | [1] → 1 | [1] | A | 1 | 0.00835419 | 0.00835419 | 0.00835419 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h106 | TTFT5.2_TPOT1.2 | legacy | [1] → 1 | [1] | A | 1 | 0.00835419 | 0.00835419 | 0.00817518 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h106 | TTFT5.2_TPOT2.4 | raw | [1] → 1 | [1] | A | 1 | 0.00835419 | 0.00835419 | 0.00835419 | 0.00% | 0.00% | 0.00% | True | 0.00% |
| h106 | TTFT5.2_TPOT2.4 | legacy | [1] → 1 | [1] | A | 1 | 0.00835419 | 0.00835419 | 0.00817518 | 0.00% | 2.14% | 2.14% | True | 2.14% |
| h106 | TTFT5.2_TPOT5 | raw | [1, 2] → 1 | [2] | T | 2 | 4.18569 | 4.096 | 0.229723 | 2.14% | 94.51% | 92.37% | False | 100.00% |
| h106 | TTFT5.2_TPOT5 | legacy | [1, 2] → 1 | [2] | T | 2 | 4.18569 | 4.096 | 0.229723 | 2.14% | 94.51% | 92.37% | False | 100.00% |
| h106 | TTFT5.2_TPOT10 | raw | [1, 2] → 1 | [2] | T | 2 | 5.54703 | 4.096 | 0.229723 | 26.16% | 95.86% | 69.70% | False | 100.00% |
| h106 | TTFT5.2_TPOT10 | legacy | [1, 2] → 1 | [2] | T | 2 | 5.54703 | 4.096 | 0.229723 | 26.16% | 95.86% | 69.70% | False | 100.00% |
| h106 | TTFT4.68_TPOT1.2 | raw | [] → None | [] | N | None | 0 | undefined | undefined | undefined | undefined | undefined | None | undefined |
| h106 | TTFT4.68_TPOT1.2 | legacy | [] → None | [] | N | None | 0 | undefined | undefined | undefined | undefined | undefined | None | undefined |
| h106 | TTFT4.68_TPOT10 | raw | [] → None | [] | N | None | 0 | undefined | undefined | undefined | undefined | undefined | None | undefined |
| h106 | TTFT4.68_TPOT10 | legacy | [] → None | [] | N | None | 0 | undefined | undefined | undefined | undefined | undefined | None | undefined |

## 11. Raw vs Legacy

判定差异在TPOT0.3/0.6各27个标签、1.2/2.4各26个、5仅1个、10为8个；最大判定差异不对应最大选分区差异。TPOT5时两种语义的六个selected shifts、决策类型、两类主loss均相同，仅一个非推荐候选点标签不同，差异近乎消失。TPOT10的selected差异最大（3/6）：Legacy修复h104/h105的winner，但h102分区损失由8.30%增至14.07%，h106仍选偏且不安全。最大安全调整损失差出现在h102的1.2/2.4，Raw100%对Legacy0%；Legacy在这些条件有益，但不能称为全局改善。

| SLA | 标签变化数 | selected变化 | 决策类型变化 | 最大分区loss差 | 最大运行点loss差 |
|---|---|---|---|---|---|
| TTFT5.2_TPOT0.3 | 27 | 0 | 0 | 0.00% | 2.14% |
| TTFT5.2_TPOT0.6 | 27 | 0 | 0 | 0.00% | 2.14% |
| TTFT5.2_TPOT1.2 | 26 | 1 | 1 | 2.14% | 2.14% |
| TTFT5.2_TPOT2.4 | 26 | 1 | 1 | 2.14% | 2.14% |
| TTFT5.2_TPOT5 | 1 | 0 | 0 | 0.00% | 0.00% |
| TTFT5.2_TPOT10 | 8 | 3 | 2 | 10.26% | 0.39% |
| TTFT4.68_TPOT1.2 | 20 | 0 | 0 | 0.00% | 2.14% |
| TTFT4.68_TPOT10 | 7 | 2 | 2 | 6.02% | 0.40% |

## 12. TTFT tightening

收紧到4.68后，h102和h106在两组受测TPOT下均无任何采样reference-safe候选，E也弃权；B=0，所有relative quality未定义，不能把其消失的不安全推荐算作性能改善。剩余四个负载在TPOT1.2均agreement。在TPOT10，Legacy h104由agreement变成tie-break mismatch（selected仍0，R-best从{0,1}变为{1}），分区loss升至4.24%；h103两语义的运行点loss由70.91%升至75.00%，而h101/h104/h105的对应运行点loss下降。变化并非同向，4个有定义场景的均值也不能直接当作原6场景均值的改善。

| 负载 | TPOT | 语义 | 5.2 → 4.68 类型 | selected | B | 分区loss | 运行点loss |
|---|---|---|---|---|---|---|---|
| h101 | 1.2 | raw | A → A | -2 → -2 | 0.00993486 → 0.00993486 | 0.00% → 0.00% | 0.00% → 0.00% |
| h101 | 1.2 | legacy | A → A | -2 → -2 | 0.00993486 → 0.00993486 | 0.00% → 0.00% | 2.14% → 2.14% |
| h101 | 10 | raw | S → S | 2 → 2 | 13.1931 → 9.53323 | 21.20% → 17.71% | 68.95% → 57.03% |
| h101 | 10 | legacy | S → S | 2 → 2 | 13.1931 → 9.53323 | 21.20% → 17.71% | 68.95% → 57.03% |
| h102 | 1.2 | raw | T → N | -1 → None | 0.010834 → 0 | 2.14% → undefined | 0.00% → undefined |
| h102 | 1.2 | legacy | A → N | -2 → None | 0.010834 → 0 | 0.00% → undefined | 0.00% → undefined |
| h102 | 10 | raw | S → N | 1 → None | 9.74198 → 0 | 8.30% → undefined | 74.45% → undefined |
| h102 | 10 | legacy | S → N | 2 → None | 9.74198 → 0 | 14.07% → undefined | 74.45% → undefined |
| h103 | 1.2 | raw | A → A | -2 → -2 | 0.00835419 → 0.00835419 | 0.00% → 0.00% | 0.00% → 0.00% |
| h103 | 1.2 | legacy | A → A | -2 → -2 | 0.00835419 → 0.00835419 | 0.00% → 0.00% | 2.14% → 2.14% |
| h103 | 10 | raw | S → S | 2 → 2 | 9.74198 → 7.19361 | 12.19% → 8.30% | 70.91% → 75.00% |
| h103 | 10 | legacy | S → S | 2 → 2 | 9.74198 → 7.19361 | 12.19% → 8.30% | 70.91% → 75.00% |
| h104 | 1.2 | raw | A → A | -2 → -2 | 0.0035125 → 0.0035125 | 0.00% → 0.00% | 0.00% → 0.00% |
| h104 | 1.2 | legacy | A → A | -2 → -2 | 0.0035125 → 0.0035125 | 0.00% → 0.00% | 2.14% → 2.14% |
| h104 | 10 | raw | S → S | 2 → 2 | 6.74101 → 6.45522 | 10.26% → 10.26% | 81.94% → 81.14% |
| h104 | 10 | legacy | A → T | 0 → 0 | 6.74101 → 6.45522 | 0.00% → 4.24% | 82.32% → 81.54% |
| h105 | 1.2 | raw | A → A | -2 → -2 | 0.00911031 → 0.00911031 | 0.00% → 0.00% | 0.00% → 0.00% |
| h105 | 1.2 | legacy | A → A | -2 → -2 | 0.00911031 → 0.00911031 | 0.00% → 0.00% | 2.14% → 2.14% |
| h105 | 10 | raw | T → T | 0 → 0 | 41.5843 → 23.1705 | 10.26% → 4.24% | 87.77% → 78.05% |
| h105 | 10 | legacy | A → A | 1 → 1 | 41.5843 → 23.1705 | 0.00% → 0.00% | 87.77% → 78.05% |
| h106 | 1.2 | raw | A → N | 1 → None | 0.00835419 → 0 | 0.00% → undefined | 0.00% → undefined |
| h106 | 1.2 | legacy | A → N | 1 → None | 0.00835419 → 0 | 0.00% → undefined | 2.14% → undefined |
| h106 | 10 | raw | T → N | 1 → None | 5.54703 → 0 | 26.16% → undefined | 95.86% → undefined |
| h106 | 10 | legacy | T → N | 1 → None | 5.54703 → 0 | 26.16% → undefined | 95.86% → undefined |

## 13. Resolution limitations

最终保留 27 个未达到2.5%目标的共同transition intervals，最大相对宽度 18.92%。全部明细和witness保存在 refinement_history.json；budget/round停止不等于所有边界已经精确。nonmonotone只描述观测序列；最大safe不构成安全前缀，范围外不推断。

八组SLA共96条语义决策中，12条在扩展grid后发生selected或决策类型变化；完整审计见 initial_grid_decision_comparison.csv。下表包括新SLA，不能混称为Stage 3历史结果变化。

| 负载 | SLA | 语义 | 原grid类型 → 最终类型 | selected原 → 最终 |
|---|---|---|---|---|
| h101 | TTFT5.2_TPOT2.4 | raw | agreement → strict best-set mismatch | -2 → -2 |
| h101 | TTFT5.2_TPOT2.4 | legacy | agreement → strict best-set mismatch | -2 → -2 |
| h102 | TTFT5.2_TPOT1.2 | raw | agreement → tie-break mismatch | 0 → -1 |
| h102 | TTFT5.2_TPOT1.2 | legacy | agreement → agreement | 0 → -2 |
| h102 | TTFT5.2_TPOT2.4 | raw | agreement → tie-break mismatch | 0 → -1 |
| h102 | TTFT5.2_TPOT2.4 | legacy | agreement → agreement | 0 → -2 |
| h103 | TTFT5.2_TPOT5 | raw | agreement → strict best-set mismatch | 0 → 1 |
| h103 | TTFT5.2_TPOT5 | legacy | agreement → strict best-set mismatch | 0 → 1 |
| h103 | TTFT4.68_TPOT10 | raw | strict best-set mismatch → strict best-set mismatch | 1 → 2 |
| h103 | TTFT4.68_TPOT10 | legacy | strict best-set mismatch → strict best-set mismatch | 1 → 2 |
| h104 | TTFT5.2_TPOT5 | raw | agreement → agreement | 0 → 1 |
| h104 | TTFT5.2_TPOT5 | legacy | agreement → agreement | 0 → 1 |

未解决区间仅在h101/h102/h105，分别12/6/9个；最大宽度18.92%。h103/h104/h106的所有已观测transition均达到目标，但这仍不排除未采样的窄safe/unsafe区间。扩展grid使96条语义决策中12条发生selected或类型变化（6条类型变化、10条selected变化，部分重叠），全部来自新SLA；这说明第一阶段旧grid不能代替共同refinement。h102在1.2/2.4的2.14%分区差、h103在5的2.14%分区差以及各best-set ties属于网格分辨率敏感的排序，不能外推为连续最优。h102实际推荐点的3/54 TPOT违规则是保存指标直接确定的事实，不依赖对未测点的插值。参考nonmonotone使largest safe不具备安全前缀含义。

Stage 3 resolution comparison:

| 负载 | SLA | 语义 | selected旧 → 新 | E best旧 → 新 | R best旧 → 新 | 类型旧 → 新 |
|---|---|---|---|---|---|---|
| h101 | TTFT5.2_TPOT0.3 | raw | -2 → -2 | [-2] → [-2] | [-2] → [-2] | agreement → agreement |
| h101 | TTFT5.2_TPOT0.3 | legacy | -2 → -2 | [-2] → [-2] | [-2] → [-2] | agreement → agreement |
| h101 | TTFT5.2_TPOT10 | raw | 2 → 2 | [2] → [2] | [0] → [0] | strict best-set mismatch → strict best-set mismatch |
| h101 | TTFT5.2_TPOT10 | legacy | 2 → 2 | [2] → [2] | [0] → [0] | strict best-set mismatch → strict best-set mismatch |
| h102 | TTFT5.2_TPOT0.3 | raw | -2 → -2 | [-2] → [-2] | [-2] → [-2] | agreement → agreement |
| h102 | TTFT5.2_TPOT0.3 | legacy | -2 → -2 | [-2] → [-2] | [-2] → [-2] | agreement → agreement |
| h102 | TTFT5.2_TPOT10 | raw | 1 → 1 | [1, 2] → [1, 2] | [0] → [0] | strict best-set mismatch → strict best-set mismatch |
| h102 | TTFT5.2_TPOT10 | legacy | 2 → 2 | [2] → [2] | [0] → [0] | strict best-set mismatch → strict best-set mismatch |
| h103 | TTFT5.2_TPOT0.3 | raw | -2 → -2 | [-2] → [-2] | [-2] → [-2] | agreement → agreement |
| h103 | TTFT5.2_TPOT0.3 | legacy | -2 → -2 | [-2] → [-2] | [-2] → [-2] | agreement → agreement |
| h103 | TTFT5.2_TPOT10 | raw | 2 → 2 | [2] → [2] | [0] → [0] | strict best-set mismatch → strict best-set mismatch |
| h103 | TTFT5.2_TPOT10 | legacy | 2 → 2 | [2] → [2] | [0] → [0] | strict best-set mismatch → strict best-set mismatch |
| h104 | TTFT5.2_TPOT0.3 | raw | -2 → -2 | [-2] → [-2] | [-2] → [-2] | agreement → agreement |
| h104 | TTFT5.2_TPOT0.3 | legacy | -2 → -2 | [-2] → [-2] | [-2] → [-2] | agreement → agreement |
| h104 | TTFT5.2_TPOT10 | raw | 2 → 2 | [2] → [2] | [0, 1] → [0, 1] | strict best-set mismatch → strict best-set mismatch |
| h104 | TTFT5.2_TPOT10 | legacy | 0 → 0 | [0, 1, 2] → [0, 1, 2] | [0, 1] → [0, 1] | agreement → agreement |
| h105 | TTFT5.2_TPOT0.3 | raw | -2 → -2 | [-2] → [-2] | [-2] → [-2] | agreement → agreement |
| h105 | TTFT5.2_TPOT0.3 | legacy | -2 → -2 | [-2] → [-2] | [-2] → [-2] | agreement → agreement |
| h105 | TTFT5.2_TPOT10 | raw | 0 → 0 | [0, 1, 2] → [0, 1, 2] | [1] → [1] | tie-break mismatch → tie-break mismatch |
| h105 | TTFT5.2_TPOT10 | legacy | 1 → 1 | [1, 2] → [1, 2] | [1] → [1] | agreement → agreement |
| h106 | TTFT5.2_TPOT0.3 | raw | 1 → 1 | [1] → [1] | [1] → [1] | agreement → agreement |
| h106 | TTFT5.2_TPOT0.3 | legacy | 1 → 1 | [1] → [1] | [1] → [1] | agreement → agreement |
| h106 | TTFT5.2_TPOT10 | raw | 1 → 1 | [1, 2] → [1, 2] | [2] → [2] | tie-break mismatch → tie-break mismatch |
| h106 | TTFT5.2_TPOT10 | legacy | 1 → 1 | [1, 2] → [1, 2] | [2] → [2] | tie-break mismatch → tie-break mismatch |

## 14. Integrity checks and reproduction

2459 个Stage 2/3保护文件哈希未变；协议hash `ac61d6e30a9b19823bf8ff595feaf7bdf935ebd72206a712ab001e4968dc3f8b`。18项要求及附加核验通过：原grid标签/决策、输入与profile/partition/network、依赖源、共同grid、SLA单调性、逐请求全drain、失败/重试、全八SLA、完整分母、ties/no-safe/nonmonotone/unresolved、loss identity。36项单元测试通过。

Run `python scripts/run_sla_sensitivity.py all`, then `python scripts/analyze_sla_sensitivity.py`, `python scripts/verify_sla_sensitivity.py`, `python scripts/figure_sla_sensitivity.py` and `python scripts/report_sla_sensitivity.py`. Existing point/attempt records support resume without resetting the budget. Verification never launches HELIX. `python -m unittest discover -s tests -v` includes targeted new refinement, missingness, monotonicity and tie tests. `scripts/check_public.py` inspects staged bytes (including decompressed results) before push. Protected history, CA material and credentials are excluded from changes.

Main-text candidate figure: ../results/sla_sensitivity/figures/sla_sensitivity.png (one figure, SVG companion). Six TPOT categories use small horizontal Raw/Legacy offsets solely to expose coincident markers; these are not different thresholds. Figure lines only join the prescribed tested conditions; red circles flag arithmetic operating losses whose recommendations are unsafe. Reference nonmonotonicity is over intensity, whereas SLA-relaxation monotonicity passed for every physical point. Table outputs and reports are tied to the saved protocol hash.
