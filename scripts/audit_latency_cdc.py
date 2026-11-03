"""Read-only routed CDC inspection. Never changes SDC, clocks or route database.

The global async exclusions are deliberately retained. Net-delay envelopes are
checked independently for the new held tuple/Gray paths; this is not a claim of
complete inherited FIFO constraint coverage or a proof of metastability MTBF.
TD SWUG105 report_nets/report_cells operate on get_nets/get_cells collections.
"""
import json,re,subprocess,hashlib
from pathlib import Path
from build_latency_performance import ROOT,P,OUT,build

GROUPS={
 'time_gray':'*latency_tick_gray* *u_latency_timebase*gray*',
 'held_tuple':'*latency_selected* *u_latency_slots*selected*',
 'select_toggle':'*latency_select_toggle* *u_latency_slots*select_toggle*',
 'read_bad':'*latency_read_bad* *u_latency_slots*read_bad*',
 'tagged_fifo_gray':'*u_video_in*g_tagged*primary_addr_gray_reg*',
}

def loads(text):
    records=[]
    for net,body in re.findall(r'RUN-1001 : Net: ([^\r\n]+)(.*?)(?=RUN-1001 : Net: |CDC_GROUP_END|\Z)',text,re.S):
        load_part=body.split('Load pin(s):',1)[-1] if 'Load pin(s):' in body else ''
        for pin,kind,location,slack,delay in re.findall(
            r'RUN-1001 :\s+\d+\s+\|\s+([^|]+?)\s*\|\s+([^|]+?)\s*\|\s+\[([^]]+)\]\s*\|\s*(\S+)\s*\|\s*(-?[\d.]+)',load_part):
            records.append(dict(net=net.strip(),pin=pin.strip(),cell=kind.strip(),location=location.strip(),delay_ps=float(delay)))
    return records

def main():
    folder=OUT/'cdc';folder.mkdir(exist_ok=True)
    phy=P/'camera_to_dsi_display_Runs/phy_1';database=phy/'camera_to_dsi_display_pr.db'
    digest=build.sha(database);assert digest==(OUT/'ROUTE_DB_SHA256.txt').read_text().strip()
    script='source ./settings.cfg\nimport_device ph1_35p.db -package PH1P35MDG324 -speed 3\nopen_project camera_to_dsi_display.prj -noanalyze\nimport_db {'+database.as_posix()+'}\n'
    script+='report_clock_summary -file {'+(folder/'clocks.rpt').as_posix()+'}\n'
    script+='report_clock_intersection -file {'+(folder/'clock_intersections.rpt').as_posix()+'}\n'
    for name,pattern in GROUPS.items():
        script+='puts {CDC_GROUP_BEGIN '+name+'}\nreport_nets [get_nets -hier {'+pattern+'}] -connection -mode final -timing -pin_output_limit 200\nputs {CDC_GROUP_END '+name+'}\n'
    script+='puts {CDC_STRUCTURE_BEGIN}\nreport_cells [get_cells -hier {*u_latency_capture*time_sync* *u_latency_display*st1* *u_latency_display*st2* *u_latency_display*st3* *u_latency_display*rb1* *u_latency_display*rb2* *u_latency_slots*hb1* *u_latency_slots*hb2* *u_video_in*g_tagged*sync_r1*}] -connection -pin_loc\nputs {CDC_STRUCTURE_END}\nputs {CDC_AUDIT_COMPLETE}\nexit\n'
    path=folder/'audit.tcl';path.write_text(script)
    with (folder/'stdout.txt').open('wb') as log:
        result=subprocess.run(['D:/TD/bin/td_commands_prompt.exe',path.as_posix()],cwd=phy,stdout=log,stderr=subprocess.STDOUT)
    text=(folder/'stdout.txt').read_text(errors='replace')
    assert result.returncode==0 and 'CDC_AUDIT_COMPLETE' in text and not re.search(r'\bERROR\s*:',text),text[-2000:]
    assert build.sha(database)==digest,'Audit changed route DB'
    parsed={}
    for group in GROUPS:
        block=text.split('CDC_GROUP_BEGIN '+group+'\n',1)[-1].split('CDC_GROUP_END '+group,1)[0]
        parsed[group]=loads(block)
    # Numeric pin delays are picoseconds in TD report_nets. All new Gray paths
    # are conservatively bounded by the faster15ns DDR/CSI period minus0.3ns.
    # The timestamp changes only once per10us, an even looser coherence bound.
    checks={};failures=[]
    specifications=[
      ('time_gray','u_latency_capture/time_sync1',20,14700),
      ('heartbeat','u_latency_slots/hb1',1,14700),
      ('held_tuple','u_latency_display/tuple',85,26666),
      ('select_toggle','u_latency_display/st1',1,26666),
      ('read_bad','u_latency_display/rb1',1,14700),
      ('tagged_fifo_gray','/sync_r1',18,14700),
    ]
    for name,pin_prefix,minimum,limit in specifications:
        raw=parsed['time_gray' if name=='heartbeat' else name]
        selected={r['pin']:r for r in raw if pin_prefix in r['pin']}
        values=[r['delay_ps'] for r in selected.values()]
        passed=len(values)>=minimum and max(values,default=float('inf'))<limit
        checks[name]=dict(passed=passed,unique_loads=len(values),minimum_expected=minimum,
          max_net_delay_ps=max(values,default=None),min_net_delay_ps=min(values,default=None),limit_ps=limit)
        if not passed:failures.append(name)
    # Both actual synchronization stage signals must survive mapping. They may
    # share an LSLICE (oqa/oqb), so raw register-name counts are not cell counts.
    structure=text.split('CDC_STRUCTURE_BEGIN',1)[-1]
    pairs=[i for i in range(20) if f'u_latency_capture/time_sync1[{i}]' in structure and f'u_latency_capture/time_sync2[{i}]' in structure]
    if len(pairs)!=20:failures.append('timestamp_stage_structure')
    info=dict(passed=not failures,route_db_sha256=digest,checks=checks,timestamp_stage_pairs=len(pairs),
        failures=failures,global_sdc_changed=False,
        inherited_gray_constraint_coverage='NOT_FIXED; widened FIFO keeps official core/pointer behavior, with explicit routed delay inspection',
        limit='Route-specific envelope/structure check, not MTBF, analog metastability simulation, or board long-run verification')
    (folder/'NET_LOADS.json').write_text(json.dumps(parsed,indent=2)+'\n')
    (folder/'results.json').write_text(json.dumps(info,indent=2)+'\n')
    print(json.dumps(info,indent=2));assert info['passed'],failures
if __name__=='__main__':main()
