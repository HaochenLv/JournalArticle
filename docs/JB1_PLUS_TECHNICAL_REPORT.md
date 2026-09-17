# JB1+ remaining-Prefill correction: technical evidence

## 1. Frozen correction

[Protocol](JB1_PLUS_PROTOCOL.md), `config/jb1_plus_protocol.json`, freeze commit e3887ca.

协议冻结提交 e3887ca，hash `66375a5dab2941a70ee3111cd1f16f09d7e05fd32b440cf3759591b78e57afe2`。5867 个旧文件逐字节未变；41项测试通过。Full关闭模式逐字段一致（runtime除外），Stage4 Full记录原样复用；HELIX commit `8639497a4aaf1eb3b7594614cb0bbd376c1342b3`、adapter/profile不变。Phase A复用2050个异构点及130个A100点，新增reference=0。Phase B新增500个physical points、500次attempt、0次retry、0次timeout、0个failed point。四变体共享grid和reference truth，全部保留ties/no-safe/nonmonotone/unresolved；逐请求drain、SLA单调性和loss identity通过。

## 2. Why this mechanism was chosen

The existing h105 trace identified full active-Prefill compute debt as a conservative component. It did not prove that deleting blocking is safe. This experiment tests only remaining compute, retaining intrinsic debt. Publication boundary: JB1 is the specified lightweight evaluator; Legacy is semantic control. Withdrawn unpublished AICCC is not prior publication. Accepted Evaluator-Guided SLA-Aware Layer Partitioning for Heterogeneous LLM Pipelines is prior work; candidate family/evaluator-as-score/search are not new contributions.

## 3. Mathematical definition

For active Prefill r: d_r=C_r for Raw, d_r=C_r+fixed+queue for Legacy; f_r(t)=1−clip((t−start_r)/d_r,0,1); D_remaining=sum(f_r C_r+H input_tokens_r). Zero duration gives f=0 at/after start. Intrinsic is not scaled. Overhead does not enter debt directly.

O=E safe/R unsafe；C=E unsafe/R safe。容量为同一网格最大观测 safe intensity，gap=(Emax−Rmax)/Rmax；任一容量无定义时 gap 保持 undefined。B=reference-best sampled capacity，S=selected partition 的 reference capacity，L=推荐 intensity。partition loss=1−S/B；operating loss=1−L/B；allocation=(S−L)/B；前两者不能相加。safe usable=L仅当该点实际R-safe；unsafe/弃权记0，缺失记null；B=0时relative loss未定义。

## 4. Implementation isolation

New `src/journal_baseline_plus.py` is an isolated copy of the frozen implementation with the debt term, two Prefill state fields and optional trace components added. Default remaining_prefill_blocking=False returns the original version and original output fields. No HELIX querying, new queue simulator, fitted coefficient, safety margin or workload/SLA-specific rule exists. New writes are confined to Stage5 outputs and status/log files.

## 5. Baseline equivalence test

All41 unit tests pass. Added tests cover clipping/zero duration, complete off-mode outputs including traces and first simultaneous violations, Raw/Legacy with nonzero fixed/queue overhead, representative real profiles, full-drain trajectory/memory equality, both-direction refinement and null labels. Stage4 Full records, including runtime, are copied exactly; sequential PhaseB timing reproduces all scientific output fields except runtime.

["protected hashes unchanged", "protocol/workloads committed before outcomes", "exact disjoint source windows regenerated", "pinned HELIX/adapter/profiles unchanged", "all old cache records read only", "full per-request drain and token metrics", "four variants share every grid", "SLA relaxation monotonicity", "Full-safe implies Remaining-safe", "both transition directions and refinement priority replayed", "500-point budget and at most two attempts", "missing labels never unsafe", "CSV/JSON tables recomputed", "loss identity and exact recommendation safety", "remaining compute and unscaled H audited", "full-drain trajectories unchanged", "runtime outputs equal saved scientific outputs"]

## 6. Phase A existing-corpus diagnosis

在相同的2050物理点×8个SLA上，每种variant有16400个配对标签。Raw C=1911→1604，Legacy C=2046→1724；分别减少307、322。Raw winner agreement=27/48→31/48，Legacy=32/48→33/48，但两种语义都有个别分区损失变差。Raw/Legacy不安全推荐仍分别4/48和2/48，另各4个弃权；两种语义的44个有定义loss场景与202个有定义capacity gap分母均保持不变。平均绝对capacity gap从34.59%→30.64%、35.86%→31.87%，总体中位数不变。A100补充对照复用130个物理点：C为9→7、20→18，O仍14、9；原乐观机制没有被修复。这些都是post-hoc diagnosis。

| Variant | O | C | paired | agreement / decisions | unsafe / abstain | gap median | mean absolute gap | partition loss | operating loss | safe loss |
|---|---|---|---|---|---|---|---|---|---|---|
| Raw-Full | 38 | 1911 | 16400 | 27/48 | 4/4 | 0.00% | 34.59% | 3.99% | 34.69% | 39.45% |
| Raw-Remaining | 39 | 1604 | 16400 | 31/48 | 4/4 | 0.00% | 30.64% | 2.77% | 31.65% | 36.41% |
| Legacy-Full | 31 | 2046 | 16400 | 32/48 | 2/4 | -2.14% | 35.86% | 3.32% | 35.88% | 36.10% |
| Legacy-Remaining | 32 | 1724 | 16400 | 33/48 | 2/4 | -2.14% | 31.87% | 2.68% | 32.82% | 33.04% |

| SLA | Variant | both safe | both unsafe | O | C | paired | missing |
|---|---|---|---|---|---|---|---|
| TTFT5.2_TPOT0.3 | Raw-Full | 217 | 1832 | 1 | 0 | 2050 | 0 |
| TTFT5.2_TPOT0.3 | Raw-Remaining | 217 | 1832 | 1 | 0 | 2050 | 0 |
| TTFT5.2_TPOT0.3 | Legacy-Full | 191 | 1833 | 0 | 26 | 2050 | 0 |
| TTFT5.2_TPOT0.3 | Legacy-Remaining | 191 | 1833 | 0 | 26 | 2050 | 0 |
| TTFT5.2_TPOT0.6 | Raw-Full | 217 | 1782 | 1 | 50 | 2050 | 0 |
| TTFT5.2_TPOT0.6 | Raw-Remaining | 217 | 1782 | 1 | 50 | 2050 | 0 |
| TTFT5.2_TPOT0.6 | Legacy-Full | 191 | 1783 | 0 | 76 | 2050 | 0 |
| TTFT5.2_TPOT0.6 | Legacy-Remaining | 191 | 1783 | 0 | 76 | 2050 | 0 |
| TTFT5.2_TPOT1.2 | Raw-Full | 275 | 1773 | 2 | 0 | 2050 | 0 |
| TTFT5.2_TPOT1.2 | Raw-Remaining | 275 | 1773 | 2 | 0 | 2050 | 0 |
| TTFT5.2_TPOT1.2 | Legacy-Full | 251 | 1775 | 0 | 24 | 2050 | 0 |
| TTFT5.2_TPOT1.2 | Legacy-Remaining | 251 | 1775 | 0 | 24 | 2050 | 0 |
| TTFT5.2_TPOT2.4 | Raw-Full | 275 | 1634 | 2 | 139 | 2050 | 0 |
| TTFT5.2_TPOT2.4 | Raw-Remaining | 275 | 1634 | 2 | 139 | 2050 | 0 |
| TTFT5.2_TPOT2.4 | Legacy-Full | 251 | 1636 | 0 | 163 | 2050 | 0 |
| TTFT5.2_TPOT2.4 | Legacy-Remaining | 251 | 1636 | 0 | 163 | 2050 | 0 |
| TTFT5.2_TPOT5 | Raw-Full | 672 | 552 | 23 | 803 | 2050 | 0 |
| TTFT5.2_TPOT5 | Raw-Remaining | 744 | 552 | 23 | 731 | 2050 | 0 |
| TTFT5.2_TPOT5 | Legacy-Full | 671 | 552 | 23 | 804 | 2050 | 0 |
| TTFT5.2_TPOT5 | Legacy-Remaining | 744 | 552 | 23 | 731 | 2050 | 0 |
| TTFT5.2_TPOT10 | Raw-Full | 966 | 476 | 8 | 600 | 2050 | 0 |
| TTFT5.2_TPOT10 | Raw-Remaining | 1091 | 476 | 8 | 475 | 2050 | 0 |
| TTFT5.2_TPOT10 | Legacy-Full | 958 | 476 | 8 | 608 | 2050 | 0 |
| TTFT5.2_TPOT10 | Legacy-Remaining | 1091 | 476 | 8 | 475 | 2050 | 0 |
| TTFT4.68_TPOT1.2 | Raw-Full | 161 | 1888 | 1 | 0 | 2050 | 0 |
| TTFT4.68_TPOT1.2 | Raw-Remaining | 161 | 1888 | 1 | 0 | 2050 | 0 |
| TTFT4.68_TPOT1.2 | Legacy-Full | 142 | 1889 | 0 | 19 | 2050 | 0 |
| TTFT4.68_TPOT1.2 | Legacy-Remaining | 142 | 1889 | 0 | 19 | 2050 | 0 |
| TTFT4.68_TPOT10 | Raw-Full | 663 | 1068 | 0 | 319 | 2050 | 0 |
| TTFT4.68_TPOT10 | Raw-Remaining | 773 | 1067 | 1 | 209 | 2050 | 0 |
| TTFT4.68_TPOT10 | Legacy-Full | 656 | 1068 | 0 | 326 | 2050 | 0 |
| TTFT4.68_TPOT10 | Legacy-Remaining | 772 | 1067 | 1 | 210 | 2050 | 0 |

