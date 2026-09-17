"""Render the Stage 5 evidence reports from verified records and explicit interpretation."""
from jb1_plus_common import *
import re

def fmt(x):
 if x is None:return 'undefined'
 if isinstance(x,bool):return str(x)
 if isinstance(x,float):return f'{x:.6g}'
 return str(x)
def pct(x):return 'undefined' if x is None else f'{100*x:.2f}%'
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|',*['| '+' | '.join(fmt(x) for x in r)+' |' for r in rows]])
def totals(data):
 return table(['Variant','O','C','paired','agreement / decisions','unsafe / abstain','gap median','mean absolute gap','partition loss','operating loss','safe loss'],[
 [r['variant'],r['optimistic'],r['conservative'],r['paired_denominator'],f"{r['decision_types'].get('agreement',0)}/{r['decisions']}",f"{r['unsafe_recommendations']}/{r['abstentions']}",pct(r['gap']['median']),pct(r['absolute_gap']['mean']),pct(r['partition_selection_loss']['mean']),pct(r['operating_point_loss']['mean']),pct(r['safe_operating_point_loss']['mean'])] for r in data['aggregate']])
def judgments(data):
 return table(['SLA','Variant','both safe','both unsafe','O','C','paired','missing'],[[r['sla'],r['variant'],*[r[k] for k in ['both_safe','both_unsafe','optimistic','conservative','paired_denominator','missing']]] for r in data['by_sla']])
def capacities(data):
 return table(['SLA','Variant','defined gap','min / median / max','mean absolute gap','E no-safe/nonmono/censored','R no-safe/nonmono/censored'],[
 [r['sla'],r['variant'],r['gap']['n'],' / '.join(pct(r['gap'][k]) for k in ['min','median','max']),pct(r['absolute_gap']['mean']),
 '/'.join(str(r['evaluator_flags'][k]) for k in ['no_safe','nonmonotone','right_censored']),'/'.join(str(r['reference_flags'][k]) for k in ['no_safe','nonmonotone','right_censored'])] for r in data['by_sla']])
def decisions(data):
 return table(['Workload','SLA','Variant','E best → selected','R best','type / rank','partition loss','operating loss','exact safe','violations','safe loss'],[
 [r['workload'],r['sla'],r['variant'],f"{r['evaluator_best_set']} → {r['selected_shift']}",r['reference_best_set'],f"{r['mismatch_type']} / {r['selected_reference_rank']}",pct(r['partition_selection_loss']),pct(r['operating_point_loss']),r['exact_reference_safe'],
 f"{r['recommendation_violations'].get('violating_requests','—')}/{r['recommendation_violations'].get('request_count','—')}",pct(r['safe_operating_point_loss'])] for r in data['decisions']])
def loss_denominators(data):
 return table(['SLA','Variant','partition mean / n','operating mean / n','safe mean / n','unsafe outputs','abstentions','decision types'],[
 [r['sla'],r['variant'],*[f"{pct(r[k]['mean'])} / {r[k]['n']}" for k in ['partition_selection_loss','operating_point_loss','safe_operating_point_loss']],r['unsafe_recommendations'],r['abstentions'],r['decision_types']] for r in data['by_sla']])
def paired(data):
 return table(['Semantic pair','removed C','new O','safe→unsafe','capacity improved/worsened','new unsafe recommendations','removed unsafe recommendations','unsafe severity worsened'],[
 [sem,p['removed_conservative'],p['new_optimistic'],p['safe_to_unsafe'],f"{p['capacity_improved']}/{p['capacity_worsened']}",p['new_unsafe_recommendations'],p['removed_unsafe_recommendations'],p['unsafe_recommendation_severity_worsened']] for sem,p in data['paired'].items()])

