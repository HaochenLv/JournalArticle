# 1. 一句话结论

**有明确 trade-off：JB1+减少了保守拒绝并提高部分推荐负载，但独立held-out中的乐观错误从7增至17，分区选择没有改善，原不安全推荐的违规请求反而从1/48增至9/48。不能作为更可靠的主evaluator替换JB1。**

# 2. 到底改了什么

以前：只要 Prefill 还活着，Decode 就背完整 Prefill compute debt。现在：按 JB1 自己的进度，仅把尚未执行完的 compute 算成未来 blocking；intrinsic H × input_tokens 仍完整保留。Raw/Legacy原有进度轨迹不变，没有拟合参数。

# 3. 原 conservative trace 有没有被直接缓解

原 h105/A100/fast/4.096、TTFT2/TPOT1 案例，在同一失败 epoch t=2.46484375 s，Raw blocking debt 从 1.547523291 s 降到 0.937171729 s，减少 0.610351562 s。Decode compute 为 0.112000 s；加 fixed .005 s 后，required TPOT 从 1.664523291 s 降到 1.054171729 s，仍超过 1 s。因此局部 full-service 高估被直接减轻，但这个 conservative verdict 没有被修复。Reference 最大 TPOT 0.945949720 s。

| request | full compute (s) | remaining fraction | remaining compute (s) | intrinsic (s) |
|---|---|---|---|---|
| azure-00002 | 0.76032 | 0.197244 | 0.149968 | 0.0779623 |
| azure-00003 | 0.64832 | 1 | 0.64832 | 0.060921 |

# 4. 有没有制造新的 optimistic errors

确实制造了新的optimistic errors。Phase A Raw为38→39、Legacy为31→32；两种语义新增的是同一个physical/SLA点：h101、shift−2、强度7.512097122、TTFT4.68/TPOT10。Reference TTFT=4.757223186 s，1/16请求超限；Remaining最大账面TTFT=4.593150197 s而接受。这个更紧TTFT条件不在Phase B范围内。Phase B更不能被描述成无新增风险：Raw和Legacy均7→17，每种语义各新增10个乐观标签，全部来自w202/TPOT5的两个强度(.256、.362038672)×五个shifts。两种语义共享这些10个physical/SLA点，不能相加成20个独立失败。新点/错误比例只描述自适应网格，非生产风险概率。

| Semantic pair | removed C | new O | safe→unsafe | capacity improved/worsened | new unsafe recommendations | removed unsafe recommendations | unsafe severity worsened |
|---|---|---|---|---|---|---|---|
| Raw | 307 | 1 | 0 | 59/0 | 0 | 0 | 0 |
| Legacy | 322 | 1 | 0 | 59/0 | 0 | 0 | 0 |

Phase B：

| Semantic pair | removed C | new O | safe→unsafe | capacity improved/worsened | new unsafe recommendations | removed unsafe recommendations | unsafe severity worsened |
|---|---|---|---|---|---|---|---|
| Raw | 72 | 10 | 0 | 30/2 | 0 | 0 | 1 |
| Legacy | 72 | 10 | 0 | 30/2 | 0 | 0 | 1 |

# 5. Existing six workloads 上发生了什么

Phase A仅为机制提出后的post-hoc diagnosis。

在相同的2050物理点×8个SLA上，每种variant有16400个配对标签。Raw C=1911→1604，Legacy C=2046→1724；分别减少307、322。Raw winner agreement=27/48→31/48，Legacy=32/48→33/48，但两种语义都有个别分区损失变差。Raw/Legacy不安全推荐仍分别4/48和2/48，另各4个弃权；两种语义的44个有定义loss场景与202个有定义capacity gap分母均保持不变。平均绝对capacity gap从34.59%→30.64%、35.86%→31.87%，总体中位数不变。A100补充对照复用130个物理点：C为9→7、20→18，O仍14、9；原乐观机制没有被修复。这些都是post-hoc diagnosis。

| Variant | O | C | paired | agreement / decisions | unsafe / abstain | gap median | mean absolute gap | partition loss | operating loss | safe loss |
|---|---|---|---|---|---|---|---|---|---|---|
| Raw-Full | 38 | 1911 | 16400 | 27/48 | 4/4 | 0.00% | 34.59% | 3.99% | 34.69% | 39.45% |
| Raw-Remaining | 39 | 1604 | 16400 | 31/48 | 4/4 | 0.00% | 30.64% | 2.77% | 31.65% | 36.41% |
| Legacy-Full | 31 | 2046 | 16400 | 32/48 | 2/4 | -2.14% | 35.86% | 3.32% | 35.88% | 36.10% |
| Legacy-Remaining | 32 | 1724 | 16400 | 33/48 | 2/4 | -2.14% | 31.87% | 2.68% | 32.82% | 33.04% |

