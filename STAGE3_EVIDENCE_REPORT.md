# 1. 一句话结论

**主线 Yes, but modified：JB1相对HELIX的误差仍会传导为分区和运行负载损失，但5 ms进度语义能改变具体决策；Legacy对照将relaxed-TPOT选偏从6/6减为4/6，并未消除问题。** 实验阶段到此停止，写作输入已经准备好。

日期2026-09-17。研究对象是明确恢复的JB1与固定HELIX reference simulator，非不可见的CA-final源码、非真实GPU部署。所有safe均仅指对应SLA和模拟器。

# 2. Legacy progress sensitivity

3268个冻结名义配对点，复用1634个物理reference records，新增reference runs=0。
仅开启5 ms fixed overhead progress；所有其他输入、账本、候选、tie-break和grid不变，未调参。
53个标签从safe变unsafe，O 23→17，C 413→460。Tight winner agreement 6/6→6/6；relaxed 0/6→2/6。

| 负载 | Raw best → selected | Legacy best → selected | R best | Raw 类型 | Legacy 类型 | Raw 分区损失 | Legacy 分区损失 |
|---|---|---|---|---|---|---|---|
| h101 | [2] → 2 | [2] → 2 | [0] | strict best-set mismatch | strict best-set mismatch | 21.20% | 21.20% |
| h102 | [1, 2] → 1 | [2] → 2 | [0] | strict best-set mismatch | strict best-set mismatch | 8.30% | 14.07% |
| h103 | [2] → 2 | [2] → 2 | [0] | strict best-set mismatch | strict best-set mismatch | 12.19% | 12.19% |
| h104 | [2] → 2 | [0, 1, 2] → 0 | [0, 1] | strict best-set mismatch | agreement | 10.26% | 0.00% |
| h105 | [0, 1, 2] → 0 | [1, 2] → 1 | [1] | tie-break mismatch | agreement | 10.26% | 0.00% |
| h106 | [1, 2] → 1 | [1, 2] → 1 | [2] | tie-break mismatch | tie-break mismatch | 26.16% | 26.16% |

Legacy h102反而变差：rank2→4，loss8.30%→14.07%；h104、h105修复，h106保持tie-break mismatch。
详见[完整对照](docs/LEGACY_PROGRESS_SENSITIVITY.md)及[独立结果目录](results/formal/legacy_progress_sensitivity/summary.json)。

# 3. Journal 主线是否仍成立

**Yes, but modified.** 保留 judgment reliability → sampled capacity error → deployment decision error → profile-mismatch sensitivity。
增加implementation-semantic sensitivity作为结论的必要条件：不能再把Raw的六次relaxed选偏写成与实现选择无关的事实。
改善不是全局一致：Legacy减少O但增加C，仍有3个strict和1个tie-break mismatch；不包装修复算法。

# 4. 最终 judgement-level evidence

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

异构TTFT均5.2 s；tight TPOT=.30 s，relaxed TPOT=10 s。A100 TTFT均2 s；TPOT=.15 s/1 s。
Raw keys `decode` / `prefill` / `relaxed_decode`不变，只映射展示标签。标签不预设first violation属于Prefill。
Raw总计953 both safe、1879 both unsafe、23 O、413 C；E接受976中23 R拒绝，R接受1366中413 E拒绝。
A100 Raw O=14/102个E接受点，需与异构分开；不能被大分母稀释。
3268是配对判定数，1634才是物理点数；自适应边界样本不是风险概率或独立重复样本。

# 5. 最终 capacity-level evidence

| variant | 有限误差 / 76 | 最小 gap | 中位数 | 最大 gap | no-safe | nonmonotone | right-censored |
|---|---|---|---|---|---|---|---|
| raw | 68 | -95.86% | 0.00% | 182.84% | 8 | 0 | 0 |
| legacy | 68 | -95.86% | -15.91% | 165.05% | 8 | 0 | 0 |

