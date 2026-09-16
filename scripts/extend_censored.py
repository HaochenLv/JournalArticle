"""Extend only reference-right-censored cases; do not invent a capacity edge."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research import ROOT
from nominal_gap import run_case,GRID
from partition_ranking import GRID as PGRID
from concurrent.futures import ProcessPoolExecutor

def run(item):
 case,folder=item
 return run_case(case,PGRID if folder=='partition_ranking' else GRID,4 if folder=='partition_ranking' else 2,folder)
if __name__=='__main__':
 jobs=[]
 for folder in ['nominal_gap','partition_ranking']:
  for p in (ROOT/'results/diagnostic'/folder).glob('*.json'):
   d=json.loads(p.read_text())
   if isinstance(d,dict) and d.get('reference_summary',{}).get('right_censored'):jobs.append((d['case'],folder))
 print('Extending',len(jobs),'reference-censored cases',flush=True)
 with ProcessPoolExecutor(max_workers=3) as pool:list(pool.map(run,jobs))
