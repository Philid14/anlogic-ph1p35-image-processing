"""Read-only physical bundled-data audit on an isolated TD database copy.

The implementation SDC is never edited. Audit-only clocks/40ns datapath bounds
reveal paths hidden by global asynchronous clock groups. Do not export this DB
or use audit constraints for place/route/bitgen.
"""
import argparse, hashlib, json, re, subprocess
from pathlib import Path
from build_style_v2_target_v1 import ROOT, PROJECT

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--database',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    database=a.database.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    run=PROJECT/'camera_to_dsi_display_Runs/phy_1'
    sdc=PROJECT/'camera_to_dsi_display.sdc';original=sdc.read_bytes()
    prj=(run/'camera_to_dsi_display.prj').read_text(encoding='utf-8')
    prj=re.sub(r'Path="([^"]+)"',lambda m:'Path="'+(run/m[1]).resolve().as_posix()+'"',prj)
    (out/'camera_to_dsi_display.prj').write_text(prj,encoding='utf-8')
    audit=out/'AUDIT_ONLY_NOT_IMPLEMENTED.sdc'
    audit.write_text(sdc.read_text().split('set_clock_groups')[0]+
        '\nset_max_delay -datapath_only 40 -from [get_cells *held_payload*] -to [all_registers]\n'
        # Strictest existing FIFO limit (75MHz domain minus 0.3ns), applied
        # conservatively to every retained Gray-pointer/first-sync pair.
        # Logical-net selection survives two FFs packed under another name.
        # Broader same-domain fanout is also checked under the strict bound.
        'set_max_delay -datapath_only 13.033 -from [all_registers] -to [all_registers] -through [get_nets *cross_inst/primary_addr_gray_reg*]\n')
    flow=out/'flow.tcl'
    flow.write_text('''if {[catch {
source {'''+(run/'settings.cfg').as_posix()+'''}
import_device ph1_35p.db -package PH1P35MDG324 -speed 3
open_project camera_to_dsi_display.prj -noanalyze
import_db {'''+database.as_posix()+'''}
clear_sdc
read_sdc {'''+audit.as_posix()+'''}
puts "BUNDLE_ROOT_CELLS [llength [get_cells *held_payload*]]"
update_timing -mode final
report_timing_path -from [get_cells *held_payload*] -to [all_registers] -ep_num 2000 -path_num 1 -file {'''+(out/'bundle.timing').as_posix()+'''}
report_timing_path -from [all_registers] -to [all_registers] -through [get_nets *cross_inst/primary_addr_gray_reg*] -ep_num 2000 -path_num 1 -file {'''+(out/'gray.timing').as_posix()+'''}
report_timing_exception -file {'''+(out/'exceptions.timing').as_posix()+'''}
} message]} {puts "AUDIT_FAILED $message"; exit 1}
puts "PHYSICAL_BUNDLE_AUDIT_COMPLETE_NO_DB_EXPORT"
exit
''')
    with (out/'stdout.txt').open('wb') as log:
        rc=subprocess.run(['D:/TD/bin/td_commands_prompt.exe',flow.as_posix()],cwd=out,stdout=log,stderr=subprocess.STDOUT).returncode
    stdout=(out/'stdout.txt').read_text(errors='replace')
    report=(out/'bundle.timing').read_text(errors='replace')
    assert rc==0 and 'PHYSICAL_BUNDLE_AUDIT_COMPLETE_NO_DB_EXPORT' in stdout
    assert not re.search(r' ERROR:| CRITICAL-WARNING:',stdout), 'Incomplete audit; inspect stdout'
    assert sdc.read_bytes()==original,'Implementation SDC changed'
    exceptions=(out/'exceptions.timing').read_text(errors='replace')
    assert re.search(r'Confidence\s+:\s+Routed',exceptions), 'A placed database is not routed evidence'
    families=sorted(set(re.findall(r'Begin Point\s+:\s+.*?/((?:u_\w+/)+)held_payload',report)))
    expected=['u_begin/','u_control/','u_display/','u_grant/','u_terminal/','u_time/u_time_csi/','u_time/u_time_ddr/']
    assert families==expected,families
    summary=re.search(r'Max\s+: SWNS\s+(-?[\d.]+)ns, STNS\s+(-?[\d.]+)ns,\s+(\d+) Viol Endpoints,\s+(\d+) Total Endpoints,\s+(\d+) Paths Analyzed',report)
    assert summary, 'Missing max-delay coverage summary'
    wns,tns=float(summary[1]),float(summary[2]);viol,total,analyzed=map(int,summary.group(3,4,5))
    assert wns>=0 and tns==0 and viol==0 and total==analyzed and total<2000
    assert 'Budget              : 40.000ns' in report
    gray=(out/'gray.timing').read_text(errors='replace')
    gm=re.search(r'Max\s+: SWNS\s+(-?[\d.]+)ns, STNS\s+(-?[\d.]+)ns,\s+(\d+) Viol Endpoints,\s+(\d+) Total Endpoints,\s+(\d+) Paths Analyzed',gray)
    assert gm and float(gm[1])>=0 and float(gm[2])==0 and int(gm[3])==0
    assert int(gm[4])==int(gm[5]) and 36<=int(gm[4])<2000,'Incomplete FIFO pointer coverage'
    assert 'Budget              : 13.033ns' in gray
    # Native physical packing can rename a Gray FF after its paired FF.
    # Select logical nets, then prove all nine bits of all four crossings.
    max_gray=gray.split('Max Paths',1)[1].split('Min Paths',1)[0]
    for owner in ('u_writer','u_reader'):
        for crossing in ('wr_to_rd_cross_inst','rd_to_wr_cross_inst'):
            bits=set(re.findall(r'net: [^\n]*/'+owner+r'/[^\n]*/'+crossing+r'/primary_addr_gray_reg\[(\d+)\]',max_gray))
            assert bits==set(map(str,range(9))),(owner,crossing,bits)
    assert set(re.findall(r'Budget\s+: ([\d.]+)ns',max_gray))=={'13.033'}
    for owner in ('u_writer','u_reader'):
        assert re.search(r'Begin Point\s+:\s+[^\n]*/'+owner+r'/[^\n]*primary_addr_gray',gray),owner
        assert re.search(r'End Point\s+:\s+[^\n]*/'+owner+r'/',gray),owner
    result=dict(passed=True,database_sha256=hashlib.sha256(database.read_bytes()).hexdigest(),
        implementation_sdc_sha256=hashlib.sha256(original).hexdigest(),bound_ns=40,
        minimum_registered_bundle_wait_ns=5*13.333,minimum_pulse_bundle_wait_ns=6*13.333,
        wns_ns=wns,tns_ns=tns,total_endpoints=total,analyzed_endpoints=analyzed,
        max_reported_data_delay_ns=max(map(float,re.findall(r'Data Path Delay\s+:\s+([\d.]+)ns',report))),
        gray_pointer_bits=36,gray_bound_ns=13.033,gray_wns_ns=float(gm[1]),gray_endpoints=int(gm[4]),
        gray_max_reported_data_delay_ns=max(map(float,re.findall(r'Data Path Delay\s+:\s+([\d.]+)ns',gray))),
        mailbox_families=families,scope='As-built routed bundles and Gray paths; does not repair implementation-SDC coverage or prove synchronizer MTBF, board or PHY behavior')
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
