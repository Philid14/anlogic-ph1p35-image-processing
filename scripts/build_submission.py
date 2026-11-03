"""Rebuild the lean submission with TD; no historical caches or .git required."""
from pathlib import Path
import argparse,json,re,shutil,subprocess,datetime
import prepare_td_runs as prep
import submission_package as check
ROOT=Path(__file__).resolve().parents[1]
def main():
 a=argparse.ArgumentParser();a.add_argument('--td-root',default='D:/TD');a.add_argument('--prepare-only',action='store_true');args=a.parse_args()
 if not args.prepare_only and len(ROOT.as_posix())>40:
  raise SystemExit('TD6.2 Windows path limit: copy the complete extracted folder to D:/P35 (short root, <=40 characters), then run again. No RTL changes needed.')
 m=check.verify();p=prep.PROJECT;runs=p/'camera_to_dsi_display_Runs'
 for kind in ('syn','phy'):
  folder=runs/(kind+'_1');folder.mkdir(parents=True,exist_ok=True)
  shutil.copy2(ROOT/'submission/build'/f'{kind}_settings.cfg',folder/'settings.cfg')
 prep.main()
 # Native IP constraints live inside the IP tree and must not be omitted.
 support=[p.parent/'user_source/hdl_source/ph1p35_ddr/ddr2/src/adc/ddr2.adc',p.parent/'user_source/hdl_source/ph1p35_ddr/ddr2/src/sdc/ddr2.sdc',p.parent/'user_source/ip_source/w128_d512_fifo/w128_d512_fifo.tcl']
 for q in support:assert q.is_file(),str(q)
 for kind in ('syn','phy'):
  text=(runs/(kind+'_1')/'camera_to_dsi_display.prj').read_text()
  assert len(re.findall(r'<File Path="',text))==91
  for rel in re.findall(r'<File Path="([^"]+)"',text):assert (runs/(kind+'_1')/rel).is_file(),rel
 if args.prepare_only:print('PASS portable TD preparation,91 direct entries and IP constraints');return
 td=Path(args.td_root);exe=td/'bin/td_commands_prompt.exe';flow=td/'doc/scripts/DefaultFlow.tcl';assert exe.is_file() and flow.is_file()
 out=ROOT/'dist/local_build'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
 def run(stage,text,cwd):
  script=out/(stage+'.tcl');script.write_text(text,encoding='utf-8')
  with (out/(stage+'.log')).open('wb') as f:rc=subprocess.run([exe.as_posix(),script.as_posix()],cwd=cwd,stdout=f,stderr=subprocess.STDOUT).returncode
  log=(out/(stage+'.log')).read_text(errors='replace')
  assert rc==0 and stage.upper()+'_COMPLETE' in log and not re.search(r'\bERROR\s*:',log),(stage,'see log')
 run('syn','source {'+flow.as_posix()+'}\nputs "SYN_COMPLETE"\nexit\n',runs/'syn_1')
 text=flow.read_text();needle='if { ![info exists alRun] } { source ./settings.cfg }';assert needle in text
 run('phy',text.replace(needle,'source ./settings.cfg\nset end_step opt_route',1)+'\nputs "PHY_COMPLETE"\nexit\n',runs/'phy_1')
 report=runs/'phy_1/camera_to_dsi_display_phy.ts'
 sw,st,hw,ht=map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',report.read_text()))
 assert sw>=0 and hw>=0 and st==ht==0,'Timing failed: no bitgen'
 db=runs/'phy_1/camera_to_dsi_display_pr.db';bit=out/'camera_to_dsi_display.bit'
 run('bit','source ./settings.cfg\nimport_device ph1_35p.db -package PH1P35MDG324 -speed 3\nopen_project camera_to_dsi_display.prj -noanalyze\nimport_db {'+db.as_posix()+'}\ncommit_param -step bitgen\nbitgen -bit {'+bit.as_posix()+'}\nputs "BIT_COMPLETE"\nexit\n',runs/'phy_1')
 assert bit.is_file() and bit.stat().st_size>1000000
 check.verify()
 (out/'LOCAL_BUILD_INFO.json').write_text(json.dumps(dict(bit_path=str(bit),sha256=check.sha(bit),setup_wns_ns=sw,hold_wns_ns=hw,source_manifest=m,board_test='NOT_RUN'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('PASS local TD build',bit,check.sha(bit))
if __name__=='__main__':main()
