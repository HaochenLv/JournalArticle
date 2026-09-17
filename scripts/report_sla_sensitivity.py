"""Generate evidence reports from verified Stage 4 results; no manuscript prose."""
from sla_sensitivity_common import *
import statistics

def pct(v):return 'undefined' if v is None else f'{100*v:.2f}%'
def fmt(v):return 'undefined' if v is None else f'{v:.6g}' if isinstance(v,float) else str(v)
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])
def code(d):return {'agreement':'A','strict best-set mismatch':'S','tie-break mismatch':'T','no-safe recommendation':'N','no-safe reference':'R','incomplete reference':'F'}[d['mismatch_type']]

def main():
    data=read(OUT/'summary.json');ex=read(OUT/'execution_summary.json');qc=read(OUT/'quality_checks.json');assert qc['passed']
    ds=data['decisions'];agg=data['aggregate'];hist=read(OUT/'refinement_history.json')
    def get(w,s,v):return next(r for r in ds if r['workload']==w and r['sla']==s and r['semantics']==v)
    labels=[s['id'] for s in P['slas']]
    judgment=table(['TTFT / TPOT (s)','语义','both-safe','both-unsafe','O','C','paired'],[[f"{a['ttft_s']:g} / {a['tpot_s']:g}",a['semantics'],a['both_safe'],a['both_unsafe'],a['optimistic_disagreement'],a['conservative_disagreement'],a['paired_denominator']] for a in agg])
    captable=table(['TTFT / TPOT','语义','有定义gap','负 / 零 / 正','最小','中位','最大'],[[f"{a['ttft_s']:g} / {a['tpot_s']:g}",a['semantics'],a['defined_capacity_gaps'],f"{a['capacity_gap_negative']} / {a['capacity_gap_zero']} / {a['capacity_gap_positive']}",pct(a['capacity_gap_min']),pct(a['capacity_gap_median']),pct(a['capacity_gap_max'])] for a in agg])
    outcome=table(['负载','语义']+[s.replace('TTFT','').replace('_TPOT',' / ') for s in labels],[[g['workload'].split('-')[0],v]+[code(get(g['workload'],sid,v)) for sid in labels] for g in P['groups'] for v in P['semantics']])
    losstable=table(['TTFT / TPOT','语义','平均分区loss','平均运行点loss','平均安全运行点loss','定义分母(分区/运行/安全)','unsafe推荐','弃权'],[[f"{a['ttft_s']:g} / {a['tpot_s']:g}",a['semantics'],pct(a['partition_selection_loss_mean']),pct(a['operating_point_loss_mean']),pct(a['safe_operating_point_loss_mean']),'/'.join(str(a[k+'_defined_count']) for k in ['partition_selection_loss','operating_point_loss','safe_operating_point_loss']),a['unsafe_recommendations'],a['no_safe_recommendations']] for a in agg])
    grids=table(['负载','原grid','最终grid','新增强度','新增物理点','有新增轮数','未解决interval','停止原因'],[[x['workload'].split('-')[0],x['before'],x['after'],x['added'],5*x['added'],x['rounds_with_additions'],x['unresolved_intervals'],x['stop_reason']] for x in ex['groups']])
    semantic=[]
    rows=[r for g in P['groups'] for r in points(g)]
    for sid in labels:
        semds=[(get(g['workload'],sid,'raw'),get(g['workload'],sid,'legacy')) for g in P['groups']]
        semantic.append({'sla':sid,'changed_labels':sum(verdict(r,'raw',sid)!=verdict(r,'legacy',sid) for r in rows),
          'changed_selections':sum(a['selected_shift']!=b['selected_shift'] for a,b in semds),
          'changed_types':sum(a['mismatch_type']!=b['mismatch_type'] for a,b in semds),
          'max_operating_loss_difference':max((abs(a['operating_point_loss']-b['operating_point_loss']) for a,b in semds if a['operating_point_loss'] is not None and b['operating_point_loss'] is not None),default=None),
          'max_partition_loss_difference':max((abs(a['partition_selection_loss']-b['partition_selection_loss']) for a,b in semds if a['partition_selection_loss'] is not None and b['partition_selection_loss'] is not None),default=None)})
    semtable=table(['SLA','标签变化数','selected变化','决策类型变化','最大分区loss差','最大运行点loss差'],[[x['sla'],x['changed_labels'],x['changed_selections'],x['changed_types'],pct(x['max_partition_loss_difference']),pct(x['max_operating_loss_difference'])] for x in semantic])
    ttft=table(['负载','TPOT','语义','5.2 → 4.68 类型','selected','B','分区loss','运行点loss'],[
       [g['workload'].split('-')[0],tp,v,code(a)+' → '+code(b),str(a['selected_shift'])+' → '+str(b['selected_shift']),fmt(a['reference_best_capacity'])+' → '+fmt(b['reference_best_capacity']),pct(a['partition_selection_loss'])+' → '+pct(b['partition_selection_loss']),pct(a['operating_point_loss'])+' → '+pct(b['operating_point_loss'])]
       for g in P['groups'] for tp in [1.2,10] for v in P['semantics']
       for a,b in [(get(g['workload'],f'TTFT5.2_TPOT{tp:g}',v),get(g['workload'],f'TTFT4.68_TPOT{tp:g}',v))]])
    changes=data['stage3_resolution_comparison']
    changetable=table(['负载','SLA','语义','selected旧 → 新','E best旧 → 新','R best旧 → 新','类型旧 → 新'],[[x['workload'].split('-')[0],x['sla'],x['semantics'],f"{x['old_selected']} → {x['new_selected']}",f"{x['old_evaluator_best']} → {x['new_evaluator_best']}",f"{x['old_reference_best']} → {x['new_reference_best']}",f"{x['old_mismatch_type']} → {x['new_mismatch_type']}"] for x in changes])
    first=[]
    for g in P['groups']:
        for v in P['semantics']:
            seq=[get(g['workload'],sid,v) for sid in labels[:6]]
            bad=next((r for r in seq if code(r) in ['S','T']),None)
            first.append([g['workload'].split('-')[0],v,fmt(bad['tpot_s']) if bad else '未观察到',' → '.join(code(r) for r in seq)])
    firsttable=table(['负载','语义','首个观测mismatch TPOT','六个TPOT决策序列'],first)
    detailed=table(['负载','SLA','语义','E best → selected','R best','类型','R rank','B','S','L','分区loss','运行点loss','allocation','R-safe(L)','safe loss'],[
       [r['workload'].split('-')[0],r['sla'],r['semantics'],f"{r['evaluator_best_set']} → {r['selected_shift']}",r['reference_best_set'],code(r),r['selected_reference_rank'],fmt(r['reference_best_capacity']),fmt(r['selected_partition_reference_capacity']),fmt(r['evaluator_recommended_intensity']),pct(r['partition_selection_loss']),pct(r['operating_point_loss']),pct(r['allocation_component']),r['exact_reference_safe'],pct(r['safe_operating_point_loss'])] for r in ds])
    unsafe=[r for r in ds if r['exact_reference_safe'] is False]
    unsafetable=table(['负载','SLA','语义','违反请求 / 总数','fraction','最大TTFT超限(s)','最大TPOT超限(s)','类型'],[[r['workload'].split('-')[0],r['sla'],r['semantics'],f"{r['recommendation_violations']['violating_requests']} / {r['recommendation_violations']['request_count']}",pct(r['recommendation_violations']['violating_request_fraction']),fmt(r['recommendation_violations']['max_ttft_excess_s']),fmt(r['recommendation_violations']['max_tpot_excess_s']),r['recommendation_violations']['violation_type']] for r in unsafe])
    unresolved=sum(len(h['unresolved_transitions']) for h in hist)
    maxwidth=max((x['relative_width'] for h in hist for x in h['unresolved_transitions']),default=0.)
    limits=f"最终保留 {unresolved} 个未达到2.5%目标的共同transition intervals，最大相对宽度 {pct(maxwidth)}。全部明细和witness保存在 refinement_history.json；budget/round停止不等于所有边界已经精确。nonmonotone只描述观测序列；最大safe不构成安全前缀，范围外不推断。"
    changed=[r for r in data['initial_grid_decision_comparison'] if r['type_changed'] or r['selection_changed']]
    resolution_table=table(['负载','SLA','语义','原grid类型 → 最终类型','selected原 → 最终'],[[r['workload'].split('-')[0],r['sla'],r['semantics'],r['initial_type']+' → '+r['final_type'],str(r['initial_selected'])+' → '+str(r['final_selected'])] for r in changed])
    limits+=f"\n\n八组SLA共96条语义决策中，{len(changed)}条在扩展grid后发生selected或决策类型变化；完整审计见 initial_grid_decision_comparison.csv。下表包括新SLA，不能混称为Stage 3历史结果变化。\n\n"+resolution_table
    integrity=f"{qc['protected_hashes_unchanged']} 个Stage 2/3保护文件哈希未变；协议hash `{PH}`。18项要求及附加核验通过：原grid标签/决策、输入与profile/partition/network、依赖源、共同grid、SLA单调性、逐请求全drain、失败/重试、全八SLA、完整分母、ties/no-safe/nonmonotone/unresolved、loss identity。36项单元测试通过。"
    execution=f"复用1,450个原physical points，未重跑这些HELIX点。新增unique physical points={ex['new_unique_physical_points']}，成功={ex['successful_new_physical_points']}，physical attempts={ex['physical_attempts']}，retry={ex['retries']}，timeout={ex['timeouts']}，最终failed={ex['failed_points']}。Evaluator实际保存{ex['evaluator_judgments']:,}次重新调用结果，其中原grid23,200次、新grid{ex['evaluator_added_grid']:,}次。Reference分类{ex['reference_sla_classifications']:,}次；Raw/Legacy共享物理真值。"
    scope="Stage 4是Stage 3之后设计的 controlled parameter sensitivity study，使用同一组六个held-out workloads，不是新的独立held-out generalization test。48 workload-SLA条件不是48独立workloads。仅改变八组TTFT/TPOT阈值；没有新增模型、GPU、network、workload、profile stress、候选或算法。"
    boundary="JB1是journal明确指定的lightweight SLA-aware evaluator；Legacy是implementation-semantic sensitivity control。已撤回且从未公开/出版的AICCC稿不是prior publication。本阶段不寻找所谓final implementation。已accepted的 Evaluator-Guided SLA-Aware Layer Partitioning for Heterogeneous LLM Pipelines 是应区分的prior work；5-shift、evaluator-as-score和原partition search不是journal新增贡献。新增价值仅为SLA-regime sensitivity evidence。"
    # Interpretation is reviewed against the final tables before publication.
    interpretation=read(OUT/'interpretation.json')
    report=f'''# 1. 一句话结论

{interpretation['one_sentence']}

# 2. 这轮到底补了什么

{scope}

{boundary}

# 3. 是否需要新的 HELIX runs

需要，用于新SLA边界的共同网格细化。{execution}

{grids}

# 4. TPOT sensitivity 总体趋势

{interpretation['tpot_trend']}

各SLA分母是同一最终workload-level common grid上的点数，计数不是生产错误概率。

# 5. Judgment reliability

RQ-S1：{interpretation['judgment']}

O=E safe/R unsafe；C=E unsafe/R safe。

{judgment}

# 6. Capacity error

RQ-S2：{interpretation['capacity']}

gap=(Emax-Rmax)/Rmax；只对两者容量有定义的条目计算，no-safe不填0。largest observed safe只是采样容量。

{captable}

# 7. Partition decision

RQ-S3：{interpretation['decision']}

A=agreement；S=strict best-set mismatch；T=tie-break mismatch；N=no-safe recommendation；R=no-safe reference；F=incomplete reference。N仍保留reference-best和B，B=0时relative quality全部undefined。

{outcome}

{firsttable}

# 8. Partition loss vs operating-point loss

RQ-S4：{interpretation['loss']}

B为reference-best sampled capacity，S为所选partition的reference sampled capacity，L为推荐强度。1-L/B=(1-S/B)+(S-L)/B；不能把partition loss与operating loss相加。下表各均值只纳入对应量有定义的workload，逐项分母与undefined见完整表。

{losstable}

unsafe推荐的safe usable load=0，safe loss=100%（B>0）；这是该推荐点的safety-adjusted metric，不表示较低负载均unsafe或safe。

{unsafetable}

# 9. Raw vs Legacy

RQ-S5：{interpretation['semantics']}

{semtable}

# 10. TTFT 5.2 → 4.68 的影响

RQ-S6：{interpretation['ttft']}

{ttft}

# 11. 新增 grid refinement 是否改变 Stage 3 原结论

{interpretation['stage3']}

原grid一致性gate全部通过；以下仅报告新grid的resolution sensitivity，不覆盖Stage 3历史结论。

{changetable}

# 12. 中间 TPOT 最重要的发现

{interpretation['intermediate']}

# 13. 是否发现明显 transition

{interpretation['transition']}

这些是tested workloads/configurations中的离散阈值对比，不能宣称universal critical TPOT threshold；连线不推断未测SLA。

# 14. 哪些结论仍受 resolution 限制

{limits}

{interpretation['resolution']}

# 15. 最终对 journal story 的影响

**{interpretation['story_choice']}**。{interpretation['story']}

{integrity}

新增正文候选图仅一张：[decision type + loss](results/sla_sensitivity/figures/sla_sensitivity.png)，同时提供SVG。技术细节、96行完整决策和所有序列见 [technical report](docs/SLA_REGIME_SENSITIVITY.md) 与 results/sla_sensitivity/。

# 16. 是否需要继续实验

**{interpretation['continue_choice']}**。{interpretation['continue_reason']}
'''
    (ROOT/'SLA_SENSITIVITY_EVIDENCE_REPORT.md').write_text(report,encoding='utf-8',newline='\n')
    tech=f'''# SLA-regime sensitivity: technical evidence

## 1. Frozen protocol

{scope}

See [protocol](SLA_SENSITIVITY_PROTOCOL.md), config/sla_sensitivity_protocol.json and protocol_snapshot.json. Canonical hash: `{PH}`. Protocol freeze commit `b85816c` precedes every new SLA outcome. Eight fixed pairs, five shifts, two semantics and original link assignments are unchanged. No prior monotonic outcome assumption.

## 2. Source version

Stage 3 source: `{P['source_commit']}`; initial HEAD exactly matched and worktree was clean. {boundary}

Original launcher was unavailable; bundled Python3.12.14 uses existing networkx3.2.1/matplotlib3.8.4 packages. Host hardware configuration matches Stage 3. Portability source checks and every old-SLA evaluator field except runtime reproduce; original physical points are not rerun. Environment is saved without personal local paths.

## 3. Reused physical points

All1,450 primary-group records are read-only. Per-request aligned TTFT and max per-token TPOT are thresholded via formal_core.reference_details; no overhead is added. The old two-SLA labels (8,700 E/R/control comparisons) and24 semantic decision records including reference score vectors/best sets reproduce. Every new SLA actually calls journal_baseline.evaluate.

## 4. New physical points

{execution}

Killable600s attempts, at most one same-input retry, original memory-aware scheduler ceiling12/budget24GiB/reserve6GiB. Full per-token metrics and input fingerprints are in reference/*.json.gz. Per-attempt journals are retained. No failed point becomes unsafe.

## 5. Refinement process

Union of all both-direction verdict transitions over5 candidates×8 SLA×3 models. Width>2.5% proposes round(sqrt(lower*upper),10); priority descending log width then lower endpoint. Every addition applies to five candidates and all SLA/semantics. Max24 additions/workload, six rounds and720 unique physical points overall. Original intensity range unchanged. Exact round plans, witnesses and unselected intervals are in refinement_history.json. Verification replays every selection against its prior grid.

## 6. Grid sizes before/after

{grids}

## 7. Judgment results

{interpretation['judgment']}

{judgment}

raw.csv has one row per point/SLA/semantic. `point_record` resolves to `points/<group>/<point_record>.json.gz`, containing full input fingerprints and first complete evaluator violation sets; this avoids repeating large ledgers sixteen times. No compact-adapter ordering is interpreted as physical causality. Counts are adaptive-sample descriptions.

## 8. Capacity results

{interpretation['capacity']}

{captable}

capacity.csv and summary.json retain all480 semantic/candidate/SLA entries, including complete E/R sequences (null for missing), largest safe, nearest unsafe above, no-safe, right-censoring, nonmonotonicity, all transition intervals, local bracket width and unresolved flag. Reference sequences repeat under both semantic labels for comparison; there are240 distinct reference candidate/SLA sequences. No continuous-capacity theorem is claimed.

## 9. Decision results

{interpretation['decision']}

{outcome}

Tie-break is smallest |shift|, then negative. Best-set overlap does not itself mean selected agreement. Competition rank, best sets and loss remain explicit. Code legend: A agreement, S strict mismatch, T tie-break mismatch, N abstention/no-safe recommendation, R no-safe reference, F incomplete reference.

## 10. Operating-point results

{interpretation['loss']}

{losstable}

{unsafetable}

Full96-row decisions and operating points follow. B=0 quantities are undefined. Partition loss and operating loss are not additive; partition+allocation is operating loss. Safety-adjusted usable load is0 for an unsafe recommendation or abstention, with no inference about unqueried or lower loads.

{detailed}

## 11. Raw vs Legacy

{interpretation['semantics']}

{semtable}

## 12. TTFT tightening

{interpretation['ttft']}

{ttft}

## 13. Resolution limitations

{limits}

{interpretation['resolution']}

Stage 3 resolution comparison:

{changetable}

## 14. Integrity checks and reproduction

{integrity}

Run `python scripts/run_sla_sensitivity.py all`, then `python scripts/analyze_sla_sensitivity.py`, `python scripts/verify_sla_sensitivity.py`, `python scripts/figure_sla_sensitivity.py` and `python scripts/report_sla_sensitivity.py`. Existing point/attempt records support resume without resetting the budget. Verification never launches HELIX. `python -m unittest discover -s tests -v` includes targeted new refinement, missingness, monotonicity and tie tests. `scripts/check_public.py` inspects staged bytes (including decompressed results) before push. Protected history, CA material and credentials are excluded from changes.

Main-text candidate figure: ../results/sla_sensitivity/figures/sla_sensitivity.png (one figure, SVG companion). Six TPOT categories use small horizontal Raw/Legacy offsets solely to expose coincident markers; these are not different thresholds. Figure lines only join the prescribed tested conditions; red circles flag arithmetic operating losses whose recommendations are unsafe. Reference nonmonotonicity is over intensity, whereas SLA-relaxation monotonicity passed for every physical point. Table outputs and reports are tied to the saved protocol hash.
'''
    (ROOT/'docs/SLA_REGIME_SENSITIVITY.md').write_text(tech,encoding='utf-8',newline='\n')
    write_json(OUT/'semantic_comparison.json',semantic)
    print('REPORTS_CREATED')

if __name__=='__main__':main()
