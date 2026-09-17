# 1. 一句话结论

中间SLA进一步支持Stage 3主线，但误差不是越放宽越大：TPOT 5的容量低估和推荐负载损失比10更严重；选对分区甚至表面运行点损失为0，都不能替代推荐点的实际安全检查。

# 2. 这轮到底补了什么

Stage 4是Stage 3之后设计的 controlled parameter sensitivity study，使用同一组六个held-out workloads，不是新的独立held-out generalization test。48 workload-SLA条件不是48独立workloads。仅改变八组TTFT/TPOT阈值；没有新增模型、GPU、network、workload、profile stress、候选或算法。

JB1是journal明确指定的lightweight SLA-aware evaluator；Legacy是implementation-semantic sensitivity control。已撤回且从未公开/出版的AICCC稿不是prior publication。本阶段不寻找所谓final implementation。已accepted的 Evaluator-Guided SLA-Aware Layer Partitioning for Heterogeneous LLM Pipelines 是应区分的prior work；5-shift、evaluator-as-score和原partition search不是journal新增贡献。新增价值仅为SLA-regime sensitivity evidence。

# 3. 是否需要新的 HELIX runs

需要，用于新SLA边界的共同网格细化。复用1,450个原physical points，未重跑这些HELIX点。新增unique physical points=600，成功=600，physical attempts=600，retry=0，timeout=0，最终failed=0。Evaluator实际保存32,800次重新调用结果，其中原grid23,200次、新grid9,600次。Reference分类16,400次；Raw/Legacy共享物理真值。

| 负载 | 原grid | 最终grid | 新增强度 | 新增物理点 | 有新增轮数 | 未解决interval | 停止原因 |
|---|---|---|---|---|---|---|---|
| h101 | 51 | 75 | 24 | 120 | 4 | 12 | 24-intensity budget |
| h102 | 53 | 77 | 24 | 120 | 3 | 6 | 24-intensity budget |
| h103 | 46 | 70 | 24 | 120 | 6 | 0 | no unresolved transition |
| h104 | 41 | 52 | 11 | 55 | 6 | 0 | no unresolved transition |
| h105 | 49 | 73 | 24 | 120 | 3 | 9 | 24-intensity budget |
| h106 | 50 | 63 | 13 | 65 | 5 | 0 | no unresolved transition |

# 4. TPOT sensitivity 总体趋势

固定TTFT=5.2时，Raw的winner agreement依次为6/6、6/6、5/6、3/6、3/6、0/6；Legacy为6/6、6/6、6/6、4/6、3/6、2/6。计数变化不是完整故事：h101在2.4为strict mismatch、5恢复agreement、10再次strict；h102 Raw在1.2/2.4发生tie-break mismatch、5恢复agreement、10再变strict。运行点损失在5达到很高水平，10时多数反而下降，不能写成随TPOT放宽单调恶化。

各SLA分母是同一最终workload-level common grid上的点数，计数不是生产错误概率。

# 5. Judgment reliability

RQ-S1：存在明显但非单调的变化。六个TPOT下Raw O依次为1、1、2、2、23、8，C为0、50、0、139、803、600（每格分母2050）；Legacy O为0、0、0、0、23、8，C为26、76、24、163、804、608。0.6→1.2时保守分歧下降，5→10时O和C同时下降。Raw在1.2仅2个O点，却包含h102的实际推荐；低总体分歧计数不能替代输出点检查。

O=E safe/R unsafe；C=E unsafe/R safe。

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

# 6. Capacity error

RQ-S2：没有贯穿所有SLA/候选的同一误差方向。Raw在0.3/0.6/1.2/2.4的相对gap中位数均为0，但0.6已有5个负gap，2.4已有10个负gap且最小达−99.81%；正gap在这些阈值仍存在。TPOT5的27个有定义候选gap全部为负，中位−95.08%；到10中位回升至−75.00%。Legacy在较紧TPOT通常更保守，而5/10的gap中位数与Raw相同。240条去重后的reference候选/SLA序列（并非独立随机样本）保留38个no-safe、23个nonmonotone、0个right-censored；不能把中位数或最大safe当成连续安全容量。

gap=(Emax-Rmax)/Rmax；只对两者容量有定义的条目计算，no-safe不填0。largest observed safe只是采样容量。

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