Capacity始终是共同网格中的largest observed safe intensity，不是连续capacity或稳态吞吐量。
Raw 68个有限gap：31负、32零、5正。8个E/R均no-safe，未以零gap纳入；R有3个非单调序列，E/R均0右删失。
Raw单边界支持65/76，已定义局部bracket最大2.190%；非单调h106最大safe仍不形成安全前缀。
Legacy沿用同一grid，保存nearest unsafe、全序列、no-safe、nonmonotone和right-censoring；不为控制变体额外细化。

# 6. 最终 decision-level evidence

Raw：tight 6/6一致；relaxed 4 strict best-set mismatches（h101–h104）和2 tie-break mismatches（h105/h106），不能写6 strict ranking reversals。
Legacy：tight 6/6一致；relaxed 3 strict（h101–h103）、1 tie-break（h106），另外2一致。
原tie-break始终为绝对shift最小，再负shift优先。Reference-best仅限五个shift和该共同网格。
h104原R-best有{0,1}并列；h102/h105/h106原E-best有并列。h106有no-safe candidates及reference nonmonotonicity，均保留。

# 7. Decision-loss decomposition

设B=reference-best sampled capacity，S=所选partition的reference sampled capacity，L=E推荐负载。
Partition loss=1−S/B；operating-point loss=1−L/B；safe operating-point loss在推荐点R-unsafe或弃权时将usable load记0。
可加分解为 (1−S/B)+(S−L)/B=1−L/B；不能把前两种总损失重复相加。

| 负载 | Raw / Legacy | SLA | 分区损失 | 运行点损失 | 安全可用损失 | 推荐点 R-safe |
|---|---|---|---|---|---|---|
| h101 | raw | tight-TPOT | 0.00% | 0.00% | 0.00% | True |
| h101 | legacy | tight-TPOT | 0.00% | 2.14% | 2.14% | True |
| h101 | raw | relaxed-TPOT (fixed TTFT) | 21.20% | 68.95% | 68.95% | True |
| h101 | legacy | relaxed-TPOT (fixed TTFT) | 21.20% | 68.95% | 68.95% | True |
| h102 | raw | tight-TPOT | 0.00% | 0.00% | 0.00% | True |
| h102 | legacy | tight-TPOT | 0.00% | 2.14% | 2.14% | True |
| h102 | raw | relaxed-TPOT (fixed TTFT) | 8.30% | 74.45% | 74.45% | True |
| h102 | legacy | relaxed-TPOT (fixed TTFT) | 14.07% | 74.45% | 74.45% | True |
| h103 | raw | tight-TPOT | 0.00% | 0.00% | 0.00% | True |
| h103 | legacy | tight-TPOT | 0.00% | 2.14% | 2.14% | True |
| h103 | raw | relaxed-TPOT (fixed TTFT) | 12.19% | 70.91% | 70.91% | True |
| h103 | legacy | relaxed-TPOT (fixed TTFT) | 12.19% | 70.91% | 70.91% | True |
| h104 | raw | tight-TPOT | 0.00% | 0.00% | 0.00% | True |
| h104 | legacy | tight-TPOT | 0.00% | 2.14% | 2.14% | True |
| h104 | raw | relaxed-TPOT (fixed TTFT) | 10.26% | 81.94% | 81.94% | True |
| h104 | legacy | relaxed-TPOT (fixed TTFT) | 0.00% | 82.32% | 82.32% | True |
| h105 | raw | tight-TPOT | 0.00% | 0.00% | 0.00% | True |
| h105 | legacy | tight-TPOT | 0.00% | 2.14% | 2.14% | True |
| h105 | raw | relaxed-TPOT (fixed TTFT) | 10.26% | 87.77% | 87.77% | True |
| h105 | legacy | relaxed-TPOT (fixed TTFT) | 0.00% | 87.77% | 87.77% | True |
| h106 | raw | tight-TPOT | 0.00% | 0.00% | 0.00% | True |
| h106 | legacy | tight-TPOT | 0.00% | 2.14% | 2.14% | True |
| h106 | raw | relaxed-TPOT (fixed TTFT) | 26.16% | 95.86% | 100.00% | False |
| h106 | legacy | relaxed-TPOT (fixed TTFT) | 26.16% | 95.86% | 100.00% | False |

