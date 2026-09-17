# 正式证据报告 — Stage 3 修订冻结

日期：2026-09-17。范围：冻结协议 FI-JB1-v1、recovered JB1、固定版本 HELIX 参考模拟器。E 表示评估器，R 表示参考模拟；safe 仅表示对应模型及本次 SLA 下达标。第3–9节沿用Raw JB1结果，Legacy control独立见第15–16节，避免混用实现口径。

本报告对应已完成的14组、1634个物理运行、3268个SLA配对判断、35,688行profile stress和336行mitigation结果。原机195个保存结果逐项保留。主矩阵、后处理、完整核验及本机顺序计时均已完成；机制证据包括复用的保守案例和4个新增逐请求指标完全一致的追踪。可复核汇总：[research_review.json](results/formal/research_review.json)、[quality_checks.json](results/formal/quality_checks.json)。

## 1. 一句话结论

**主线 Yes, but modified：Raw JB1的tight-TPOT六场景全部选对，relaxed-TPOT六场景包含4个strict best-set mismatch和2个tie-break mismatch；Legacy 5 ms progress对照修复其中两场景，仍保留3个strict和1个tie-break mismatch。实现语义会改变具体结论，但没有消除误差向决策传导的现象。**

Stage 3仅新增3268次evaluator control判断，复用全部1634个physical reference records。完整写作交接见 [STAGE3_EVIDENCE_REPORT.md](STAGE3_EVIDENCE_REPORT.md)。Raw分区损失8.30%–26.16%，运行点损失68.95%–95.86%；h106实际推荐点R-unsafe，其安全可用损失为100%。参考验证只是在已用reference信息构造的冻结网格上的conditional replay，不能声称从零5次调用即可规划。

这里的“全部”仅限六个冻结工作负载，不是总体成功率或错误概率。贡献是参考模拟器约束下的可靠性诊断，不是新优化器或真实部署保证。

## 2. Baseline是否可信

**足以作为定义明确、可复核的实验对象；不足以声称恢复了原CA论文最终实现。** JB1的2051-token账本及24组轨迹检查已有审计。按raw-compute推进时，12组已发表采样边界均不匹配；将旧5ms固定开销放回进度后恢复12/12。这个差异已公开，不通过改模型追数字。

冻结基线SHA256为 `4f186748f3fb5940179e833ffe68cf463bb8b9d1dbbd16926490062065669b15`；协议hash为 `75120a5593b7c9574fe5bb3b21c3172179b95700955464d6aada0d12f04024bf`。本阶段没有改变冻结模型、workload或共同网格规则。Windows迁移短trace与旧缓存的逐请求指标和判定完全一致，新增解释性追踪也通过指标一致性门槛。HELIX目录在固定commit上保持干净，adapter文件逐字节匹配固定git对象。

未找到的原始最终源码和历史测试包继续列为复现边界，不再开展代码考古。详见 [BASELINE_IMPLEMENTATION_AUDIT.md](docs/BASELINE_IMPLEMENTATION_AUDIT.md) 和 [CLAIM_BOUNDARY.md](docs/CLAIM_BOUNDARY.md)。

## 3. RQ1：什么时候判断对、什么时候判断错

六个新seed/window为101–106；每个负载的请求数分别为16、54、15、81、14、49，原始窗口为30/120秒。强度改变到达时间尺度，实际模拟结束时间不限定为该窗口长度。异构主比较为六负载×五shift×两SLA，另含两个反向链路anchor及六个A100控制，共76个配置/SLA。链路与时长并非完整交叉设计。

| 类型与SLA | E/R均safe | E safe、R unsafe | E unsafe、R safe | E/R均unsafe | 配对分母 |
|---|---:|---:|---:|---:|---:|
| 异构 tight-TPOT | 209 | 1 | 0 | 1294 | 1504 |
| 异构 relaxed-TPOT (fixed TTFT) | 656 | 8 | 404 | 436 | 1504 |
| A100 tight-TPOT | 26 | 1 | 2 | 101 | 130 |
| A100 relaxed-TPOT (fixed TTFT) | 62 | 13 | 7 | 48 | 130 |
| 合计 | 953 | 23 | 413 | 1879 | 3268 |

异构两SLA的TTFT限制均5.2s，TPOT分别0.30s/10s；A100的TTFT均2s，TPOT分别0.15s/1s。展示标签按TPOT阈值命名，不预设首先触发的约束属于Prefill；冻结JSON key `prefill`及原协议文档保留原样。

