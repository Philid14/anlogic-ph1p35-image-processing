"""Resource-only experiment in isolated TD directory. NOT a candidate build.

Never modifies active run databases or historical archives. Inputs are hashed;
staged MAIN adapters are used before their promotion to the formal .al project.
All clock/IP constraints retain identical contents, with absolute paths only.
"""
from pathlib import Path
import re,json,shutil,hashlib,subprocess,os
import prepare_td_runs
ROOT=prepare_td_runs.ROOT
P=prepare_td_runs.PROJECT
HDL=P.parent/'user_source/hdl_source'
STAGING=ROOT/os.environ.get('LATENCY_STAGE_ROOT','tmp/latency_performance/staging')
OUT=ROOT/os.environ.get('LATENCY_RESOURCE_OUT','tmp/latency_performance/integrated_syn_r5')
ADDED=['edge_row_history.v','latency_capture_tag.v','latency_slot_journal.v','latency_tagged_fifo.v','latency_osd.v']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert not OUT.exists(),'Preserve each experiment'
    OUT.mkdir(parents=True)
    original=P/'camera_to_dsi_display_Runs/syn_1'
    manifest={}
    def freeze(logical,path):
        frozen=OUT/'inputs'/logical.relative_to(ROOT)
        frozen.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,frozen)
        return frozen
    def resolved(m):
        path=(original/m[1]).resolve();logical=path
        if path.is_relative_to(HDL):
            candidate=STAGING/path.relative_to(HDL)
            if candidate.exists():path=candidate
        manifest[logical.relative_to(ROOT).as_posix()]=dict(actual_path=str(path),sha256=sha(path))
        # IP paths may resolve helper files relatively. Freeze HDL only; retain
        # the official IP directory layout and verify those original hashes.
        if (path.is_relative_to(HDL) or path.is_relative_to(STAGING)) and path.suffix.lower() in ('.v','.sv'):
            path=freeze(logical,path)
        return '<File Path="'+path.as_posix()+'"'
    project=re.sub(r'<File Path="([^"]+)"',resolved,(original/'camera_to_dsi_display.prj').read_text())
    entries=''
    for order,name in enumerate(ADDED,200):
        path=HDL/'vision'/name
        if path.relative_to(ROOT).as_posix() in manifest:continue
        manifest[path.relative_to(ROOT).as_posix()]=dict(actual_path=str(path),sha256=sha(path))
        frozen=freeze(path,path)
        entries+='<File Path="'+frozen.as_posix()+'"><FileInfo><Attr Name="UsedInSyn" Val="true"/><Attr Name="UsedInP&R" Val="true"/><Attr Name="BelongTo" Val="design_1"/><Attr Name="CompileOrder" Val="'+str(order)+'"/></FileInfo></File>\n'
    project=project.replace('</Verilog>',entries+'</Verilog>',1)
    (OUT/'camera_to_dsi_display.prj').write_text(project)
    settings=(original/'settings.cfg').read_text()
    settings=re.sub(r'\.\./[^\s"}]+',lambda m:(original/m[0]).resolve().as_posix(),settings)
    (OUT/'settings.cfg').write_text(settings)
    for name in ('vision_logo_index.dath','vision_logo_palette.dath','inspection_font.dath','latency_font.dath'):
        path=HDL/'vision'/name;shutil.copy2(path,OUT/name)
        freeze(path,path)
        manifest[path.relative_to(ROOT).as_posix()]=dict(actual_path=str(path),sha256=sha(path))
    (OUT/'SOURCE_MANIFEST.json').write_text(json.dumps(dict(kind='resource-only staged experiment',files=manifest),indent=2)+'\n')
    flow='source {D:/TD/doc/scripts/DefaultFlow.tcl}\nputs "SYN_COMPLETE"\nexit\n'
    (OUT/'syn.tcl').write_text(flow)
    with (OUT/'syn_stdout.txt').open('wb') as log:
        result=subprocess.run(['D:/TD/bin/td_commands_prompt.exe',(OUT/'syn.tcl').as_posix()],cwd=OUT,stdout=log,stderr=subprocess.STDOUT)
    output=(OUT/'syn_stdout.txt').read_text(errors='replace')
    assert result.returncode==0 and 'SYN_COMPLETE' in output and not re.search(r'\bERROR\s*:',output),output[-2500:]
    for item in manifest.values():assert sha(Path(item['actual_path']))==item['sha256']
    print((OUT/'camera_to_dsi_display_gate.area').read_text()[:1600])
if __name__=='__main__':main()
