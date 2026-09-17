# Mitigation interpretation and derating audit

所有reference validation结果均为 **conditional reference-validation replay on the frozen grid**。
网格已利用E和R的transition信息构造；该构造成本没有计入最多5次的post-selection query预算。
最多5次只指一个已有网格上、已有selected partition后的回放查询，不代表从零planning所需调用数。
这只是practical engineering evidence，不是新optimizer、最优验证算法或超过reference-only方法的证据。

## 20%-target derating with grid snapping

目标为0.8×E最大推荐强度，然后向下取现有网格点，再按原规则选择候选。不得将实际降幅统称20%。

| profiles | 场景 | 实际降额有定义 | 最小 | 中位数 | 最大 | 取整后分区变化 | unsafe 输出 |
|---|---|---|---|---|---|---|---|
| nominal | 28 | 26 | 21.20% | 46.53% | 79.87% | 8 | 2 |
| Both −10% | 28 | 28 | 21.20% | 26.09% | 78.98% | 0 | 5 |

Nominal h101/tight-TPOT：0.0099348625→target 0.00794789→output 0.004，实际降幅59.74%。
56 cases全部保留，54有定义的实际降幅；2个nominal无E-safe输出使实际降幅未定义，未填作0或100%。
Nominal有8/28 cases在取整后因重新tie-break而改变partition；所以这套现有policy不等同于始终固定原selected partition的纯负载缩放。所有original/selected shifts都在CSV。
No new policy或参数调优；保留旧数据和实现，只修正解释。

全28场景/每policy每bias的可用质量均值只含26个B>0场景；unsafe/abstention分母仍28。核心图仅12个五候选场景。
Nominal边界回放0 unsafe/4 abstain，质量71.37%；Both−10%为0/8、70.00%。Raw E-only分别5 unsafe/2 abstain、55.33%，以及20/0、7.97%。
“只返回查询过的safe点”保证的是这些oracle点的直接标签，不是泛化安全性；非单调时不能把未查询低负载自动判safe。
额外5次最多只在selected partition上局部查询，不修复已选错partition；逻辑查询和物理去重数见原research_review。

数据：`results/formal/mitigation_derating_audit.csv`、`results/formal/mitigation_derating_audit/summary.json`。
复现：`python scripts/stage3_evidence.py derating`。
