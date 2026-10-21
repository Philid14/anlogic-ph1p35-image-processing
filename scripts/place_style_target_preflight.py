"""Measured packing/placement of a specific fresh SYN attempt; never bitgen."""
from pathlib import Path
import argparse, hashlib, json, re, shutil, subprocess
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--synthesis',required=True);ap.add_argument('--attempt',required=True);a=ap.parse_args()
    src=ROOT/'tmp/style_v2_target_v1'/a.synthesis
    manifest=json.loads((src/'SOURCE_MANIFEST.json').read_text())
    assert 'STYLE_TARGET_FLOW_COMPLETE' in (src/'syn_1_stdout.txt').read_text(errors='replace')
    out=ROOT/'tmp/style_v2_target_v1'/a.attempt;out.mkdir(exist_ok=False)
    gate=PROJECT/'camera_to_dsi_display_Runs/syn_1/camera_to_dsi_display_gate.db'
    assert gate.stat().st_mtime >= (src/'SOURCE_MANIFEST.json').stat().st_mtime
    sha=hashlib.sha256(gate.read_bytes()).hexdigest()
    tcl=out/'flow.tcl'
    tcl.write_text('''if {[catch {
source ./settings.cfg
import_device ph1_35p.db -package PH1P35MDG324 -speed 3
open_project camera_to_dsi_display.prj -noanalyze
import_db ../syn_1/camera_to_dsi_display_gate.db
commit_param -step place
place
report_area -io_info -file {'''+(out/'place.area').as_posix()+'''}
export_db {'''+(out/'place.db').as_posix()+'''}
} message]} {puts "PLACEMENT_FAILED $message"; exit 1}
puts "PLACEMENT_COMPLETE_NO_ROUTE_NO_BIT"
exit
''')
    with (out/'stdout.txt').open('wb') as log:
        r=subprocess.run(['D:/TD/bin/td_commands_prompt.exe',tcl.as_posix()],cwd=PROJECT/'camera_to_dsi_display_Runs/phy_1',stdout=log,stderr=subprocess.STDOUT)
    text=(out/'stdout.txt').read_text(errors='replace')
    packed=re.findall(r'(\d+) mslices, (\d+) lslices, \d+ pads',text)
    failure=re.search(r"Design's slice number = (\d+), exceeds the limit (\d+)",text)
    good=r.returncode==0 and 'PLACEMENT_COMPLETE_NO_ROUTE_NO_BIT' in text and (out/'place.db').is_file()
    result=dict(source_commit=manifest['source_commit'],gate_sha256=sha,exit_code=r.returncode,placement_passed=good,
        packed_slices=sum(map(int,packed[-1])) if packed else None,
        capacity_error=int(failure[1]) if failure else None,route='NOT_RUN',bit='NOT_GENERATED')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    dest=ROOT/'docs/evidence/STYLE_V2_TARGET_V1'/a.attempt;dest.mkdir(exist_ok=False)
    for name in ('flow.tcl','stdout.txt','result.json','place.area'):
        if (out/name).is_file():shutil.copy2(out/name,dest/name)
    print(json.dumps(result,indent=2))
    if not good:raise SystemExit(1)
if __name__=='__main__':main()
