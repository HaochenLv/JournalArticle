# 1. 一句话结论

首选写一篇“快评估器的安全判断、容量估计和分区选择到底有多可靠”的实证论文；目前不要把复杂鲁棒优化或新的 reference 调用分配算法作为核心创新。

# 2. 今晚到底发现了什么

1. 两篇 accepted CA 和 reviewer form 已完整阅读；两份旧仓库的核心实现、实验历史、测试、结果及 HELIX 调用链已审计，旧仓库保持只读。
2. HELIX reference 是 CPU 上运行的离散事件模拟器，不是真实 GPU 执行。
3. 关键复现成立：2051-token 反例、正常 workload、12 组已发表 evaluator 边界端点，以及第二篇 20-seed 九候选主要结果均恢复。
4. 在恢复实现上，nominal 误差是 mixed：175 个 A100 配对点有 13 个 optimistic、22 个 conservative disagreement。
5. 固定 reference 后，仅低估 evaluator 的 compute profile，就会增加 optimistic disagreement；但这不能解释已经存在的 nominal 结构误差。
6. nominal 分区选择比绝对容量稳定：四组五候选试验，按既定 tie-break 选出的候选都属于 reference-best 集合。
7. 四场景检查没有超过简单的 25% compute inflation；停止这条方法路线。
8. 更强基线推翻了初步规划算法优势：在同一粗网格上，只验证均匀分区的 reference-only 方法用 5 次调用就达到四组网格最优，evaluator-seeded 方法需要 10 次。不能据较弱基线包装新算法。

# 3. HELIX reference 到底是什么

统一称 **HELIX reference simulator**。固定 commit `8639497a4aaf1eb3b7594614cb0bbd376c1342b3`；adapter 建立固定路由和 pipeline，调用上游批处理执行策略与计算/网络事件模拟，drain 全部请求后解析指标。没有加载模型权重、CUDA 推理或真实集群。

新诊断中，两端共享 absolute per-layer profile、相同 workload/partition/network。aligned TTFT 是 Prefill 完成减到达加 5 ms；native TTFT 另含首个 Decode 完成。TPOT 判断所有 Decode iteration 的最大值，不是平均数或 p95。固定 overhead 和 intrinsic Prefill charge 分别处理。第二篇旧模型只使用 HELIX 相对速度比例缩放 analytical compute，必须与新 matched-profile 诊断分开。

第一篇最终 accounting-only 源码/40-test snapshot 未在公开分支找到。本次恢复 ledger 可复现关键数值，但公开 event engine 的 fixed-overhead progress、post-event 检查及 memory 项与最终论文描述存在差别；不能把新失败直接归到不可见的最终实现。

# 4. Nominal evaluator vs reference

十组 A100、175 个同输入配对点：68 both-safe、72 both-unsafe、13 optimistic（E safe/R unsafe）、22 conservative（E unsafe/R safe）。全部十组都扩展到了 reference 自己的不安全点。

下表是**最大已观测 safe intensity**，不是连续容量或稳定吞吐量。每个 workload 只有 17 个请求，intensity 压缩其到达间隔。

| 条件 | E 最大 safe | R 最大 safe | 下一 R unsafe |
|---|---:|---:|---:|
| seed0，慢/快链路，原 Decode SLA | .015 | .015 | .01625 |
| seed7，慢链路，原 Decode SLA | .01315 | .0132 | .01365 |
| seed7，快链路，原 Decode SLA | .01315 | .01365 | .0141 |
| seed19，快链路，原 Decode SLA | .015 | .04 | .05 |
| seed0，放宽 Decode 至 1 s | .8 | .0325 | .03625 |
| seed7，放宽 Decode 至 1 s | .04 | .0132 | .01365 |
| seed0，TTFT 1.8 s / TPOT 10 s | 3.2 | 40.96 | 51.2 |
| seed7，TTFT 1.8 s / TPOT 10 s | 1.28 | 12.8 | 15.36 |

剩余 seed19 慢链路出现 .01625 unsafe → .0175 safe → .01875 unsafe，因此不报告单一 reference 边界。表中 seed0 慢/快合并展示两组。历史文件名 `prefill` 的 TPOT=1 s 案例实际上有 Decode 限制，不能据文件名解释机制。

结论：既不能只称“保守”，也不能统一乘一个系数当作修复。完整首次分歧、violation、TTFT/TPOT 与采样序列见 [nominal_summary.json](results/diagnostic/nominal_summary.json) 和逐例原始记录。

# 5. Profile mismatch 有没有意义

**值得作为受控压力测试，不适合作为独立算法主线。** Reference、intrinsic charge 不变，仅缩放 evaluator 看见的 compute 时间。

| evaluator profile | optimistic / 175 | conservative / 175 |
|---|---:|---:|
| nominal | 13 | 22 |
| Prefill −5% / −10% / −20% | 14 / 14 / 20 | 18 / 18 / 15 |
| Decode −5% / −10% / −20% | 15 / 20 / 26 | 17 / 16 / 14 |
| Both −5% / −10% / −20% | 16 / 21 / 31 | 15 / 14 / 11 |