2832/3268个判定一致，23个乐观分歧，413个保守分歧。E接受976个点，其中23个被R拒绝（2.36%）；R接受1366个点，其中413个被E拒绝（30.23%）。后者主要集中在异构relaxed-TPOT (fixed TTFT)。A100的乐观分歧占其E接受点14/102，不能被异构大分母稀释。

这些是自适应边界采样的描述性比例，不是部署流量上的风险估计；同一物理运行对应两个SLA，不能把3268当作独立重复实验数。运行失败、保存尝试中的timeout及重试均为0。人工资源切换中未保存的中断不产生unsafe标签，不能据此声称执行从未中断。

## 4. RQ2：容量预测错多少

容量定义为**共同网格中最大观测safe强度**。相对误差为 `(Emax−Rmax)/Rmax`；强度是负载倍率，不直接等于requests/s。

76个配置/SLA中68个有可计算的有限误差：31个负、32个零、5个正，中位数0。范围为 **−95.86%到+182.84%**，所以总体中位数会掩盖两类SLA的系统差异。

最大正误差出现在h103/A100/relaxed-TPOT (fixed TTFT)；最负值出现在h106/异构/relaxed-TPOT (fixed TTFT)/shift2，其R序列非单调，只能按最大采样safe点描述。另一个单边界支持案例h105/A100/relaxed-TPOT (fixed TTFT)达到−95.18%。

8个配置在E和R中均无采样safe点，未以零误差混入平均值；65个配置同时满足两个模型的单边界支持条件。3个R序列非单调：h102/A100/tight-TPOT，以及h106/异构/relaxed-TPOT (fixed TTFT)的shift1和shift2。E非单调为0，E/R右删失均为0。已定义的最大safe到最近更高unsafe的相对间距最大2.190%，没有超过冻结2.5%目标。对非单调序列，即使这个局部间距很小，也不能宣称得到连续容量界。

详见 [容量表](results/formal/rq2_capacity/summary.csv)；全safe/unsafe序列和标志保留在对应JSON中。

## 5. RQ3：误差是否导致partition选错

**确实会，而且取决于SLA。** 六个tight-TPOT主场景均选中R最优候选，所选候选的E/R最大safe强度一致。六个relaxed-TPOT (fixed TTFT)主场景均选偏，其中h101–h104为strict best-set mismatch（最佳集合不相交），h105/h106为tie-break mismatch（最佳集合有交集但tie-break选偏），不是6个strict ranking reversals：

| 工作负载 | E所选shift | R最优shift集合 | 所选候选R名次 | R容量损失 |
|---|---:|---|---:|---:|
| h101 | 2 | {0} | 4 | 21.20% |
| h102 | 1 | {0} | 2 | 8.30% |
| h103 | 2 | {0} | 3 | 12.19% |
| h104 | 2 | {0,1} | 3 | 10.26% |
| h105 | 0 | {1} | 2 | 10.26% |
| h106 | 1 | {2} | 2 | 26.16% |

损失定义为 `1−Rmax(E所选)/max候选Rmax`，六场景中位数11.23%。它衡量“选哪个候选”的损失，与E直接推荐的运行负载可能不safe是两个指标。

h101给出清楚的真实反转：E认为shift2容量4.096高于shift0的3.838295；R却给shift0容量13.193137、shift2容量10.396065。所有候选使用相同51点网格，因此这不是候选各自细化造成的偏差。

Tie规则保持“绝对shift最小，再负shift优先”。h102、h105、h106存在E最佳集合并列；h104存在R最佳集合并列。h105尤其说明高整体排序相关性仍可能选错第一名：Spearman约0.894，但tie规则选出的shift0不在R最佳集合。h106非单调，因此26.16%是最大采样safe点意义下的描述，不是稳定运行容量损失保证。

每个场景的分数向量、并列集合、参考最优与第二名差值、相关系数见 [决策表](results/formal/rq3_decision_transfer/summary.json)。不将12个确定性场景视作总体错误概率。

## 6. RQ4：profile mismatch影响

参考历史完全冻结，仅改变E的Prefill/Decode计算profile；不扩展有利场景的专用网格。共35,688行，错误0。下表每行均在同一3268配对点上比较：

| 条件 | 乐观分歧 | 保守分歧 | 正确选择R最优的主场景 |
|---|---:|---:|---:|
| Nominal | 23 | 413 | 6/12 |
| Both −5% | 264 | 297 | 9/12 |
| Both −10% | 324 | 279 | 3/12 |
| Both −20% | 395 | 253 | 3/12 |
| Prefill −10% | 195 | 279 | 8/12 |
| Decode −10% | 150 | 403 | 1/12 |

