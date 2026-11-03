"""Denoise equivalence/stream tests; real vendor IP and board are not modeled."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import tempfile
import numpy as np
import edge_denoise_model as model

ROOT=Path(__file__).resolve().parents[1]
HDL=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source'
spec=importlib.util.spec_from_file_location('control',ROOT/'tests/run_edge_control_v1.py')
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)


def frozen():
    manifest=json.loads((ROOT/'tests/edge_denoise_frozen_manifest.json').read_text(encoding='utf-8'))
    for kind in ('frozen_main','read_only_reference','hardware_sources'):
        for name,sha in manifest[kind].items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
        print(f'PASS {kind}: {len(manifest[kind])} unchanged hashes',flush=True)
    control.frozen()
    assert '.EDGE_CONTROL_ENABLE(1), .DENOISE_ENABLE(1)' in (HDL/'design_top_wrapper.v').read_text(encoding='utf-8')


def gaussian_vectors(directory):
    rng=np.random.default_rng(139)
    arrays=[np.full((16,32),255),np.zeros((16,32),dtype=int),
            rng.integers(0,256,(16,32)),np.indices((16,32)).sum(axis=0)%256]
    path=directory/'gaussian.txt';beats=0
    with path.open('w') as f:
        def cycle(v=0,u=0,l=0,t=0,p=0,e=0):f.write(f'{v} {u} {l} {t:02x} {p:04x} {e:04x}\n')
        for frame,a in enumerate(arrays):
            expected=model.prefilter(a,'gaussian')
            early=frame%2==0
            if early:
                cycle(u=1)
                for _ in range(8):cycle()
            for y in range(16):
                for x in range(0,32,2):
                    cycle(1,int(not early and y==0 and x==0),int(x==30),
                        (x+17*y)%256,int(a[y,x])*256+int(a[y,x+1]),int(expected[y,x])*256+int(expected[y,x+1]))
                    beats+=1
                    if frame==2 and x%6==0:cycle(t=187)
                for _ in range(1+y%3):cycle(t=31)
        # Abort an incomplete white frame then restore a black full frame.
        cycle(u=1);cycle(1,p=65535);cycle(1,l=1,p=65535)
        beats+=2
        cycle(u=1)
        for y in range(16):
            for x in range(0,32,2):cycle(1,l=int(x==30));beats+=1
            cycle()
    return path,beats


def vectors(directory,width,height,denoise,full):
    scenes=model.scenes(width,height)
    names={n:noisy for n,_,noisy in scenes}
    names['rgb_random']=np.random.default_rng(917).integers(0,256,(height,width,3),dtype=np.uint8)
    # Each tuple is a full frame, except the explicitly labeled abort sequence.
    configs=[(1,80,n) for n in names]
    configs += [(1,t,'low_step') for t in (10,20,40,60,100,120,160,250)]
    configs += [(0,10,'mixed_noise'),(1,40,'black'),(0,250,'white'),(1,20,'texture')]
    if full:configs=[(1,80,'mixed_noise'),(0,80,'texture'),(1,40,'low_step'),(1,20,'black')]
    stimulus=directory/'stim.txt';packed=directory/'pack.txt'
    font=control.glyph_table();beats=words=0;requested=336
    with stimulus.open('w') as sf,packed.open('w') as pf:
        def cycle(v=0,u=0,l=0,rgb=0,ex=b'\0'*12,request=None):
            nonlocal requested
            if request is not None:requested=request
            sf.write(f'{v} {u} {l} {requested:03x} {rgb:024x} {ex.hex()}\n')
        for frame,(mode,threshold,name) in enumerate(configs):
            rgb=names[name].copy()
            # Independently colored lanes expose byte/order errors in Origin
            # and the pair-gray front end, not merely replicated gray inputs.
            if name=='texture':
                rgb[:,:,0]=np.roll(rgb[:,:,0],3,axis=1)
                rgb[:,:,2]=np.clip(rgb[:,:,2].astype(int)+19,0,255)
            edge=model.edges(rgb,threshold,'gaussian' if denoise else 'sobel')
            cfg=(mode<<8)|threshold;early=frame%2==0
            if early:
                cycle(u=1,request=cfg)
                for _ in range(60):cycle()
            for y in range(height):
                row=bytearray()
                for x in range(0,width,4):
                    if not early and y==0 and x==0:requested=cfg
                    if x%20==4:requested=(((frame+x)&1)<<8)|(10+((x+y)%25)*10)
                    pixels=rgb[y,x:x+4] if not mode else [(e,e,e) for e in edge[y,x:x+4]]
                    output=control.overlay(pixels,x,y,mode,threshold,font)
                    data=int.from_bytes(rgb[y,x:x+4].tobytes(),'big')
                    cycle(1,int(not early and y==0 and x==0),int(x==width-4),data,output)
                    row.extend(output);beats+=1
                for off in range(0,len(row),16):pf.write(row[off:off+16].hex()+'\n');words+=1
                for _ in range(1+y%5):cycle()
            # Next SOF can arrive while old pixels remain in the longer pipe.
        if not full:
            cycle(u=1,request=336)
            for x in range(4):cycle(1,l=int(x==1),rgb=(1<<96)-1);beats+=1
            for _ in range(3):pf.write('0'*32+'\n');words+=1
            cycle(u=1,request=266)
            for _ in range(60):cycle()
            for y in range(height):
                row=bytearray()
                for x in range(0,width,4):
                    output=control.overlay([(0,0,0)]*4,x,y,1,10,font)
                    cycle(1,l=int(x==width-4),rgb=int.from_bytes(b'\xa0'*12,'big'),ex=output)
                    row.extend(output);beats+=1
                for off in range(0,len(row),16):pf.write(row[off:off+16].hex()+'\n');words+=1
                cycle()
    return stimulus,packed,words,beats


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--full',action='store_true');args=parser.parse_args()
    frozen();model.baseline_equivalence()
    with tempfile.TemporaryDirectory(prefix='denoise-unit-') as temp:
        d=Path(temp);stim,beats=gaussian_vectors(d)
        result=control.simulate(d,'tb_gaussian_pair',[ROOT/'tests/tb_gaussian_pair.v',HDL/'isp/gaussian_pair_3x3.v'],plus=[f'+STIM={stim.as_posix()}'])
        assert f'valid_beats={beats} ' in result
    # Prior key/CDC/sensor/decimal tests stay unchanged and are run by the
    # existing control suite. This runner adds both compilation variants.
    cases=[(64,16,0,False),(64,16,1,False),(1280,96,1,False)]
    if args.full:cases.append((1280,720,1,True))
    for width,height,denoise,full in cases:
        with tempfile.TemporaryDirectory(prefix='denoise-stream-') as temp:
            d=Path(temp);stim,packed,words,beats=vectors(d,width,height,denoise,full)
            sources=[ROOT/'tests/tb_edge_control_stream.v',HDL/'isp/edge_control_stream.v',HDL/'isp/edge_detect_96.v',
                HDL/'isp/gaussian_pair_3x3.v',HDL/'edge_status_osd.v',HDL/'osd_char_lib.v',HDL/'data_96bit_to_128bit.v',
                HDL/'isp/isp_top.v',HDL/'isp/data128_96/data128_96.v',ROOT/'tests/isp_boundary_stubs.v']
            result=control.simulate(d,'tb_edge_control_stream',sources,
                [f'-Ptb_edge_control_stream.WIDTH={width}',f'-Ptb_edge_control_stream.HEIGHT={height}',f'-Ptb_edge_control_stream.DENOISE={denoise}'],
                [f'+STIM={stim.as_posix()}',f'+PACK={packed.as_posix()}',f'+WORDS={words}'])
            assert f'valid_beats={beats} ' in result
            frame_label='4' if full else '26+recovery'
            print(f'PASS denoise={denoise} {width}x{height}, frames={frame_label}, beats={beats}, words={words}',flush=True)
    frozen();print('PASS EDGE_DENOISE_V1; board noise/long-run behavior pending',flush=True)


if __name__=='__main__':main()
