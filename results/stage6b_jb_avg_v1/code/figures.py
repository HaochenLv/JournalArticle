"""Static scientific figures from complete evidence tables; no new experiments."""
from common import *
from finalize import csvread,num
import os
os.environ['MPLCONFIGDIR']=str(OUT/'runtime/matplotlib_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
def main():
    dest=OUT/'figures';dest.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    ws=[w['short_id'] for w in P['workloads']];acc=csvread(OUT/'metrics/request_accuracy.csv');jud=csvread(OUT/'metrics/judgment_summary.csv');cap=csvread(OUT/'capacity/capacities.csv');op=csvread(OUT/'decisions/operating_points.csv')
    def save(fig,name):
        fig.savefig(dest/(name+'.png'),dpi=180,bbox_inches='tight');fig.savefig(dest/(name+'.svg'),bbox_inches='tight');plt.close(fig)
    fig=plt.figure(figsize=(12,7));layout=fig.add_gridspec(2,2,height_ratios=[3,1.3]);axes=[fig.add_subplot(layout[0,i]) for i in range(2)]
    for ax,m,scale in zip(axes,['TTFT','TPOT'],[1,1000]):
        rows=[next(r for r in acc if r['grid_version']=='G0' and r['workload']==w and r['metric']==m and r['error_kind']=='seconds' and r['scope']=='full_grid' and not r['SLA']) for w in ws]
        x=np.arange(10)
        for field,label,offset in [('median_absolute','Median absolute',-.18),('p90_absolute','P90 absolute',.18)]:ax.bar(x+offset,[num(r[field])*scale if num(r[field]) is not None else 0 for r in rows],.34,label=label)
        ax.set_xticks(x,ws,rotation=45);ax.set_ylabel(f'{m} error ({"s" if scale==1 else "ms"})');ax.set_title('G0: equal candidate / point / request weights');ax.legend()
        for i,r in enumerate(rows):
            if not r['valid_points'] or r['valid_points']=='0':ax.annotate('NA', (i,0),ha='center')
    coverage=fig.add_subplot(layout[1,:]);status=csvread(OUT/'status/point_status.csv');bottom=np.zeros(10)
    for label,color,predicate in [('Paired complete','#187e9c',lambda r:r['pairable']=='True'),('Unsupported / unknown','#8056ad',lambda r:r['status'].startswith('unsupported')),('Other unpaired','#a9b0b8',lambda r:r['pairable']!='True' and not r['status'].startswith('unsupported'))]:
        counts=np.array([sum(predicate(r) for r in status if r['grid_version']=='G0' and r['model']=='E' and r['workload']==w) for w in ws]);coverage.bar(np.arange(10),counts,bottom=bottom,label=label,color=color);bottom+=counts
    coverage.set_xticks(np.arange(10),ws);coverage.set_ylabel('Physical points');coverage.set_title('G0 coverage: all scheduled physical inputs');coverage.legend(ncol=3,loc='upper center',bbox_to_anchor=(.5,-.2))
    fig.suptitle('Request error and coverage: all ten workloads');fig.tight_layout();save(fig,'01_request_accuracy')
    fig,axes=plt.subplots(1,2,figsize=(12,4.7));colors={'BS':'#248277','BU':'#a9b0b8','O':'#c53939','C':'#dc9c32','unknown':'#8056ad'}
    for ax,v in zip(axes,['G0','G1']):
        rows=[next(r for r in jud if r['grid_version']==v and r['workload']=='ALL' and r['SLA']==s['id'] and r['scope']=='service' and r['aggregation']=='pooled_counts') for s in P['slas']];bottom=np.zeros(6)
        for k in colors:
            vals=np.array([int(r[k])/int(r['scheduled']) for r in rows]);ax.bar(np.arange(6),vals,bottom=bottom,label=k,color=colors[k]);bottom+=vals
        ax.set_xticks(np.arange(6),[s['id'] for s in P['slas']]);ax.set_ylim(0,1);ax.set_ylabel('Fraction of scheduled judgments (pooled)');ax.set_title(v+' — repeated SLA conditions, not independent evidence');ax.legend(ncol=3,loc='upper center',bbox_to_anchor=(.5,-.1))
    fig.tight_layout();save(fig,'02_attainment_and_coverage')
    fig,axes=plt.subplots(2,3,figsize=(13,8))
    for ax,sla in zip(axes.flat,P['slas']):
        rs=[r for r in cap if r['grid_version']=='G1' and r['SLA']==sla['id']]
        for r in rs:
            x=num(r['R_C_lower']);y=num(r['E_C_lower']);unknown=r['E_identified']!='True' or r['R_identified']!='True';censored=r['E_right_censored']=='True' or r['R_right_censored']=='True'
            ax.scatter(x,y,marker='x' if unknown else '^' if censored else 'o',s=25,alpha=.65,color='#8056ad' if unknown else '#cb7c19' if censored else '#187e9c')
            if unknown:ax.plot([x,num(r['R_C_upper'])],[y,y],color='#8056ad',alpha=.3);ax.plot([x,x],[y,num(r['E_C_upper'])],color='#8056ad',alpha=.3)
        maxv=max([num(r['R_C_upper']) for r in rs]+[num(r['E_C_upper']) for r in rs]);ax.plot([0,maxv],[0,maxv],color='gray',linestyle='--',linewidth=.8)
        ax.set_xscale('symlog',linthresh=.001);ax.set_yscale('symlog',linthresh=.001);ax.set_title(sla['id']);ax.set_xlabel('R sampled capacity / lower bound');ax.set_ylabel('E sampled capacity / lower bound')
    fig.suptitle('G1 sampled capacity: ○ identified; △ right-censored; × unknown (bounds shown)');fig.tight_layout();save(fig,'03_sampled_capacity')
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,v in zip(axes,['G0','G1']):
        matrix=np.full((10,6),np.nan)
        for r in op:
            if r['grid_version']==v and r['A_R']:matrix[ws.index(r['workload']),int(r['SLA'][1:])-1]=float(r['A_R'])
        im=ax.imshow(matrix,vmin=0,vmax=1,cmap='RdYlGn',aspect='auto');ax.set_xticks(range(6),[s['id'] for s in P['slas']]);ax.set_yticks(range(10),ws);ax.set_title(v+' original E recommendation: reference attainment')
        for i,w in enumerate(ws):
            for j,s in enumerate(P['slas']):
                r=next(r for r in op if r['grid_version']==v and r['workload']==w and r['SLA']==s['id']);value=matrix[i,j]
                label='A' if not r['candidate'] else '?' if np.isnan(value) else f'{value:.3f}'+('!' if r['safe_R']=='False' else '')
                ax.text(j,i,label,ha='center',va='center',fontsize=8)
    fig.suptitle('A = abstain, ? = unknown, ! = unsafe (individual violations do not suffice)');fig.subplots_adjust(top=.88,wspace=.35,right=.86)
    coloraxis=fig.add_axes([.91,.2,.015,.6]);fig.colorbar(im,cax=coloraxis,label='Joint attainment; target 0.90');save(fig,'04_recommended_operating_points')
    write(OUT/'checks/figure_checks.json',{'source':'complete tables including unfavorable/unknown/censored conditions','files':[p.name for p in dest.iterdir()],'visual_review':'pending'})
if __name__=='__main__':main()
