"""Matched-input five-shift diagnostics using absolute HELIX profiles.

SLAs differ deliberately from the analytical conference model: original .28 s
TTFT is infeasible for long prompts under absolute group-device profiles.
"""
from pathlib import Path
import sys,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research import *
from nominal_gap import run_case

CASES=[{'id':f'hetero-s{seed}-{regime}-shift{shift}','seed':seed,'placement':'fast','shift':shift,'hetero':True,'ttft':4.2,'tpot':tpot}
 for seed in [0,7] for regime,tpot in [('decode',.30),('prefill',10.)] for shift in [-2,-1,0,1,2]]
GRID=[.003,.006,.010,.015,.020,.030,.045,.0675,.10,.15,.225,.34,.51,.77,1.16,2.32,4.64,9.28,18.56]

def run(case):return run_case(case,GRID,4,'partition_ranking')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--case',type=int);parser.add_argument('--seed',type=int);parser.add_argument('--workers',type=int,default=4);args=parser.parse_args()
 cases=[c for c in CASES if args.seed is None or c['seed']==args.seed]
 if args.case is not None:run(cases[args.case])
 else:
  from concurrent.futures import ProcessPoolExecutor
  with ProcessPoolExecutor(max_workers=args.workers) as pool:list(pool.map(run,cases))
