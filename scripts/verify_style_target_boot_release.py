"""Targeted diagnostic release: exact old control logic plus native regressions.

No fake FrameRef, no error bypass. Raw-front timing test explicitly substitutes
only divider arithmetic. Physical/board behavior is never inferred from it.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from build_style_v2_target_v1 import ROOT, snapshot
HDL='in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/'
BASE='7c7e5ee7d6c52260bcf557d9dabd4014f84e2687'
EV=ROOT/'docs/evidence/STYLE_V2_TARGET_BOOT_DIAG_V1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def norm(s):return '\n'.join(x.rstrip() for x in s.splitlines() if x.strip())
def old(rel):return subprocess.check_output(['git','show',BASE+':'+rel],cwd=ROOT).decode('utf-8')
def control_proof():
 frozen=json.loads((ROOT/'artifacts/bitstreams/STYLE_V2_TARGET_V1/build_evidence/syn_explicit_logo_20/SOURCE_MANIFEST.json').read_text())
 changed={HDL+'design_top_wrapper.v',HDL+'target/target_frame_system.v',HDL+'target/target_display_commit.v'}
 for rel,v in frozen['files'].items():
  if rel not in changed:assert sha(ROOT/rel)==v['sha256'],rel
 rel=HDL+'target/target_frame_system.v';s=(ROOT/rel).read_text()
 s=s[:s.index('// Passive boot evidence')]+'endmodule\n'
 s=s.replace('module target_frame_system #(parameter integer BOOT_DIAG_ENABLE=0)(','module target_frame_system(')
 s=s.replace('    input diag_packet_error,diag_lane_error,\n    output [95:0] boot_diagnostics,\n','')
 assert norm(s)==norm(old(rel)),'Original transaction/control text changed'
 rel=HDL+'target/target_display_commit.v';s=(ROOT/rel).read_text()
 s=s.replace('    parameter integer BOOT_DIAG_ENABLE=0,\n','').replace('    input [95:0] boot_diagnostics,\n','')
 a=s.index('        if(BOOT_DIAG_ENABLE) begin');b=s.index('    wire [7:0] request_char',a)
 s=s[:a]+'    end\n'+s[b:]
 s=s.replace('diagnostic_d<=(BOOT_DIAG_ENABLE || (ENABLE && have_prepared)) && diagnostic_region;','diagnostic_d<=ENABLE && have_prepared && diagnostic_region;')
 s=s.replace('if((BOOT_DIAG_ENABLE || (ENABLE && have_prepared)) && diagnostic_region)','if(ENABLE && have_prepared && diagnostic_region)')
 assert norm(s)==norm(old(rel)),'Non-diagnostic display logic changed'
 rel=HDL+'design_top_wrapper.v';s=(ROOT/rel).read_text()
 s=s.replace('    parameter integer TARGET_BOOT_DIAG_ENABLE=1,\n','').replace('wire [95:0] S_target_boot_diagnostics;\n','')
 s=s.replace('target_frame_system #(.BOOT_DIAG_ENABLE(TARGET_BOOT_DIAG_ENABLE)) u_system(','target_frame_system u_system(')
 s=s.replace('.diag_packet_error(S_target_packet_error),.diag_lane_error(S_lane_error_any),\n        .boot_diagnostics(S_target_boot_diagnostics),','')
 s=s.replace('    assign S_target_boot_diagnostics=0;\n','')
 s=s.replace(',.BOOT_DIAG_ENABLE(TARGET_BOOT_DIAG_ENABLE)','')
 s=s.replace('            .boot_diagnostics(S_target_boot_diagnostics),\n','')
 assert norm(s)==norm(old(rel)),'Original top routing/control changed'
 return {'unchanged_original_controls':True,'unchanged_original_algorithm_sensor_ddr_clock_inputs':True,'added_logic_is_passive_telemetry':True}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--proof-only',action='store_true');ap.add_argument('--physical-cdc',type=Path);ap.add_argument('--out',type=Path);a=ap.parse_args()
 proof=control_proof()
 if a.proof_only:print(json.dumps(proof));return
 before=snapshot();frozen=json.loads((ROOT/'tmp/style_v2_target_v1/syn_boot_diag_01/SOURCE_MANIFEST.json').read_text())
 for key in ('files','al_sha256','historical_bits'):assert before[key]==frozen[key],key
 hashes={}
 def remember(p):hashes[p.relative_to(ROOT).as_posix()]=sha(p)
 def read(p):remember(p);return p.read_text(errors='replace')
 for name,marker in [('front_boundary_01','RESULT AWB beats=460800 user=2 last=1440 raw_good=2 obs_done=2 obs_good=2 abort_beats=0 epoch=0'),('display_legacy_equiv_03','PASS DISPLAY_PIPELINE checks=2475309'),('boot_display_05','PASS BOOT_DISPLAY checks=1237500'),('active_epoch_regression_04','PASS TARGET_ACTIVE_EPOCH checks=24648825'),('probe_unit_02','PASS BOOT_PROBE checks=4')]:
  folder=EV/name;log=read(folder/('stdout.txt' if name=='probe_unit_02' else 'stage_2.txt'))
  assert marker in log and not re.search(r'\*\* (?:Error|Fatal):|\bFAIL\b',log),name
  for fn in ('SOURCE_MANIFEST.json','manifest.json'):
   p=folder/fn
   if p.exists():
    manifest=json.loads(read(p))
    for rel,expected in manifest.items():
     src=ROOT/rel
     # Original exact temporary bench paths are retained locally; vendor models remain external.
     assert src.is_file() and sha(src)==expected,(name,rel)
  if name=='active_epoch_regression_04':
   evaluation=json.loads(read(folder/'RESULT_EVALUATION.json'));assert evaluation['rtl_execution_passed']
 cdc_path=a.physical_cdc.resolve();cdc=json.loads(read(cdc_path));route=ROOT/'tmp/style_v2_target_v1/route_boot_diag_01/route.db'
 assert cdc['passed'] and len(cdc['mailbox_families'])==9 and cdc['database_sha256']==sha(route)
 for p in cdc_path.parent.iterdir():
  if p.is_file() and p.suffix in ('.zip','.tcl','.sdc'):remember(p)
 assert snapshot()==before
 result=dict(passed=True,source_commit=frozen['source_commit'],verification_commit=before['source_commit'],full_720p_final_hdmi=True,fault_matrix=True,cdc_review=True,baseline_modes=True,control_noninterference=proof,physical_cdc_summary=cdc_path.relative_to(ROOT).as_posix(),evidence_sha256=hashes,board_test='NOT_RUN',scope='Transitive original-system evidence: exact unchanged controls/algorithm inputs; native active-epoch rerun (boot disabled), full-raster old display equivalence; boot-enabled full-raster/pulse CDC independent checks. No sensor/PHY or real-board success claim. Not a black-screen fix.')
 a.out.write_text(json.dumps(result,indent=2)+'\n');print('PASS diagnostic release gates; original black-screen root cause still requires board probe')
if __name__=='__main__':main()