2051-token 单请求在 nominal corrected ledger 下拒绝；仅低估 Prefill 5% 就再次接受，而 reference 仍不安全。这是灵敏度证据，不是“真实 GPU 有 5% 噪声”的证据。

简单 guard 对照也已完成：nominal 下固定 compute inflation 25% 与四场景检查均为 0 optimistic、32 个 accepted/reference-safe 点；Both 低估 10% 后，两者均为 8 optimistic、54 个 accepted/reference-safe 点。相同结果不支持增加 scenario 方法复杂度。这里统计的是离散点数，不能冒充保留容量百分比。

# 6. Partition decision 有没有问题

四组：seeds 0/7 × Decode/Prefill 两种 SLA，每组五个 shifts。设备为交替 L4x2/T4x4 **device groups**；不是八张单 GPU。SLAs 为 (4.2 s,.30 s) 与 (4.2 s,10 s)，因 absolute profile 下旧 analytical 模型的 .28 s TTFT 不适用。

| 试验 | E 选中 shift | R-best shifts | 选中项的 R 排名 | E/R 最大 safe（选中项） |
|---|---:|---|---:|---:|
| seed0 Decode | −2 | −2 | 1 | .008 / .008 |
| seed7 Decode | −2 | −2 | 1 | .007 / .007 |
| seed0 Prefill | 1 | 0, 1 | 1 | 2.755 / 12.76 |
| seed7 Prefill | 1 | 1 | 1 | 1.2325 / 4.205 |

E 的 Prefill 最优集合均为 {1,2}；既定 tie-break 选 1。选 shift 2 并不总是 reference-best，所以“selected winner 一致”不等于完整排序一致。保留采样区间，不把相邻误差条重叠写成严格的真实排名。

异构 nominal 的 502 个配对点为 0 optimistic、68 conservative。对每组加入十种非 nominal profile stress，共40个候选选择比较：在各候选已有局部细化点上，6个出现 selected shift 改变并落到较低的 sampled R 排名。seed0 Prefill 的 −10%/−20% Prefill 或 Both 从 shift1 改为2，sampled quality 为90.91%；seed7 Decode 的 −20% Decode/Both 从−2改为0，sampled quality 为96.43%。

但这些是**候选特定细化网格上的预警**：强制使用所有候选相同的19点粗网格后，44组（含nominal）选择都仍属于该粗网格 reference-best，较小差异被 ties 掩盖。因此不能把6/40写成稳健的 ranking-error rate；正式论文必须补共同细网格确认。原始与分辨率对照分别见 `mismatch_rankings.json` 和 `common_grid_rankings.json`。

因此值得研究“容量误差是否传导到决策”，但不能预设 ranking 比 safe/unsafe 更敏感。当前 nominal 证据恰好显示 winner 相对稳定。

# 7. 最推荐的 journal 主线

简单说：**先把同一任务交给快评估器和 reference simulator，弄清它们何时同意、何时不同意，以及这些误差是否真的让我们选错分区；再比较简单可复现的验证办法。**

Academic formulation：**Reference-Grounded Reliability Assessment for SLA-Aware Capacity and Partition Planning**。

这是一条统一的 empirical reliability 主线，包含 nominal、structured profile mismatch、decision transfer 三层证据。主要增量是公平输入契约、完整 reference 侧诊断、容量误差到决策误差的分析与验证协议；不是“再加一些噪声实验”。

# 8. 为什么它比其他方向好

现有 mixed discrepancy 已经提供具体问题，代码与模拟环境已跑通，两周内可完成 held-out 扩展。相比之下：profile uncertainty 单独成篇容易只有预期内的曲线；scenario checking 没有超过 margin；nominal ranking failure 没被观察到；更大 partition search 已有 CA 基础且成本高；budgeted 方法的优势被均匀分区强基线否定。按当前证据选择可靠性研究，避免为了方法名增加工作。

# 9. 新方法需要做到什么程度

只需一个透明的 **reference-grounded validation protocol**：冻结输入与指标；同时探测 E/R safe 和 unsafe 区域；保留非单调点；分开报告两方向分歧；按相同候选/负载集合分析选择质量；若输出“validated”运行点，必须实际查询该点，无 safe 点则 abstain。

所有 margin、scenario 和 query policy 都是实验对照。不要声称“只返回查过的 safe 点”是一条新安全定理。best-first 未超过 equal allocation，不保留其创新主张。最低可行论文是可信的诊断与建议，而非复杂优化器。

# 10. 正式 journal 实验需要哪些

