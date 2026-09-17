# Decision-loss decomposition

令 B 为五候选中最大的reference sampled capacity，S为E所选partition的reference sampled capacity，L为E推荐强度。

- Partition-selection loss = 1 − S/B：只反映选partition的损失。
- Operating-point loss = 1 − L/B：反映最终推荐负载与reference-best sampled capacity的差距；本身不证明L安全。
- Safe operating-point loss = 1 − (L if exact reference-safe else 0)/B：unsafe或弃权的可用负载计0；B=0时未定义。
- 可加分解：1−L/B = (1−S/B) + (S−L)/B。两种loss不能相加；后者已经包含前者。

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

Raw relaxed的分区损失8.30%–26.16%，而运行点损失68.95%–95.86%。h106有非单调参考序列；其推荐点0.2297227616实际R-unsafe，因此安全可用损失为100%，并非95.86%或26.16%。其selected partition仍有更高的观测safe点4.096，恰好说明不能从最大safe点推断更低点安全。
Raw与Legacy的12个主推荐均为11 safe / 1 unsafe。Legacy修复h105选分区，但推荐负载仍为5.0866495983，相对R-best 41.5842617652的运行点损失仍87.77%；修复winner没有自动恢复可用负载。
Legacy h104选对后，推荐负载略降，运行点损失81.94%→82.32%。这两个例子将两类损失清楚分离。

`results/formal/decision_loss_decomposition.csv` / `.json` 包含每变体12场景的best sets、交集、rank、ties、no-safe、nonmonotone、精确点标签及两类损失。
JSON另含144行mitigation主场景(policy×bias×12)，独立CSV为 `decision_loss_mitigation.csv`；弃权的partition loss未定义，安全可用损失为100%（B>0）。该表直接复用原mitigation输出，没有新运行。
复现：`python scripts/stage3_evidence.py decomposition`。
