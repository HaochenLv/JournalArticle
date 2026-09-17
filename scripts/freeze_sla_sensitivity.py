"""Freeze Stage 4 inputs before any new SLA judgments are inspected."""
from pathlib import Path
import sys, json, hashlib, subprocess, platform, importlib.metadata, datetime
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from formal_core import groups, fingerprint, CONFIG, load_workload, pipeline, asdict, check_pins
from host_execution import host_metadata

def main():
    check_pins()
    out = ROOT / 'results/sla_sensitivity'
    assert not (out / 'protocol_snapshot.json').exists(), 'Already frozen; do not overwrite'
    source = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    assert source == '69a6b175b5be6788b6448f23edbf1366c1f626c3'
    gs = [g for g in groups() if g['kind']=='heterogeneous' and g['role']=='primary']
    expected = [51,53,46,41,49,50]
    for g,n in zip(gs,expected):
        state=json.loads((ROOT/'results/formal/groups'/ (g['id']+'.json')).read_text())
        assert len(state['grid'])==n
        g.update(original_grid=state['grid'], original_grid_size=n,
                 workload_fingerprint=load_workload(g['workload'])[0]['workload_fingerprint'],
                 partition_fingerprints={str(s):fingerprint(asdict(pipeline(g['link'],s,True))) for s in g['shifts']})
    slas=[{'id':f'TTFT{t:g}_TPOT{p:g}','ttft_s':t,'tpot_s':p} for t,p in
          [(5.2,.3),(5.2,.6),(5.2,1.2),(5.2,2.4),(5.2,5.),(5.2,10.),(4.68,1.2),(4.68,10.)]]
    protocol={'protocol_id':'FI-SLA-SENSITIVITY-v1','source_commit':source,
      'study':'Post-Stage-3 controlled parameter sensitivity supplement on the same six held-out workloads; not independent held-out evaluation',
      'groups':gs,'slas':slas,'candidate_shifts':[-2,-1,0,1,2],
      'semantics':{'raw':{'fixed_in_progress':False},'legacy':{'fixed_in_progress':True}},
      'fixed_overhead_s':.005,'queue_overhead_s':0.,
      'unchanged':'model, profiles, workload sequence and scaling, partition builder, memory, network, topology, intrinsic and blocking accounting, event processing and block size',
      'profile_fingerprint':CONFIG['profile_fingerprint'],'baseline_sha256':CONFIG['baseline_sha256'],
      'refinement':{'relative_resolution':.025,'midpoint':'round(sqrt(lower*upper),10)',
        'intervals':'union of both-direction adjacent boolean verdict changes across all five shifts, eight SLAs, Raw/Legacy/Reference; failed labels remain null and do not create a transition',
        'priority':'descending log(upper/lower), then ascending lower',
        'max_added_intensities_per_workload':24,'max_rounds':6,'max_new_unique_physical_points':720,
        'stop':['no unresolved transition','24 added intensities','six rounds','no new legal midpoint'],
        'range':'within original Stage 3 minimum and maximum only','fairness':'each selected intensity is applied to all five candidates and all eight SLAs and both evaluator semantics',
        'unresolved':'retain every unselected and final unresolved interval; no outcome-driven budget extension'},
      'reference':{'reuse_original_physical_points':1450,'reclassify':'immutable aligned per-request TTFT and max TPOT; do not add overhead again',
        'timeout_s':600,'retry_count':1,'failed_verdict':None,'full_drain_required':True,
        'cache':'old references read-only; new executions stored only under results/sla_sensitivity/reference'},
      'scheduler':{'worker_ceiling':12,'memory_budget_gib':24,'reserve_gib':6,
        'cost_rule':'ceil((512 + .30 * output_tokens)/256)*256 MiB',
        'source':'results/formal/desktop_parallel12_change.json; src/memory_scheduler.py'},
      'gate':'Before refinement, exact old-grid Raw, Legacy and reference labels, scores, best sets and selected decisions must reproduce Stage 3; full SLA monotonicity required',
      'tie_break':'prefer smaller absolute shift, then negative shift',
      'capacity':'largest observed safe intensity; retain full sequence, no-safe, censoring, nonmonotonicity and all transitions; null gaps when either capacity undefined',
      'decision':'agreement iff selected in reference-best; disjoint best sets => strict mismatch; overlap but selected outside => tie-break mismatch; abstention/no-safe/failed separate',
      'loss':{'partition':'1-S/B','operating':'1-L/B','allocation':'(S-L)/B','safe_usable':'L if exact reference-safe else 0 for unsafe/abstention; null if failed','safe_loss':'1-safe_usable/B','undefined':'B=0 or missing required quantities => null'},
      'output_schema':{'points':'group,shift,intensity,input fingerprints,reference provenance,status,attempts,evaluator[semantics][SLA] including complete first_violations,reference[SLA] including per-request violation aggregate',
        'raw.csv':'one row per physical point x SLA x semantics, including failed cases',
        'judgment.csv':'workload x SLA x semantics confusion counts and paired denominator',
        'capacity.csv':'workload x candidate x SLA x semantics full verdict sequence, bracket flags and signed gaps',
        'decisions.csv':'workload x SLA x semantics best sets, selection, rank and mismatch',
        'operating_points.csv':'B,S,L, exact recommendation safety, violations and loss decomposition',
        'other':['source_manifest.json','protocol_snapshot.json','execution_summary.json','summary.json','quality_checks.json','refinement_history.json','failed_points.json']},
      'publication_boundary':'JB1 is the explicitly specified lightweight evaluator; Legacy is implementation-semantic sensitivity. Withdrawn unpublished AICCC is not prior publication. Accepted Evaluator-Guided SLA-Aware Layer Partitioning for Heterogeneous LLM Pipelines is prior work; shift family and evaluator-guided search are not new contributions.'}
    def save(path,value):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    save(ROOT/'config/sla_sensitivity_protocol.json',protocol)
    paths=[]
    for folder in ['results/formal','results/raw_reference','src']:
        paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.extend(ROOT/p for p in ['config/formal_protocol.json','docs/FORMAL_EXPERIMENT_PROTOCOL.md','docs/LEGACY_PROGRESS_SENSITIVITY.md','docs/DECISION_LOSS_DECOMPOSITION.md','docs/MECHANISM_ANALYSIS.md','docs/CLAIM_BOUNDARY.md','STAGE3_EVIDENCE_REPORT.md','FORMAL_EVIDENCE_REPORT.md'])
    manifest={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}
    save(out/'source_manifest.json',manifest)
    save(out/'protocol_snapshot.json',{'protocol':protocol,'protocol_hash':fingerprint(protocol),'config_sha256':hashlib.sha256((ROOT/'config/sla_sensitivity_protocol.json').read_bytes()).hexdigest(),
         'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_manifest_hash':fingerprint(manifest),
         'environment':{'host':host_metadata(),'dependencies':{p:importlib.metadata.version(p) for p in ['networkx','matplotlib','numpy']},
         'runtime_note':'Original desktop venv launcher points to an unavailable Python executable. Use bundled Python 3.12 with the existing pinned venv site-packages; no scientific source changes.'}})
    print(json.dumps({'protocol_hash':fingerprint(protocol),'protected_files':len(manifest),'original_points':sum(expected)*5,'environment':host_metadata()}))

if __name__=='__main__':main()