# 7. Partition decision

RQ-S3：最终网格上，最早的Raw mismatch出现在TPOT1.2的h102，是best sets有交集但tie-break选出−1、reference-best仅−2的情况；2.4继续保留。首个strict mismatch出现在2.4的h101和h105（两种语义均如此）。h103在5开始strict；h106在5开始tie-break；h104 Raw到10才strict，而Legacy在TTFT5.2的六个TPOT均agreement。出现/消失/再出现并存，不存在本实验支持的统一critical TPOT阈值。

A=agreement；S=strict best-set mismatch；T=tie-break mismatch；N=no-safe recommendation；R=no-safe reference；F=incomplete reference。N仍保留reference-best和B，B=0时relative quality全部undefined。

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

| 负载 | 语义 | 首个观测mismatch TPOT | 六个TPOT决策序列 |
|---|---|---|---|
| h101 | raw | 2.4 | A → A → A → S → A → S |
| h101 | legacy | 2.4 | A → A → A → S → A → S |
| h102 | raw | 1.2 | A → A → T → T → A → S |
| h102 | legacy | 10 | A → A → A → A → A → S |
| h103 | raw | 5 | A → A → A → A → S → S |
| h103 | legacy | 5 | A → A → A → A → S → S |
| h104 | raw | 10 | A → A → A → A → A → S |
| h104 | legacy | 未观察到 | A → A → A → A → A → A |
| h105 | raw | 2.4 | A → A → A → S → T → T |
| h105 | legacy | 2.4 | A → A → A → S → T → A |
| h106 | raw | 5 | A → A → A → A → T → T |
| h106 | legacy | 5 | A → A → A → A → T → T |

# 8. Partition loss vs operating-point loss

RQ-S4：两层损失在中间SLA仍显著不同。TPOT5时Raw和Legacy的平均分区损失仅2.43%，平均运行点损失却为94.90%（范围90.57%–97.93%）；h101、h102、h104虽然选对分区，运行点损失分别94.97%、95.86%、95.58%。TPOT2.4的h105分区损失19.48%，Raw运行点损失99.79%。更关键的是h102在TPOT1.2/2.4：Raw的B=L=0.0108340444，S=0.0106018931，partition loss=2.14%，allocation=−2.14%，所以算术operating loss=0%；但所选shift−1的该点有3/54请求违反TPOT，safe loss=100%。Legacy选shift−2，同一推荐强度实际safe，safe loss=0%。

B为reference-best sampled capacity，S为所选partition的reference sampled capacity，L为推荐强度。1-L/B=(1-S/B)+(S-L)/B；不能把partition loss与operating loss相加。下表各均值只纳入对应量有定义的workload，逐项分母与undefined见完整表。

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

unsafe推荐的safe usable load=0，safe loss=100%（B>0）；这是该推荐点的safety-adjusted metric，不表示较低负载均unsafe或safe。

| 负载 | SLA | 语义 | 违反请求 / 总数 | fraction | 最大TTFT超限(s) | 最大TPOT超限(s) | 类型 |
|---|---|---|---|---|---|---|---|
| h102 | TTFT5.2_TPOT1.2 | raw | 3 / 54 | 5.56% | 0 | 3.54843 | TPOT only |
| h102 | TTFT5.2_TPOT2.4 | raw | 3 / 54 | 5.56% | 0 | 2.34843 | TPOT only |
| h106 | TTFT5.2_TPOT5 | raw | 7 / 49 | 14.29% | 0.0292473 | 0.236598 | both |
| h106 | TTFT5.2_TPOT5 | legacy | 7 / 49 | 14.29% | 0.0292473 | 0.236598 | both |
| h106 | TTFT5.2_TPOT10 | raw | 1 / 49 | 2.04% | 0.0292473 | 0 | TTFT only |
| h106 | TTFT5.2_TPOT10 | legacy | 1 / 49 | 2.04% | 0.0292473 | 0 | TTFT only |

# 9. Raw vs Legacy

