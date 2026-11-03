"""Patch unit, legacy off regression and full enabled five-mode/packer comparison.

Boundary Demosaic/AWB are stubs in the stream bench, as in STYLE_V2. This is
post-AWB RTL verification, never a claim of camera, DDR PHY or board success.
"""
from pathlib import Path
import sys,json,hashlib,argparse
import numpy as np
import run_edge_style_fill_v2 as old
import run_edge_control_v1 as control
import color_compare_model as model

ROOT=control.ROOT;HDL=control.HDL;OUT=ROOT/'tmp/color_compare_v1'

def unit():
    rng=np.random.default_rng(20261028);rows=[]
    rv=0;sid=0;mean=[(0,0,0)]*2;seq=0;previous=None;good=False
    def emit(r=1,v=0,u=0,l=0,data=0):
        rows.append(f'{r} {v} {u} {l} {data:024x} {rv} {sid} '+bytes(c for p in mean for c in p).hex())
    for _ in range(3):emit(0)
    colors=[(0,0,0),(255,255,255),(127,127,127),(255,0,0),(0,255,0),(0,0,255),(255,255,0),(0,255,255),(255,0,255)]
    for f in range(80):
        if f==40:
            # Reset abandons both an in-flight capture and the old valid result.
            emit(v=1,data=0xabcdef)
            rv=0;sid=0;seq=0;previous=None;good=False;mean=[(0,0,0)]*2
            emit(r=0);emit(r=0)
        if f<9:
            frame=np.zeros((8,16,3),np.uint8);frame[:]=colors[f]
        else:frame=rng.integers(0,256,(8,16,3),dtype=np.uint8)
        # All last samples matter: test region contains the very last frame beat.
        if f>=9:frame[-1,-4:]=[(255,1,250),(0,255,0),(33,11,99),(200,100,10)]
        rv=int(good);sid=seq;seq=(seq+1)&65535
        if previous is not None:mean=model.patch_means(previous,((0,0,4,8),(12,0,4,8)))
        early=f%2==0;broken=f%11==7;extra=f%17==12;truncated=f%19==15
        if early:emit(u=1);emit();emit()
        for y in range(8):
            for x in range(0,16,4):
                if truncated and y==7:break
                data=int.from_bytes(frame[y,x:x+4].tobytes(),'big')
                emit(v=1,u=int(not early and x==0 and y==0),l=int(x==12 and not(broken and y==3)),data=data)
                if (x+y+f)%5==1:emit()
            emit();emit()
        if extra:emit(v=1,data=0x123456)
        previous=frame;good=not(broken or extra or truncated)
    rv=int(good);sid=seq;mean=model.patch_means(previous,((0,0,4,8),(12,0,4,8)));emit(u=1)
    path=OUT/'stats_vectors.txt';path.write_text('\n'.join(rows)+'\n')
    log=control.simulate(OUT,'tb_color_compare_stats',[ROOT/'tests/tb_color_compare_stats.sv',HDL/'isp/color_compare_stats.v'],plus=['+STIM='+path.as_posix()])
    (OUT/'stats_console.txt').write_text(log)
    return dict(frames=80,checks=len(rows),malformed_frames=True,last_pixel_in_roi=True,seed=20261028)

def stream(full):
    # Existing independent STYLE/Edge/gray/binary/packing model; add only the
    # camera-RGB measurement overlay. Baseline mode/threshold OSD stays last.
    last_rgb=None;stats=None;sid=0
    original_rgb=old.frame_rgb;original_overlay=old.overlay_pixels
    def frame_rgb(w,h,f,rng):
        nonlocal last_rgb,stats,sid
        stats=model.patch_means(last_rgb) if last_rgb is not None and full else None
        sid=f
        last_rgb=original_rgb(w,h,f,rng)
        return last_rgb
    def overlay(pixels,x,y,mode,et,bt,font,fifo_counts=0x1234ABCD):
        pixels=model.overlay(pixels,x,y,stats or [(0,0,0)]*2,sid,font,stats is not None)
        return original_overlay(pixels,x,y,mode,et,bt,font,fifo_counts)
    old.frame_rgb=frame_rgb;old.overlay_pixels=overlay
    w,h=(1280,720) if full else (64,32)
    d=OUT/('full' if full else 'small');d.mkdir(exist_ok=True)
    stim,pack,words,beats=old.stream_vectors(d,w,h,full)
    sources=[ROOT/'tests/tb_edge_style_stream.v']+[HDL/p for p in [
        'isp/edge_control_stream.v','isp/rgb_effects_96.v','isp/style_fill_96.v',
        'isp/edge_detect_96.v','isp/gaussian_pair_3x3.v','isp/nms_gradient_pair_3x3.v',
        'isp/edge_link_pair_3x3.v','isp/edge_center_pair_delay.v','isp/edge_temporal_hold.v',
        'isp/color_compare_stats.v','isp/color_compare_osd.v','edge_status_osd.v','osd_char_lib.v',
        'data_96bit_to_128bit.v','isp/isp_top.v','isp/data128_96/data128_96.v']]+[ROOT/'tests/isp_boundary_stubs.v']
    log=control.simulate(d,'tb_edge_style_stream',sources,
        [f'-Ptb_edge_style_stream.WIDTH={w}',f'-Ptb_edge_style_stream.HEIGHT={h}','-Ptb_edge_style_stream.COMPARE=1'],
        [f'+STIM={stim.as_posix()}',f'+PACK={pack.as_posix()}',f'+WORDS={words}'])
    (d/'console.txt').write_text(log)
    old.frame_rgb=original_rgb;old.overlay_pixels=original_overlay
    return dict(width=w,height=h,beats=beats,packed_words=words,compare_enabled=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--full',action='store_true');a=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    results=dict(unit=unit(),stream=stream(a.full),boundary='post-AWB explicit input; no PHY/board claim')
    results['sources']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [*HDL.glob('isp/color_compare*.v'),HDL/'isp/edge_control_stream.v',HDL/'isp/isp_top.v',ROOT/'tests/tb_edge_style_stream.v',ROOT/'tests/tb_color_compare_stats.sv',ROOT/'tests/color_compare_model.py',Path(__file__)]}
    (OUT/('full_results.json' if a.full else 'small_results.json')).write_text(json.dumps(results,indent=2)+'\n')
    print('PASS COLOR_COMPARE_V1 model/RTL/packing; board not tested',flush=True)

if __name__=='__main__':main()
