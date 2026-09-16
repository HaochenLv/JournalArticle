"""Fetch pinned public code without changing sibling conference repositories."""
from pathlib import Path
import subprocess, tarfile, io
ROOT = Path(__file__).resolve().parents[1]
PINS = {
 'evaluator': ('https://github.com/HaochenLv/sla-aware-evaluator.git', '1cd5c56365b084fb06e3ca14f67448ddbf45275a', ['src','tests','HELIX_FIXED_REFERENCE.md']),
 'partition': ('https://github.com/HaochenLv/SLA-Aware-Layer-Partitioning.git', '2f876f0b889bb26d2c759b9b2d6eb3e7e97a9b4b', ['src','tests','config','data/helix_profiles','LICENSE','results/phase13','results/phase16']),
 'helix': ('https://github.com/Thesys-lab/Helix-ASPLOS25.git', '8639497a4aaf1eb3b7594614cb0bbd376c1342b3', None),
}
def main():
 deps=ROOT/'.deps';deps.mkdir(exist_ok=True)
 for name,(url,commit,paths) in PINS.items():
  dest=deps/name
  if dest.exists():
   print(f'{name}: exists; retained');continue
  if paths is None:
   subprocess.run(['git','clone',url,str(dest)],check=True)
   subprocess.run(['git','-C',str(dest),'checkout',commit],check=True)
  else:
   repo=deps/(name+'-git')
   if not repo.exists():subprocess.run(['git','clone','--bare',url,str(repo)],check=True)
   archive=subprocess.check_output(['git','-C',str(repo),'archive',commit,*paths])
   dest.mkdir()
   with tarfile.open(fileobj=io.BytesIO(archive)) as t:t.extractall(dest,filter='data')
 print('Create a Python 3.12 venv and install requirements.txt; see README.md.')
if __name__=='__main__':main()
