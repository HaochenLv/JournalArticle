"""Serial physical execution worker. Parent enforces 600 seconds per invocation."""
from common import *
import time,os,platform,contextlib,traceback,ctypes,gc
from dataclasses import asdict
from research import pipeline,RequestSpec,ref,HELIX,SLA
from jb_avg_v1 import simulate,BatchProfiles
class PMC(ctypes.Structure):
    _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong),('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t)]
def memory():
    p=PMC();p.cb=ctypes.sizeof(p)
    fn=ctypes.windll.psapi.GetProcessMemoryInfo;fn.argtypes=[ctypes.c_void_p,ctypes.POINTER(PMC),ctypes.c_ulong]
    handle=ctypes.windll.kernel32.GetCurrentProcess;handle.restype=ctypes.c_void_p
    return p.PeakWorkingSetSize if fn(handle(),ctypes.byref(p),p.cb) else None
def main():
    start=time.perf_counter();prof=BatchProfiles.pinned();profile_s=time.perf_counter()-start
    print(json.dumps({'ready':True,'pid':os.getpid(),'profile_load_s':profile_s,'python':sys.version}),flush=True)
    for line in sys.stdin:
        job=json.loads(line);start=time.perf_counter()
        inputs=job['inputs'];p=pipeline(job['link'],job['candidate'],True);w=tuple(RequestSpec(**r) for r in inputs['workload'])
        assert fingerprint(asdict(p))==fingerprint(inputs['pipeline'])
        prep=time.perf_counter()-start
        try:
            gc.collect();started=time.perf_counter()
            if job['model']=='E':result=simulate(p,w,profiles=prof,q=16,max_events=100000,diagnostic_shares=False)
            else:
                with (OUT/'runtime/helix_stdout.log').open('a',encoding='utf-8') as logfile,contextlib.redirect_stdout(logfile):
                    result=asdict(ref.evaluate_helix_fixed_reference(pipeline=p,workload=w,sla=SLA(**inputs['sla']),helix_root=HELIX))
            wall=time.perf_counter()-started;peak=memory();start=time.perf_counter()
            if job['model']=='E':
                semantic={k:v for k,v in result.items() if k!='runtime_s'};semantic_hash=fingerprint(semantic)
                info={'status':result['status'],'wall_s':wall,'self_runtime_s':result['runtime_s'],'trajectory_hash':result['trajectory_hash'],'semantic_hash':semantic_hash,'events':len(result['trajectory']),'requests':len(w),'input_tokens':sum(r.input_tokens for r in w),'output_tokens':sum(r.output_tokens for r in w),'peak_process_memory_bytes':peak,'peak_memory_scope':'process lifetime high-water mark','pid':os.getpid(),'input_object_preparation_s':prep}
                if job.get('save'):write(OUT/'evaluator'/(job['physical_id']+'.json.gz'),result)
            else:
                raw={'inputs':inputs,'raw':result,'summary':{'runtime_s':wall,'cache_key':fingerprint(inputs)},'stage6b_actual_execution':True}
                write(OUT/'reference'/(job['physical_id']+'.json.gz'),raw)
                info={'status':'complete' if result['finished_requests']==result['total_requests'] else 'incomplete','wall_s':wall,'peak_process_memory_bytes':peak,'pid':os.getpid(),'input_object_preparation_s':prep}
            info['serialization_and_semantic_hash_s']=time.perf_counter()-start
            print(json.dumps(info,allow_nan=False),flush=True)
            del result
        except Exception as exc:
            print(json.dumps({'status':'exception','exception_type':type(exc).__name__,'detail':str(exc),'traceback':traceback.format_exc(),'wall_s':time.perf_counter()-started}),flush=True)
if __name__=='__main__':main()
