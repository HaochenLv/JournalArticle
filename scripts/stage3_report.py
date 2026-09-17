"""Render compact Stage 3 writing inputs from the audited result tables."""
from stage3_evidence import *

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text.strip()+'\n',encoding='utf-8',newline='\n')

def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
                     ['| '+' | '.join(str(v) for v in r)+' |' for r in rows])

def pct(v):return 'undefined' if v is None else f'{v*100:.2f}%'

def main():
    s=json.loads((OUT/'summary.json').read_text());caps=s['capacity']
    d=json.loads((FORMAL/'decision_loss_decomposition.json').read_text())['rows']
    der=json.loads((FORMAL/'mitigation_derating_audit/summary.json').read_text())
    counts=table(['配置 / SLA','variant','both safe','both unsafe','optimistic','conservative','分母'],
        [[r['kind']+' / '+r['sla_label'],r['variant'],r['both_safe'],r['both_unsafe'],r['optimistic'],r['conservative'],r['paired']] for r in s['counts']])
    comparison=[]
    for raw in [r for r in d if r['variant']=='raw' and r['regime']=='prefill']:
        legacy=next(r for r in d if r['variant']=='legacy' and r['group']==raw['group'] and r['regime']=='prefill')
        comparison.append([raw['workload'].split('-')[0],str(raw['evaluator_best_set'])+' → '+str(raw['selected_shift']),
            str(legacy['evaluator_best_set'])+' → '+str(legacy['selected_shift']),raw['reference_best_set'],
            raw['mismatch_type'],legacy['mismatch_type'],pct(raw['partition_selection_regret']),pct(legacy['partition_selection_regret'])])
    decisions=table(['负载','Raw best → selected','Legacy best → selected','R best','Raw 类型','Legacy 类型','Raw 分区损失','Legacy 分区损失'],comparison)
    losses=table(['负载','Raw / Legacy','SLA','分区损失','运行点损失','安全可用损失','推荐点 R-safe'],
       [[r['workload'].split('-')[0],r['variant'],r['sla_label'],pct(r['partition_selection_regret']),pct(r['operating_point_loss']),pct(r['safe_operating_point_loss']),r['exact_recommendation_reference_safe']] for r in d])
    caprows=[]
    for variant in ['raw','legacy']:
        vals=[c[variant+'_relative_gap'] for c in caps if c[variant+'_relative_gap'] is not None]
        caprows.append([variant,len(vals),pct(min(vals)),pct(statistics.median(vals)),pct(max(vals)),
                       sum(c[variant]['all_unsafe'] for c in caps),sum(c[variant]['nonmonotone'] for c in caps),sum(c[variant]['right_censored'] for c in caps)])
    capacity=table(['variant','有限误差 / 76','最小 gap','中位数','最大 gap','no-safe','nonmonotone','right-censored'],caprows)
    derating=table(['profiles','场景','实际降额有定义','最小','中位数','最大','取整后分区变化','unsafe 输出'],
       [['nominal' if r['bias']==1 else 'Both −10%',r['cases'],r['defined_realized_derating'],pct(r['min']),pct(r['median']),pct(r['max']),r['shift_changes_after_snapping'],r['unsafe_outputs']] for r in der['summary']])
    legacy_text=f'''# Legacy fixed-overhead progress sensitivity

Stage 3，2026-09-17。新增的是独立 control，不是替换 JB1，也不是确认恢复 CA-final 源码。
仅使 5 ms fixed overhead 进入 Prefill / Decode progress。使用冻结 JB1 的 `fixed_in_progress=True`；断言 queue overhead=0，intrinsic Prefill、blocking、profile、network、memory、SLA、tie-break 均不变。

复用 1634 个物理 reference records、3268 个 paired judgments；没有新 reference simulation。
所有 workload / scaled workload / partition / profile fingerprints、共同网格、point IDs、参考标签均核验。
每个标签从已有完整请求指标重新核算；Stage 2 raw 和冻结协议逐字节不变。完整清单与核验在 `results/formal/legacy_progress_sensitivity/source_manifest.json` 和 `integrity_checks.json`。

## Judgment：分层计数

{counts}

总计 Raw O=23/C=413，Legacy O=17/C=460；53/3268 标签变化，全部 safe→unsafe。
Legacy both-safe=906、both-unsafe=1885，一致数2791/3268；它降低乐观分歧但增加保守分歧，不能称为统一改善。
异构分母包含两个单候选反向链路 anchor；decision 表仅六个五候选主场景。

## Capacity：沿用原共同网格

{capacity}

每个配置的 largest observed safe、nearest unsafe above、全序列、非单调/no-safe/右删失和相对 gap 都保留在 `summary.json` / `capacity.csv`。
Reference 仍有3个非单调配置、8个no-safe配置、0右删失。Legacy不另行细化网格；局部 gap 不能证明连续容量，控制变体的边界精度也不能自动继承Raw的2.5%目标。

## Decision：12 个主场景

Tight-TPOT：Raw和Legacy均6/6 winner agreement，所选partition都不变；Legacy推荐强度均低约2.14%。
Relaxed-TPOT (fixed TTFT)：Raw为0/6，Legacy为2/6；下表逐项保留所有正负变化。

{decisions}

回答原审查问题：h101–h103 strict mismatch保留；h104不再strict且selected winner正确；h105 tie-break mismatch消失，h106保留。
h102反而由shift1转为shift2，reference rank从2降到4，分区损失8.30%→14.07%。
Relaxed场景平均分区损失 Raw {pct(statistics.mean(r['partition_selection_regret'] for r in d if r['variant']=='raw' and r['regime']=='prefill'))} → Legacy {pct(statistics.mean(r['partition_selection_regret'] for r in d if r['variant']=='legacy' and r['regime']=='prefill'))}；均为六个描述性场景的等权平均。

## 解释

**Yes, but modified.** Reliability / decision transfer 现象并非完全由raw-progress造成，但具体winner、并列集合、错误数明显依赖实现语义。
不能说“6/6 relaxed选偏与实现无关”，也不能将legacy描述为普遍修复或已确认CA-final。
本对照只覆盖名义profiles；已有profile stress仍是Raw JB1结果，不能外推为Legacy stress结果。

复现：`python scripts/stage3_evidence.py legacy`（已有分组结果会校验后复用）；源码 `scripts/stage3_evidence.py`。无需额外reference runs。
'''
    write(ROOT/'docs/LEGACY_PROGRESS_SENSITIVITY.md',legacy_text)
    loss_text=f'''# Decision-loss decomposition

令 B 为五候选中最大的reference sampled capacity，S为E所选partition的reference sampled capacity，L为E推荐强度。

- Partition-selection loss = 1 − S/B：只反映选partition的损失。
- Operating-point loss = 1 − L/B：反映最终推荐负载与reference-best sampled capacity的差距；本身不证明L安全。
- Safe operating-point loss = 1 − (L if exact reference-safe else 0)/B：unsafe或弃权的可用负载计0；B=0时未定义。
- 可加分解：1−L/B = (1−S/B) + (S−L)/B。两种loss不能相加；后者已经包含前者。

{losses}

Raw relaxed的分区损失8.30%–26.16%，而运行点损失68.95%–95.86%。h106有非单调参考序列；其推荐点0.2297227616实际R-unsafe，因此安全可用损失为100%，并非95.86%或26.16%。其selected partition仍有更高的观测safe点4.096，恰好说明不能从最大safe点推断更低点安全。
Raw与Legacy的12个主推荐均为11 safe / 1 unsafe。Legacy修复h105选分区，但推荐负载仍为5.0866495983，相对R-best 41.5842617652的运行点损失仍87.77%；修复winner没有自动恢复可用负载。
Legacy h104选对后，推荐负载略降，运行点损失81.94%→82.32%。这两个例子将两类损失清楚分离。

`results/formal/decision_loss_decomposition.csv` / `.json` 包含每变体12场景的best sets、交集、rank、ties、no-safe、nonmonotone、精确点标签及两类损失。
JSON另含144行mitigation主场景(policy×bias×12)，独立CSV为 `decision_loss_mitigation.csv`；弃权的partition loss未定义，安全可用损失为100%（B>0）。该表直接复用原mitigation输出，没有新运行。
复现：`python scripts/stage3_evidence.py decomposition`。
'''
    write(ROOT/'docs/DECISION_LOSS_DECOMPOSITION.md',loss_text)
    mitigation_text=f'''# Mitigation interpretation and derating audit

所有reference validation结果均为 **conditional reference-validation replay on the frozen grid**。
网格已利用E和R的transition信息构造；该构造成本没有计入最多5次的post-selection query预算。
最多5次只指一个已有网格上、已有selected partition后的回放查询，不代表从零planning所需调用数。
这只是practical engineering evidence，不是新optimizer、最优验证算法或超过reference-only方法的证据。

## 20%-target derating with grid snapping

目标为0.8×E最大推荐强度，然后向下取现有网格点，再按原规则选择候选。不得将实际降幅统称20%。

{derating}

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
'''
    write(ROOT/'docs/MITIGATION_INTERPRETATION_AUDIT.md',mitigation_text)
    report=f'''# 1. 一句话结论

**主线 Yes, but modified：JB1相对HELIX的误差仍会传导为分区和运行负载损失，但5 ms进度语义能改变具体决策；Legacy对照将relaxed-TPOT选偏从6/6减为4/6，并未消除问题。** 实验阶段到此停止，写作输入已经准备好。

日期2026-09-17。研究对象是明确恢复的JB1与固定HELIX reference simulator，非不可见的CA-final源码、非真实GPU部署。所有safe均仅指对应SLA和模拟器。

# 2. Legacy progress sensitivity

3268个冻结名义配对点，复用1634个物理reference records，新增reference runs=0。
仅开启5 ms fixed overhead progress；所有其他输入、账本、候选、tie-break和grid不变，未调参。
53个标签从safe变unsafe，O 23→17，C 413→460。Tight winner agreement 6/6→6/6；relaxed 0/6→2/6。

{decisions}

Legacy h102反而变差：rank2→4，loss8.30%→14.07%；h104、h105修复，h106保持tie-break mismatch。
详见[完整对照](docs/LEGACY_PROGRESS_SENSITIVITY.md)及[独立结果目录](results/formal/legacy_progress_sensitivity/summary.json)。

# 3. Journal 主线是否仍成立

**Yes, but modified.** 保留 judgment reliability → sampled capacity error → deployment decision error → profile-mismatch sensitivity。
增加implementation-semantic sensitivity作为结论的必要条件：不能再把Raw的六次relaxed选偏写成与实现选择无关的事实。
改善不是全局一致：Legacy减少O但增加C，仍有3个strict和1个tie-break mismatch；不包装修复算法。

# 4. 最终 judgement-level evidence

{counts}

异构TTFT均5.2 s；tight TPOT=.30 s，relaxed TPOT=10 s。A100 TTFT均2 s；TPOT=.15 s/1 s。
Raw keys `decode` / `prefill` / `relaxed_decode`不变，只映射展示标签。标签不预设first violation属于Prefill。
Raw总计953 both safe、1879 both unsafe、23 O、413 C；E接受976中23 R拒绝，R接受1366中413 E拒绝。
A100 Raw O=14/102个E接受点，需与异构分开；不能被大分母稀释。
3268是配对判定数，1634才是物理点数；自适应边界样本不是风险概率或独立重复样本。

# 5. 最终 capacity-level evidence

{capacity}

Capacity始终是共同网格中的largest observed safe intensity，不是连续capacity或稳态吞吐量。
Raw 68个有限gap：31负、32零、5正。8个E/R均no-safe，未以零gap纳入；R有3个非单调序列，E/R均0右删失。
Raw单边界支持65/76，已定义局部bracket最大2.190%；非单调h106最大safe仍不形成安全前缀。
Legacy沿用同一grid，保存nearest unsafe、全序列、no-safe、nonmonotone和right-censoring；不为控制变体额外细化。

# 6. 最终 decision-level evidence

Raw：tight 6/6一致；relaxed 4 strict best-set mismatches（h101–h104）和2 tie-break mismatches（h105/h106），不能写6 strict ranking reversals。
Legacy：tight 6/6一致；relaxed 3 strict（h101–h103）、1 tie-break（h106），另外2一致。
原tie-break始终为绝对shift最小，再负shift优先。Reference-best仅限五个shift和该共同网格。
h104原R-best有{{0,1}}并列；h102/h105/h106原E-best有并列。h106有no-safe candidates及reference nonmonotonicity，均保留。

# 7. Decision-loss decomposition

设B=reference-best sampled capacity，S=所选partition的reference sampled capacity，L=E推荐负载。
Partition loss=1−S/B；operating-point loss=1−L/B；safe operating-point loss在推荐点R-unsafe或弃权时将usable load记0。
可加分解为 (1−S/B)+(S−L)/B=1−L/B；不能把前两种总损失重复相加。

{losses}

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
冻结baseline SHA256 `{CONFIG['baseline_sha256']}`；protocol hash `{PROTOCOL_HASH}`。

# 11. Mitigation evidence

**Conditional reference-validation replay on the frozen grid**：网格构造已使用reference transition信息，最多5次query只是post-selection回放，构造成本不在预算里。
禁止“five calls solve planning from scratch”。边界回放不重新搜索partition，不是新optimizer或对reference-only算法的优越性证据。

{derating}

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
'''
    write(ROOT/'STAGE3_EVIDENCE_REPORT.md',report)
    # Small presentation-layer additions only: preserve raw Stage 2 JSON files.
    review=json.loads((FORMAL/'research_review.json').read_text())
    for t in review['rq3']:
        t['sla_display_label']=label(t['regime']);t['mismatch_type']=mismatch(t)
    review['stage3']={'assessment':'Yes, but modified','new_reference_runs':0,
        'raw_strict_mismatches':4,'raw_tie_break_mismatches':2,'legacy_strict_mismatches':3,'legacy_tie_break_mismatches':1,
        'legacy_summary':'legacy_progress_sensitivity/summary.json','decision_loss':'decision_loss_decomposition.json',
        'derating_audit':'mitigation_derating_audit/summary.json',
        'mitigation_scope':'conditional reference-validation replay; reference-informed grid construction cost excluded',
        'derating_label':'20%-target derating with grid snapping'}
    write_json(FORMAL/'research_review.json',review)
    print('Stage 3 reports rendered')

if __name__=='__main__':main()
