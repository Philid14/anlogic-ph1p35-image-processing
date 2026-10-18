"""One complete, unchanged-option TD run; exact committed inputs and old bits.

No seed/clock/constraint changes. Raw failure evidence stays in tmp and must
be archived rather than declaring a failing route to be a candidate.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,json,os,re,subprocess
import prepare_td_runs

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project'
OUT=ROOT/'tmp/edge_temporal_v1'


def main():
    assert not subprocess.check_output(['git','diff','HEAD','--name-only'],cwd=ROOT).strip(),'commit tracked work first'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    entries=re.findall(r'<File Path="([^"]+)"',(P/'camera_to_dsi_display.al').read_text(encoding='utf-8'))
    assert len(entries)==64,len(entries)
    assert not any('temporal_roi_capture' in x or 'probe_' in x or 'temporal_packet' in x for x in entries)
    manifest={}
    for entry in entries:
        f=(P/entry).resolve();rel=f.relative_to(ROOT).as_posix();data=f.read_bytes()
        saved=subprocess.check_output(['git','show',commit+':'+rel],cwd=ROOT)
        assert data.replace(b'\r\n',b'\n')==saved.replace(b'\r\n',b'\n'),rel
        manifest[rel]=hashlib.sha256(data).hexdigest()
    td=Path(os.environ.get('TD_HOME','D:/TD'));exe=td/'bin/td_commands_prompt.exe';flow=td/'doc/scripts/DefaultFlow.tcl'
    snapshot=dict(source_commit=commit,time=datetime.now(timezone(timedelta(hours=8))).isoformat(),files=manifest,
        old_bits={f.relative_to(ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/'artifacts/bitstreams').glob('*/*.bit')},
        default_flow_sha256=hashlib.sha256(flow.read_bytes()).hexdigest())
    OUT.mkdir(exist_ok=True);(OUT/'prebuild.json').write_text(json.dumps(snapshot,indent=2)+'\n')
    prepare_td_runs.main()
    wrapper=OUT/'final_flow.tcl'
    wrapper.write_text('source {'+flow.as_posix()+'}\nreport_timing_summary -file final_timing.rpt -ep_num 10 -path_num 1\nreport_timing_ignored -file ignored_timing.rpt\nexit\n')
    for run,script in (('syn_1',flow),('phy_1',wrapper)):
        directory=P/'camera_to_dsi_display_Runs'/run
        stop=directory/'.stop.f'
        if stop.exists():stop.unlink()
        output=OUT/(run+'_stdout.txt')
        print('START',run,commit,flush=True)
        with output.open('wb') as f:
            result=subprocess.run([exe.as_posix(),script.as_posix()],cwd=directory,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
        text=output.read_text(errors='replace')
        assert result.returncode==0 and not re.search(r'\bERROR\s*:',text),(run,result.returncode)
        assert 'Flow Statistics' in text,run
        if run=='syn_1':
            assert 'export_db camera_to_dsi_display_gate.db' in text
            area=(directory/'camera_to_dsi_display_gate.area').read_text()
            row=next(line for line in area.splitlines() if '|u_hold ' in line)
            cols=[x.strip() for x in row.split('|')[1:-1]]
            print('HISTORY RAM ROW',row,flush=True)
            assert int(cols[5])>=1 and int(cols[4])<2000,'history became registers; stop before PHY'
        else:assert 'BIT-1004 : Generate file camera_to_dsi_display.bit.' in text
        print('COMPLETE',run,'exit',result.returncode,flush=True)
    print('COMPLETE TD; inspect final STA, resources and warnings before candidate',flush=True)


if __name__=='__main__':main()