A100 controls (130 old physical points, two SLAs; single candidate, so agreement is not partition-search evidence):

| Variant | O | C | paired | agreement / decisions | unsafe / abstain | gap median | mean absolute gap | partition loss | operating loss | safe loss |
|---|---|---|---|---|---|---|---|---|---|---|
| Raw-Full | 14 | 9 | 260 | 10/12 | 4/2 | 0.00% | 30.23% | 0.00% | -7.65% | 51.29% |
| Raw-Remaining | 14 | 7 | 260 | 10/12 | 4/2 | 0.00% | 30.20% | 0.00% | -7.68% | 51.26% |
| Legacy-Full | 9 | 20 | 260 | 10/12 | 1/2 | -6.29% | 38.30% | 0.00% | 5.29% | 31.79% |
| Legacy-Remaining | 9 | 18 | 260 | 10/12 | 1/2 | -6.29% | 38.26% | 0.00% | 5.25% | 31.76% |

| Semantic pair | removed C | new O | safe→unsafe | capacity improved/worsened | new unsafe recommendations | removed unsafe recommendations | unsafe severity worsened |
|---|---|---|---|---|---|---|---|
| Raw | 307 | 1 | 0 | 59/0 | 0 | 0 | 0 |
| Legacy | 322 | 1 | 0 | 59/0 | 0 | 0 | 0 |

## 7. Conservative mechanism replay

原 h105/A100/fast/4.096、TTFT2/TPOT1 案例，在同一失败 epoch t=2.46484375 s，Raw blocking debt 从 1.547523291 s 降到 0.937171729 s，减少 0.610351562 s。Decode compute 为 0.112000 s；加 fixed .005 s 后，required TPOT 从 1.664523291 s 降到 1.054171729 s，仍超过 1 s。因此局部 full-service 高估被直接减轻，但这个 conservative verdict 没有被修复。Reference 最大 TPOT 0.945949720 s。

| request | full compute (s) | remaining fraction | remaining compute (s) | intrinsic (s) |
|---|---|---|---|---|
| azure-00002 | 0.76032 | 0.197244 | 0.149968 | 0.0779623 |
| azure-00003 | 0.64832 | 1 | 0.64832 | 0.060921 |