# 6. New held-out workloads 上发生了什么

四个预冻结新负载完整执行500个物理点，正好达到硬上限，无失败、重试或超时。每种variant为500×4=2000个SLA配对标签、80条候选/SLA容量序列、16个部署决策。Raw C=225→153，Legacy=227→155，均减少72；O均7→17。16条决策的正确数量和mismatch类型完全不变；w202/TPOT10的selected从0变1，但二者本来都在reference-best集合内。新证据支持受测held-out上的保守分歧和平均利用率改善，同时直接证实安全性代价，不支持全面可靠性改善。37个未解决共同区间保留，最大相对宽度41.42%；不能把本结果当作精确连续边界。

| ID | seed | offset (3s bins) | duration(s) | link | requests | input mean/max | output mean/max |
|---|---|---|---|---|---|---|---|
| w201 | 201 | 1140 | 30 | fast | 13 | 804.77/1670 | 232.15/405 |
| w202 | 202 | 1150 | 120 | slow | 48 | 869.02/1992 | 245.98/605 |
| w203 | 203 | 1190 | 30 | slow | 5 | 804.80/1203 | 172.40/406 |
| w204 | 204 | 1200 | 120 | fast | 44 | 753.84/1854 | 217.95/591 |

| Variant | O | C | paired | agreement / decisions | unsafe / abstain | gap median | mean absolute gap | partition loss | operating loss | safe loss |
|---|---|---|---|---|---|---|---|---|---|---|
| Raw-Full | 7 | 225 | 2000 | 14/16 | 1/0 | 0.00% | 41.11% | 3.66% | 44.78% | 45.06% |
| Raw-Remaining | 17 | 153 | 2000 | 14/16 | 1/0 | 0.00% | 38.94% | 3.66% | 38.87% | 39.42% |
| Legacy-Full | 7 | 227 | 2000 | 13/16 | 1/0 | 0.00% | 41.31% | 9.91% | 44.78% | 45.06% |
| Legacy-Remaining | 17 | 155 | 2000 | 13/16 | 1/0 | 0.00% | 39.14% | 9.91% | 38.87% | 39.42% |

| Group | grid | added | unresolved | max width | stop |
|---|---|---|---|---|---|
| w201-heterogeneous-fast | 25 | 16 | 10 | 41.42% | 16-intensity budget |
| w202-heterogeneous-slow | 25 | 16 | 12 | 41.42% | 16-intensity budget |
| w203-heterogeneous-slow | 25 | 16 | 6 | 18.92% | 16-intensity budget |
| w204-heterogeneous-fast | 25 | 16 | 9 | 41.42% | 16-intensity budget |

# 7. Judgment 是否改善

保守错误下降，乐观错误增加，不能概括成单一‘accuracy提高’。Held-out新增变化全部发生在TPOT5/10：TPOT5 C=151→105但O=7→17；TPOT10 C=64→38且O保持0。TPOT0.3/1.2没有correction引起的标签变化。总量上Raw C减少32.0%、Legacy减少31.72%，但O增加10个；应并列报告工程后果，不能用减少的C抵消新增O。

Phase B四个SLA分别报告，不能将同一physical point的四个标签当作独立重复：

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

# 8. Capacity 是否改善

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

# 9. Partition decision 是否改善

Phase A的总winner agreement有所增加，但独立Phase B没有分区选择质量改善：Raw保持14/16（2个tie-break mismatch），Legacy保持13/16（2个tie-break、1个strict mismatch）。平均partition loss分别保持3.66%和9.91%。Raw/Legacy各只有w202/TPOT10从shift0变为shift1，reference-best包含二者，因此不能算修复错误。Phase A还存在反向变化：h103/TPOT5的partition loss约2.14%→12.19%；Legacy h105/TPOT10从agreement退化为tie-break mismatch，TTFT5.2和4.68两条件均如此。

# 10. Recommended operating-point safety 是否改善

推荐点安全性没有改善，而且一个已有不安全输出的严重程度变差。Phase B四个variants均有1/16个不安全推荐：w202/TTFT5.2/TPOT5，均选shift0且partition loss=0。Full推荐强度.181019336，1/48请求违规（2.08%），最大TPOT5.025706073 s；Remaining推荐翻倍到.362038672，9/48违规（18.75%），最大TPOT5.206560685 s。算术operating loss95.58%→91.16%，但safe loss仍100%。不能把更高的unsafe负载算成安全改善。另一方面，16个场景平均operating loss44.78%→38.87%、平均safe operating loss45.06%→39.42%，说明其他受测场景有利用率收益；这与安全代价同时成立。

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

