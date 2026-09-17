"""One main-text candidate figure: decision type and two distinct losses."""
from sla_sensitivity_common import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

def main():
    data=read(OUT/'summary.json')['decisions']
    colors={'raw':'#17608a','legacy':'#c16b20'}
    markers={'agreement':'o','strict best-set mismatch':'X','tie-break mismatch':'^','no-safe recommendation':'s','no-safe reference':'s','incomplete reference':'s'}
    lowest=min([0.]+[100*r[f] for r in data if r['ttft_s']==5.2 for f in ['partition_selection_loss','operating_point_loss'] if r[f] is not None])
    fig,axes=plt.subplots(2,3,figsize=(13.6,8.0),sharex=True,sharey=True)
    for ax,g in zip(axes.flat,P['groups']):
        for v in P['semantics']:
            rs=sorted([r for r in data if r['workload']==g['workload'] and r['ttft_s']==5.2 and r['semantics']==v],key=lambda r:r['tpot_s'])
            # Fixed categorical positions with a small semantic offset keep
            # coincident Raw/Legacy markers visible without inventing SLA probes.
            xs=[i+(-.065 if v=='raw' else .065) for i in range(len(rs))]
            for field,ls in [('partition_selection_loss','-'),('operating_point_loss','--')]:
                ax.plot(xs,[100*r[field] if r[field] is not None else float('nan') for r in rs],ls,color=colors[v],alpha=.85,lw=1.7)
                for x,r in zip(xs,rs):
                    if r[field] is not None:
                        ax.scatter(x,100*r[field],marker=markers[r['mismatch_type']],s=43,color=colors[v],edgecolor='white',linewidth=.5,zorder=5)
            for x,r in zip(xs,rs):
                if r['exact_reference_safe'] is False and r['operating_point_loss'] is not None:
                    ax.scatter(x,100*r['operating_point_loss'],s=130,facecolors='none',edgecolors='#b52f3b',linewidth=1.4,zorder=6)
        ax.set_title(g['workload'].split('-')[0],loc='left',fontweight='bold',fontsize=12)
        ax.set_xticks(range(6),['0.3','0.6','1.2','2.4','5','10'])
        ax.set_ylim(lowest-4,104);ax.set_yticks([0,25,50,75,100]);ax.grid(axis='y',alpha=.18)
        ax.spines[['top','right']].set_visible(False)
    for ax in axes[-1]:ax.set_xlabel('TPOT SLA (s), TTFT fixed at 5.2 s')
    for ax in axes[:,0]:ax.set_ylabel('Loss relative to reference best (%)')
    handles=[Line2D([0],[0],color=c,lw=2,label=v.title()) for v,c in colors.items()]
    handles += [Line2D([0],[0],color='#555555',ls=ls,label=name) for ls,name in [('-','Partition loss'),('--','Operating-point loss')]]
    handles += [Line2D([0],[0],marker=m,ls='',color='#555555',label=name) for name,m in [('Agreement','o'),('Strict mismatch','X'),('Tie-break mismatch','^')]]
    handles += [Line2D([0],[0],marker='o',ls='',markerfacecolor='none',markeredgecolor='#b52f3b',markersize=10,label='Reference-unsafe recommendation')]
    fig.suptitle('SLA sensitivity: selecting a partition and recommending a load are different decisions',fontsize=14,y=.985)
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.005),ncol=4,frameon=False,fontsize=9)
    fig.tight_layout(rect=(0,.10,1,.94))
    dest=OUT/'figures';dest.mkdir(exist_ok=True)
    for suffix in ['png','svg']:fig.savefig(dest/('sla_sensitivity.'+suffix),dpi=180,facecolor='white')
    plt.close(fig)
    write_json(dest/'manifest.json',{'figure_count':1,'data_source':'results/sla_sensitivity/summary.json','data_sha256':hashlib.sha256((OUT/'summary.json').read_bytes()).hexdigest(),
      'scope':'Six original workloads, TTFT5.2, six prescribed TPOT thresholds; final shared grids. Lines connect tested conditions only, not a continuous threshold estimate.',
      'axis':'Six tested TPOT categories, with small horizontal Raw/Legacy offsets solely to expose coincident markers; offsets are not new SLA values.',
      'unsafe_note':'Circled operating losses are arithmetic 1-L/B only; safety-adjusted loss is 100% for these unsafe recommendations. Full values and TTFT4.68 conditions are in tables.'})

if __name__=='__main__':main()
