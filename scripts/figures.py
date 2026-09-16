from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research import ROOT
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def main():
 out=ROOT/'results/figures';out.mkdir(parents=True,exist_ok=True)
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
 fig,axes=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
 for ax,case in zip(axes,['a100-s19-slow-decode','a100-s19-fast-decode']):
  path=ROOT/'results/diagnostic/nominal_gap'/(case+'.json')
  if not path.exists():continue
  d=json.loads(path.read_text());rows=[r for r in d['rows'] if r['lambda']<=.06]
  x=[r['lambda'] for r in rows]
  ax.plot(x,[r['reference']['max_tpot_s'] for r in rows],'o-',label='HELIX maximum TPOT',color='#245ab3')
  ax.axhline(.15,color='#c63838',linestyle='--',label='TPOT limit (0.15 s)')
  for r in rows:
   if not r['evaluator']['safe']:ax.plot(r['lambda'],.10,'x',color='#b55900')
  ax.set(title=case.replace('a100-',''),xlabel='Finite-workload intensity',ylabel='Seconds')
  ax.legend(fontsize=8)
 fig.suptitle('Nominal disagreement and nonmonotone reference behavior\nOrange crosses: evaluator rejects (shown at y=0.10 for visibility)',fontsize=12)
 fig.savefig(out/'nominal_reference.png',dpi=180);fig.savefig(out/'nominal_reference.svg');plt.close(fig)
 path=ROOT/'results/diagnostic/partition_ranking/summary.json'
 if path.exists():
  trials=json.loads(path.read_text())['trials']
  if trials:
   fig,axes=plt.subplots(2,2,figsize=(11,7),constrained_layout=True)
   for ax,t in zip(axes.flat,trials):
    for key,color in [('evaluator','#b55900'),('reference','#245ab3')]:
     vals=t[key+'_scores'];x=sorted(map(int,vals));y=[vals[str(s)] for s in x]
     ax.plot(x,y,'o-',label=key,color=color)
    ax.set(title=t['case'],xlabel='Partition shift',ylabel='Largest observed safe intensity');ax.legend()
   for ax in list(axes.flat)[len(trials):]:ax.set_visible(False)
   fig.suptitle('Matched absolute profiles; finite tested family, no global-optimum claim',fontsize=12)
   fig.savefig(out/'partition_ranking.png',dpi=180);fig.savefig(out/'partition_ranking.svg');plt.close(fig)
 path=ROOT/'results/diagnostic/profile_mismatch/summary.json'
 if path.exists():
  groups=[r for r in json.loads(path.read_text())['groups'] if r['source']=='nominal_gap']
  fig,ax=plt.subplots(figsize=(11,4.8),constrained_layout=True);x=np.arange(len(groups))
  ax.bar(x-.18,[r['optimistic'] for r in groups],.36,label='Optimistic',color='#c63838');ax.bar(x+.18,[r['conservative'] for r in groups],.36,label='Conservative',color='#245ab3')
  ax.set_xticks(x,[r['variant'].replace('_',' ') for r in groups],rotation=30,ha='right');ax.set(ylabel='Observed disagreement count',title='Evaluator-only profile stress on nominal diagnostic probes');ax.legend()
  fig.savefig(out/'profile_mismatch.png',dpi=180);fig.savefig(out/'profile_mismatch.svg');plt.close(fig)
 print(out.relative_to(ROOT))
if __name__=='__main__':main()
