"""One bounded native post-route optimization; no RTL/SDC/clock change."""
from pathlib import Path
import subprocess,re,json,time
from build_inspection_ui_dimension_v1 import ROOT,P,OUT,snapshot,sha

def main():
    before=snapshot();frozen=json.loads((OUT/'SOURCE_MANIFEST.json').read_text())
    for k in ('files','al_sha256','old_bits'):assert before[k]==frozen[k]
    phy=P/'camera_to_dsi_display_Runs/phy_1';parent=phy/'camera_to_dsi_display_pr.db'
    assert sha(parent)==(OUT/'ROUTE_DB_SHA256.txt').read_text().strip()
    d=OUT/'polish01';d.mkdir(exist_ok=False)
    flow='''if {[catch {
source ./settings.cfg
import_device ph1_35p.db -package PH1P35MDG324 -speed 3
open_project camera_to_dsi_display.prj -noanalyze
import_db {'''+parent.as_posix()+'''}
phys_opt -post_route -effort high
fix_hold
report_area -io_info -file {'''+(d/'route.area').as_posix()+'''}
update_timing -mode final
report_timing_status -file {'''+(d/'route.ts').as_posix()+'''}
report_timing_summary -file {'''+(d/'route.timing').as_posix()+'''} -ep_num 10 -path_num 1
report_timing_ignored -file {'''+(d/'ignored.timing').as_posix()+'''}
report_timing_exception -file {'''+(d/'exceptions.timing').as_posix()+'''}
report_clock_utilization -file {'''+(d/'clock.txt').as_posix()+'''}
export_db {'''+(d/'route.db').as_posix()+'''}
} msg]} {puts "POLISH_FAILED $msg";exit 1}
puts "POLISH_COMPLETE_NO_BIT"
exit
'''
    (d/'flow.tcl').write_text(flow)
    with (d/'stdout.txt').open('wb') as log:rc=subprocess.run(['D:/TD/bin/td_commands_prompt.exe',(d/'flow.tcl').as_posix()],cwd=phy,stdout=log,stderr=subprocess.STDOUT).returncode
    log=(d/'stdout.txt').read_text(errors='replace');assert rc==0 and 'POLISH_COMPLETE_NO_BIT' in log and not re.search(r'\bERROR\s*:',log)
    def timing(p):return list(map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',p.read_text())))
    sw,st,hw,ht=timing(d/'route.ts');oldsw,_,_,_=timing(OUT/'phy_camera_to_dsi_display_phy.ts')
    selected=sw>oldsw and sw>=0 and hw>=0 and st==ht==0
    result=dict(selected=selected,source_commit=frozen['source_commit'],physical_driver_commit=before['source_commit'],
        parent_database_sha256=sha(parent),database_sha256=sha(d/'route.db'),
        route_database=(d/'route.db').as_posix(),timing_report=(d/'route.ts').as_posix(),area_report=(d/'route.area').as_posix(),
        setup_wns_ns=sw,hold_wns_ns=hw,setup_tns_ns=st,hold_tns_ns=ht,parent_setup_wns_ns=oldsw,
        purpose='One native post-route physical optimization; source/SDC/clock constraints unchanged',board_test='NOT_RUN')
    (d/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    if selected:(OUT/'SELECTED_ROUTE.json').write_text(json.dumps(result,indent=2)+'\n')
    after=snapshot()
    for k in ('files','al_sha256','old_bits'):assert before[k]==after[k],k
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
