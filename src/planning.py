"""Small deterministic budgeted reference-query policies.

Local brackets guide queries heuristically. They never certify unqueried loads
and never justify returning an unvalidated operating point.
"""
def plan(loads, candidates, evaluator_safe, query, budget, policy='best_first'):
 observed={s:{} for s in candidates};trace=[]
 def call(s,j):
  if len(trace)>=budget or j in observed[s]:return
  safe=bool(query(s,j));observed[s][j]=safe;trace.append({'candidate':s,'index':j,'load':loads[j],'safe':safe})
 def eindex(s):return max((j for j in range(len(loads)) if evaluator_safe[s][j]),default=0)
 order=sorted(candidates,key=lambda s:(-loads[eindex(s)],abs(s),s))
 if policy=='fixed_grid':
  # Fixed shared schedule, no adaptation to observed labels or evaluator values.
  levels=[]
  intervals=[(0,len(loads)-1)]
  levels.extend([0,len(loads)-1])
  while intervals:
   a,b=intervals.pop(0)
   if b-a<=1:continue
   m=(a+b)//2
   if m not in levels:levels.append(m)
   intervals.extend([(a,m),(m,b)])
  for j in levels:
   for s in sorted(candidates,key=lambda s:(abs(s),s)):call(s,j)
 else:
  for s in order:call(s,eindex(s))
  def next_point(s):
   values=observed[s];available=[j for j in range(len(loads)) if j not in values]
   if not available:return None
   safe=[j for j,v in values.items() if v]
   if not safe:
    high=min(values,default=len(loads)-1)
    j=high//2
    if j in values:j=min(available)
    return j,loads[high]
   low=max(safe);unsafe=[j for j,v in values.items() if not v and j>low]
   if unsafe:
    high=min(unsafe);middle=(low+high)//2
    if middle not in values:return middle,loads[high]
   elif low<len(loads)-1:
    j=min(len(loads)-1,low+2)
    if j not in values:return j,loads[-1]
   # Unexplored islands remain eligible; no correctness claim relies on a prefix.
   return max(available),loads[low]
  turn=0
  while len(trace)<budget:
   options=[(s,next_point(s)) for s in order];options=[(s,v) for s,v in options if v is not None]
   if not options:break
   if policy=='round_robin':
    s,v=options[turn%len(options)];turn+=1
   else:s,v=max(options,key=lambda sv:(sv[1][1],loads[eindex(sv[0])],-abs(sv[0]),-sv[0]))
   call(s,v[0])
 valid=[x for x in trace if x['safe']]
 chosen=max(valid,key=lambda r:(r['load'],-abs(r['candidate']),-r['candidate'])) if valid else None
 return {'chosen':chosen,'trace':trace,'reference_calls':len(trace)}