Raw relaxed分区loss8.30%–26.16%，运行点loss68.95%–95.86%。h106实际推荐R-unsafe，因此safe usable loss为100%。
Legacy h105选对partition但运行点loss仍87.77%，h104选对但运行点loss略增到82.32%；winner修复不能替代最终负载审计。
详见[分解说明](docs/DECISION_LOSS_DECOMPOSITION.md)、[逐场景数据](results/formal/decision_loss_decomposition.json)，后者另附144行mitigation主场景损失。

# 8. Profile mismatch evidence

冻结35,688行Raw JB1 stress，0 errors。Nominal O/C=23/413、winner6/12；Both−5%=264/297、9/12；Both−10%=324/279、3/12；Both−20%=395/253、3/12。
每个上述条件分母3268。Both−10%的E接受点324/1411被R拒绝，所选shift改变10/12，六个原本正确tight全部变错，同时修复三个relaxed错误。
L4x2-only−10%分母3008，O/C=235/295，winner8/12；不能套用3268。
Stress可改善winner却恶化点判定，不能用排序质量代替安全。Legacy未做profile stress，不把Raw stress结论外推为legacy结论。

# 9. Mechanism evidence

五个已保存的metric-identical解释trace，全部复用。h105/A100的full active-Prefill charge 1.547523 s，加compute .112 s、fixed .005 s=1.664523 s，超过1 s；R最大TPOT .945950 s。
h103/A100的Raw提前完成请求，漏掉随后真实P/D重叠：E最大TPOT .117367 s，R 1.103934 s；5 ms progress诊断恢复该重叠，但首次失败在更早请求，不能叫精确修复。
h101相同load4.096两shift账本跨越10 s阈值、R均safe，解释局部选择偏向；未隔离高负载完整参考排序因果链。
大误差且winner正确的h103来自Both−5%/−10% stress，Both−10% gap −70.27%；不能冒充名义成功。
详见[机制分析](docs/MECHANISM_ANALYSIS.md)。案例为结果后选择，不能用于估计发生率。

# 10. Implementation-semantic sensitivity

JB1 raw-progress恢复published endpoint 0/12；legacy control恢复12/12只是已完成baseline audit，不等于恢复CA-final。
正式held-out sensitivity现在完整补齐。小语义选择能改变53个标签和3个主selected shifts，但并未消除错误传导。
总体判断属于“保留主线，同时明确部分implementation dependence”，不能选择性隐藏h104/h105改善或h102恶化。
冻结baseline SHA256 `4f186748f3fb5940179e833ffe68cf463bb8b9d1dbbd16926490062065669b15`；protocol hash `75120a5593b7c9574fe5bb3b21c3172179b95700955464d6aada0d12f04024bf`。

# 11. Mitigation evidence

**Conditional reference-validation replay on the frozen grid**：网格构造已使用reference transition信息，最多5次query只是post-selection回放，构造成本不在预算里。
禁止“five calls solve planning from scratch”。边界回放不重新搜索partition，不是新optimizer或对reference-only算法的优越性证据。

| profiles | 场景 | 实际降额有定义 | 最小 | 中位数 | 最大 | 取整后分区变化 | unsafe 输出 |
|---|---|---|---|---|---|---|---|
| nominal | 28 | 26 | 21.20% | 46.53% | 79.87% | 8 | 2 |
| Both −10% | 28 | 28 | 21.20% | 26.09% | 78.98% | 0 | 5 |

名义h101/tight：原负载0.0099348625，20%-target 0.00794789，grid-snapped output .004，实际降幅59.74%。
Nominal取整还改变8/28个selected partitions；保留原policy实现并明确披露。正式名称为 **20%-target derating with grid snapping**。
全28场景中有26个定义reference oracle；质量均值分母26，unsafe/abstention分母28；主图仅12。
E-only名义5 unsafe/2 abstain、usable quality55.33%；边界回放0/4、71.37%。Both−10%分别20/0、7.97%和0/8、70.00%。
0 unsafe来自只输出实际查询safe点的规则，不是独立泛化安全结论。详见[mitigation审计](docs/MITIGATION_INTERPRETATION_AUDIT.md)。

