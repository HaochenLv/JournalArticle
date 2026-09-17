"""Read-only recomputation of Stage 3 evidence; write only quality manifests."""
from stage3_evidence import *
import csv, re, subprocess
from datetime import datetime, timezone

def main():
    check_pins(); protected=snapshot()
    integrity=json.loads((OUT/'integrity_checks.json').read_text())
    assert integrity['driver_sha256']==hashlib.sha256((ROOT/'scripts/stage3_evidence.py').read_bytes()).hexdigest()
    rows=[]
    for g in groups():
        state=json.loads((FORMAL/'groups'/(g['id']+'.json')).read_text())
        result=json.loads((OUT/'groups'/(g['id']+'.json')).read_text())
        assert result['source_hash']==fingerprint(state)
        base={(r['shift'],r['intensity'],r['regime']):r for r in flatten(state)}
        assert len(result['rows'])==len(base)
        assert len({(r['shift'],r['intensity'],r['regime']) for r in result['rows']})==len(base)
        for r in result['rows']:
            b=base[r['shift'],r['intensity'],r['regime']]
            for key in ['reference_safe','reference_cache_key','workload_fingerprint','scaled_workload_fingerprint','partition_fingerprint','profile_fingerprint','case_id']:
                assert r[key]==b[key]
            assert r['raw_safe']==b['evaluator_safe']
            assert r['evaluator_safe']==r['legacy_result']['safe']
            assert r['grid_fingerprint']==fingerprint(state['grid'])
            assert r['point_id']==fingerprint([r['group'],r['shift'],r['intensity'],r['regime']])
            assert r['sla_label']==label(r['regime'])
        rows.extend(result['rows'])
    assert len(rows)==3268
    changed=[r for r in rows if r['raw_safe']!=r['evaluator_safe']]
    assert len(changed)==53 and all(r['raw_safe'] and not r['evaluator_safe'] for r in changed)
    summary=json.loads((OUT/'summary.json').read_text())
    for c in summary['counts']:
        subset=[r for r in rows if r['kind']==c['kind'] and r['regime']==c['regime']]
        key='raw_safe' if c['variant']=='raw' else 'evaluator_safe'
        for k,v in matrix([dict(r,evaluator_safe=r[key]) for r in subset]).items():assert c[k]==v
    for c in summary['capacity']:
        subset=[r for r in rows if r['case_id']==c['case_id']]
        for v,k in [('raw','raw'),('legacy','evaluator'),('reference','reference')]:assert c[v]==safe_summary(subset,k)
    for v in ['raw','legacy']:
        assert sum(c[v]['all_unsafe'] for c in summary['capacity'])==8
        assert sum(c[v]['nonmonotone'] for c in summary['capacity'])==0
        assert sum(c[v]['right_censored'] for c in summary['capacity'])==0
    assert sum(c['reference']['nonmonotone'] for c in summary['capacity'])==3
    trials=json.loads((OUT/'decision_summary.json').read_text())['trials']
    for t in trials:
        cs=[c for c in summary['capacity'] if c['group']==t['group'] and c['regime']==t['regime']]
        expected=decision({c['shift']:c[t['variant']]['largest_safe'] or 0 for c in cs},
                          {c['shift']:c['reference']['largest_safe'] or 0 for c in cs})
        # Normalize integer candidate keys without depending on JSON key order.
        for k,v in expected.items():assert t[k]==json.loads(json.dumps(v)), (t['group'],t['regime'],k)
        assert t['mismatch_type']==mismatch(t)
    for v,strict,tie,winners in [('raw',4,2,6),('legacy',3,1,8)]:
        ts=[t for t in trials if t['variant']==v]
        assert len(ts)==12 and sum(t['winner_agrees'] for t in ts)==winners
        assert sum(t['mismatch_type']=='strict best-set mismatch' for t in ts)==strict
        assert sum(t['mismatch_type']=='tie-break mismatch' for t in ts)==tie
    losses=json.loads((FORMAL/'decision_loss_decomposition.json').read_text())
    for r in losses['rows']:
        selected=str(r['selected_shift']); es=r['evaluator_scores']; rs=r['reference_scores']
        assert r['evaluator_recommended_intensity']==es[selected]
        assert r['reference_capacity_selected_partition']==rs[selected]
        assert r['reference_best_capacity']==max(rs.values())
        base=next(x for x in rows if x['group']==r['group'] and x['regime']==r['regime'] and x['shift']==r['selected_shift'] and x['intensity']==r['evaluator_recommended_intensity'])
        assert r['exact_recommendation_reference_safe']==base['reference_safe']
        assert math.isclose(r['partition_selection_regret'],1-rs[selected]/max(rs.values()))
        assert math.isclose(r['operating_point_loss'],1-es[selected]/max(rs.values()))
        assert math.isclose(r['safe_operating_point_loss'],1-(es[selected] if base['reference_safe'] else 0)/max(rs.values()))
    assert len(losses['rows'])==24 and len(losses['mitigation_main_rows'])==144
    mit=json.loads((FORMAL/'mitigation/results.json').read_text())['rows']
    for r in losses['mitigation_main_rows']:
        old=next(x for x in mit if all(x[k]==r[k] for k in ['group','regime','bias','policy']))
        assert r['chosen_shift']==old['chosen_shift'] and r['reported_intensity']==old['reported_intensity']
        if old['normalized_usable_quality'] is not None:assert math.isclose(r['safe_operating_point_loss'],1-old['normalized_usable_quality'])
    stress=json.loads((FORMAL/'rq4_profile_mismatch/summary.json').read_text())
    stress_caps=json.loads((FORMAL/'rq4_profile_mismatch/capacity.json').read_text())
    assert stress['rows']==35688 and len(mit)==336
    audit=json.loads((FORMAL/'mitigation_derating_audit/summary.json').read_text())
    for r in audit['rows']:
        state=json.loads((FORMAL/'groups'/(r['group']+'.json')).read_text())
        variant='nominal' if r['bias']==1. else 'both_minus10'
        cs=[c for c in stress_caps if c['group']==r['group'] and c['regime']==r['regime'] and c['variant']==variant]
        pairs=[(v,c['shift']) for c in cs for v in state['grid'] if v<=(c['evaluator']['largest_safe'] or 0)*.8]
        chosen=max(pairs,key=lambda x:(x[0],-abs(x[1]),-x[1])) if pairs else (None,None)
        assert chosen==(r['grid_snapped_output'],r['chosen_shift'])
        if r['original_intensity'] is not None:
            assert math.isclose(r['target_intensity'],r['original_intensity']*.8)
            assert math.isclose(r['realized_derating'],1-r['grid_snapped_output']/r['original_intensity'])
    for s in audit['summary']:
        rs=[r for r in audit['rows'] if r['bias']==s['bias']]; vals=[r['realized_derating'] for r in rs if r['realized_derating'] is not None]
        assert len(rs)==s['cases']==28 and len(vals)==s['defined_realized_derating']
        assert (min(vals),statistics.median(vals),max(vals))==(s['min'],s['median'],s['max'])
    for path,n in [(OUT/'raw.csv',3268),(OUT/'capacity.csv',76),(OUT/'decision_summary.csv',24),
                   (FORMAL/'decision_loss_decomposition.csv',24),(FORMAL/'decision_loss_mitigation.csv',144),(FORMAL/'mitigation_derating_audit.csv',56)]:
        with path.open(encoding='utf-8',newline='') as f:assert len(list(csv.DictReader(f)))==n
    docs=[ROOT/p for p in ['STAGE3_EVIDENCE_REPORT.md','FORMAL_EVIDENCE_REPORT.md','docs/LEGACY_PROGRESS_SENSITIVITY.md','docs/DECISION_LOSS_DECOMPOSITION.md','docs/MITIGATION_INTERPRETATION_AUDIT.md','docs/CLAIM_BOUNDARY.md','paper/OUTLINE.md']]
    for p in docs:
        text=p.read_text(encoding='utf-8')
        assert 'Prefill-oriented' not in text and 'Decode-tight' not in text
        for link in re.findall(r'\]\(([^)]+)\)',text):
            if '://' not in link:assert (p.parent/link.split('#')[0]).exists(),(p,link)
    assert len(re.findall(r'^# \d+\.',(ROOT/'STAGE3_EVIDENCE_REPORT.md').read_text(encoding='utf-8'),re.M))==18
    figdir=FORMAL/'figures';manifest=json.loads((figdir/'manifest.json').read_text())
    for name in manifest['figures']:
        text=(figdir/(name+'.svg')).read_text(encoding='utf-8')
        assert 'Prefill-oriented' not in text
        assert (figdir/(name+'.png')).stat().st_size>10000
    svg=(figdir/'03_decision_stress.svg').read_text(encoding='utf-8')
    assert '0.79 S' in svg and '0.90 T' in svg and '0.74 T' in svg
    svg=(figdir/'04_mitigation.svg').read_text(encoding='utf-8')
    assert 'Conditional reference-validation replay' in svg and '20%-target, grid snapped' in svg
    for policy in CONFIG['mitigations']:
        for bias in [1.,.9]:assert len([r for r in mit if r['policy']==policy and r['bias']==bias and r['candidate_count']==5])==12
    suite=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,capture_output=True,text=True)
    tests=suite.stdout+suite.stderr
    assert suite.returncode==0, tests
    assert 'Ran 31 tests' in tests and tests.rstrip().endswith('OK')
    quality=json.loads((FORMAL/'quality_checks.json').read_text())
    assert quality['logical_paired_points']==3268 and quality['failed_points']==0 and quality['stress_errors']==0
    assert protected_manifest()==protected
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in docs}
    hashes.update({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in figdir.glob('*') if p.is_file()})
    report={'stage':3,'checked_utc':datetime.now(timezone.utc).isoformat(),'passed':True,'tests_passed':31,
        'new_reference_runs':0,'reference_records_reused':1634,'paired_control_judgments':3268,
        'protected_files_unchanged':len(protected),'protocol_hash':PROTOCOL_HASH,
        'raw_strict_mismatches':4,'raw_tie_break_mismatches':2,'legacy_strict_mismatches':3,'legacy_tie_break_mismatches':1,
        'stress_rows_preserved':35688,'mitigation_rows_preserved':336,'loss_rows':24,'mitigation_loss_rows':144,'derating_cases':56,
        'source_fingerprints_grids_ids_labels_preserved':True,'all_capacity_sequences_and_decisions_recomputed':True,
        'derating_outputs_and_shifts_independently_recomputed':True,'report_links_valid':True,'stage3_sections':18,
        'figure_data_inputs_checked':True,'figures_visually_reviewed_at_freeze':['01_reliability','02_capacity','03_decision_stress','04_mitigation','optimistic_h103_a100_timeline','conservative_h105_a100_timeline','reversal_h101_shift0_timeline'],
        'test_output_sha256':hashlib.sha256(tests.encode()).hexdigest(),
        'assessment':'Yes, but modified','experiments_remaining':0,'sha256':hashes}
    write_json(FORMAL/'stage3_quality_checks.json',report)
    write_json(FORMAL/'final_review_checks.json',{'stage':3,'supersedes':'Stage 2 review retained in Git history',**report})
    print(json.dumps({k:v for k,v in report.items() if k!='sha256'},indent=2))

if __name__=='__main__':main()