Full per-epoch comparisons for Raw and Legacy are retained in phase_a_mechanisms.json and mechanisms/*.json.gz; saved reference trace metrics are reused exactly, with zero new reference trace executions.

## 8. Optimistic mechanism impact

原 h103/A100/slow/.016、TPOT .15 案例中，Raw-Full 和 Raw-Remaining 均接受而 reference 拒绝；Legacy 两者均拒绝。减少 debt 没有修复 Raw 漏掉真实重叠的问题。Raw 请求13在1720.199600 s结束，reference为1721.840915 s，新请求14在1720.250000 s到达；同一语义的 Full/Remaining 完整轨迹一致，completion-time drift 仍存在。

确实制造了新的optimistic errors。Phase A Raw为38→39、Legacy为31→32；两种语义新增的是同一个physical/SLA点：h101、shift−2、强度7.512097122、TTFT4.68/TPOT10。Reference TTFT=4.757223186 s，1/16请求超限；Remaining最大账面TTFT=4.593150197 s而接受。这个更紧TTFT条件不在Phase B范围内。Phase B更不能被描述成无新增风险：Raw和Legacy均7→17，每种语义各新增10个乐观标签，全部来自w202/TPOT5的两个强度(.256、.362038672)×五个shifts。两种语义共享这些10个physical/SLA点，不能相加成20个独立失败。新点/错误比例只描述自适应网格，非生产风险概率。

## 9. Capacity comparison

有所改善，但没有证据称capacity全面或明显变准。Phase B平均绝对相对gap仅从Raw41.11%→38.94%、Legacy41.31%→39.14%，下降2.17个百分点；80个配对候选/SLA中30个改善、2个变差、48个不变。总体signed-gap median均为0，掩盖SLA差异。TPOT10的median为−78.66%→−50.00%，mean absolute gap58.88%→41.89%；TPOT5的median虽从−94.74%→−87.50%，mean absolute gap却90.58%→98.89%，因为w202/shift−2的过高估计从+100%恶化到+300%，shift−1新增+100%。因此只看signed median会漏掉危险尾部。Phase B保留7条reference非单调、12条reference右删失序列；每个evaluator有5条右删失序列，均无no-safe序列。所有gap只针对采样最大safe，右删失值不是完整容量估计。

| SLA | Variant | defined gap | min / median / max | mean absolute gap | E no-safe/nonmono/censored | R no-safe/nonmono/censored |
|---|---|---|---|---|---|---|
| TTFT5.2_TPOT0.3 | Raw-Full | 27 | 0.00% / 0.00% / 2.19% | 0.08% | 3/0/0 | 3/0/0 |
| TTFT5.2_TPOT0.3 | Raw-Remaining | 27 | 0.00% / 0.00% / 2.19% | 0.08% | 3/0/0 | 3/0/0 |
| TTFT5.2_TPOT0.3 | Legacy-Full | 27 | -8.30% / -2.14% / 0.00% | 2.29% | 3/0/0 | 3/0/0 |
| TTFT5.2_TPOT0.3 | Legacy-Remaining | 27 | -8.30% / -2.14% / 0.00% | 2.29% | 3/0/0 | 3/0/0 |
| TTFT5.2_TPOT0.6 | Raw-Full | 27 | -22.89% / 0.00% / 2.19% | 4.32% | 3/0/0 | 3/4/0 |
| TTFT5.2_TPOT0.6 | Raw-Remaining | 27 | -22.89% / 0.00% / 2.19% | 4.32% | 3/0/0 | 3/4/0 |
| TTFT5.2_TPOT0.6 | Legacy-Full | 27 | -24.54% / -2.14% / 0.00% | 6.44% | 3/0/0 | 3/4/0 |
| TTFT5.2_TPOT0.6 | Legacy-Remaining | 27 | -24.54% / -2.14% / 0.00% | 6.44% | 3/0/0 | 3/4/0 |
| TTFT5.2_TPOT1.2 | Raw-Full | 27 | 0.00% / 0.00% / 2.19% | 0.16% | 3/0/0 | 3/0/0 |
| TTFT5.2_TPOT1.2 | Raw-Remaining | 27 | 0.00% / 0.00% / 2.19% | 0.16% | 3/0/0 | 3/0/0 |
| TTFT5.2_TPOT1.2 | Legacy-Full | 27 | -8.30% / -2.14% / 0.00% | 2.21% | 3/0/0 | 3/0/0 |
| TTFT5.2_TPOT1.2 | Legacy-Remaining | 27 | -8.30% / -2.14% / 0.00% | 2.21% | 3/0/0 | 3/0/0 |
| TTFT5.2_TPOT2.4 | Raw-Full | 27 | -99.81% / 0.00% / 2.19% | 30.39% | 3/0/0 | 3/10/0 |
| TTFT5.2_TPOT2.4 | Raw-Remaining | 27 | -99.81% / 0.00% / 2.19% | 30.39% | 3/0/0 | 3/10/0 |
| TTFT5.2_TPOT2.4 | Legacy-Full | 27 | -99.83% / -2.14% / 0.00% | 31.56% | 3/0/0 | 3/10/0 |
| TTFT5.2_TPOT2.4 | Legacy-Remaining | 27 | -99.83% / -2.14% / 0.00% | 31.56% | 3/0/0 | 3/10/0 |
| TTFT5.2_TPOT5 | Raw-Full | 27 | -97.93% / -95.08% / -87.50% | 94.29% | 3/0/0 | 3/7/0 |
| TTFT5.2_TPOT5 | Raw-Remaining | 27 | -95.08% / -92.24% / -83.07% | 91.52% | 3/0/0 | 3/7/0 |
| TTFT5.2_TPOT5 | Legacy-Full | 27 | -97.93% / -95.08% / -87.77% | 94.30% | 3/0/0 | 3/7/0 |
| TTFT5.2_TPOT5 | Legacy-Remaining | 27 | -95.08% / -92.24% / -83.07% | 91.52% | 3/0/0 | 3/7/0 |
| TTFT5.2_TPOT10 | Raw-Full | 27 | -95.86% / -75.00% / -60.60% | 76.02% | 3/0/0 | 3/2/0 |
| TTFT5.2_TPOT10 | Raw-Remaining | 27 | -95.86% / -67.58% / -21.20% | 64.07% | 3/0/0 | 3/2/0 |
| TTFT5.2_TPOT10 | Legacy-Full | 27 | -95.86% / -75.00% / -60.60% | 76.18% | 3/0/0 | 3/2/0 |
| TTFT5.2_TPOT10 | Legacy-Remaining | 27 | -95.86% / -67.58% / -21.20% | 64.07% | 3/0/0 | 3/2/0 |
| TTFT4.68_TPOT1.2 | Raw-Full | 20 | 0.00% / 0.00% / 2.19% | 0.11% | 10/0/0 | 10/0/0 |
| TTFT4.68_TPOT1.2 | Raw-Remaining | 20 | 0.00% / 0.00% / 2.19% | 0.11% | 10/0/0 | 10/0/0 |
| TTFT4.68_TPOT1.2 | Legacy-Full | 20 | -8.30% / -2.14% / 0.00% | 2.34% | 10/0/0 | 10/0/0 |
| TTFT4.68_TPOT1.2 | Legacy-Remaining | 20 | -8.30% / -2.14% / 0.00% | 2.34% | 10/0/0 | 10/0/0 |
| TTFT4.68_TPOT10 | Raw-Full | 20 | -86.95% / -76.04% / -47.79% | 72.13% | 10/0/0 | 10/0/0 |
| TTFT4.68_TPOT10 | Raw-Remaining | 20 | -86.95% / -63.08% / 4.43% | 52.14% | 10/0/0 | 10/0/0 |
| TTFT4.68_TPOT10 | Legacy-Full | 20 | -87.23% / -76.04% / -47.79% | 72.35% | 10/0/0 | 10/0/0 |
| TTFT4.68_TPOT10 | Legacy-Remaining | 20 | -87.23% / -63.08% / 4.43% | 52.15% | 10/0/0 | 10/0/0 |

## 10. Decision comparison

Phase A的总winner agreement有所增加，但独立Phase B没有分区选择质量改善：Raw保持14/16（2个tie-break mismatch），Legacy保持13/16（2个tie-break、1个strict mismatch）。平均partition loss分别保持3.66%和9.91%。Raw/Legacy各只有w202/TPOT10从shift0变为shift1，reference-best包含二者，因此不能算修复错误。Phase A还存在反向变化：h103/TPOT5的partition loss约2.14%→12.19%；Legacy h105/TPOT10从agreement退化为tie-break mismatch，TTFT5.2和4.68两条件均如此。

h101名义relaxed reversal在Phase A共同网格上被消除：两种语义都从shift2改选shift0，reference-best为{0}；partition loss21.20%→0%，operating loss68.95%→40.54%。Remaining的E-best为{0,1,2}，由原tie-break选0，所以这是该网格上的agreement，不是严格恢复了所有候选排序。共同负载4.096的局部trace中shift0由拒绝变接受，shift2一直接受；该局部改善与最终采样选择一致，但不证明真实连续前沿已被恢复。

Complete192 PhaseA variant decisions and best sets/ranks are in phase_a_decisions.csv; all Full→Remaining paired changes, including worsened cases, are in summary.json.

## 11. Operating-point comparison

推荐点安全性没有改善，而且一个已有不安全输出的严重程度变差。Phase B四个variants均有1/16个不安全推荐：w202/TTFT5.2/TPOT5，均选shift0且partition loss=0。Full推荐强度.181019336，1/48请求违规（2.08%），最大TPOT5.025706073 s；Remaining推荐翻倍到.362038672，9/48违规（18.75%），最大TPOT5.206560685 s。算术operating loss95.58%→91.16%，但safe loss仍100%。不能把更高的unsafe负载算成安全改善。另一方面，16个场景平均operating loss44.78%→38.87%、平均safe operating loss45.06%→39.42%，说明其他受测场景有利用率收益；这与安全代价同时成立。

| SLA | Variant | partition mean / n | operating mean / n | safe mean / n | unsafe outputs | abstentions | decision types |
|---|---|---|---|---|---|---|---|
| TTFT5.2_TPOT0.3 | Raw-Full | 0.00% / 6 | 0.00% / 6 | 0.00% / 6 | 0 | 0 | {'agreement': 6} |
| TTFT5.2_TPOT0.3 | Raw-Remaining | 0.00% / 6 | 0.00% / 6 | 0.00% / 6 | 0 | 0 | {'agreement': 6} |
| TTFT5.2_TPOT0.3 | Legacy-Full | 0.00% / 6 | 2.14% / 6 | 2.14% / 6 | 0 | 0 | {'agreement': 6} |
| TTFT5.2_TPOT0.3 | Legacy-Remaining | 0.00% / 6 | 2.14% / 6 | 2.14% / 6 | 0 | 0 | {'agreement': 6} |
| TTFT5.2_TPOT0.6 | Raw-Full | 0.00% / 6 | 3.81% / 6 | 3.81% / 6 | 0 | 0 | {'agreement': 6} |
| TTFT5.2_TPOT0.6 | Raw-Remaining | 0.00% / 6 | 3.81% / 6 | 3.81% / 6 | 0 | 0 | {'agreement': 6} |
| TTFT5.2_TPOT0.6 | Legacy-Full | 0.00% / 6 | 5.88% / 6 | 5.88% / 6 | 0 | 0 | {'agreement': 6} |
| TTFT5.2_TPOT0.6 | Legacy-Remaining | 0.00% / 6 | 5.88% / 6 | 5.88% / 6 | 0 | 0 | {'agreement': 6} |
| TTFT5.2_TPOT1.2 | Raw-Full | 0.36% / 6 | 0.00% / 6 | 16.67% / 6 | 1 | 0 | {'agreement': 5, 'tie-break mismatch': 1} |
| TTFT5.2_TPOT1.2 | Raw-Remaining | 0.36% / 6 | 0.00% / 6 | 16.67% / 6 | 1 | 0 | {'agreement': 5, 'tie-break mismatch': 1} |
| TTFT5.2_TPOT1.2 | Legacy-Full | 0.00% / 6 | 1.79% / 6 | 1.79% / 6 | 0 | 0 | {'agreement': 6} |
| TTFT5.2_TPOT1.2 | Legacy-Remaining | 0.00% / 6 | 1.79% / 6 | 1.79% / 6 | 0 | 0 | {'agreement': 6} |
| TTFT5.2_TPOT2.4 | Raw-Full | 4.99% / 6 | 27.14% / 6 | 43.81% / 6 | 1 | 0 | {'strict best-set mismatch': 2, 'tie-break mismatch': 1, 'agreement': 3} |
| TTFT5.2_TPOT2.4 | Raw-Remaining | 4.99% / 6 | 27.14% / 6 | 43.81% / 6 | 1 | 0 | {'strict best-set mismatch': 2, 'tie-break mismatch': 1, 'agreement': 3} |
| TTFT5.2_TPOT2.4 | Legacy-Full | 4.63% / 6 | 28.35% / 6 | 28.35% / 6 | 0 | 0 | {'strict best-set mismatch': 2, 'agreement': 4} |
| TTFT5.2_TPOT2.4 | Legacy-Remaining | 4.63% / 6 | 28.35% / 6 | 28.35% / 6 | 0 | 0 | {'strict best-set mismatch': 2, 'agreement': 4} |
| TTFT5.2_TPOT5 | Raw-Full | 2.43% / 6 | 94.90% / 6 | 95.82% / 6 | 1 | 0 | {'agreement': 3, 'strict best-set mismatch': 1, 'tie-break mismatch': 2} |
| TTFT5.2_TPOT5 | Raw-Remaining | 4.10% / 6 | 92.25% / 6 | 93.17% / 6 | 1 | 0 | {'agreement': 3, 'strict best-set mismatch': 1, 'tie-break mismatch': 2} |
| TTFT5.2_TPOT5 | Legacy-Full | 2.43% / 6 | 94.90% / 6 | 95.82% / 6 | 1 | 0 | {'agreement': 3, 'strict best-set mismatch': 1, 'tie-break mismatch': 2} |
| TTFT5.2_TPOT5 | Legacy-Remaining | 4.10% / 6 | 92.25% / 6 | 93.17% / 6 | 1 | 0 | {'agreement': 3, 'strict best-set mismatch': 1, 'tie-break mismatch': 2} |
| TTFT5.2_TPOT10 | Raw-Full | 14.73% / 6 | 79.98% / 6 | 80.67% / 6 | 1 | 0 | {'strict best-set mismatch': 4, 'tie-break mismatch': 2} |
| TTFT5.2_TPOT10 | Raw-Remaining | 8.10% / 6 | 71.25% / 6 | 71.94% / 6 | 1 | 0 | {'agreement': 3, 'strict best-set mismatch': 1, 'tie-break mismatch': 2} |
| TTFT5.2_TPOT10 | Legacy-Full | 12.27% / 6 | 80.04% / 6 | 80.73% / 6 | 1 | 0 | {'strict best-set mismatch': 3, 'agreement': 2, 'tie-break mismatch': 1} |
| TTFT5.2_TPOT10 | Legacy-Remaining | 8.10% / 6 | 71.25% / 6 | 71.94% / 6 | 1 | 0 | {'agreement': 3, 'strict best-set mismatch': 1, 'tie-break mismatch': 2} |
| TTFT4.68_TPOT1.2 | Raw-Full | 0.00% / 4 | 0.00% / 4 | 0.00% / 4 | 0 | 2 | {'agreement': 4, 'no-safe recommendation': 2} |
| TTFT4.68_TPOT1.2 | Raw-Remaining | 0.00% / 4 | 0.00% / 4 | 0.00% / 4 | 0 | 2 | {'agreement': 4, 'no-safe recommendation': 2} |
| TTFT4.68_TPOT1.2 | Legacy-Full | 0.00% / 4 | 2.14% / 4 | 2.14% / 4 | 0 | 2 | {'agreement': 4, 'no-safe recommendation': 2} |
| TTFT4.68_TPOT1.2 | Legacy-Remaining | 0.00% / 4 | 2.14% / 4 | 2.14% / 4 | 0 | 2 | {'agreement': 4, 'no-safe recommendation': 2} |
| TTFT4.68_TPOT10 | Raw-Full | 10.13% / 4 | 72.80% / 4 | 72.80% / 4 | 0 | 2 | {'strict best-set mismatch': 3, 'no-safe recommendation': 2, 'tie-break mismatch': 1} |
| TTFT4.68_TPOT10 | Raw-Remaining | 4.19% / 4 | 56.41% / 4 | 56.41% / 4 | 0 | 2 | {'agreement': 1, 'no-safe recommendation': 2, 'strict best-set mismatch': 1, 'tie-break mismatch': 2} |
| TTFT4.68_TPOT10 | Legacy-Full | 7.56% / 4 | 72.91% / 4 | 72.91% / 4 | 0 | 2 | {'strict best-set mismatch': 2, 'no-safe recommendation': 2, 'tie-break mismatch': 1, 'agreement': 1} |
| TTFT4.68_TPOT10 | Legacy-Remaining | 4.19% / 4 | 56.41% / 4 | 56.41% / 4 | 0 | 2 | {'agreement': 1, 'no-safe recommendation': 2, 'strict best-set mismatch': 1, 'tie-break mismatch': 2} |

## 12. Phase B held-out protocol

| ID | seed | offset (3s bins) | duration(s) | link | requests | input mean/max | output mean/max |
|---|---|---|---|---|---|---|---|
| w201 | 201 | 1140 | 30 | fast | 13 | 804.77/1670 | 232.15/405 |
| w202 | 202 | 1150 | 120 | slow | 48 | 869.02/1992 | 245.98/605 |
| w203 | 203 | 1190 | 30 | slow | 5 | 804.80/1203 | 172.40/406 |
| w204 | 204 | 1200 | 120 | fast | 44 | 753.84/1854 | 217.95/591 |

Offsets count3-second source bins; w204 wraps to0–39. Workloads and exact requests were committed before any correction outputs. Same generator/target .5/filtering/token distributions as Stage3. Only four TPOT thresholds, five heterogeneous shifts, nine fixed initial intensities; max16 additions/workload, four rounds, 500 physical points total. Both-direction transitions across reference and allfour variants share a grid. Failed reference points stay null.

| Group | grid | added | unresolved | max width | stop |
|---|---|---|---|---|---|
| w201-heterogeneous-fast | 25 | 16 | 10 | 41.42% | 16-intensity budget |
| w202-heterogeneous-slow | 25 | 16 | 12 | 41.42% | 16-intensity budget |
| w203-heterogeneous-slow | 25 | 16 | 6 | 18.92% | 16-intensity budget |
| w204-heterogeneous-fast | 25 | 16 | 9 | 41.42% | 16-intensity budget |

## 13. Held-out judgment results

四个预冻结新负载完整执行500个物理点，正好达到硬上限，无失败、重试或超时。每种variant为500×4=2000个SLA配对标签、80条候选/SLA容量序列、16个部署决策。Raw C=225→153，Legacy=227→155，均减少72；O均7→17。16条决策的正确数量和mismatch类型完全不变；w202/TPOT10的selected从0变1，但二者本来都在reference-best集合内。新证据支持受测held-out上的保守分歧和平均利用率改善，同时直接证实安全性代价，不支持全面可靠性改善。37个未解决共同区间保留，最大相对宽度41.42%；不能把本结果当作精确连续边界。

| SLA | Variant | both safe | both unsafe | O | C | paired | missing |
|---|---|---|---|---|---|---|---|
| TTFT5.2_TPOT0.3 | Raw-Full | 98 | 402 | 0 | 0 | 500 | 0 |
| TTFT5.2_TPOT0.3 | Raw-Remaining | 98 | 402 | 0 | 0 | 500 | 0 |
| TTFT5.2_TPOT0.3 | Legacy-Full | 97 | 402 | 0 | 1 | 500 | 0 |
| TTFT5.2_TPOT0.3 | Legacy-Remaining | 97 | 402 | 0 | 1 | 500 | 0 |
| TTFT5.2_TPOT1.2 | Raw-Full | 112 | 378 | 0 | 10 | 500 | 0 |
| TTFT5.2_TPOT1.2 | Raw-Remaining | 112 | 378 | 0 | 10 | 500 | 0 |
| TTFT5.2_TPOT1.2 | Legacy-Full | 111 | 378 | 0 | 11 | 500 | 0 |
| TTFT5.2_TPOT1.2 | Legacy-Remaining | 111 | 378 | 0 | 11 | 500 | 0 |
| TTFT5.2_TPOT5 | Raw-Full | 252 | 90 | 7 | 151 | 500 | 0 |
| TTFT5.2_TPOT5 | Raw-Remaining | 298 | 80 | 17 | 105 | 500 | 0 |
| TTFT5.2_TPOT5 | Legacy-Full | 252 | 90 | 7 | 151 | 500 | 0 |
| TTFT5.2_TPOT5 | Legacy-Remaining | 298 | 80 | 17 | 105 | 500 | 0 |
| TTFT5.2_TPOT10 | Raw-Full | 384 | 52 | 0 | 64 | 500 | 0 |
| TTFT5.2_TPOT10 | Raw-Remaining | 410 | 52 | 0 | 38 | 500 | 0 |
| TTFT5.2_TPOT10 | Legacy-Full | 384 | 52 | 0 | 64 | 500 | 0 |
| TTFT5.2_TPOT10 | Legacy-Remaining | 410 | 52 | 0 | 38 | 500 | 0 |

| Semantic pair | removed C | new O | safe→unsafe | capacity improved/worsened | new unsafe recommendations | removed unsafe recommendations | unsafe severity worsened |
|---|---|---|---|---|---|---|---|
| Raw | 72 | 10 | 0 | 30/2 | 0 | 0 | 1 |
| Legacy | 72 | 10 | 0 | 30/2 | 0 | 0 | 1 |

## 14. Held-out capacity results

有所改善，但没有证据称capacity全面或明显变准。Phase B平均绝对相对gap仅从Raw41.11%→38.94%、Legacy41.31%→39.14%，下降2.17个百分点；80个配对候选/SLA中30个改善、2个变差、48个不变。总体signed-gap median均为0，掩盖SLA差异。TPOT10的median为−78.66%→−50.00%，mean absolute gap58.88%→41.89%；TPOT5的median虽从−94.74%→−87.50%，mean absolute gap却90.58%→98.89%，因为w202/shift−2的过高估计从+100%恶化到+300%，shift−1新增+100%。因此只看signed median会漏掉危险尾部。Phase B保留7条reference非单调、12条reference右删失序列；每个evaluator有5条右删失序列，均无no-safe序列。所有gap只针对采样最大safe，右删失值不是完整容量估计。

| SLA | Variant | defined gap | min / median / max | mean absolute gap | E no-safe/nonmono/censored | R no-safe/nonmono/censored |
|---|---|---|---|---|---|---|
| TTFT5.2_TPOT0.3 | Raw-Full | 20 | 0.00% / 0.00% / 0.00% | 0.00% | 0/0/0 | 0/0/0 |
| TTFT5.2_TPOT0.3 | Raw-Remaining | 20 | 0.00% / 0.00% / 0.00% | 0.00% | 0/0/0 | 0/0/0 |
| TTFT5.2_TPOT0.3 | Legacy-Full | 20 | -15.91% / 0.00% / 0.00% | 0.80% | 0/0/0 | 0/0/0 |
| TTFT5.2_TPOT0.3 | Legacy-Remaining | 20 | -15.91% / 0.00% / 0.00% | 0.80% | 0/0/0 | 0/0/0 |
| TTFT5.2_TPOT1.2 | Raw-Full | 20 | -99.92% / 0.00% / 0.00% | 14.98% | 0/0/0 | 0/3/2 |
| TTFT5.2_TPOT1.2 | Raw-Remaining | 20 | -99.92% / 0.00% / 0.00% | 14.98% | 0/0/0 | 0/3/2 |
| TTFT5.2_TPOT1.2 | Legacy-Full | 20 | -99.92% / 0.00% / 0.00% | 14.98% | 0/0/0 | 0/3/2 |
| TTFT5.2_TPOT1.2 | Legacy-Remaining | 20 | -99.92% / 0.00% / 0.00% | 14.98% | 0/0/0 | 0/3/2 |
| TTFT5.2_TPOT5 | Raw-Full | 20 | -96.28% / -94.74% / 100.00% | 90.58% | 0/0/0 | 0/4/5 |
| TTFT5.2_TPOT5 | Raw-Remaining | 20 | -91.16% / -87.50% / 300.00% | 98.89% | 0/0/0 | 0/4/5 |
| TTFT5.2_TPOT5 | Legacy-Full | 20 | -96.28% / -94.74% / 100.00% | 90.58% | 0/0/0 | 0/4/5 |
| TTFT5.2_TPOT5 | Legacy-Remaining | 20 | -91.16% / -87.50% / 300.00% | 98.89% | 0/0/0 | 0/4/5 |
| TTFT5.2_TPOT10 | Raw-Full | 20 | -87.50% / -78.66% / 0.00% | 58.88% | 0/0/5 | 0/0/5 |
| TTFT5.2_TPOT10 | Raw-Remaining | 20 | -82.32% / -50.00% / 0.00% | 41.89% | 0/0/5 | 0/0/5 |
| TTFT5.2_TPOT10 | Legacy-Full | 20 | -87.50% / -78.66% / 0.00% | 58.88% | 0/0/5 | 0/0/5 |
| TTFT5.2_TPOT10 | Legacy-Remaining | 20 | -82.32% / -50.00% / 0.00% | 41.89% | 0/0/5 | 0/0/5 |

## 15. Held-out decision results

Phase A的总winner agreement有所增加，但独立Phase B没有分区选择质量改善：Raw保持14/16（2个tie-break mismatch），Legacy保持13/16（2个tie-break、1个strict mismatch）。平均partition loss分别保持3.66%和9.91%。Raw/Legacy各只有w202/TPOT10从shift0变为shift1，reference-best包含二者，因此不能算修复错误。Phase A还存在反向变化：h103/TPOT5的partition loss约2.14%→12.19%；Legacy h105/TPOT10从agreement退化为tie-break mismatch，TTFT5.2和4.68两条件均如此。

| Workload | SLA | Variant | E best → selected | R best | type / rank | partition loss | operating loss | exact safe | violations | safe loss |
|---|---|---|---|---|---|---|---|---|---|---|
| w201 | TTFT5.2_TPOT0.3 | Raw-Full | [-2] → -2 | [-2] | agreement / 1 | 0.00% | 0.00% | True | 0/13 | 0.00% |
| w201 | TTFT5.2_TPOT0.3 | Raw-Remaining | [-2] → -2 | [-2] | agreement / 1 | 0.00% | 0.00% | True | 0/13 | 0.00% |
| w201 | TTFT5.2_TPOT0.3 | Legacy-Full | [-2] → -2 | [-2] | agreement / 1 | 0.00% | 0.00% | True | 0/13 | 0.00% |
| w201 | TTFT5.2_TPOT0.3 | Legacy-Remaining | [-2] → -2 | [-2] | agreement / 1 | 0.00% | 0.00% | True | 0/13 | 0.00% |
| w201 | TTFT5.2_TPOT1.2 | Raw-Full | [-2, -1, 0, 1, 2] → 0 | [-2, -1, 0, 1, 2] | agreement / 1 | 0.00% | 0.00% | True | 0/13 | 0.00% |
| w201 | TTFT5.2_TPOT1.2 | Raw-Remaining | [-2, -1, 0, 1, 2] → 0 | [-2, -1, 0, 1, 2] | agreement / 1 | 0.00% | 0.00% | True | 0/13 | 0.00% |
| w201 | TTFT5.2_TPOT1.2 | Legacy-Full | [-2, -1, 0, 1, 2] → 0 | [-2, -1, 0, 1, 2] | agreement / 1 | 0.00% | 0.00% | True | 0/13 | 0.00% |
| w201 | TTFT5.2_TPOT1.2 | Legacy-Remaining | [-2, -1, 0, 1, 2] → 0 | [-2, -1, 0, 1, 2] | agreement / 1 | 0.00% | 0.00% | True | 0/13 | 0.00% |
| w201 | TTFT5.2_TPOT5 | Raw-Full | [-1, 0, 1, 2] → 0 | [1, 2] | tie-break mismatch / 3 | 29.29% | 95.58% | True | 0/13 | 95.58% |
| w201 | TTFT5.2_TPOT5 | Raw-Remaining | [-2, -1, 0, 1, 2] → 0 | [1, 2] | tie-break mismatch / 3 | 29.29% | 87.50% | True | 0/13 | 87.50% |
| w201 | TTFT5.2_TPOT5 | Legacy-Full | [-1, 0, 1, 2] → 0 | [1, 2] | tie-break mismatch / 3 | 29.29% | 95.58% | True | 0/13 | 95.58% |
| w201 | TTFT5.2_TPOT5 | Legacy-Remaining | [-2, -1, 0, 1, 2] → 0 | [1, 2] | tie-break mismatch / 3 | 29.29% | 87.50% | True | 0/13 | 87.50% |
| w201 | TTFT5.2_TPOT10 | Raw-Full | [-2, -1, 0, 1, 2] → 0 | [1, 2] | tie-break mismatch / 3 | 29.29% | 87.50% | True | 0/13 | 87.50% |
| w201 | TTFT5.2_TPOT10 | Raw-Remaining | [-2, -1, 0, 1, 2] → 0 | [1, 2] | tie-break mismatch / 3 | 29.29% | 64.64% | True | 0/13 | 64.64% |
| w201 | TTFT5.2_TPOT10 | Legacy-Full | [-2, -1, 0, 1, 2] → 0 | [1, 2] | tie-break mismatch / 3 | 29.29% | 87.50% | True | 0/13 | 87.50% |
| w201 | TTFT5.2_TPOT10 | Legacy-Remaining | [-2, -1, 0, 1, 2] → 0 | [1, 2] | tie-break mismatch / 3 | 29.29% | 64.64% | True | 0/13 | 64.64% |
| w202 | TTFT5.2_TPOT0.3 | Raw-Full | [-2, -1, 0] → 0 | [-2, -1, 0] | agreement / 1 | 0.00% | 0.00% | True | 0/48 | 0.00% |
| w202 | TTFT5.2_TPOT0.3 | Raw-Remaining | [-2, -1, 0] → 0 | [-2, -1, 0] | agreement / 1 | 0.00% | 0.00% | True | 0/48 | 0.00% |
| w202 | TTFT5.2_TPOT0.3 | Legacy-Full | [-2, -1, 0] → 0 | [-2, -1, 0] | agreement / 1 | 0.00% | 0.00% | True | 0/48 | 0.00% |
| w202 | TTFT5.2_TPOT0.3 | Legacy-Remaining | [-2, -1, 0] → 0 | [-2, -1, 0] | agreement / 1 | 0.00% | 0.00% | True | 0/48 | 0.00% |
| w202 | TTFT5.2_TPOT1.2 | Raw-Full | [-2, -1, 0] → 0 | [-2, -1, 0] | agreement / 1 | 0.00% | 0.00% | True | 0/48 | 0.00% |
| w202 | TTFT5.2_TPOT1.2 | Raw-Remaining | [-2, -1, 0] → 0 | [-2, -1, 0] | agreement / 1 | 0.00% | 0.00% | True | 0/48 | 0.00% |
| w202 | TTFT5.2_TPOT1.2 | Legacy-Full | [-2, -1, 0] → 0 | [-2, -1, 0] | agreement / 1 | 0.00% | 0.00% | True | 0/48 | 0.00% |
| w202 | TTFT5.2_TPOT1.2 | Legacy-Remaining | [-2, -1, 0] → 0 | [-2, -1, 0] | agreement / 1 | 0.00% | 0.00% | True | 0/48 | 0.00% |
| w202 | TTFT5.2_TPOT5 | Raw-Full | [-2, -1, 0, 1, 2] → 0 | [0, 1, 2] | agreement / 1 | 0.00% | 95.58% | False | 1/48 | 100.00% |
| w202 | TTFT5.2_TPOT5 | Raw-Remaining | [-2, -1, 0, 1, 2] → 0 | [0, 1, 2] | agreement / 1 | 0.00% | 91.16% | False | 9/48 | 100.00% |
| w202 | TTFT5.2_TPOT5 | Legacy-Full | [-2, -1, 0, 1, 2] → 0 | [0, 1, 2] | agreement / 1 | 0.00% | 95.58% | False | 1/48 | 100.00% |
| w202 | TTFT5.2_TPOT5 | Legacy-Remaining | [-2, -1, 0, 1, 2] → 0 | [0, 1, 2] | agreement / 1 | 0.00% | 91.16% | False | 9/48 | 100.00% |
| w202 | TTFT5.2_TPOT10 | Raw-Full | [0, 1, 2] → 0 | [0, 1, 2] | agreement / 1 | 0.00% | 64.64% | True | 0/48 | 64.64% |
| w202 | TTFT5.2_TPOT10 | Raw-Remaining | [1, 2] → 1 | [0, 1, 2] | agreement / 1 | 0.00% | 50.00% | True | 0/48 | 50.00% |
| w202 | TTFT5.2_TPOT10 | Legacy-Full | [0, 1, 2] → 0 | [0, 1, 2] | agreement / 1 | 0.00% | 64.64% | True | 0/48 | 64.64% |
| w202 | TTFT5.2_TPOT10 | Legacy-Remaining | [1, 2] → 1 | [0, 1, 2] | agreement / 1 | 0.00% | 50.00% | True | 0/48 | 50.00% |
| w203 | TTFT5.2_TPOT0.3 | Raw-Full | [-2, -1, 0] → 0 | [-2, -1, 0] | agreement / 1 | 0.00% | 0.00% | True | 0/5 | 0.00% |
| w203 | TTFT5.2_TPOT0.3 | Raw-Remaining | [-2, -1, 0] → 0 | [-2, -1, 0] | agreement / 1 | 0.00% | 0.00% | True | 0/5 | 0.00% |
| w203 | TTFT5.2_TPOT0.3 | Legacy-Full | [-2, -1] → -1 | [-2, -1, 0] | agreement / 1 | 0.00% | 0.00% | True | 0/5 | 0.00% |
| w203 | TTFT5.2_TPOT0.3 | Legacy-Remaining | [-2, -1] → -1 | [-2, -1, 0] | agreement / 1 | 0.00% | 0.00% | True | 0/5 | 0.00% |
| w203 | TTFT5.2_TPOT1.2 | Raw-Full | [-2, -1, 0] → 0 | [0, 1] | agreement / 1 | 0.00% | 99.90% | True | 0/5 | 99.90% |
| w203 | TTFT5.2_TPOT1.2 | Raw-Remaining | [-2, -1, 0] → 0 | [0, 1] | agreement / 1 | 0.00% | 99.90% | True | 0/5 | 99.90% |
| w203 | TTFT5.2_TPOT1.2 | Legacy-Full | [-2, -1] → -1 | [0, 1] | strict best-set mismatch / 4 | 99.90% | 99.90% | True | 0/5 | 99.90% |
| w203 | TTFT5.2_TPOT1.2 | Legacy-Remaining | [-2, -1] → -1 | [0, 1] | strict best-set mismatch / 4 | 99.90% | 99.90% | True | 0/5 | 99.90% |
| w203 | TTFT5.2_TPOT5 | Raw-Full | [-2, -1, 0, 1, 2] → 0 | [-2, -1, 0, 1, 2] | agreement / 1 | 0.00% | 94.74% | True | 0/5 | 94.74% |
| w203 | TTFT5.2_TPOT5 | Raw-Remaining | [-2, -1, 0, 1, 2] → 0 | [-2, -1, 0, 1, 2] | agreement / 1 | 0.00% | 87.50% | True | 0/5 | 87.50% |
| w203 | TTFT5.2_TPOT5 | Legacy-Full | [-2, -1, 0, 1, 2] → 0 | [-2, -1, 0, 1, 2] | agreement / 1 | 0.00% | 94.74% | True | 0/5 | 94.74% |
| w203 | TTFT5.2_TPOT5 | Legacy-Remaining | [-2, -1, 0, 1, 2] → 0 | [-2, -1, 0, 1, 2] | agreement / 1 | 0.00% | 87.50% | True | 0/5 | 87.50% |
| w203 | TTFT5.2_TPOT10 | Raw-Full | [-2, -1, 0, 1, 2] → 0 | [-2, -1, 0, 1, 2] | agreement / 1 | 0.00% | 0.00% | True | 0/5 | 0.00% |
| w203 | TTFT5.2_TPOT10 | Raw-Remaining | [-2, -1, 0, 1, 2] → 0 | [-2, -1, 0, 1, 2] | agreement / 1 | 0.00% | 0.00% | True | 0/5 | 0.00% |
| w203 | TTFT5.2_TPOT10 | Legacy-Full | [-2, -1, 0, 1, 2] → 0 | [-2, -1, 0, 1, 2] | agreement / 1 | 0.00% | 0.00% | True | 0/5 | 0.00% |
| w203 | TTFT5.2_TPOT10 | Legacy-Remaining | [-2, -1, 0, 1, 2] → 0 | [-2, -1, 0, 1, 2] | agreement / 1 | 0.00% | 0.00% | True | 0/5 | 0.00% |
| w204 | TTFT5.2_TPOT0.3 | Raw-Full | [-2] → -2 | [-2] | agreement / 1 | 0.00% | 0.00% | True | 0/44 | 0.00% |
| w204 | TTFT5.2_TPOT0.3 | Raw-Remaining | [-2] → -2 | [-2] | agreement / 1 | 0.00% | 0.00% | True | 0/44 | 0.00% |
| w204 | TTFT5.2_TPOT0.3 | Legacy-Full | [-2] → -2 | [-2] | agreement / 1 | 0.00% | 0.00% | True | 0/44 | 0.00% |
| w204 | TTFT5.2_TPOT0.3 | Legacy-Remaining | [-2] → -2 | [-2] | agreement / 1 | 0.00% | 0.00% | True | 0/44 | 0.00% |
| w204 | TTFT5.2_TPOT1.2 | Raw-Full | [-2] → -2 | [-2] | agreement / 1 | 0.00% | 0.00% | True | 0/44 | 0.00% |
| w204 | TTFT5.2_TPOT1.2 | Raw-Remaining | [-2] → -2 | [-2] | agreement / 1 | 0.00% | 0.00% | True | 0/44 | 0.00% |
| w204 | TTFT5.2_TPOT1.2 | Legacy-Full | [-2] → -2 | [-2] | agreement / 1 | 0.00% | 0.00% | True | 0/44 | 0.00% |
| w204 | TTFT5.2_TPOT1.2 | Legacy-Remaining | [-2] → -2 | [-2] | agreement / 1 | 0.00% | 0.00% | True | 0/44 | 0.00% |
| w204 | TTFT5.2_TPOT5 | Raw-Full | [-2, -1, 0, 1, 2] → 0 | [-1, 0, 1, 2] | agreement / 1 | 0.00% | 96.28% | True | 0/44 | 96.28% |
| w204 | TTFT5.2_TPOT5 | Raw-Remaining | [-2, -1, 0, 1, 2] → 0 | [-1, 0, 1, 2] | agreement / 1 | 0.00% | 91.16% | True | 0/44 | 91.16% |
| w204 | TTFT5.2_TPOT5 | Legacy-Full | [-2, -1, 0, 1, 2] → 0 | [-1, 0, 1, 2] | agreement / 1 | 0.00% | 96.28% | True | 0/44 | 96.28% |
| w204 | TTFT5.2_TPOT5 | Legacy-Remaining | [-2, -1, 0, 1, 2] → 0 | [-1, 0, 1, 2] | agreement / 1 | 0.00% | 91.16% | True | 0/44 | 91.16% |
| w204 | TTFT5.2_TPOT10 | Raw-Full | [-2, -1, 0, 1, 2] → 0 | [-1, 0, 1, 2] | agreement / 1 | 0.00% | 82.32% | True | 0/44 | 82.32% |
| w204 | TTFT5.2_TPOT10 | Raw-Remaining | [-1, 0, 1, 2] → 0 | [-1, 0, 1, 2] | agreement / 1 | 0.00% | 50.00% | True | 0/44 | 50.00% |
| w204 | TTFT5.2_TPOT10 | Legacy-Full | [-2, -1, 0, 1, 2] → 0 | [-1, 0, 1, 2] | agreement / 1 | 0.00% | 82.32% | True | 0/44 | 82.32% |
| w204 | TTFT5.2_TPOT10 | Legacy-Remaining | [-1, 0, 1, 2] → 0 | [-1, 0, 1, 2] | agreement / 1 | 0.00% | 50.00% | True | 0/44 | 50.00% |

| SLA | Variant | partition mean / n | operating mean / n | safe mean / n | unsafe outputs | abstentions | decision types |
|---|---|---|---|---|---|---|---|
| TTFT5.2_TPOT0.3 | Raw-Full | 0.00% / 4 | 0.00% / 4 | 0.00% / 4 | 0 | 0 | {'agreement': 4} |
| TTFT5.2_TPOT0.3 | Raw-Remaining | 0.00% / 4 | 0.00% / 4 | 0.00% / 4 | 0 | 0 | {'agreement': 4} |
| TTFT5.2_TPOT0.3 | Legacy-Full | 0.00% / 4 | 0.00% / 4 | 0.00% / 4 | 0 | 0 | {'agreement': 4} |
| TTFT5.2_TPOT0.3 | Legacy-Remaining | 0.00% / 4 | 0.00% / 4 | 0.00% / 4 | 0 | 0 | {'agreement': 4} |
| TTFT5.2_TPOT1.2 | Raw-Full | 0.00% / 4 | 24.98% / 4 | 24.98% / 4 | 0 | 0 | {'agreement': 4} |
| TTFT5.2_TPOT1.2 | Raw-Remaining | 0.00% / 4 | 24.98% / 4 | 24.98% / 4 | 0 | 0 | {'agreement': 4} |
| TTFT5.2_TPOT1.2 | Legacy-Full | 24.98% / 4 | 24.98% / 4 | 24.98% / 4 | 0 | 0 | {'agreement': 3, 'strict best-set mismatch': 1} |
| TTFT5.2_TPOT1.2 | Legacy-Remaining | 24.98% / 4 | 24.98% / 4 | 24.98% / 4 | 0 | 0 | {'agreement': 3, 'strict best-set mismatch': 1} |
| TTFT5.2_TPOT5 | Raw-Full | 7.32% / 4 | 95.55% / 4 | 96.65% / 4 | 1 | 0 | {'tie-break mismatch': 1, 'agreement': 3} |
| TTFT5.2_TPOT5 | Raw-Remaining | 7.32% / 4 | 89.33% / 4 | 91.54% / 4 | 1 | 0 | {'tie-break mismatch': 1, 'agreement': 3} |
| TTFT5.2_TPOT5 | Legacy-Full | 7.32% / 4 | 95.55% / 4 | 96.65% / 4 | 1 | 0 | {'tie-break mismatch': 1, 'agreement': 3} |
| TTFT5.2_TPOT5 | Legacy-Remaining | 7.32% / 4 | 89.33% / 4 | 91.54% / 4 | 1 | 0 | {'tie-break mismatch': 1, 'agreement': 3} |
| TTFT5.2_TPOT10 | Raw-Full | 7.32% / 4 | 58.62% / 4 | 58.62% / 4 | 0 | 0 | {'tie-break mismatch': 1, 'agreement': 3} |
| TTFT5.2_TPOT10 | Raw-Remaining | 7.32% / 4 | 41.16% / 4 | 41.16% / 4 | 0 | 0 | {'tie-break mismatch': 1, 'agreement': 3} |
| TTFT5.2_TPOT10 | Legacy-Full | 7.32% / 4 | 58.62% / 4 | 58.62% / 4 | 0 | 0 | {'tie-break mismatch': 1, 'agreement': 3} |
| TTFT5.2_TPOT10 | Legacy-Remaining | 7.32% / 4 | 41.16% / 4 | 41.16% / 4 | 0 | 0 | {'tie-break mismatch': 1, 'agreement': 3} |

## 16. Runtime / complexity

| Variant | n | runtime median (ms) | runtime p95 (ms) | events median | events p95 |
|---|---|---|---|---|---|
| Raw-Full | 720 | 1.91165 | 34.9277 | 66 | 857 |
| Raw-Remaining | 720 | 1.95445 | 39.6383 | 66 | 857 |
| Legacy-Full | 720 | 1.9061 | 35.0599 | 66 | 857 |
| Legacy-Remaining | 720 | 1.9457 | 40.1113 | 66 | 857 |

Sequential same-process evaluator calls after physical campaign; one pass all 180 initial points x 4 SLAs x 4 variants, shared CachedProfiles per workload, deterministic rotating variant order; Full calls frozen journal_baseline.py and Remaining calls journal_baseline_plus.py. perf_counter wall seconds on CPU, no reference query.

Two stored scalars (start, progress duration) per active Prefill; existing frozen compute reused; fraction computed transiently. O(active Prefill) per check, same asymptotic debt-scan order. Early rejection can change measured event count; full-drain trajectories unchanged.

每种variant独立顺序计时720次。Raw median 1.912→1.954 ms，p95 34.928→39.638 ms；Legacy median 1.906→1.946 ms，p95 35.060→40.111 ms。事件数median均66、p95均857；小幅增加的CPU计算仍在同一数量级。这些是特定主机和调用集上的描述性规划计时，不是生产延迟或GPU serving speedup。 These are CPU planning measurements, not GPU serving speedup. Early-stop event counts may increase because more requests are admitted; the correction has the same full-drain trajectory and asymptotic event structure.

## 17. Failure cases

必须保留四类反例：原h105保守trace债务下降但仍被拒绝；原h103乐观trace的completion-time drift完全保留；Phase A h103/h105部分partition选择变差；Phase B w202/TPOT5同时出现新增10个optimistic点、capacity高估尾部+100%→+300%、不安全推荐违规请求1/48→9/48。Legacy w203/TPOT1.2的strict mismatch及99.90%partition loss也保持。正确partition、较小算术operating loss与推荐点安全性不能互相替代。

h101名义relaxed reversal在Phase A共同网格上被消除：两种语义都从shift2改选shift0，reference-best为{0}；partition loss21.20%→0%，operating loss68.95%→40.54%。Remaining的E-best为{0,1,2}，由原tie-break选0，所以这是该网格上的agreement，不是严格恢复了所有候选排序。共同负载4.096的局部trace中shift0由拒绝变接受，shift2一直接受；该局部改善与最终采样选择一致，但不证明真实连续前沿已被恢复。

Failed physical points remain explicit in failed_points.json; no failure was converted to unsafe. All changed verdicts and all changed/worsened selection and loss cases remain in paired records. There is no result-driven refit or second correction.

## 18. Limitations

仅在指定 HELIX reference simulator、同一 Azure 生成分布、有限 trace、五个候选及采样网格内成立；没有真实GPU验证、连续capacity、安全前缀或普遍风险概率。Phase A是post-hoc，Phase B是四个新seed/非重叠源窗口的受限held-out，不是外部数据集验证。Source窗口按构造器循环，w204 offset1200对应原始bins0–39；只保证与h101–h106及本批其他窗口不重叠，未声称所有项目历史从未用过这些源bins。源token分布复用且workload/link/duration非完整交叉。Phase A沿用Stage4网格，未为Remaining重新细化，不能继承原Full边界精度；Raw/Legacy的Remaining分别有67/70个候选-SLA序列存在未达2.5%的已观测transition。Phase B网格由reference与四个variants的transition共同构造；未解决边界照实保留，没有发现的窄safe/unsafe岛不能排除。

**B. Partial — keep JB1 as main object, use JB1+ as mechanism-guided correction.** 独立held-out支持机制作用和部分保守性/利用率收益，但新增optimistic errors、恶化的违规严重度、没有改善的partition selection，以及仍很大的capacity误差，均不支持把JB1+替换为更可靠的主evaluator。它适合作为预冻结、无拟合参数、保留反例的mechanism-guided correction实验。不是只有post-hoc有效的纯负消融，因此不选C；也不满足全面替换的依据，因此不选A。

保留500点预算终点、37个未解决区间和全部负结果，不追加新workloads/SLA/profile/model，也不开发JB1++。本阶段仅交付experiment evidence，不写manuscript。

Reproduction: `run_jb1_plus.py all` resumes missing saved campaign points; `analyze_jb1_plus.py`, `audit_jb1_plus.py mechanisms`, `audit_jb1_plus.py timing`, `verify_jb1_plus.py`, `figure_jb1_plus.py`, `report_jb1_plus.py`. Verification and analysis do not launch HELIX. Protect all earlier results. New main-text candidates are only FigureA (judgment/capacity) and FigureB (held-out decisions/loads), PNG+SVG. Horizontal offsets expose coincident category markers; lines do not interpolate new SLA thresholds. No manuscript sections were written.
