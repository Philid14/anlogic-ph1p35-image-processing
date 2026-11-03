"""Check the exact task delta, frozen inputs, staged credentials and archive trace."""
from pathlib import Path
import subprocess,re,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
BASE='7cffe56c384340f59a526da80a2ac3f3018bf209'
H='in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/'
AL=H.replace('user_source/hdl_source/','td_project/')+'camera_to_dsi_display.al'
ALLOWED={H+x for x in ('design_top_wrapper.v','isp/isp_top.v','isp/edge_control_stream.v','isp/color_compare_osd.v','isp/planar_measure_stats.v','isp/ruler_auto_calibration.v','isp/engineering_dimension_marks.v')}
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
def main():
    assert git('branch','--show-current').decode().strip()=='codex/main/inspection-auto-dimension-v2'
    manifest=json.loads((ROOT/'artifacts/bitstreams/INSPECTION_UI_DIMENSION_V1/build_evidence/SOURCE_MANIFEST.json').read_text())
    frozen=0
    for p in manifest['files']:
        if p not in ALLOWED:
            assert (ROOT/p).read_bytes().replace(b'\r\n',b'\n')==git('show',BASE+':'+p).replace(b'\r\n',b'\n'),p
            frozen+=1
    changed=git('diff','--name-only',BASE,'--',H).decode().splitlines()
    assert set(changed)<=ALLOWED,changed
    s=(ROOT/H/'isp/color_compare_osd.v').read_text();b=git('show',BASE+':'+H+'isp/color_compare_osd.v').decode()
    pat=r'function \[3:0\] classify;(.*?)endfunction'
    assert re.search(pat,s,re.S)[0]==re.search(pat,b,re.S)[0]
    assert 'wire compare_match=max_difference<=12;' in s
    staged=[p.decode() for p in git('diff','--cached','--name-only','-z',BASE).split(b'\0') if p]
    patterns=[rb'gh[pousr]_[A-Za-z0-9]{25,}',rb'github_pat_[A-Za-z0-9_]{30,}',rb'sk-[A-Za-z0-9]{30,}',rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----']
    bits=0
    for p in staged:
        assert not p.startswith(('features/','2026-10-05/','3_原理图/','最终作品实现/')),p
        assert p!='docs/GITHUB_REFERENCE_RESEARCH.md' and '_Runs/' not in p and not p.startswith('tmp/'),p
        data=git('show',':'+p);assert len(data)<100_000_000,p
        assert not any(re.search(pattern,data) for pattern in patterns),'Potential credential in '+p
        if p.endswith('.bit'):
            assert p=='artifacts/bitstreams/INSPECTION_AUTO_DIMENSION_V2/camera_to_dsi_display.bit',p
            info=json.loads(git('show',':artifacts/bitstreams/INSPECTION_AUTO_DIMENSION_V2/BUILD_INFO.json'))
            assert hashlib.sha256(data).hexdigest()==info['bit_sha256']
            assert info['setup_wns_ns']>=0 and info['hold_wns_ns']>=0 and info['board_test']=='NOT_RUN'
            git('cat-file','-e',info['source_commit']+'^{commit}');bits+=1
    out=ROOT/'tmp/auto_dimension_v2/SOURCE_SCOPE.json'
    out.write_text(json.dumps(dict(passed=True,base=BASE,frozen_td_inputs=frozen,allowed_hdl_changes=sorted(ALLOWED),
      staged_file_count=len(staged),candidate_bits=bits,credential_pattern_hits=0),indent=2)+'\n')
    print(f'PASS {frozen} frozen TD inputs, classifier/MAX12, staged task scope, {bits} candidate bit, credential scan')
if __name__=='__main__':main()
