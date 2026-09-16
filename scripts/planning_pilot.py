"""Offline replay with labels exposed only through counted reference calls."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research import *
from planning import plan
from nominal_gap import GRID as NOMINAL_GRID
from partition_ranking import GRID as RANKING_GRID

def main():
 groups=[]
 for path in sorted((ROOT/'results/diagnostic/nominal_gap').glob('*.json')):
  d=json.loads(path.read_text())
  if 'reference_summary' in d:groups.append((d['case']['id'],{0:d},NOMINAL_GRID,[3,5,8]))
 data={}
 for path in sorted((ROOT/'results/diagnostic/partition_ranking').glob('hetero-*.json')):
  d=json.loads(path.read_text())
  if 'reference_summary' not in d:continue
  key=d['case']['id'].split('-shift')[0];data.setdefault(key,{})[d['case']['shift']]=d
 for key,cases in data.items():
  if len(cases)==5:groups.append((key,cases,RANKING_GRID,[5,10,20,40]))
 rows=[]
 for name,cases,loads,budgets in groups:
  lookups={s:{round(r['lambda'],10):r for r in d['rows']} for s,d in cases.items()}
  if any(any(round(v,10) not in table for v in loads) for table in lookups.values()):continue
  e={s:[table[round(v,10)]['evaluator']['safe'] for v in loads] for s,table in lookups.items()}
  evaluator_cost=sum(table[round(v,10)]['evaluator']['runtime_s'] for table in lookups.values() for v in loads)
  oracle=max((v for s,t in lookups.items() for v in loads if t[round(v,10)]['reference']['safe']),default=0.)
  def query(s,j):return lookups[s][round(loads[j],10)]['reference']['safe']
  for budget in budgets:
   for policy in ['fixed_grid','reference_only_adaptive','round_robin','best_first']:
    r=plan(loads,list(cases),e,query,budget,policy);chosen=r['chosen'];value=chosen['load'] if chosen else 0.
    replay_cost=sum(lookups[x['candidate']][round(x['load'],10)]['reference']['runtime_s'] for x in r['trace'])
    e_cost=evaluator_cost if policy in ['round_robin','best_first'] else 0.
    rows.append({'case':name,'policy':policy,'budget':budget,'validated_load':value,'oracle_grid_load':oracle,'oracle_ratio':value/oracle if oracle else None,'simulator_calls':r['reference_calls'],'exhaustive_simulator_calls':len(cases)*len(loads),'evaluator_calls':len(cases)*len(loads) if e_cost else 0,'evaluator_runtime_s':e_cost,'replayed_reference_runtime_s':replay_cost,'estimated_total_planning_runtime_s':replay_cost+e_cost,'chosen_shift':chosen['candidate'] if chosen else None,'trace':r['trace']})
  esafe=[(v,s) for s in cases for j,v in enumerate(loads) if e[s][j]]
  if esafe:
   v,s=max(esafe,key=lambda x:(x[0],-abs(x[1]),-x[1]));safe=lookups[s][round(v,10)]['reference']['safe']
   rows.append({'case':name,'policy':'evaluator_only','budget':0,'reported_load':v,'chosen_shift':s,'reference_safe_at_reported_load':safe,'validated_load_for_scoring':v if safe else 0.,'oracle_grid_load':oracle,'oracle_ratio':v/oracle if safe and oracle else 0.,'simulator_calls':0,'evaluator_calls':len(cases)*len(loads),'estimated_total_planning_runtime_s':evaluator_cost,'exhaustive_simulator_calls':len(cases)*len(loads)})
  rows.append({'case':name,'policy':'reference_exhaustive','budget':len(cases)*len(loads),'validated_load':oracle,'oracle_grid_load':oracle,'oracle_ratio':1. if oracle else None,'simulator_calls':len(cases)*len(loads),'evaluator_calls':0,'estimated_total_planning_runtime_s':sum(t[round(v,10)]['reference']['runtime_s'] for t in lookups.values() for v in loads)})
 write_json(ROOT/'results/diagnostic/planning_pilot/results.json',{'scope':'exploratory replay on fixed predeclared coarse grids; zero optimistic outputs for validation methods is by construction, not a new guarantee; costs sum recorded simulator calls and are not fresh sequential wall-clock measurements','rows':rows})
 print(json.dumps([{k:v for k,v in r.items() if k!='trace'} for r in rows],indent=2))
if __name__=='__main__':main()
