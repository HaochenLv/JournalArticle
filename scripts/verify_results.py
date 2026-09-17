"""Validate the completed exploratory matrix before publishing its summaries."""
from pathlib import Path
import sys,json,csv,gzip,collections,subprocess
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
from research import ROOT,fingerprint,write_json
from partition_ranking import GRID

def main():
 case_counts={};cases={};pairs={}
 for folder,expected in [('nominal_gap',10),('partition_ranking',20)]:
  ds=[]
  for path in (ROOT/'results/diagnostic'/folder).glob('*.json'):
   d=json.loads(path.read_text())
   if not isinstance(d,dict) or 'reference_summary' not in d:continue
   assert not d['reference_summary']['right_censored'],path
   assert any(not r['reference']['safe'] for r in d['rows']),path
   assert len({r['lambda'] for r in d['rows']})==len(d['rows'])
   assert max(r['evaluator']['events'] for r in d['rows'])<20_000
   if folder=='partition_ranking':assert set(GRID)<={r['lambda'] for r in d['rows']}
   for r in d['rows']:
    rawpath=ROOT/'results/raw_reference'/(r['reference']['cache_key']+'.json.gz')
    with gzip.open(rawpath,'rt') as f:raw=json.load(f)
    assert fingerprint(raw['inputs'])==r['reference']['cache_key']
    assert raw['summary']['safe']==r['reference']['safe']
   ds.append(d);cases[d['case']['id']]=d
  assert len(ds)==expected,(folder,len(ds));case_counts[folder]=len(ds);pairs[folder]=sum(len(d['rows']) for d in ds)
 with (ROOT/'results/diagnostic/profile_mismatch/trials.csv').open() as f:mr=list(csv.DictReader(f))
 assert not any(r['disagreement']=='error' for r in mr)
 for name,d in cases.items():
  rows=[r for r in mr if r['case']==name];byvariant=collections.defaultdict(list)
  for r in rows:byvariant[r['variant']].append(r)
  assert len(byvariant)==(11 if d['case']['hetero'] else 10)
  expected={r['lambda']:r['reference']['cache_key'] for r in d['rows']}
  for variant,rs in byvariant.items():
   assert len(rs)==len(expected)
   assert {float(r['lambda']):r['reference_cache_key'] for r in rs}==expected
 pilot=json.loads((ROOT/'results/diagnostic/planning_pilot/results.json').read_text())['rows']
 for r in pilot:
  if 'trace' not in r:continue
  assert len(r['trace'])==r['simulator_calls']<=r['budget']
  assert len({(x['candidate'],x['load']) for x in r['trace']})==len(r['trace'])
  if r['validated_load']:
   assert any(x['safe'] and x['load']==r['validated_load'] and x['candidate']==r['chosen_shift'] for x in r['trace'])
  assert 0<=r['oracle_ratio']<=1
 end=[]
 for repo in ['sla-aware-evaluator','SLA-Aware-Layer-Partitioning']:
  path=ROOT.parent/repo
  end.append({'repository':repo,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=path,text=True).strip(),'status_short':subprocess.check_output(['git','status','--short'],cwd=path,text=True)})
 assert end==json.loads((ROOT/'results/reproduction/repository_state_start.json').read_text())
 write_json(ROOT/'results/reproduction/repository_state_end.json',end)
 result={'case_counts':case_counts,'paired_probes':pairs,'mismatch_rows':len(mr),'mismatch_run_errors':0,'planning_rows':len(pilot),'raw_reference_records':len(list((ROOT/'results/raw_reference').glob('*.json.gz'))),'original_repositories_unchanged':True,'checks':'case completeness; observed reference failures; common ranking grid; event budget; raw fingerprints/verdicts; mismatch coverage and immutable reference keys; query budgets and validated outputs; old repository HEAD/status'}
 write_json(ROOT/'results/reproduction/data_integrity.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
