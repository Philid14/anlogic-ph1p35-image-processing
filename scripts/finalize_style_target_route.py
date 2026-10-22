"""Finish a proven, unchanged SYN -> place -> route chain, then archive its bit.

Separate processes are intentional: functional and physical CDC audit must finish
before bitgen. Never reroute an audit database or substitute a stale Runs bit.
"""
import argparse, datetime, hashlib, json, re, shutil, subprocess, time
from pathlib import Path
from build_style_v2_target_v1 import ROOT, PROJECT, snapshot

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--synthesis',required=True)
    ap.add_argument('--placement',required=True)
    ap.add_argument('--route',required=True)
    ap.add_argument('--verification',type=Path,required=True)
    a=ap.parse_args()
    tmp=ROOT/'tmp/style_v2_target_v1'
    syn=tmp/a.synthesis; place=tmp/a.placement; route=tmp/a.route
    frozen=json.loads((syn/'SOURCE_MANIFEST.json').read_text())
    before=snapshot()
    for key in ('files','al_sha256','historical_bits'):
        assert before[key]==frozen[key], 'Actual TD inputs changed: '+key
    placed=json.loads((place/'result.json').read_text())
    assert placed['placement_passed'] and placed['source_commit']==frozen['source_commit']
    assert 'STYLE_TARGET_FLOW_COMPLETE' in (syn/'syn_1_stdout.txt').read_text(errors='replace')
    assert 'ROUTE_COMPLETE_NO_BIT' in (route/'stdout.txt').read_text(errors='replace')
    assert (route/'route.db').stat().st_mtime>=(place/'place.db').stat().st_mtime
    verification=json.loads(a.verification.read_text())
    assert verification['passed'] and verification['source_commit']==frozen['source_commit']
    assert all(verification[k] for k in ('full_720p_final_hdmi','fault_matrix','cdc_review','baseline_modes'))
    # Evidence is immutable between verification and bitgen, including the
    # physical CDC report generated on a separate database with audit-only SDC.
    for rel,expected in verification['evidence_sha256'].items():
        assert sha(ROOT/rel)==expected, rel
    timing=(route/'route.ts').read_text()
    sw,st,hw,ht=map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',timing))
    assert sw>=0 and hw>=0 and st==0 and ht==0, timing
    area=(route/'route.area').read_text()
    def number(name):
        found=re.search(r'^#'+re.escape(name)+r'\s+(\d+)',area,re.M)
        assert found,name
        return int(found[1])
    counts={name:number(name) for name in ('slice','lut6','reg','eram','dsp')}
    assert counts['slice']<=21216
    dest=ROOT/'artifacts/bitstreams/STYLE_V2_TARGET_V1'
    assert not dest.exists(), 'Never overwrite an archive'
    bit=route/'camera_to_dsi_display.bit'
    assert not bit.exists(), 'Never reuse an existing bit'
    flow=route/'bitgen.tcl'
    flow.write_text('''if {[catch {
source ./settings.cfg
import_device ph1_35p.db -package PH1P35MDG324 -speed 3
open_project camera_to_dsi_display.prj -noanalyze
import_db {'''+(route/'route.db').as_posix()+'''}
commit_param -step bitgen
bitgen -bit {'''+bit.as_posix()+'''}
export_bitgen_param -file {'''+(route/'bitgen_params.txt').as_posix()+'''}
} message]} {puts "BITGEN_FAILED $message"; exit 1}
puts "VERIFIED_ROUTE_BITGEN_COMPLETE"
exit
''')
    started=time.time()
    with (route/'bitgen_stdout.txt').open('wb') as log:
        rc=subprocess.run(['D:/TD/bin/td_commands_prompt.exe',flow.as_posix()],cwd=PROJECT/'camera_to_dsi_display_Runs/phy_1',stdout=log,stderr=subprocess.STDOUT).returncode
    assert rc==0 and 'VERIFIED_ROUTE_BITGEN_COMPLETE' in (route/'bitgen_stdout.txt').read_text(errors='replace')
    assert bit.is_file() and bit.stat().st_size>100000 and bit.stat().st_mtime>=started
    assert snapshot()==before,'Source changed during bitgen'
    dest.mkdir(); evidence=dest/'build_evidence'; evidence.mkdir()
    shutil.copy2(bit,dest/bit.name)
    for folder,names in ((syn,['SOURCE_MANIFEST.json','stages.json','flow.tcl','syn_1_stdout.txt']),
        (route,['flow.tcl','stdout.txt','route.area','route.ts','route.timing','ignored.timing','clock.txt','bitgen.tcl','bitgen_stdout.txt','bitgen_params.txt'])):
        sub=evidence/folder.name;sub.mkdir()
        for name in names:shutil.copy2(folder/name,sub/name)
    shutil.copy2(a.verification,evidence/'FINAL_VERIFICATION.json')
    info=dict(version='STYLE_V2_TARGET_V1',source_commit=frozen['source_commit'],verification_commit=before['source_commit'],
        tag='style-v2-target-v1-candidate',bit_sha256=sha(bit),route_db_sha256=sha(route/'route.db'),
        synthesis=a.synthesis,placement=a.placement,route=a.route,resources=counts,
        setup_wns=sw,hold_wns=hw,setup_tns=st,hold_tns=ht,board_test='NOT_RUN')
    (dest/'BUILD_INFO.json').write_text(json.dumps(info,indent=2)+'\n')
    (dest/'BUILD_INFO.md').write_text(f'''# STYLE_V2_TARGET_V1

- Actual build source commit: `{frozen['source_commit']}`
- Verification commit: `{before['source_commit']}`
- Candidate tag: `style-v2-target-v1-candidate` (created separately only after archive review)
- Build time: {datetime.datetime.now().astimezone().isoformat()}
- Device: PH1P35MDG324, speed 3; top: design_top_wrapper
- Original generated bit: `{bit.as_posix()}`
- Bit SHA-256: `{sha(bit)}`
- Resources: {json.dumps(counts)}
- Routed Setup/Hold WNS: {sw:+.3f}/{hw:+.3f} ns; TNS: {st:.3f}/{ht:.3f} ns
- SYN, placement and route use identical committed TD inputs. Their processes and raw reports are recorded separately.
- Board Test Status: **NOT_RUN**. Functional simulation and STA do not prove real board stability.
- Warnings and CDC limitations: see `docs/STYLE_V2_TARGET_V1_CDC_REVIEW.md` and final optimization report.
- Rollback: `edge-style-fill-v2-candidate`; historical archive is unchanged.
''')
    print(json.dumps(info,indent=2))

if __name__=='__main__':main()