Both−10%的E接受点中有324/1411（22.96%）被R拒绝，较名义23/976明显增加。它改变10/12个场景的所选shift，并使原本正确的6个tight-TPOT选择全部变错；同时修复了3个名义relaxed-TPOT (fixed TTFT)错误，因此净正确数为3，而不是0。Both−5%甚至提高正确候选数，同时大幅增加乐观分歧：**选择质量与判定安全性不能互相代替。**

L4x2-only−10%仅适用于异构3008个配对点，乐观235、保守295，选择正确8/12；不可把这个分母与包含A100的3268混用。受检主决策stress条目没有E右删失或E非单调，但h106等R非单调限制仍继承。其余5/10/20%组合完整保留于 [stress汇总](results/formal/rq4_profile_mismatch/summary.json)。这些是受控确定性扰动，不是对真实GPU噪声分布的推断。

## 7. 主要机制

**保守机制：全额active-Prefill阻塞账本。** 复用h105/A100保守追踪。在2.464844s，E/R均为2 Prefill+2 Decode；E账本把1.547523s阻塞、0.112s计算与0.005s固定开销相加为1.664523s，超过1s TPOT。R最大TPOT只有0.945950s。该例不用并发计数错误就能解释E拒绝；不能由此断言删除阻塞项普遍安全。

**乐观机制：完成时间漂移使实际重叠从E状态中消失。** h103/A100、强度0.016、TPOT0.15s：E最大账面TPOT0.117367s而接受，R最大TPOT1.103934s而拒绝。E认为请求13在1720.199600s结束，新请求14于1720.250000s到达；R中的请求13实际到1721.840915s才结束。E在新到达后看到1 Prefill/0 Decode，R实际上为1 Prefill/1 Decode。违规迭代物理跨度1.098934s，80层执行区间仅合计0.112059s；剩余时间没有强行归因于唯一队列或网络机制。

单案例E-only消融将5ms放回进度后，请求13延后到1722.964600s结束，恢复该重叠且判定变为unsafe。不过首个失败发生在另一个更早请求，故它证明语义敏感性，不能当作已验证修复，更没有替换名义结果。

**大误差但winner稳定：原机制trace明确来自Raw stress。** Raw名义主场景没有“大所选容量误差且选对”的实例。h103/relaxed-TPOT (fixed TTFT)在Both−5%和Both−10%都选中R最优shift0；Both−10%的Emax2.896309对Rmax9.741985，误差−70.27%。强度4.096的追踪中，E账本10.831892s超过10s，而R最大TPOT4.478798s。此处同时有阻塞账本和阶段占用差异，无法隔离唯一原因。不得把这个stress例写成Raw名义稳定成功。Stage3的Legacy名义h104/h105另有正确winner和大运行点损失，见第16节，不能与原Raw trace混同。

**真实反转的局部证据。** h101在共同强度4.096，shift0 E拒绝/R接受，shift2 E/R均接受。shift0首次账本为9.822287s阻塞+0.232s计算+0.005s开销=10.059287s；shift2最大账本为9.953235s。微小账本差异跨过E阈值，而R两候选的最大TPOT均约4.5s。共同网格证实后续容量排序反转；这两个局部trace说明E为何提前偏向shift2，但没有完整隔离R更高负载下反转的排队因果链。

详见 [机制分析](docs/MECHANISM_ANALYSIS.md)、[五例汇总](results/formal/mechanisms/summary.json) 及逐请求trace。所有案例均为观察结果后选择的解释案例，不是代表性随机样本。

## 8. 意外结果

第一，总体容量误差中位数为0，却不能阻止六个relaxed-TPOT (fixed TTFT)场景全部选偏。第二，固定方向的profile低估可能改善候选排序，却恶化所推荐运行点的达标性。第三，名义上小的乐观点数23掩盖了E直接推荐输出中5个不safe的结果。第四，统一25%计算裕量与四场景控制在本数据上输出相同，额外四倍E调用没有带来已观察到的收益。

三个非单调R序列也提醒：不能把“强度降低”自动等同于“变得safe”，所以20%-target负载降额（含grid snapping）并不保证消除乐观输出。

## 9. Practical mitigation是否有必要

**有必要保留一个简单、明确的参考验证环节；没有证据支持复杂新优化器。** 每个policy/bias有28个物理组/SLA决策，其中26个存在非零R oracle；质量均值只在这26个上计算，失败推荐或弃权记可用负载0，两例无R-safe点保持未定义。