1. **Artifact gate**：固定所有 commit/依赖；尽可能对齐最终 CA source。若仍不可得，在摘要/方法明确 recovered implementation，限制继承结论。
2. **Held-out nominal**：保留今晚 seeds 0/7/19 为探索；另取至少六个 seed，30 s 和 120 s 两种长度、另一时间窗口、两档链路；每个预选案例追到 R unsafe 或明确标记截断。
3. **机制检查**：选少量代表性的 optimistic/conservative 点，比较请求级进度、Prefill/Decode 重叠、blocking charge 与 reference latency；避免仅凭总数猜因果。
4. **Structured stress**：同样 −5/−10/−20% phase bias，另一个 device-specific bias；完整 reference 保持固定，不做巨大 Monte Carlo。
5. **Decision transfer**：五候选足够；使用所有候选共同的更细 load grid，报告 winner set、ties、区间、reference quality/regret；不能用各自不同分辨率制造排名。
6. **Mitigation/cost**：E-only、固定 margin、capacity derating、有限场景、uniform reference-only、reference-only adaptive、E-seeded equal allocation、小集合 exhaustive；报告调用数、拒绝输出、validated intensity 和重复顺序 wall-clock。今晚 runtime 是并发条件下的缓存 replay 总和，只能作试验记录。

这些是最小正式验证计划，不声称今晚已完成 held-out 或真实硬件实验。先做少量预选矩阵，稳定后补足，不扩展模型数量。

# 11. 两篇 CA 与 journal 的增量关系

| Old：必须归于 CA | New：journal 需要交付 |
|---|---|
| event-driven evaluator、TTFT/TPOT、network/memory accounting | 同输入、同 absolute profile 的 reference 侧可靠性矩阵 |
| progress/accounting separation、2051-token correction、原 regression | nominal 结构误差与 evaluator-only profile stress 的分离 |
| sampled evaluator capacity、488× 原 benchmark | 完整 R unsafe 扩展、非单调处理、validated-point 口径 |
| evaluator-as-score、5/7/9 shifts、local/coarse-to-fine search、20 seeds | E 排名向 R 排名的 transfer、decision stability 与误差传导 |
| 同一 evaluator 内部的 tested-family oracle | reference-best within tested family/grid 与公平 mitigation 对照 |

0/136 是 correction 在此前 both-safe 案例中没有新增拒绝，不是零 false acceptance；17/136 是 trajectory-coupled correction 的新增拒绝；488× 是某一 workload 的 CPU evaluator/reference simulator wall-clock 比值，不是 GPU 加速。历史代码已经提过非单调，不能把重发现本身列为新贡献。

# 12. 可以 claim 什么

在 pinned HELIX reference simulator 和明确测试配置下，恢复实现存在双向 nominal disagreement；结构化 profile underestimation 会改变其频数；绝对容量偏差不必然改变 selected partition。所有数字给出精确分母、采样规则、指标和实现范围。正式 held-out 完成后才能扩大措辞。

可以说“某运行点被该 reference simulator 验证为 safe”，或“测试集合中的 reference-best candidate”。可以报告简单方法不优于 baseline 的负结果。

# 13. 不可以 claim 什么

不能声称 real deployment guarantee、零 false acceptance probability、真实 profiling noise distribution、连续域 safe prefix、stationary throughput、global optimum，或本文方法已经优于强基线。不能把原论文全部40 tests/140 regression说成今晚重新运行，也不能保证 Future Internet 录用。

目前没有支持预算分配算法优越性的证据：19-load 五候选 exhaustive 为95个点；E-seeded 用10次达到四组该网格最优，但 uniform reference-only 用5次也达到4/4，且不需要 E 的95次评分。这个粗网格结果揭示 baseline 与分辨率的重要性，并不证明 uniform 在细网格或所有分区上最优。

# 14. 两周计划

| Day | 交付 |
|---|---|
| 1 | 固定研究问题、源码范围、指标；处理最终 artifact 缺口 |
| 2 | 冻结 held-out seeds/windows、共同细网格、完整 baseline |
| 3 | 跑 held-out nominal 与 reference unsafe 扩展 |
| 4 | 检查代表性分歧的请求轨迹，形成机制证据 |
| 5 | 完成 profile 与 device bias，报告增量影响 |
| 6 | 完成五候选 decision transfer，检查 resolution/ties |
| 7 | margin/derating/scenario 公平比较，停止无优势方法 |
| 8 | reference 查询策略对照与顺序重复 runtime |
| 9 | 整理总表、原始记录、错误/截断/非单调检查 |
| 10 | 写方法、reference contract、实验部分 |
| 11 | 写 introduction、related work、CA增量声明 |
| 12 | 全文 claim 审计，补最关键一个缺失对照 |
| 13 | 从干净环境复现，检查图表和公开材料 |
| 14 | 完成投稿稿件和补充材料；按官网核对期刊扩展稿要求 |

Day 6 gate：若 held-out 后现象只剩个别恢复实现问题，先缩小范围并解释，不强推普遍结论。期刊的具体扩展/重叠要求需要正式核对；本次官网访问受限，不编造固定“新增百分比”政策。

# 15. Backup direction

唯一备选：**Budgeted Reference-Assisted Capacity Planning**。

仅当共同细网格、held-out seeds/windows 上，简单 E-seeded 策略能持续以更少 reference calls 达到同等 validated intensity/partition quality，并且超过 uniform reference-only、reference-only bisection 与 equal-budget 对照，才切换。当前四组粗网格结果不满足条件，不应现在切换。若它也不成立，保留可靠性论文的实证定位，不制造第二套复杂算法。
