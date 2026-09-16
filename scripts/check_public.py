"""Inspect the actual staged blobs, including decompressed raw-result records."""
import gzip,re,subprocess
from pathlib import PurePosixPath

def main():
 files=subprocess.check_output(['git','diff','--cached','--name-only','--diff-filter=ACMR','-z']).decode().split('\0')
 failures=[]
 for name in filter(None,files):
  p=PurePosixPath(name)
  if any(part in {'.deps','.venv','.private','CA','__pycache__'} for part in p.parts) or p.suffix in {'.pdf','.docx','.pkl','.pem','.key'}:failures.append((name,'prohibited file'));continue
  data=subprocess.check_output(['git','show',':'+name])
  if len(data)>10_000_000:failures.append((name,'oversize'))
  if name.endswith('.json.gz'):data=gzip.decompress(data)
  try:s=data.decode()
  except UnicodeDecodeError:
   if p.suffix not in {'.png','.svg'}:failures.append((name,'unexpected binary'))
   continue
  patterns=[r'/Users/[A-Za-z0-9_.-]+/',r'/home/[A-Za-z0-9_.-]+/',r'ghp_[A-Za-z0-9]{20,}',r'github_pat_[A-Za-z0-9_]{20,}',r'sk-proj-[A-Za-z0-9_-]{20,}',r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----']
  for pattern in patterns:
   if re.search(pattern,s):failures.append((name,'sensitive marker'))
 if failures:raise SystemExit(str(failures))
 print(f'Public preflight passed for {len(list(filter(None,files)))} staged files.')
if __name__=='__main__':main()