表内“错误/弃权”计数保留全部28个决策；质量为安全可用负载除以最佳测试参考负载。R调用是对冻结oracle的回放计数，不是额外执行了这么多新模拟。 **这是一项conditional reference-validation replay on the frozen grid：网格构造已使用reference transition信息，构造成本不计入最多5次的post-selection回放预算，不能解释为从零planning预算。**

| 策略 | 名义：不safe输出 / 弃权 | 名义平均可用质量 | Both−10%：不safe / 弃权 | Both−10%平均可用质量 | R调用：名义 / stress |
|---|---:|---:|---:|---:|---:|
| E-only | 5 / 2 | 55.33% | 20 / 0 | 7.97% | 0 / 0 |
| 25%计算裕量 | 0 / 18 | 12.05% | 1 / 10 | 31.90% | 0 / 0 |
| 20%-target derating with grid snapping | 2 / 2 | 34.41% | 5 / 0 | 44.67% | 0 / 0 |
| 四场景控制 | 0 / 18 | 12.05% | 1 / 10 | 31.90% | 0 / 0 |
| 所选点R验证 | 0 / 7 | 55.33% | 0 / 20 | 7.97% | 26 / 28 |
| 所选分区边界R验证条件回放（最多5次查询） | 0 / 4 | 71.37% | 0 / 8 | 70.00% | 130 / 140 |

每策略每bias的基础E调用为3268，四场景为13072。单点验证最多1次，边界验证最多5次/决策；跨SLA复用的唯一物理query数另列在 `research_review.json`，不把逻辑调用与唯一模拟次数混为一谈。

对全部56个降额case的审计显示：nominal实际降幅21.20%–79.87%，中位46.53%（26/28有定义）；Both−10%为21.20%–78.98%，中位26.09%（28/28）。h101/tight推荐0.0099348625→目标0.00794789→网格输出0.004，实际降低59.74%。取整后重新tie-break还改变8/28个nominal分区，不能描述成固定原分区的纯20%降额。详见 [mitigation审计](docs/MITIGATION_INTERPRETATION_AUDIT.md)。

单点验证能拒绝不安全推荐，但本身不恢复因保守偏差损失的负载；边界验证在所选分区附近找到了更高的可验证负载。它不跨分区重新优化，也不保证选到全局或本候选集最佳分区。验证策略的0不safe输出由“只返回实际验证safe点”的规则决定，是本oracle下的工程属性，不是独立泛化证明。没有进行新策略与强reference-only算法的预算匹配竞赛，因此不主张算法优越性。

## 10. 是否足够支撑Future Internet

**Yes, but modified——足以支撑范围受限、明确实现语义敏感性的经验研究稿件。** 判断依据是：冻结的新负载共同网格、完整分母和失败审计、从判定到容量再到决策的可复核链条、受控stress、指标一致的机制追踪，以及保留负结果的简单工程控制。

这不等于验证了文献新颖性、真实GPU适用性或保证录用。主要风险是研究对象仅为明确恢复的JB1、参考真值来自HELIX而非实机、候选家族有限、六窗口及链路设计不完整。若论文改成“通用LLM部署安全保证”或“新调度优化方法”，现有证据不足。本阶段不写完整论文。

## 11. 唯一推荐的journal contribution

**Reference-Grounded Reliability Assessment for SLA-Aware Capacity and Partition Planning：用冻结共同负载网格揭示便宜评估器的判定误差何时会、何时不会转化为容量与分区决策损失，并给出有限参考验证的实际边界。**

主贡献是可复核的可靠性评估流程和条件性实证发现。基线恢复审计、机制追踪和六种简单控制提供支撑，不各自包装成新算法贡献。

## 12. 最小充分图表集合

建议正文保留四张主图和一张两面板机制图：

1. [判定混淆计数](results/formal/figures/01_reliability.png)：四种类型/SLA，明确自适应采样分母。
2. [采样容量比较](results/formal/figures/02_capacity.png)：Emax对Rmax，非单边界案例单独标记；八个无safe点配置在表中保留。
3. [决策及stress热图](results/formal/figures/03_decision_stress.png)：展示排名变化与参考质量，避免只报winner正确率。
4. [mitigation质量](results/formal/figures/04_mitigation.png)：图中仅12个五候选主场景，与第9节28个全部场景的表区分；弃权和错误输出计数配表呈现。
5. [乐观时间线](results/formal/figures/optimistic_h103_a100_timeline.png) 与 [保守时间线](results/formal/figures/conservative_h105_a100_timeline.png)：构成机制对照。反转trace及完整网格放补充材料。

图已逐张检查并修正标题/坐标裁切及晚到请求的时间窗口选择。SVG同时提供；所有数字来自已保存结果。

