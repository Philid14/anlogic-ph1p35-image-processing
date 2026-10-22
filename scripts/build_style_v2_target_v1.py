"""TD integration preflight/full build; preserves all historical archives.

Synthesis alone is a resource investigation, never a board-ready candidate.
Full flow is deliberately gated by independently recorded verification results.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import prepare_td_runs

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project'
OUT=ROOT/'tmp/style_v2_target_v1'
BASE='89093f428878b918036c8a30a0d1afe7764946b8'
HDL='in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/'
ALLOWED={HDL+p for p in ('design_top_wrapper.v','video_in.v','video_out.v','isp/isp_top.v','hdmi_mixer.v','isp/edge_control_stream.v')}
INIT_NAMES=('style_logo_index.dath','style_logo_palette.dath')
INIT_DIR=ROOT/HDL/'target'

def verify_run_initializers():
    for name in INIT_NAMES:
        original=INIT_DIR/name
        if original.exists():
            assert original.read_bytes()==(PROJECT/name).read_bytes(), 'Initialization mirror mismatch: '+name
            for run in ('syn_1','phy_1'):
                assert original.read_bytes()==(PROJECT/'camera_to_dsi_display_Runs'/run/name).read_bytes(),name


def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)


def snapshot():
    dirty=git('diff','HEAD','--name-only').decode('utf-8').splitlines()
    # Other MAIN research may edit prose concurrently. Never stage or overwrite
    # it here. Every actual TD input is independently compared to HEAD below;
    # non-document code/configuration still must be committed before a build.
    assert all(p.startswith('docs/') for p in dirty), 'Commit tracked code/config changes before building'
    if dirty:print('Uncommitted documents excluded from build inputs:',', '.join(dirty),flush=True)
    head=git('rev-parse','HEAD').decode().strip()
    al=PROJECT/'camera_to_dsi_display.al'
    entries=re.findall(r'<File Path="([^"]+)"',al.read_text(encoding='utf-8'))
    assert len(set(entries))==len(entries)
    old=json.loads((ROOT/'artifacts/bitstreams/EDGE_STYLE_FILL_V2/build_evidence/SOURCE_MANIFEST.json').read_text())
    files={}; frozen=[]
    for entry in entries:
        p=(PROJECT/entry).resolve(); rel=p.relative_to(ROOT).as_posix()
        data=p.read_bytes(); saved=git('show',head+':'+rel)
        assert data.replace(b'\r\n',b'\n')==saved.replace(b'\r\n',b'\n'),rel
        assert not any(x in rel for x in ('/tb/','/tools/guard_synth','/temporal_roi','/probe_')),rel
        if rel in old['files'] and rel not in ALLOWED:
            assert data.replace(b'\r\n',b'\n')==git('show',BASE+':'+rel).replace(b'\r\n',b'\n'),rel
            frozen.append(rel)
        files[rel]=dict(sha256=hashlib.sha256(data).hexdigest(),git_blob=git('rev-parse',head+':'+rel).decode().strip())
    assert len(frozen)==60,len(frozen)
    target=[p for p in files if p.startswith('features/color_target/rtl/')]
    assert len(target)==8 and not any(p.endswith('color_target_detect.v') for p in target)
    for run,name in [('syn_1','syn_settings.cfg'),('phy_1','phy_settings.cfg')]:
        settings=PROJECT/'camera_to_dsi_display_Runs'/run/'settings.cfg'
        assert settings.read_bytes()==(ROOT/'artifacts/bitstreams/EDGE_STYLE_FILL_V2/build_evidence'/name).read_bytes()
    implicit=[];mirrors={}
    for name in INIT_NAMES:
        p=INIT_DIR/name
        if p.exists():
            rel=p.relative_to(ROOT).as_posix();raw=p.read_bytes();saved=git('show',head+':'+rel)
            assert raw.replace(b'\r\n',b'\n')==saved.replace(b'\r\n',b'\n'),rel
            files[rel]=dict(sha256=hashlib.sha256(raw).hexdigest(),git_blob=git('rev-parse',head+':'+rel).decode().strip())
            implicit.append(rel)
            mirror=PROJECT/name;mr=mirror.relative_to(ROOT).as_posix()
            assert mirror.read_bytes()==raw,mr
            assert mirror.read_bytes().replace(b'\r\n',b'\n')==git('show',head+':'+mr).replace(b'\r\n',b'\n'),mr
            mirrors[mr]=dict(sha256=hashlib.sha256(raw).hexdigest(),canonical=rel)
    assert len(implicit) in (0,2),'Both ROM initialization files are required'
    return dict(source_commit=head,files=files,frozen_inputs=frozen,
        project_entry_count=len(entries),implicit_initialization_files=implicit,
        initialization_mirrors=mirrors,
        al_sha256=hashlib.sha256(al.read_bytes()).hexdigest(),
        historical_bits={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT/'artifacts/bitstreams').glob('*/*.bit')})


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--full',action='store_true'); ap.add_argument('--attempt',required=True)
    args=ap.parse_args(); before=snapshot()
    dest=OUT/args.attempt; dest.mkdir(parents=True,exist_ok=False)
    (dest/'SOURCE_MANIFEST.json').write_text(json.dumps(before,indent=2)+'\n')
    if args.full:
        gate=json.loads((OUT/'FINAL_VERIFICATION.json').read_text())
        assert gate['source_commit']==before['source_commit'] and gate['passed']
        assert all(gate[k] for k in ('full_720p_final_hdmi','fault_matrix','cdc_review','baseline_modes'))
    prepare_td_runs.main()
    verify_run_initializers()
    td=Path(os.environ.get('TD_HOME','D:/TD'))
    flow=td/'doc/scripts/DefaultFlow.tcl'
    script=dest/'flow.tcl'
    script.write_text('source {'+flow.as_posix()+'}\n'+
        ('report_timing_summary -file final_timing.rpt -ep_num 10 -path_num 1\n'
         'report_timing_ignored -file ignored_timing.rpt\n' if args.full else '')+
         'puts "STYLE_TARGET_FLOW_COMPLETE"\nexit\n')
    stages=[]
    for stage in (['syn_1','phy_1'] if args.full else ['syn_1']):
        cwd=PROJECT/'camera_to_dsi_display_Runs'/stage
        stop=cwd/'.stop.f'
        if stop.exists():stop.unlink()
        started=time.time()
        with (dest/(stage+'_stdout.txt')).open('wb') as log:
            r=subprocess.run([(td/'bin/td_commands_prompt.exe').as_posix(),script.as_posix()],cwd=cwd,
                stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
        stages.append(dict(stage=stage,exit_code=r.returncode))
        (dest/'stages.json').write_text(json.dumps(stages,indent=2)+'\n')
        assert r.returncode==0,(stage,r.returncode)
        output=(dest/(stage+'_stdout.txt')).read_text(errors='replace')
        assert 'STYLE_TARGET_FLOW_COMPLETE' in output,'TD exited without executing the requested flow'
        db=cwd/('camera_to_dsi_display_gate.db' if stage=='syn_1' else 'camera_to_dsi_display_pr.db')
        assert db.is_file() and db.stat().st_mtime>=started,'Missing/stale implementation database'
        print('COMPLETE',stage,'source',before['source_commit'],flush=True)
        verify_run_initializers()
    assert snapshot()==before,'Source or historical bit changed during build'
    print('FULL_FLOW_COMPLETE' if args.full else 'SYNTHESIS_PREFLIGHT_ONLY_NO_BIT',flush=True)


if __name__=='__main__':main()