# 11. Raw vs Legacy interaction

Legacy没有消除correction的held-out安全代价：两种语义都新增同样10个optimistic点，并在同一个推荐点从1/48违规变为9/48。Held-out的Full→Remaining变化量几乎重合；Legacy原有的w203/TPOT1.2 strict mismatch仍保留，partition loss达到99.90%。Phase A中Legacy会让h105原本正确的TPOT10选择退化，因此Raw的净winner改善不能直接外推成Legacy的统一改善。

# 12. 哪些原问题仍然存在

原 h103/A100/slow/.016、TPOT .15 案例中，Raw-Full 和 Raw-Remaining 均接受而 reference 拒绝；Legacy 两者均拒绝。减少 debt 没有修复 Raw 漏掉真实重叠的问题。Raw 请求13在1720.199600 s结束，reference为1721.840915 s，新请求14在1720.250000 s到达；同一语义的 Full/Remaining 完整轨迹一致，completion-time drift 仍存在。

h101名义relaxed reversal在Phase A共同网格上被消除：两种语义都从shift2改选shift0，reference-best为{0}；partition loss21.20%→0%，operating loss68.95%→40.54%。Remaining的E-best为{0,1,2}，由原tie-break选0，所以这是该网格上的agreement，不是严格恢复了所有候选排序。共同负载4.096的局部trace中shift0由拒绝变接受，shift2一直接受；该局部改善与最终采样选择一致，但不证明真实连续前沿已被恢复。

仅在指定 HELIX reference simulator、同一 Azure 生成分布、有限 trace、五个候选及采样网格内成立；没有真实GPU验证、连续capacity、安全前缀或普遍风险概率。Phase A是post-hoc，Phase B是四个新seed/非重叠源窗口的受限held-out，不是外部数据集验证。Source窗口按构造器循环，w204 offset1200对应原始bins0–39；只保证与h101–h106及本批其他窗口不重叠，未声称所有项目历史从未用过这些源bins。源token分布复用且workload/link/duration非完整交叉。Phase A沿用Stage4网格，未为Remaining重新细化，不能继承原Full边界精度；Raw/Legacy的Remaining分别有67/70个候选-SLA序列存在未达2.5%的已观测transition。Phase B网格由reference与四个variants的transition共同构造；未解决边界照实保留，没有发现的窄safe/unsafe岛不能排除。

协议冻结提交 e3887ca，hash `66375a5dab2941a70ee3111cd1f16f09d7e05fd32b440cf3759591b78e57afe2`。5867 个旧文件逐字节未变；41项测试通过。Full关闭模式逐字段一致（runtime除外），Stage4 Full记录原样复用；HELIX commit `8639497a4aaf1eb3b7594614cb0bbd376c1342b3`、adapter/profile不变。Phase A复用2050个异构点及130个A100点，新增reference=0。Phase B新增500个physical points、500次attempt、0次retry、0次timeout、0个failed point。四变体共享grid和reference truth，全部保留ties/no-safe/nonmonotone/unresolved；逐请求drain、SLA单调性和loss identity通过。

# 13. JB1+ 是否值得作为 journal 的主 evaluator

**B. Partial — keep JB1 as main object, use JB1+ as mechanism-guided correction.**

独立held-out支持机制作用和部分保守性/利用率收益，但新增optimistic errors、恶化的违规严重度、没有改善的partition selection，以及仍很大的capacity误差，均不支持把JB1+替换为更可靠的主evaluator。它适合作为预冻结、无拟合参数、保留反例的mechanism-guided correction实验。不是只有post-hoc有效的纯负消融，因此不选C；也不满足全面替换的依据，因此不选A。

# 14. 是否需要再开发 JB1++

**No。** 本次one-shot correction已经完成；不调参数、不增加第二个correction、不扩展矩阵。保留500点预算终点、37个未解决区间和全部负结果，不追加新workloads/SLA/profile/model，也不开发JB1++。本阶段仅交付experiment evidence，不写manuscript。

完整数据：[technical report](docs/JB1_PLUS_TECHNICAL_REPORT.md)、[summary](results/jb1_plus/summary.json)、[quality checks](results/jb1_plus/quality_checks.json)。
