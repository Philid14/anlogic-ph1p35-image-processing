"""Check staged COLOR_COMPARE_V1 delta, credentials, bit scope and release gates."""
from pathlib import Path
import subprocess,re,json,hashlib,zipfile,io
ROOT=Path(__file__).resolve().parents[1]
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
assert git('branch','--show-current').decode().strip()=='codex/main/color-compare-v1'
base='8d26c6eba95f07723b0f634efa82ed1424218975'
files=[p.decode() for p in git('diff','--cached','--name-only','-z',base).split(b'\0') if p]
patterns=[rb'gh[pousr]_[A-Za-z0-9]{25,}',rb'github_pat_[A-Za-z0-9_]{30,}',rb'sk-[A-Za-z0-9]{30,}',rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----']
suspects=[];bits=0;rows=[]
for name in files:
    assert not any(p.endswith('_Runs') for p in Path(name).parts),name
    assert not name.startswith(('features/','2026-10-05/','3_原理图/','最终作品实现/')),name
    assert name!='docs/GITHUB_REFERENCE_RESEARCH.md' and Path(name).name not in ('.env','id_rsa','credentials.json'),name
    b=git('show',':'+name);assert len(b)<100_000_000,name
    for pattern in patterns:
        if re.search(pattern,b):suspects.append(name)
    if name.endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            for member in z.namelist():
                for pattern in patterns:
                    if re.search(pattern,z.read(member)):suspects.append(name+'::'+member)
    if name.endswith('.bit'):
        assert name=='artifacts/bitstreams/COLOR_COMPARE_V1/camera_to_dsi_display.bit',name
        info=json.loads(git('show',':artifacts/bitstreams/COLOR_COMPARE_V1/BUILD_INFO.json'))
        assert info['version']=='COLOR_COMPARE_V1' and info['board_test']=='NOT_RUN'
        assert hashlib.sha256(b).hexdigest()==info['bit_sha256']
        assert info['setup_wns_ns']>=0 and info['hold_wns_ns']>=0 and info['setup_tns_ns']==info['hold_tns_ns']==0
        assert info['resources']['slice']<=21216
        git('cat-file','-e',info['source_commit']+'^{commit}');bits+=1
    rows.append(dict(path=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
assert not suspects,'Potential credentials in '+','.join(suspects)
(ROOT/'tmp/color_compare_v1/PUSH_SCOPE_CHECK.json').write_text(json.dumps(dict(base=base,file_count=len(files),candidate_bits=bits,credential_hits=0,files=rows),indent=2)+'\n')
print('PASS COLOR_COMPARE push scope:',len(files),'files;',bits,'candidate bit; no Runs, teammate, user data or credential patterns')
