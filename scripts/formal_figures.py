"""Minimal descriptive figures; adaptive-grid counts are not probabilities."""
from pathlib import Path
import sys,json,collections
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from formal_core import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def main():
 folder=FORMAL/'figures';folder.mkdir(parents=True,exist_ok=True)
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
 rq1=json.loads((FORMAL/'rq1_reliability/summary.json').read_text());assert rq1['status']=='complete'
 caps=json.loads((FORMAL/'rq2_capacity/summary.json').read_text())['rows']
 decisions=json.loads((FORMAL/'rq3_decision_transfer/summary.json').read_text())['trials']
 stress=json.loads((FORMAL/'rq4_profile_mismatch/summary.json').read_text())
 mitigation=json.loads((FORMAL/'mitigation/results.json').read_text())
 def save(fig,name):
  fig.tight_layout();fig.savefig(folder/(name+'.png'));fig.savefig(folder/(name+'.svg'));plt.close(fig)
  svg=folder/(name+'.svg');svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
 categories=[('heterogeneous','decode'),('heterogeneous','prefill'),('a100','decode'),('a100','relaxed_decode')]
 fig,axes=plt.subplots(1,4,figsize=(12,3.2))
 for ax,(kind,regime) in zip(axes,categories):
  rs=[r for r in rq1['configurations'] if r['kind']==kind and r['regime']==regime]
  vals=np.array([[sum(r['both_safe'] for r in rs),sum(r['optimistic'] for r in rs)],[sum(r['conservative'] for r in rs),sum(r['both_unsafe'] for r in rs)]])
  ax.imshow(vals,cmap='Blues',vmin=0,vmax=max(1,vals.max()))
  for i in range(2):
   for j in range(2):ax.text(j,i,str(vals[i,j]),ha='center',va='center',color='white' if vals[i,j]>.6*vals.max() else 'black',fontsize=13)
  ax.set_xticks([0,1],['R safe','R unsafe']);ax.set_yticks([0,1],['E safe','E unsafe']);ax.set_title(kind+'\n'+regime.replace('_',' '))
 fig.suptitle('Paired point counts on adaptively refined grids',y=1.05);save(fig,'01_reliability')
 fig,ax=plt.subplots(figsize=(6.5,5))
 for kind,regime in categories:
  rs=[r for r in caps if r['kind']==kind and r['regime']==regime and r['status']=='ok' and r['evaluator']['largest_safe'] and r['reference']['largest_safe']]
  ax.scatter([r['reference']['largest_safe'] for r in rs],[r['evaluator']['largest_safe'] for r in rs],label=kind+' / '+regime.replace('_',' '),alpha=.7,s=30)
  unresolved=[r for r in rs if not r['precise_sampled_gap']]
  ax.scatter([r['reference']['largest_safe'] for r in unresolved],[r['evaluator']['largest_safe'] for r in unresolved],marker='x',color='black',s=45)
 valid=[r for r in caps if r.get('relative_gap') is not None]
 bounds=[r[m]['largest_safe'] for r in valid for m in ['evaluator','reference']]
 if bounds:ax.plot([min(bounds),max(bounds)],[min(bounds),max(bounds)],'k--',lw=1)
 ax.set_xscale('log');ax.set_yscale('log');ax.set_xlabel('Largest observed reference-safe intensity');ax.set_ylabel('Largest observed evaluator-safe intensity');ax.legend(fontsize=8);ax.set_title('Sampled capacity comparison (×: unresolved boundary)');save(fig,'02_capacity')
 variants=['nominal','prefill_minus5','prefill_minus10','prefill_minus20','decode_minus5','decode_minus10','decode_minus20','both_minus5','both_minus10','both_minus20','l4x2_minus10']
 trials=sorted({(r['group'],r['regime']) for r in decisions});array=np.full((len(trials),len(variants)),np.nan)
 lookup={(r['group'],r['regime'],r['variant']):r for r in stress['decision_trials']}
 for i,(g,regime) in enumerate(trials):
  for j,v in enumerate(variants):
   quality=lookup.get((g,regime,v),{}).get('normalized_reference_quality')
   if quality is not None:array[i,j]=quality
 fig,ax=plt.subplots(figsize=(10,6));im=ax.imshow(array,vmin=0,vmax=1,cmap='YlGnBu',aspect='auto');fig.colorbar(im,ax=ax,label='Selected candidate capacity / best tested capacity')
 ax.set_xticks(range(len(variants)),[v.replace('_minus',' −').replace('nominal','Nominal') for v in variants],rotation=45,ha='right');ax.set_yticks(range(len(trials)),[g.split('-')[0]+' / '+r for g,r in trials]);ax.set_title('Decision transfer on a common grid (blank: no defined quality)')
 for i in range(len(trials)):
  for j in range(len(variants)):
   if np.isfinite(array[i,j]):ax.text(j,i,f'{array[i,j]:.2f}',ha='center',va='center',fontsize=7,color='white' if array[i,j]>.7 else 'black')
 save(fig,'03_decision_stress')
 fig,axes=plt.subplots(1,2,figsize=(11,4));names=CONFIG['mitigations'];labels=['E only','25% margin','20% derating','4 scenarios','Point validation','Boundary ≤5']
 for ax,bias in zip(axes,[1.,.9]):
  rs=[r for r in mitigation['rows'] if r['candidate_count']==5 and r['bias']==bias]
  for j,name in enumerate(names):
   a=[r for r in rs if r['policy']==name];values=[r['normalized_usable_quality'] for r in a if r['normalized_usable_quality'] is not None]
   ax.scatter([j]*len(values),values,s=20,alpha=.65);ax.plot([j-.2,j+.2],[statistics.mean(values)]*2,color='black',lw=2) if values else None
  ax.set_xticks(range(len(names)),labels,rotation=40,ha='right');ax.set_ylim(-.04,1.05);ax.set_title('Nominal profiles' if bias==1 else 'Both profiles −10%');ax.set_ylabel('Usable selected load / best tested reference load')
 save(fig,'04_mitigation')
 write_json(folder/'manifest.json',{'protocol_hash':PROTOCOL_HASH,'figures':['01_reliability','02_capacity','03_decision_stress','04_mitigation'],'notes':['Counts describe the frozen adaptive sample, not population risk.','Capacity scatter omits all-unsafe configurations; full tables retain them.','Decision quality uses the largest observed safe load even for nonmonotone sequences; see flags in tables.','Mitigation shows main five-candidate trials only; line is mean over defined qualities, dots are individual trials.']})
if __name__=='__main__':main()
