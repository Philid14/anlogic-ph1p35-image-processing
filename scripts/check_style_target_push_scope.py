"""Inspect this task's complete staged delta before a version push."""
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import zipfile
ROOT=Path(__file__).resolve().parents[1]
BASE='89093f428878b918036c8a30a0d1afe7764946b8'
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
branch=git('branch','--show-current').decode().strip()
assert branch=='codex/main/style-v2-target-v1'
files=git('diff','--cached','--name-only','-z',BASE).split(b'\0')
patterns=[re.compile(rb'gh[pousr]_[A-Za-z0-9]{25,}'),re.compile(rb'github_pat_[A-Za-z0-9_]{30,}'),
    re.compile(rb'sk-[A-Za-z0-9]{30,}'),re.compile(rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')]
rows=[];suspects=[]
for raw in files:
    if not raw:continue
    name=raw.decode('utf-8')
    assert not any(part.endswith('_Runs') for part in Path(name).parts),name
    assert not name.endswith('.bit'),name
    assert not name.startswith(('3_原理图/','2026-10-05/','features/latency_view/')),name
    assert Path(name).name not in ('.env','id_rsa','credentials.json')
    content=git('show',':'+name)
    assert len(content)<100_000_000,name
    for pat in patterns:
        if pat.search(content):suspects.append(name)
    if name.endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            for member in z.namelist():
                for pat in patterns:
                    if pat.search(z.read(member)):suspects.append(name+'::'+member)
    rows.append(dict(path=name,bytes=len(content),sha256=hashlib.sha256(content).hexdigest()))
assert not suspects,'Credential-like material detected in: '+','.join(suspects)
out=ROOT/'tmp/style_v2_target_v1/PUSH_SCOPE_CHECK.json'
out.write_text(json.dumps(dict(branch=branch,base=BASE,file_count=len(rows),
    new_bit_count=0,large_runs_count=0,credential_pattern_hits=0,files=rows),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS staged push scope:',len(rows),'files; no added bit/Runs, excluded teammate/user paths; credential patterns clear')