# 12. 最终最强 3 个 research findings

1. 判定、容量和决策可靠性不等价：同一评估器在tight下保留winner，在relaxed下出现strict和tie-break两类错误；总体gap中位数0会掩盖差异。
2. 分区选对仍可能严重浪费或错误推荐负载；实现语义能修复winner却不恢复运行点利用率，必须联合报告两层loss和精确点安全标签。
3. Profile与progress语义的改变会重新分配乐观/保守错误及决策错误；参考验证在已构造网格的条件回放中有工程价值，但不能据此宣称低预算从零规划或普遍安全。

# 13. 最终 limitations

Recovered JB1而非CA-final；HELIX reference而非real GPUs；六个有限trace，非随机风险样本；五候选，无global search；workload/link/duration非完整交叉；reference非单调；共同grid由Raw和R构造，legacy是该grid上的条件敏感性而非独立重新精化容量；没有legacy×profile stress交叉实验；机制trace为post hoc；mitigation预算排除reference-informed grid构造成本。
原40-test/140-row历史包仍不可得，没有声称复跑。两例顺序CPU规划R/E时间比1328.6、1389.1仅属于这些案例，不是GPU推理加速或整套policy的端到端加速。

# 14. 可以 claim 什么

JB1 shows the stated differences under the pinned HELIX reference simulator；legacy-progress control changes/preserves具体列明结果；Raw 4 strict + 2 tie-break、Legacy 3 strict + 1 tie-break；tested family/common-grid sampled capacity；conditional reference-validation replay；实际grid-snapped降额；参考点级验证。

# 15. 不可以 claim 什么

Unavailable CA-final evaluator shows these failures；legacy control is confirmed CA-final code；6 strict ranking reversals；从零5次reference足够planning；real deployment safety；global optimum；连续安全前缀；新scheduler/optimizer或普遍风险概率；真实profile噪声分布；Legacy stress未经运行的结果。

# 16. 推荐正文 figures/tables

保留[01 reliability](results/formal/figures/01_reliability.png)、[02 capacity](results/formal/figures/02_capacity.png)、[03 decision stress](results/formal/figures/03_decision_stress.png)、[04 mitigation](results/formal/figures/04_mitigation.png)，以及[乐观](results/formal/figures/optimistic_h103_a100_timeline.png)/[保守](results/formal/figures/conservative_h105_a100_timeline.png)两面板机制时间线。
03明确标S/T；04明确conditional replay和grid-snapped target。各图SVG同时提供。
增加一张compact Legacy decision comparison table（本报告第2节），loss表取relaxed六行；不再扩充大量图。
Figure 02未绘制8个no-safe配置，表中保留；h106非单调点不能解释成连续容量。

# 17. 写论文时推荐故事线

只给outline：研究对象/输入契约与provenance → 三层reliability指标 → Raw名义证据与strict/tie区分 → 两类loss → Legacy实现敏感性 → Raw profile stress → 机制解释 → conditional mitigation → 限制。
Prior CA贡献和journal新增诊断要分清。正文写作由后续对话负责；本阶段没有创建完整manuscript、Introduction、Related Work、Abstract或Conclusion。

# 18. 是否还需要实验

**No further experiments needed.** 此结论限于上面的受限实证主张；Stage 3两项必要工作已完成，不再扩大矩阵或寻找CA-final。
运行与核验入口：`scripts/stage3_evidence.py all`（复用已有control结果）、`scripts/stage3_report.py`、`scripts/formal_verify.py`、`scripts/stage3_verify.py`、`python -m unittest discover -s tests -v`。
最终机器可读质量记录见 `results/formal/stage3_quality_checks.json`，原始保护清单覆盖冻结协议、JB1、workloads、reference和Stage 2结果。Git提交与clean状态在交付时单独报告。