本机独立顺序计时另用小表即可：

| 预声明负载 | E中位数 | R中位数 | R/E规划时间比 |
|---|---:|---:|---:|
| h101，16请求 | 7.476ms | 9.932s | 1328.6 |
| h102，54请求 | 28.470ms | 39.547s | 1389.1 |

各模型1次warmup；E重复10次、R新鲜运行3次，R指标与缓存一致。在Windows/Python3.12.10、20逻辑CPU、约32GiB主机上，主矩阵并行进程退出后执行。只说明这两个案例的CPU规划计算差异；不混入笔记本并发wall time，不称为GPU推理加速，也不由此推导整个mitigation策略的端到端加速。

## 13. 仅真正必要的缺失实验

**No further experiments needed：Stage 3要求的Legacy sensitivity、decision-loss decomposition与mitigation口径审计也已完成。** RQ1–RQ4、六种mitigation、完整核验、绘图、主机顺序计时以及要求的机制类型均已覆盖。

剩余的是明确的解释边界：局部反转trace未隔离高负载参考排序的完整因果链；Raw stress稳定winner案例不能替代一个不存在的Raw名义实例。这些应作为限制写清，不为填补故事而增加无必要实验。只有下一阶段改变主张时才需要新增证据：主张实机有效需实机验证；主张新优化器优于参考搜索需新的预算匹配比较；主张普遍风险概率需独立采样设计。本阶段不启动这些扩展。

## 14. 下一阶段建议

以本报告为依据决定是否进入论文写作，保留“recovered JB1、HELIX-relative、tested candidate family、sampled capacity”四个限定。优先组织RQ3的条件性决策差异，再用RQ1/RQ2解释其来源，用stress与验证控制说明实际使用边界。把所有错误、弃权、ties、非单调和未定义质量一起报告。

不要更改已冻结结果来提升故事强度，不再追寻缺失历史最终代码，不新增optimizer。写作提纲与交接包已经准备好，后续对话负责正文。本阶段停止实验，原研究监控保持暂停。

## 15. Stage 3：Legacy进度敏感性最终结果

Raw源码与原reference/raw标签、冻结协议均未改变。仅通过已有开关使5 ms进入进度，queue overhead断言为0，其余设置不变。3268个判断中53个safe→unsafe；O由23降至17，C由413升至460。Raw/Legacy分别有68个有限capacity gap，median为0/−15.91%，最大正gap182.84%/165.05%；均8个no-safe、0 evaluator nonmonotone、0 right-censored。Reference3个nonmonotone保留。Legacy网格不另行细化，其边界精度不自动继承Raw的2.5%目标。

Tight-TPOT均6/6 winner正确，Legacy推荐负载均低约2.14%。Relaxed下h101/h103 strict保留，h102仍strict且shift1→2使regret8.30%→14.07%；h104 strict消失、h105 tie-break消失，h106 tie-break保留。Raw的4 strict+2 tie变成Legacy的3 strict+1 tie；平均relaxed分区损失14.73%→12.27%，不能称为全面修复。

详细分层计数、compact decision table和76配置完整容量序列见 [LEGACY_PROGRESS_SENSITIVITY.md](docs/LEGACY_PROGRESS_SENSITIVITY.md) 与独立结果目录。结论部分依赖实现语义；legacy不是已确认CA-final代码，Raw profile stress也不能自动外推到legacy。

## 16. Stage 3：Partition loss与operating-point loss

令B为reference-best sampled capacity、S为E所选partition的reference sampled capacity、L为E推荐强度。Partition loss=1−S/B；operating-point loss=1−L/B；两者不相加，因为后者已包含前者。可加分解为(1−S/B)+(S−L)/B。另报safe operating-point loss，将实际R-unsafe输出或弃权的可用负载记0。

Raw relaxed的partition loss8.30%–26.16%，而operating-point loss68.95%–95.86%。h106的0.2297227616推荐实际R-unsafe，safe operating-point loss=100%。它的所选分区有更高safe点4.096，不能从该点推断低负载safe。Raw/Legacy主推荐均为11 safe/1 unsafe。

Legacy h105虽选对分区，但最终推荐仍5.0866495983，对R-best41.5842617652，operating-point loss仍87.77%；h104 winner修复但operating-point loss81.94%→82.32%。这比只报告winner或partition regret更完整。
详见 [DECISION_LOSS_DECOMPOSITION.md](docs/DECISION_LOSS_DECOMPOSITION.md)，逐场景包含best-set overlap、rank、ties、no-safe、nonmonotone与精确标签；JSON另保留144个mitigation主场景输出分解。
