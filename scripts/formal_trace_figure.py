"""Show query occupancy and first-failure accounting for a saved trace."""
from pathlib import Path
import sys,gzip,json,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from formal_core import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

def main(name):
 d=json.load(gzip.open(FORMAL/'mechanisms'/(name+'.json.gz'),'rt'));e=d['evaluator'];first=e['first_violation'];rv=d['reference_violations_in_physical_finish_order']
 focus=first['time_s'] if first else rv[0]['physical_end_s'] if rv else 5.
 # Show queries overlapping the displayed window, including late-arriving
 # violations; the first eight arrivals may have finished long before it.
 ids=[r['id'] for r in d['workload'] if d['reference_queries'][r['id']]['iterations'][0]['start_s']<=focus+2 and d['reference_queries'][r['id']]['iterations'][-1]['end_s']>=focus-3][:8]
 if first and first.get('request_id') and first['request_id'] not in ids:ids=[first['request_id'],*ids][:8]
 fig,axes=plt.subplots(2,1,figsize=(9,6),sharex=True)
 colors={'Prefill':'#32658f','Decode':'#d78831'}
 for ax,title in zip(axes,['JB1 query-phase occupancy','HELIX reference query-phase occupancy']):
  for j,rid in enumerate(ids):
   if ax is axes[0]:
    pre=next((x['time_s'] for x in e['trajectory'] if rid in x['active'] and x['active'][rid]['phase']=='prefill'),None)
    dec=next((x['time_s'] for x in e['trajectory'] if rid in x['active'] and x['active'][rid]['phase']=='decode'),None)
    end=next((x['time_s'] for x in e['trajectory'] if ['Finish',rid] in x['events']),e['final_time_s'])
   else:
    its=d['reference_queries'][rid]['iterations'];pre=its[0]['start_s'];dec=its[0]['end_s'];end=its[-1]['end_s']
   if pre is not None and dec is not None:ax.broken_barh([(pre,dec-pre)],(j-.3,.6),facecolors=colors['Prefill'])
   if dec is not None:ax.broken_barh([(dec,end-dec)],(j-.3,.6),facecolors=colors['Decode'])
  ax.axvline(focus,color='#a32929',ls='--',lw=1);ax.set_yticks(range(len(ids)),[r.replace('azure-','q') for r in ids]);ax.set_title(title);ax.spines[['top','right']].set_visible(False)
 axes[1].set_xlabel('Time from common simulation origin (s)');axes[1].set_xlim(max(0,focus-3),focus+2);axes[0].legend(handles=[Patch(facecolor=v,label=k) for k,v in colors.items()],loc='upper left',ncol=2)
 fig.suptitle(d['group']['workload']+' · '+d['regime'].replace('_',' ')+' · intensity '+str(d['intensity'])+'\nDashed line: '+('first evaluator failure' if first else 'first reference violation'));fig.tight_layout()
 folder=FORMAL/'figures';folder.mkdir(exist_ok=True);fig.savefig(folder/(name+'_timeline.png'),dpi=180);fig.savefig(folder/(name+'_timeline.svg'));plt.close(fig)
 svg=folder/(name+'_timeline.svg');svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('name');a=p.parse_args();main(a.name)
