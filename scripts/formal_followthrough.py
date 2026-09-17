"""Finish already-authorized formal analyses after the resumable matrix exits."""
from pathlib import Path
import sys,json,time,os,argparse,subprocess,datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from formal_core import *
from host_execution import process_alive

def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main(pid):
 dest=FORMAL/'execution_workflow.json';state={'protocol_hash':PROTOCOL_HASH,'workflow_started_utc':stamp(),'status':'waiting_for_matrix','steps':[]}
 write_json(dest,state)
 while process_alive(pid):
  time.sleep(30)
 for g in groups():
  p=FORMAL/'groups'/(g['id']+'.json')
  if not p.exists() or json.loads(p.read_text())['status']!='complete':
   state.update(status='matrix_incomplete',checked_utc=stamp());write_json(dest,state);raise SystemExit('Matrix stopped before every group completed; resume formal_run.py')
 state.update(status='postprocessing',matrix_exit_observed_utc=stamp());write_json(dest,state)
 for script,args in [('formal_analyze.py',[]),('formal_mismatch.py',['--workers','8']),('formal_mitigation.py',['--workers','8']),('formal_verify.py',[]),('formal_figures.py',[]),('formal_timing.py',[])]:
  item={'script':script,'started_utc':stamp()};state['steps'].append(item);write_json(dest,state)
  begin=time.perf_counter()
  with (ROOT/'.private'/('followthrough_'+script+'.log')).open('w') as f:r=subprocess.run([sys.executable,str(ROOT/'scripts'/script),*args],stdout=f,stderr=subprocess.STDOUT,cwd=ROOT)
  item.update(returncode=r.returncode,elapsed_s=time.perf_counter()-begin,finished_utc=stamp());write_json(dest,state)
  print(json.dumps(item),flush=True)
  if r.returncode:state['status']='analysis_error';write_json(dest,state);raise SystemExit(r.returncode)
 state.update(status='computed_pending_research_review',finished_utc=stamp());write_json(dest,state)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--wait-pid',required=True,type=int);a=p.parse_args();main(a.wait_pid)