def main():
 guard();s=read(OUT/'summary.json');a=s['phase_a'];b=s['phase_b'];control=s['a100_controls'];ex=read(OUT/'execution_summary.json');q=read(OUT/'quality_checks.json');assert q['passed']
 text=read(OUT/'interpretation.json');mech=read(OUT/'phase_a_mechanisms.json');rt=read(OUT/'runtime.json')
 # Audit the headline prose against the finalized tables, independently of rendering.
 for phase,expected_c,expected_o,expected_agree in [(a,[1911,1604,2046,1724],[38,39,31,32],[27,31,32,33]),(b,[225,153,227,155],[7,17,7,17],[14,14,13,13])]:
  assert [r['conservative'] for r in phase['aggregate']]==expected_c
  assert [r['optimistic'] for r in phase['aggregate']]==expected_o
  assert [r['decision_types'].get('agreement',0) for r in phase['aggregate']]==expected_agree
 assert ex['phase_b_unique_physical_points']==ex['physical_attempts']==500
 assert ex['failed_points']==ex['timeouts']==ex['retries']==0
 assert sum(g['unresolved_intervals'] for g in ex['groups'])==37
 assert [r['unsafe_recommendations'] for r in b['aggregate']]==[1,1,1,1]
 assert [r['unsafe_recommendations'] for r in a['aggregate']]==[4,4,2,2]
 for sem in ['Raw','Legacy']:
  assert b['paired'][sem]['new_optimistic']==10 and b['paired'][sem]['removed_conservative']==72
  assert b['paired'][sem]['capacity_improved']==30 and b['paired'][sem]['capacity_worsened']==2
  assert b['paired'][sem]['unsafe_recommendation_severity_worsened']==1
  f=next(d for d in b['decisions'] if d['workload']=='w202' and d['sla']=='TTFT5.2_TPOT5' and d['variant']==sem+'-Full')
  r=next(d for d in b['decisions'] if d['workload']=='w202' and d['sla']=='TTFT5.2_TPOT5' and d['variant']==sem+'-Remaining')
  assert f['selected_shift']==r['selected_shift']==0
  assert f['recommendation_violations']['violating_requests']==1 and r['recommendation_violations']['violating_requests']==9
  assert f['recommendation_violations']['request_count']==r['recommendation_violations']['request_count']==48
  assert r['evaluator_recommended_intensity']==2*f['evaluator_recommended_intensity']
 assert max(x['gap']['max'] for x in b['aggregate'])==3
 for row in b['aggregate']:
  assert row['reference_flags']['nonmonotone']==7 and row['reference_flags']['right_censored']==12
  assert row['evaluator_flags']['no_safe']==0 and row['evaluator_flags']['right_censored']==5
 conservative=mech['cases'][0];epoch=conservative['failure_epoch_comparison']['Raw'];rid=next(iter(epoch['decode']));ledger=epoch['decode'][rid]
 mechanism=f"原 h105/A100/fast/4.096、TTFT2/TPOT1 案例，在同一失败 epoch t={epoch['time_s']:.8f} s，Raw blocking debt 从 {epoch['full_debt_s']:.9f} s 降到 {epoch['remaining_debt_s']:.9f} s，减少 {epoch['debt_reduction_s']:.9f} s。Decode compute 为 {ledger['full']['compute_s']:.6f} s；加 fixed .005 s 后，required TPOT 从 {ledger['full_required_tpot_s']:.9f} s 降到 {ledger['remaining_required_tpot_s']:.9f} s，仍超过 1 s。因此局部 full-service 高估被直接减轻，但这个 conservative verdict 没有被修复。Reference 最大 TPOT {conservative['reference']['max_tpot_s']:.9f} s。"
 components=table(['request','full compute (s)','remaining fraction','remaining compute (s)','intrinsic (s)'],[[x['request_id'],x['full_compute_s'],x['remaining_fraction'],x['remaining_compute_s'],x['intrinsic_s']] for x in epoch['active_prefill']])
 optimism="原 h103/A100/slow/.016、TPOT .15 案例中，Raw-Full 和 Raw-Remaining 均接受而 reference 拒绝；Legacy 两者均拒绝。减少 debt 没有修复 Raw 漏掉真实重叠的问题。Raw 请求13在1720.199600 s结束，reference为1721.840915 s，新请求14在1720.250000 s到达；同一语义的 Full/Remaining 完整轨迹一致，completion-time drift 仍存在。"
 definitions="O=E safe/R unsafe；C=E unsafe/R safe。容量为同一网格最大观测 safe intensity，gap=(Emax−Rmax)/Rmax；任一容量无定义时 gap 保持 undefined。B=reference-best sampled capacity，S=selected partition 的 reference capacity，L=推荐 intensity。partition loss=1−S/B；operating loss=1−L/B；allocation=(S−L)/B；前两者不能相加。safe usable=L仅当该点实际R-safe；unsafe/弃权记0，缺失记null；B=0时relative loss未定义。"
 limits_text="仅在指定 HELIX reference simulator、同一 Azure 生成分布、有限 trace、五个候选及采样网格内成立；没有真实GPU验证、连续capacity、安全前缀或普遍风险概率。Phase A是post-hoc，Phase B是四个新seed/非重叠源窗口的受限held-out，不是外部数据集验证。Source窗口按构造器循环，w204 offset1200对应原始bins0–39；只保证与h101–h106及本批其他窗口不重叠，未声称所有项目历史从未用过这些源bins。源token分布复用且workload/link/duration非完整交叉。Phase A沿用Stage4网格，未为Remaining重新细化，不能继承原Full边界精度；Raw/Legacy的Remaining分别有67/70个候选-SLA序列存在未达2.5%的已观测transition。Phase B网格由reference与四个variants的transition共同构造；未解决边界照实保留，没有发现的窄safe/unsafe岛不能排除。"
 unresolved=table(['Group','grid','added','unresolved','max width','stop'],[[g['group'],g['grid_size'],g['added_intensities'],g['unresolved_intervals'],pct(g['max_unresolved_relative_width']),g['stop_reason']] for g in ex['groups']])
 runtime=table(['Variant','n','runtime median (ms)','runtime p95 (ms)','events median','events p95'],[[v,x['runtime_s']['n'],1000*x['runtime_s']['median'],1000*x['runtime_s']['p95'],x['events']['median'],x['events']['p95']] for v,x in rt['variants'].items()])
 workload=table(['ID','seed','offset (3s bins)','duration(s)','link','requests','input mean/max','output mean/max'],[[w['id'],w['seed'],w['interval_offset'],w['duration_s'],w['primary_link'],w['features']['request_count'],f"{w['features']['input_mean']:.2f}/{w['features']['input_max']}",f"{w['features']['output_mean']:.2f}/{w['features']['output_max']}"] for w in P['phase_b']['workloads']])
 integrity=f"协议冻结提交 e3887ca，hash `{PH}`。{q['protected_files']} 个旧文件逐字节未变；41项测试通过。Full关闭模式逐字段一致（runtime除外），Stage4 Full记录原样复用；HELIX commit `{HELIX_COMMIT}`、adapter/profile不变。Phase A复用2050个异构点及130个A100点，新增reference=0。Phase B新增{ex['phase_b_unique_physical_points']}个physical points、{ex['physical_attempts']}次attempt、{ex['retries']}次retry、{ex['timeouts']}次timeout、{ex['failed_points']}个failed point。四变体共享grid和reference truth，全部保留ties/no-safe/nonmonotone/unresolved；逐请求drain、SLA单调性和loss identity通过。"
 evidence=[('一句话结论',text['conclusion']),('到底改了什么','以前：只要 Prefill 还活着，Decode 就背完整 Prefill compute debt。现在：按 JB1 自己的进度，仅把尚未执行完的 compute 算成未来 blocking；intrinsic H × input_tokens 仍完整保留。Raw/Legacy原有进度轨迹不变，没有拟合参数。'),
 ('原 conservative trace 有没有被直接缓解',mechanism+'\n\n'+components),('有没有制造新的 optimistic errors',text['safety']+'\n\n'+paired(a)+'\n\nPhase B：\n\n'+paired(b)),
 ('Existing six workloads 上发生了什么','Phase A仅为机制提出后的post-hoc diagnosis。\n\n'+text['phase_a']+'\n\n'+totals(a)),
 ('New held-out workloads 上发生了什么',text['phase_b']+'\n\n'+workload+'\n\n'+totals(b)+'\n\n'+unresolved),
 ('Judgment 是否改善',text['judgment']+'\n\nPhase B四个SLA分别报告，不能将同一physical point的四个标签当作独立重复：\n\n'+judgments(b)),
 ('Capacity 是否改善',text['capacity']+'\n\n'+capacities(b)),('Partition decision 是否改善',text['decision']),
 ('Recommended operating-point safety 是否改善',text['operating']+'\n\n'+loss_denominators(b)),('Raw vs Legacy interaction',text['interaction']),
 ('哪些原问题仍然存在',optimism+'\n\n'+text['reversal']+'\n\n'+limits_text+'\n\n'+integrity),
 ('JB1+ 是否值得作为 journal 的主 evaluator',text['position']+'\n\n'+text['position_reason']),('是否需要再开发 JB1++','**No。** 本次one-shot correction已经完成；不调参数、不增加第二个correction、不扩展矩阵。'+text['stop']+'\n\n完整数据：[technical report](docs/JB1_PLUS_TECHNICAL_REPORT.md)、[summary](results/jb1_plus/summary.json)、[quality checks](results/jb1_plus/quality_checks.json)。')]
 (ROOT/'JB1_PLUS_EVIDENCE_REPORT.md').write_text('\n\n'.join(f'# {i}. {title}\n\n{body}' for i,(title,body) in enumerate(evidence,1))+'\n',encoding='utf-8',newline='\n')
 technical=[('Frozen correction',f"[Protocol](JB1_PLUS_PROTOCOL.md), `config/jb1_plus_protocol.json`, freeze commit e3887ca.\n\n{integrity}"),
 ('Why this mechanism was chosen','The existing h105 trace identified full active-Prefill compute debt as a conservative component. It did not prove that deleting blocking is safe. This experiment tests only remaining compute, retaining intrinsic debt. Publication boundary: JB1 is the specified lightweight evaluator; Legacy is semantic control. Withdrawn unpublished AICCC is not prior publication. Accepted Evaluator-Guided SLA-Aware Layer Partitioning for Heterogeneous LLM Pipelines is prior work; candidate family/evaluator-as-score/search are not new contributions.'),
 ('Mathematical definition','For active Prefill r: d_r=C_r for Raw, d_r=C_r+fixed+queue for Legacy; f_r(t)=1−clip((t−start_r)/d_r,0,1); D_remaining=sum(f_r C_r+H input_tokens_r). Zero duration gives f=0 at/after start. Intrinsic is not scaled. Overhead does not enter debt directly.\n\n'+definitions),
 ('Implementation isolation','New `src/journal_baseline_plus.py` is an isolated copy of the frozen implementation with the debt term, two Prefill state fields and optional trace components added. Default remaining_prefill_blocking=False returns the original version and original output fields. No HELIX querying, new queue simulator, fitted coefficient, safety margin or workload/SLA-specific rule exists. New writes are confined to Stage5 outputs and status/log files.'),
 ('Baseline equivalence test','All41 unit tests pass. Added tests cover clipping/zero duration, complete off-mode outputs including traces and first simultaneous violations, Raw/Legacy with nonzero fixed/queue overhead, representative real profiles, full-drain trajectory/memory equality, both-direction refinement and null labels. Stage4 Full records, including runtime, are copied exactly; sequential PhaseB timing reproduces all scientific output fields except runtime.\n\n'+json.dumps(q['checks'],ensure_ascii=False)),
 ('Phase A existing-corpus diagnosis',text['phase_a']+'\n\n'+totals(a)+'\n\n'+judgments(a)+'\n\nA100 controls (130 old physical points, two SLAs; single candidate, so agreement is not partition-search evidence):\n\n'+totals(control)+'\n\n'+paired(a)),
 ('Conservative mechanism replay',mechanism+'\n\n'+components+'\n\nFull per-epoch comparisons for Raw and Legacy are retained in phase_a_mechanisms.json and mechanisms/*.json.gz; saved reference trace metrics are reused exactly, with zero new reference trace executions.'),
 ('Optimistic mechanism impact',optimism+'\n\n'+text['safety']),
 ('Capacity comparison',text['capacity']+'\n\n'+capacities(a)),
 ('Decision comparison',text['decision']+'\n\n'+text['reversal']+'\n\nComplete192 PhaseA variant decisions and best sets/ranks are in phase_a_decisions.csv; all Full→Remaining paired changes, including worsened cases, are in summary.json.'),
 ('Operating-point comparison',text['operating']+'\n\n'+loss_denominators(a)),
 ('Phase B held-out protocol',workload+'\n\nOffsets count3-second source bins; w204 wraps to0–39. Workloads and exact requests were committed before any correction outputs. Same generator/target .5/filtering/token distributions as Stage3. Only four TPOT thresholds, five heterogeneous shifts, nine fixed initial intensities; max16 additions/workload, four rounds, 500 physical points total. Both-direction transitions across reference and allfour variants share a grid. Failed reference points stay null.\n\n'+unresolved),
 ('Held-out judgment results',text['phase_b']+'\n\n'+judgments(b)+'\n\n'+paired(b)),
 ('Held-out capacity results',text['capacity']+'\n\n'+capacities(b)),
 ('Held-out decision results',text['decision']+'\n\n'+decisions(b)+'\n\n'+loss_denominators(b)),
 ('Runtime / complexity',runtime+'\n\n'+rt['method']+'\n\n'+rt['complexity']+'\n\n'+text['runtime']+' These are CPU planning measurements, not GPU serving speedup. Early-stop event counts may increase because more requests are admitted; the correction has the same full-drain trajectory and asymptotic event structure.'),
 ('Failure cases',text['failure_cases']+'\n\n'+text['reversal']+'\n\nFailed physical points remain explicit in failed_points.json; no failure was converted to unsafe. All changed verdicts and all changed/worsened selection and loss cases remain in paired records. There is no result-driven refit or second correction.'),
 ('Limitations',limits_text+'\n\n'+text['position']+' '+text['position_reason']+'\n\n'+text['stop']+'\n\nReproduction: `run_jb1_plus.py all` resumes missing saved campaign points; `analyze_jb1_plus.py`, `audit_jb1_plus.py mechanisms`, `audit_jb1_plus.py timing`, `verify_jb1_plus.py`, `figure_jb1_plus.py`, `report_jb1_plus.py`. Verification and analysis do not launch HELIX. Protect all earlier results. New main-text candidates are only FigureA (judgment/capacity) and FigureB (held-out decisions/loads), PNG+SVG. Horizontal offsets expose coincident category markers; lines do not interpolate new SLA thresholds. No manuscript sections were written.')]
 (ROOT/'docs/JB1_PLUS_TECHNICAL_REPORT.md').write_text('# JB1+ remaining-Prefill correction: technical evidence\n\n'+'\n\n'.join(f'## {i}. {title}\n\n{body}' for i,(title,body) in enumerate(technical,1))+'\n',encoding='utf-8',newline='\n')
 paths=[ROOT/'JB1_PLUS_EVIDENCE_REPORT.md',ROOT/'docs/JB1_PLUS_TECHNICAL_REPORT.md']
 checks={'passed':True,'evidence_sections':14,'technical_sections':18,'protocol_hash':PH,'headline_numeric_assertions':'A/B O/C, winner and unsafe counts; 500/500 attempts, no failures,37 unresolved; paired72 C removed and10 new O;30 capacity improvements/2 worsening; w202 doubled unsafe load and1/48 to9/48 violations;300% max gap;nonmonotone and censor flags',
  'report_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'source_summary_sha256':hashlib.sha256((OUT/'summary.json').read_bytes()).hexdigest()}
 assert len(re.findall(r'^# \d+\.',paths[0].read_text(encoding='utf-8'),re.M))==14
 assert len(re.findall(r'^## \d+\.',paths[1].read_text(encoding='utf-8'),re.M))==18
 for p in paths:
  for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
   assert (p.parent/link).exists(),link
 write_json(OUT/'report_checks.json',checks)

if __name__=='__main__':main()
