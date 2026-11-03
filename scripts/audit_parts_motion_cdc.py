"""Read-only route audit with bit coverage, ALL fanouts and logical Q aliases.

Packed LSLICE names need not contain the register they house. Never reduce
expected20/85/18 bits to the subset whose physical cell has a familiar name.
"""
import json,re,subprocess,shutil
from pathlib import Path
import audit_latency_cdc as old
from build_inspection_parts_motion import OUT,ROOT,P,build

def source_bits(group,net):
 if group=='time_gray':
  m=re.fullmatch(r'(?:latency_tick_gray|u_latency_timebase/gray)\[(\d+)\]',net)
  return ('time',int(m[1])) if m else None
 if group=='held_tuple':
  m=re.fullmatch(r'(?:latency_selected|u_latency_slots/selected)\[(\d+)\]',net)
  return ('tuple',int(m[1])) if m else None
 m=re.search(r'/(rd_to_wr|wr_to_rd)_cross_inst/primary_addr_gray_reg\[(\d+)\]$',net)
 return (m[1],int(m[2])) if m else None

def main():
 folder=OUT/'cdc';raw=folder/'stdout.txt'
 database=P/'camera_to_dsi_display_Runs/phy_1/camera_to_dsi_display_pr.db'
 digest=build.sha(database);assert digest==(OUT/'ROUTE_DB_SHA256.txt').read_text().strip()
 if not raw.exists():
  old.OUT=OUT
  try:old.main()
  except AssertionError:pass # Our stricter per-source-bit checks below decide.
 text=raw.read_text();assert 'CDC_AUDIT_COMPLETE' in text and not re.search(r'\bERROR\s*:',text)
 prior=json.loads((folder/'results.json').read_text())
 assert prior['route_db_sha256']==digest,'Refuse stale CDC report'
 if not (folder/'NAME_FILTER_FAILURE.json').exists():shutil.copy2(folder/'results.json',folder/'NAME_FILTER_FAILURE.json')
 checks={};patterns=set();points={}
 for group,expected,limit in [('time_gray',{('time',i) for i in range(20)},14700),('held_tuple',{('tuple',i) for i in range(85)},26666),('tagged_fifo_gray',{(d,i) for d in ('rd_to_wr','wr_to_rd') for i in range(9)},14700)]:
  block=text.split('CDC_GROUP_BEGIN '+group+'\n')[1].split('CDC_GROUP_END '+group)[0]
  records=old.loads(block);seen=set();delays=[];fail=[]
  for net,body in re.findall(r'RUN-1001 : Net: ([^\n]+)(.*?)(?=RUN-1001 : Net: |\Z)',block,re.S):
   bit=source_bits(group,net.strip())
   if bit is None:continue
   seen.add(bit);loads=[r for r in records if r['net']==net.strip()]
   declared=int(re.search(r'\bLoads\s+\|\s*(\d+)',body)[1])
   drivers=int(re.search(r'\bDrivers\s+\|\s*(\d+)',body)[1])
   if drivers!=1 or declared<1 or len(loads)!=declared:fail.append(net.strip())
   for r in loads:
    delays.append(r['delay_ps'])
    cell=r['pin'].rsplit('.',1)[0]
    patterns.add(re.sub(r'\[[^]]+\]','*',cell))
  passed=seen==expected and not fail and bool(delays) and max(delays)<limit
  checks[group]=dict(passed=passed,source_bits=len(seen),expected_source_bits=len(expected),missing_bits=sorted(expected-seen),unexpected_bits=sorted(seen-expected),load_count_mismatch=fail,all_routed_loads_checked=len(delays),max_net_delay_ps=max(delays,default=None),limit_ps=limit)
  points[group]=records
 # Also fetch the physical cells housing logical stage outputs, even where
 # the cell's canonical name belongs to an unrelated colocated LUT/register.
 patterns.update(['*u_latency_capture*time_sync*','*u_latency_display*tuple*','*u_latency_display*st1*','*u_latency_display*st2*','*u_latency_display*st3*','*u_latency_display*rb1*','*u_latency_display*rb2*','*u_latency_slots*hb1*','*u_latency_slots*hb2*','*u_video_in*g_tagged*sync_r*'])
 assert all('{' not in p and '}' not in p for p in patterns)
 script='source ./settings.cfg\nimport_device ph1_35p.db -package PH1P35MDG324 -speed 3\nopen_project camera_to_dsi_display.prj -noanalyze\nimport_db {'+database.as_posix()+'}\n'
 script+='report_cells [get_cells -hier {'+' '.join(sorted(patterns))+'}] -connection -pin_loc\nputs {CDC_ALIAS_COMPLETE}\nexit\n'
 path=folder/'aliases.tcl';path.write_text(script)
 with (folder/'alias_stdout.txt').open('wb') as log:
  result=subprocess.run(['D:/TD/bin/td_commands_prompt.exe',path.as_posix()],cwd=database.parent,stdout=log,stderr=subprocess.STDOUT)
 alias=(folder/'alias_stdout.txt').read_text();assert result.returncode==0 and 'CDC_ALIAS_COMPLETE' in alias and not re.search(r'\bERROR\s*:',alias)
 outputs=set()
 for body in re.findall(r'RUN-1001 : Inst\s+: [^\n]+(.*?)(?=RUN-1001 : Inst\s+:|CDC_ALIAS_COMPLETE|\Z)',alias,re.S):
  out=body.split('Output Pin(s):',1)[-1]
  outputs.update(n.strip() for n in re.findall(r'RUN-1001 :\s+\d+\s+\|\s*[^|]+\|\s*\[[^]]+\]\s*\|\s*([^\n]+)',out))
 structures={}
 specifications=[('timestamp_stage1',r'u_latency_capture/time_sync1\[(\d+)\]',20),('timestamp_stage2',r'u_latency_capture/time_sync2\[(\d+)\]',20),('held_tuple',r'u_latency_display/tuple\[(\d+)\]',85)]
 specifications +=[(d+'_firststage',r'u_video_in/.*/'+d+r'_cross_inst/sync_r1\[(\d+)\]',9) for d in ('rd_to_wr','wr_to_rd')]
 for name,pattern,n in specifications:
  bits={int(m[1]) for v in outputs if (m:=re.fullmatch(pattern,v))}
  aliases=0
  if name=='held_tuple':
   # The upper64 tuple bits have the explicit RTL wire alias key. TD chose
   # key[i] as the Q net name; prove that exact slice before mapping aliases.
   rtl=(ROOT/build.HDL/'vision/latency_slot_journal.v').read_text()
   assert re.search(r'wire\s*\[63:0\]\s*key\s*=\s*tuple\[84:21\]',rtl)
   keybits={int(m[1]) for v in outputs if (m:=re.fullmatch(r'u_latency_display/key\[(\d+)\]',v))}
   assert all(0<=b<64 for b in keybits)
   aliases=len(keybits);bits.update(b+21 for b in keybits)
  structures[name]=dict(passed=bits==set(range(n)),output_bits=len(bits),expected=n,explicit_RTL_aliases=aliases,missing=sorted(set(range(n))-bits))
 for group in ('heartbeat','select_toggle','read_bad'):
  checks[group]=prior['checks'][group];assert checks[group]['passed']
 failures=[name for name,c in checks.items() if not c['passed']]+[name for name,c in structures.items() if not c['passed']]
 info=dict(passed=not failures,route_db_sha256=digest,audit_script_sha256=build.sha(Path(__file__)),raw_net_report_sha256=build.sha(raw),alias_report_sha256=build.sha(folder/'alias_stdout.txt'),checks=checks,logical_outputs=structures,failures=failures,global_sdc_changed=False,
  method='Complete20/85/18 source-bit coverage and ALL physical fanouts, plus logical Q-output aliases; never filter by a colocated physical cell canonical name',
  inherited_gray_constraint_coverage='NOT_FIXED; read-only routed envelope/structure audit, not new global SDC constraints',limit='Not full CDC/MTBF signoff, hardware PVT or long-run validation')
 assert build.sha(database)==digest
 (folder/'ALIAS_OUTPUTS.json').write_text(json.dumps(sorted(outputs),indent=2)+'\n')
 (folder/'results.json').write_text(json.dumps(info,indent=2)+'\n')
 print(json.dumps(info,indent=2));assert info['passed'],failures

if __name__=='__main__':main()
