"""Two compact main-text candidates, drawn only from saved analysis."""
from jb1_plus_common import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

STYLE={'Raw-Full':('#2563a6','--','o'),'Raw-Remaining':('#2563a6','-','^'),'Legacy-Full':('#cf701e','--','s'),'Legacy-Remaining':('#cf701e','-','D')}
def draw(ax,rows,sids,field,label,percent=False,counts=False):
 for i,v in enumerate(VARIANTS):
  data=[next(r for r in rows if r['variant']==v and r['sla']==sid) for sid in sids]
  y=[field(r) for r in data];c,ls,m=STYLE[v]
  ax.plot([j+(i-1.5)*.045 for j in range(len(sids))],[x*100 if percent and x is not None else x for x in y],color=c,ls=ls,marker=m,markersize=5,lw=1.5,label=v)
 ax.set_ylabel(label);ax.grid(axis='y',alpha=.22);ax.spines[['top','right']].set_visible(False)
 ax.set_xticks(range(len(sids)),[s.replace('TTFT5.2_TPOT','').replace('TTFT4.68_TPOT','4.68 / ') for s in sids],rotation=30 if len(sids)>4 else 0,ha='right' if len(sids)>4 else 'center')
 ax.set_xlabel('TPOT (s); TTFT = 5.2 unless shown')
 if counts:ax.set_ylim(-.15,4.3);ax.set_yticks(range(5))

def main():
 s=read(OUT/'summary.json');ex=read(OUT/'execution_summary.json');folder=OUT/'figures';folder.mkdir(exist_ok=True)
 plt.rcParams.update({'font.size':9,'axes.titlesize':11,'svg.fonttype':'none'})
 fig,axes=plt.subplots(2,3,figsize=(13,7.5))
 for row,phase in enumerate(['a','b']):
  data=s['phase_'+phase]['by_sla'];sids=[x['id'] for x in P['phase_'+phase]['slas']]
  n=2050 if phase=='a' else ex['phase_b_unique_physical_points']
  for col,(field,label,title) in enumerate([(lambda r:r['optimistic'],'Optimistic count','Optimistic disagreements'),(lambda r:r['conservative'],'Conservative count','Conservative disagreements'),(lambda r:r['absolute_gap']['mean'],'Mean absolute gap (%)','Sampled capacity error')]):
   draw(axes[row,col],data,sids,field,label,percent=col==2)
   axes[row,col].set_title(f"{'A: existing corpus' if phase=='a' else 'B: held-out'} | {title}")
   axes[row,col].text(.02,.98,f'{n} physical points / SLA',transform=axes[row,col].transAxes,va='top',fontsize=8)
 handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.95),ncol=4,frameon=False)
 fig.suptitle('Full vs remaining Prefill compute debt',fontsize=14,y=.995)
 save(fig,folder/'figure_a');plt.close(fig)
 fig,axes=plt.subplots(2,2,figsize=(10,7.3));data=s['phase_b']['by_sla'];sids=[x['id'] for x in P['phase_b']['slas']]
 for ax,field,label,title,pct,count in [
  (axes[0,0],lambda r:r['decision_types'].get('agreement',0),'Agreements / 4','Partition winner agreement',False,True),
  (axes[0,1],lambda r:r['unsafe_recommendations'],'Unsafe outputs / 4','Exact recommendation safety',False,True),
  (axes[1,0],lambda r:r['partition_selection_loss']['mean'],'Mean loss (%)','Partition-selection loss',True,False),
  (axes[1,1],lambda r:r['operating_point_loss']['mean'],'Mean loss (%)','Recommended operating-point loss',True,False)]:
  draw(ax,data,sids,field,label,pct,count);ax.set_title(title)
 axes[0,1].text(.04,.9,'Unsafe count unchanged, severity worse:\nw202 / TPOT 5 violating requests\nFull 1/48 → Remaining 9/48',transform=axes[0,1].transAxes,va='top',fontsize=9,color='#a52a2a')
 handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.95),ncol=4,frameon=False)
 fig.suptitle('Held-out decisions and recommended loads',fontsize=14,y=.995);save(fig,folder/'figure_b');plt.close(fig)
 write_json(folder/'manifest.json',{'figures':2,'formats':['png','svg'],'source':'results/jb1_plus/summary.json','source_sha256':hashlib.sha256((OUT/'summary.json').read_bytes()).hexdigest(),
  'caption_a':'Counts are adaptive-grid descriptions, not production risk probabilities. Mean absolute sampled capacity gap excludes undefined capacities; signed medians, ranges and no-safe flags remain in tables. Phase A is post-hoc; Phase B uses four new workloads. Last two Phase A x labels show TTFT / TPOT.',
  'caption_b':'Four workload decisions per SLA. Counts do not establish population reliability. Loss means include only defined quantities, with denominators in tables; arithmetic operating loss does not establish point safety. All cases, ties and unresolved intervals retained.',
  'display':'Small horizontal offsets separate coincident variants within each fixed SLA category; they are not different SLA thresholds. Lines connect tested categories only.'})
def save(fig,path):
 fig.tight_layout(rect=(0,0,1,.90),h_pad=1.8,w_pad=2)
 fig.savefig(path.with_suffix('.png'),dpi=180);fig.savefig(path.with_suffix('.svg'))
 svg=path.with_suffix('.svg');svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n')
if __name__=='__main__':main()
