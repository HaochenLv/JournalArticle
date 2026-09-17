"""Engineering controls, without an optimizer novelty claim or test-label tuning."""
from pathlib import Path
import sys,json,collections,time,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from formal_core import *

def run_group(g):
 pth=FORMAL/'groups'/(g['id']+'.json')
 if not pth.exists():return []
 data=json.loads(pth.read_text())
 if data['status']!='complete' or any(r['status']!='ok' for r in data['rows']):return []
 dest=FORMAL/'mitigation/groups'/(g['id']+'.json');sha=fingerprint(data)
 if dest.exists():
  old=json.loads(dest.read_text());assert old['source_hash']==sha;return old['rows']
 wd,base=load_workload(g['workload']);grid=data['grid'];ps={s:pipeline(g['link'],s,g['kind']=='heterogeneous') for s in g['shifts']};lookup={(r['shift'],r['intensity']):r for r in data['rows']};cache={};profiles={};rows=[]
 for regime,sla in slas(g).items():
  def evaluate_grid(pp,dd):
   key=(regime,pp,dd)
   if key not in cache:
    prof=profiles.setdefault((pp,dd),CachedProfiles(pp,dd));scores={};cost=0.
    for s in g['shifts']:
     scores[s]=[]
     for v in grid:
      if pp==dd==1.:e=lookup[s,v]['evaluator'][regime]
      else:e=jb(ps[s],scale_workload(base,v),sla,prof)
      scores[s].append(e['safe']);cost+=e['runtime_s']
    cache[key]=(scores,cost)
   return cache[key]
  refs={s:[lookup[s,v]['reference'][regime]['safe'] for v in grid] for s in g['shifts']}
  rscore={s:max((v for v,b in zip(grid,flags) if b),default=0.) for s,flags in refs.items()};oracle=max(rscore.values())
  def select(scores):
   values=[(v,s,j) for s,flags in scores.items() for j,(v,b) in enumerate(zip(grid,flags)) if b]
   return max(values,key=lambda x:(x[0],-abs(x[1]),-x[1])) if values else None
  for bias in [1.,.9]:
   e,e_cost=evaluate_grid(bias,bias);inflated,margin_cost=evaluate_grid(bias*1.25,bias*1.25)
   ec={s:max((v for v,b in zip(grid,flags) if b),default=0.) for s,flags in e.items()}
   derated={s:[v<=ec[s]*.8 for v in grid] for s in e}
   corner1,c1=evaluate_grid(bias*1.25,bias);corner2,c2=evaluate_grid(bias,bias*1.25)
   scenarios={s:[all(t[s][j] for t in [e,inflated,corner1,corner2]) for j in range(len(grid))] for s in e}
   for name,scores,ecost,ecalls in [('evaluator_only',e,e_cost,len(grid)*len(e)),('compute_margin_25pct',inflated,margin_cost,len(grid)*len(e)),('capacity_derating_20pct',derated,e_cost,len(grid)*len(e)),('four_scenarios',scenarios,e_cost+margin_cost+c1+c2,4*len(grid)*len(e)),('selected_point_reference',e,e_cost,len(grid)*len(e)),('selected_partition_boundary_reference',e,e_cost,len(grid)*len(e))]:
    chosen=select(scores);queries=[];query_cost=0.
    if chosen and name in ['selected_point_reference','selected_partition_boundary_reference']:
     v,s,j=chosen;seen={};limit=1 if name=='selected_point_reference' else CONFIG['boundary_validation_budget']
     for _ in range(limit):
      safe=refs[s][j];seen[j]=safe;queries.append({'shift':s,'intensity':grid[j],'safe':safe});query_cost+=lookup[s,grid[j]]['reference_physical_runtime_s']
      direction=1 if safe else -1;possible=[k for k in range(j+direction,len(grid) if direction==1 else -1,direction) if k not in seen]
      if not possible:possible=[k for k in range(len(grid)) if k not in seen]
      if not possible:break
      j=possible[0]
     valid=[j for j,b in seen.items() if b];chosen=(grid[max(valid)],s,max(valid)) if valid else None
    safe=refs[chosen[1]][chosen[2]] if chosen else None;usable=chosen[0] if chosen and safe else 0.
    selective=name.startswith('selected_')
    row={'group':g['id'],'regime':regime,'kind':g['kind'],'role':g['role'],'bias':bias,'policy':name,'candidate_count':len(g['shifts']),'grid_points':len(grid),'chosen_shift':chosen[1] if chosen else None,'reported_intensity':chosen[0] if chosen else None,'output_reference_safe':safe,'selected_optimistic':bool(chosen and not safe),'validated_usable_intensity':usable,'reference_oracle_intensity':oracle,'normalized_usable_quality':usable/oracle if oracle else None,'reference_regret':oracle-usable if oracle else None,'abstention':chosen is None,'reference_calls':len(queries),'evaluator_calls':ecalls,'evaluator_runtime_s':ecost,'replayed_reference_runtime_s':query_cost,'estimated_planning_runtime_s':ecost+query_cost,'query_trace':queries,'grid_optimistic':None if selective else sum(a and not b for s in scores for a,b in zip(scores[s],refs[s])),'grid_conservative':None if selective else sum(not a and b for s in scores for a,b in zip(scores[s],refs[s])),'grid_denominator':None if selective else len(grid)*len(scores)}
    rows.append(row)
 print('MITIGATION_GROUP',g['id'],len(rows),flush=True);write_json(dest,{'protocol_hash':PROTOCOL_HASH,'source_hash':sha,'rows':rows});return rows

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');ap.add_argument('--workers',type=int,default=2);args=ap.parse_args();check_pins()
 from concurrent.futures import ProcessPoolExecutor
 with ProcessPoolExecutor(max_workers=args.workers) as pool:results=list(pool.map(run_group,groups()))
 missing=[g['id'] for g,r in zip(groups(),results) if not r]
 if missing and not args.partial:raise SystemExit('Missing groups: '+','.join(missing))
 rows=[r for group in results for r in group];write_json(FORMAL/'mitigation/results.json',{'protocol_hash':PROTOCOL_HASH,'status':'partial' if missing else 'complete','missing_groups':missing,'runtime_scope':'sum of observed component runtimes; not fresh sequential policy timing; selective validation only labels queried outputs, so full-grid confusion is undefined','rows':rows});csv_write(FORMAL/'mitigation/results.csv',rows)
 print('MITIGATION_TOTAL',len(rows))
