"""Current ISP/packer five-mode regression; historical frozen gates stay intact.

This reuses the independent STYLE V2 pixel model, not its obsolete whole-video
hash assumptions. The 61 unchanged TD inputs are checked against actual V2.
Actual transactional DDR/display verification is a separate named test suite.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
import run_edge_style_fill_v2 as model
ROOT=Path(__file__).resolve().parents[1]
HDL=model.HDL
BASE='89093f428878b918036c8a30a0d1afe7764946b8'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--msim',type=Path)
    ap.add_argument('--icarus',action='store_true');a=ap.parse_args()
    assert a.icarus or a.msim
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    old=json.loads((ROOT/'artifacts/bitstreams/EDGE_STYLE_FILL_V2/build_evidence/SOURCE_MANIFEST.json').read_text())['files']
    allowed={str((HDL/p).relative_to(ROOT)).replace('\\','/') for p in ('design_top_wrapper.v','video_in.v','video_out.v','isp/isp_top.v','hdmi_mixer.v')}
    frozen={}
    for rel in old:
        if rel in allowed:continue
        data=(ROOT/rel).read_bytes();reference=subprocess.check_output(['git','show',BASE+':'+rel],cwd=ROOT)
        assert data.replace(b'\r\n',b'\n')==reference.replace(b'\r\n',b'\n'),rel
        frozen[rel]=hashlib.sha256(data).hexdigest()
    assert len(frozen)==61
    stages=[];source_hashes={}
    def simulate(name,top,files,params=(),plus=()):
        out=a.out/name;out.mkdir()
        hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files};source_hashes.update(hashes)
        commands=[[(a.msim/'vlib.exe').as_posix(),'work'],[(a.msim/'vlog.exe').as_posix(),*[p.as_posix() for p in files]],
            [(a.msim/'vsim.exe').as_posix(),'-c','-quiet',*params,top,*plus,'-do','run -all; quit -f -code 0']]
        if a.icarus:
            executable=out/'test.vvp'
            parameters=['-P'+top+'.'+p[2:] for p in params]
            commands=[['C:/iverilog/bin/iverilog.exe','-g2012','-s',top,*parameters,'-o',str(executable),*map(str,files)],
                ['C:/iverilog/bin/vvp.exe',str(executable),*plus]]
        for i,cmd in enumerate(commands):
            r=subprocess.run(cmd,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=3600)
            (out/f'stage_{i}.txt').write_bytes(r.stdout)
            stages.append(dict(name=name,stage=i,argv=cmd,exit_code=r.returncode))
            (a.out/'stages.json').write_text(json.dumps(stages,indent=2)+'\n')
            assert r.returncode==0 and not re.search(rb'\*\* (?:Error|Fatal):|\bFAIL\b',r.stdout),(name,i,r.stdout[-1500:])
        assert b'PASS' in r.stdout,(name,r.stdout[-1500:])
        assert hashes=={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        print('PASS',name,flush=True)
        return r.stdout.decode(errors='replace')
    rgb=a.out/'rgb_vectors.txt';beats,pixels=model.rgb_vectors(rgb)
    simulate('rgb','tb_edge_multi_mode_rgb',[ROOT/'tests/tb_edge_multi_mode_rgb.v',HDL/'isp/rgb_effects_96.v'],plus=['+STIM='+rgb.as_posix()])
    keys=[ROOT/'tests/tb_edge_style_keys.v',HDL/'edge_key_control.v',HDL/'edge_config_cdc.v']
    simulate('keys','tb_edge_style_keys',keys);simulate('config_cdc','tb_edge_style_mailbox',keys)
    results=[]
    for width,height,full in [(64,32,False),(1280,720,True)]:
        data=a.out/f'vectors_{width}';data.mkdir()
        stimulus,packed,words,valid_beats=model.stream_vectors(data,width,height,full)
        files=[ROOT/'tests/tb_edge_style_stream.v',*[HDL/p for p in (
            'isp/edge_control_stream.v','isp/rgb_effects_96.v','isp/style_fill_96.v','isp/edge_detect_96.v',
            'isp/gaussian_pair_3x3.v','isp/nms_gradient_pair_3x3.v','isp/edge_link_pair_3x3.v',
            'isp/edge_center_pair_delay.v','isp/edge_temporal_hold.v','edge_status_osd.v','osd_char_lib.v',
            'data_96bit_to_128bit.v','isp/isp_top.v','isp/data128_96/data128_96.v')],ROOT/'tests/isp_boundary_stubs.v']
        log=simulate('stream_'+str(width),'tb_edge_style_stream',files,
            params=[f'-gWIDTH={width}',f'-gHEIGHT={height}'],
            plus=['+STIM='+stimulus.as_posix(),'+PACK='+packed.as_posix(),'+WORDS='+str(words)])
        assert f'valid_beats={valid_beats} ' in log
        results.append(dict(width=width,height=height,valid_beats=valid_beats,packed_words=words))
    assert frozen=={rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in frozen}
    result=dict(passed=True,reference_commit=BASE,frozen_inputs=frozen,source_sha256=source_hashes,rgb_beats=beats,rgb_pixels=pixels,streams=results,
        scope='Current production ISP/OSD/packer and keys/CDC, forced post-AWB boundary; not physical MIPI/DDR/HDMI or TARGET transactions')
    (a.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS STYLE_TARGET_FIVE_MODES',flush=True)
if __name__=='__main__':main()