RQ-S5：判定差异在TPOT0.3/0.6各27个标签、1.2/2.4各26个、5仅1个、10为8个；最大判定差异不对应最大选分区差异。TPOT5时两种语义的六个selected shifts、决策类型、两类主loss均相同，仅一个非推荐候选点标签不同，差异近乎消失。TPOT10的selected差异最大（3/6）：Legacy修复h104/h105的winner，但h102分区损失由8.30%增至14.07%，h106仍选偏且不安全。最大安全调整损失差出现在h102的1.2/2.4，Raw100%对Legacy0%；Legacy在这些条件有益，但不能称为全局改善。

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

# 10. TTFT 5.2 → 4.68 的影响

RQ-S6：收紧到4.68后，h102和h106在两组受测TPOT下均无任何采样reference-safe候选，E也弃权；B=0，所有relative quality未定义，不能把其消失的不安全推荐算作性能改善。剩余四个负载在TPOT1.2均agreement。在TPOT10，Legacy h104由agreement变成tie-break mismatch（selected仍0，R-best从{0,1}变为{1}），分区loss升至4.24%；h103两语义的运行点loss由70.91%升至75.00%，而h101/h104/h105的对应运行点loss下降。变化并非同向，4个有定义场景的均值也不能直接当作原6场景均值的改善。

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

# 11. 新增 grid refinement 是否改变 Stage 3 原结论

没有改变。24条原端点语义决策（6 workloads×2旧SLA×2 semantics）的selected shift、evaluator/reference best sets和mismatch类型全部保持。TTFT5.2/TPOT0.3两语义仍6/6一致；TPOT10仍为Raw4 strict+2 tie-break，Legacy3 strict+1 tie-break+2 agreement。扩大grid改变了采样分母和judgment计数，不能据此重写原Stage 3计数。

原grid一致性gate全部通过；以下仅报告新grid的resolution sensitivity，不覆盖Stage 3历史结论。

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

# 12. 中间 TPOT 最重要的发现

最重要的补充不是简单的中间插值，而是三类可分离现象：h102在1.2/2.4出现‘算术运行点loss为0但推荐unsafe’；h101在2.4→5→10的分区决策非单调；TPOT5出现大量‘选对分区但推荐负载严重不足’的Raw和Legacy名义案例。这些直接支持同时报告judgment、sampled capacity、partition decision和exact operating-point safety。

# 13. 是否发现明显 transition

有离散条件间的明显transition：Raw从1.2首次出现tie-break mismatch，两语义在2.4出现strict mismatch，5时保守分歧和运行点损失显著增大；但5→10的容量低估中位数和多数运行点损失反而缓解，部分winner又恶化。各负载的起点、方向和实现依赖不同，不支持单一阈值或普遍单调规律。

这些是tested workloads/configurations中的离散阈值对比，不能宣称universal critical TPOT threshold；连线不推断未测SLA。

# 14. 哪些结论仍受 resolution 限制

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

# 15. 最终对 journal story 的影响

**strengthens current story**。受控中间SLA补强了judgment reliability→sampled capacity error→deployment decision error这条证据链，并提供Raw名义‘winner正确但运行点损失巨大’和‘算术loss为零但unsafe’的新案例；同时明确SLA变化非单调、具体排序受progress语义和grid resolution影响。保留simulator-relative、同六workloads、五候选和共同采样grid的限定，不引入新算法或独立泛化主张。

2459 个Stage 2/3保护文件哈希未变；协议hash `ac61d6e30a9b19823bf8ff595feaf7bdf935ebd72206a712ab001e4968dc3f8b`。18项要求及附加核验通过：原grid标签/决策、输入与profile/partition/network、依赖源、共同grid、SLA单调性、逐请求全drain、失败/重试、全八SLA、完整分母、ties/no-safe/nonmonotone/unresolved、loss identity。36项单元测试通过。

新增正文候选图仅一张：[decision type + loss](results/sla_sensitivity/figures/sla_sensitivity.png)，同时提供SVG。技术细节、96行完整决策和所有序列见 [technical report](docs/SLA_REGIME_SENSITIVITY.md) 与 results/sla_sensitivity/。

# 16. 是否需要继续实验

**No**。本轮协议已完整执行并通过质量核验，足以支持上述受限的参数敏感性结论；27个未解决区间作为明确限制公开，不为使曲线更好看或给出连续critical threshold追加预算。本阶段不再开展任何新增模型、负载、网络、profile、SLA或算法实验。
