"""Full TD flow from a clean committed source tree; generated files stay in Runs/tmp.

Does not modify constraints, seeds or TD options. TD_HOME may override D:/TD.
Archive the fresh bit even if final STA misses timing; never label it candidate.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,sys,re,json,hashlib,subprocess
import prepare_td_runs

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project'

def main():
    assert not subprocess.check_output(['git','diff','HEAD','--name-only'],cwd=ROOT).strip(),'Commit tracked changes before build'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    paths=re.findall(r'<File Path="([^"]+)"',(P/'camera_to_dsi_display.al').read_text(encoding='utf-8'))
    assert len(paths)==63
    manifest={}
    for value in paths:
        f=(P/value).resolve();rel=f.relative_to(ROOT).as_posix();b=f.read_bytes()
        original=subprocess.check_output(['git','show',commit+':'+rel],cwd=ROOT)
        assert b.replace(b'\r\n',b'\n')==original.replace(b'\r\n',b'\n'),rel
        manifest[rel]=hashlib.sha256(b).hexdigest()
    td=Path(os.environ.get('TD_HOME','D:/TD'));exe=td/'bin/td_commands_prompt.exe';flow=td/'doc/scripts/DefaultFlow.tcl'
    tmp=ROOT/'tmp';tmp.mkdir(exist_ok=True)
    snapshot=dict(source_commit=commit,time=datetime.now(timezone(timedelta(hours=8))).isoformat(),files=manifest,
        old_bits={f.relative_to(ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/'artifacts/bitstreams').glob('*/*.bit')},
        td_default_flow_sha256=hashlib.sha256(flow.read_bytes()).hexdigest())
    assert len(snapshot['old_bits'])>=15 # preserve failed checkpoints as well
    (tmp/'probe_prebuild.json').write_text(json.dumps(snapshot,indent=2)+'\n',encoding='utf-8')
    prepare_td_runs.main()
    wrapper=tmp/'probe_final_flow.tcl'
    wrapper.write_text('source {'+flow.as_posix()+'}\nreport_timing_summary -file final_timing.rpt -ep_num 10 -path_num 1\nreport_timing_ignored -file ignored_timing.rpt\nexit\n')
    for run,script in (('syn_1',flow),('phy_1',wrapper)):
        directory=P/'camera_to_dsi_display_Runs'/run
        stop=directory/'.stop.f'
        if stop.exists():stop.unlink() # exact generated stop-file, no recursive cleanup
        output=tmp/('probe_'+run+'_stdout.txt')
        print('START',run,commit,flush=True)
        with output.open('wb') as f:
            # TD parses its argv as Tcl: backslash paths lose their separators.
            result=subprocess.run([exe.as_posix(),script.as_posix()],cwd=directory,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
        text=output.read_text(errors='replace')
        assert result.returncode==0 and not re.search(r'\bERROR\s*:',text),(run,result.returncode)
        assert 'Flow Statistics' in text,run
        if run=='syn_1':assert 'export_db camera_to_dsi_display_gate.db' in text
        else:assert 'BIT-1004 : Generate file camera_to_dsi_display.bit.' in text
        print('COMPLETE',run,'exit',result.returncode,flush=True)
    print('PASS TD full flow completed; inspect routed timing and archive before candidate declaration',flush=True)

if __name__=='__main__':main()
