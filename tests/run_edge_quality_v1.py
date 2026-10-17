"""Independent spatial labels, all four hardware hops and actual ISP packing."""
from pathlib import Path
import argparse,tempfile,json,hashlib
import numpy as np
import edge_quality_model as model
import edge_nms_model as nms_model
import edge_denoise_model as denoise_model
import run_edge_nms_v1 as nms

ROOT=nms.ROOT;HDL=nms.HDL;control=nms.control;old=nms.old


def frozen():
    manifest=json.loads((ROOT/'tests/edge_quality_frozen_manifest.json').read_text(encoding='utf-8'))
    for name,sha in manifest.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    print('PASS additional quality frozen files',len(manifest),flush=True)
    nms.frozen()
    top=(HDL/'design_top_wrapper.v').read_text()
    assert '.QUALITY_ENABLE(1), .QUALITY_HOPS(4)' in top


def unit_vectors(d,width=64):
    h,w=24,width//2;rng=np.random.default_rng(407);cases=[]
    for state in (0,2,3):
        labels=np.full((h,w),state,dtype=np.uint8);cases.append(labels)
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            if not(dy or dx):continue
            labels=np.zeros((h,w),dtype=np.uint8);labels[10,15]=2;labels[10+dy,15+dx]=3;cases.append(labels)
    for parity in (0,1):
        labels=np.zeros((h,w),np.uint8);labels[10,5+parity:25+parity]=2
        labels[10,5+parity]=3;labels[10,24+parity]=3;labels[16,5:26]=2;labels[18,28]=3
        labels[10,15]=0 # a zero-response gap is NEVER painted across
        cases.append(labels)
    for _ in range(3):cases.append(rng.choice(np.array([0,2,3],np.uint8),(h,w)))
    # Previous frame row/column contamination is visible in following black.
    cases.append(np.zeros((h,w),np.uint8))
    p=d/'labels.txt';beats=0
    with p.open('w') as f:
        def cycle(v=0,u=0,l=0,a=0,expected=(0,0,0,0)):
            f.write(f'{v} {u} {l} {a:x} '+' '.join(f'{e:x}' for e in expected)+'\n')
        for frame,labels in enumerate(cases):
            weak=labels>>1!=0;active=labels&1!=0;stages=[]
            for k in range(4):
                weak,active=model.window_labels(weak,active,False,k*2)
                stages.append((weak.astype(np.uint8)<<1)|active.astype(np.uint8))
            early=frame%2==0
            if early:
                cycle(u=1)
                for _ in range(15):cycle()
            for y in range(h):
                for x in range(0,w,2):
                    cycle(1,int(not early and y==0 and x==0),int(x==w-2),nms.packed(labels[y,x:x+2],2),
                          tuple(nms.packed(s[y,x:x+2],2) for s in stages));beats+=1
                    if frame==14 and x%6==0:cycle()
                for _ in range(y%3+1):cycle()
        cycle(u=1)
        for x in range(4):cycle(1,l=int(x==1),a=15);beats+=1
        cycle(u=1)
        for y in range(h):
            for x in range(w//2):cycle(1,l=int(x==w//2-1));beats+=1
            cycle()
    return p,beats


class Adapter:
    def __init__(self,quality):self.quality=quality
    def scenes(self,width,height):
        values={name:(name,clean,noisy) for name,clean,noisy in nms.ImageAdapter(1).scenes(width,height)}
        values.update({name:(name,clean,noisy) for name,clean,noisy in model.scenes(width,height)})
        return list(values.values())
    def edges(self,rgb,threshold,kind):return model.edges(rgb,threshold,self.quality)


def main():
    p=argparse.ArgumentParser();p.add_argument('--full',action='store_true');p.add_argument('--small',action='store_true');args=p.parse_args()
    frozen()
    sources=[HDL/'isp/edge_detect_96.v',HDL/'isp/gaussian_pair_3x3.v',HDL/'isp/nms_gradient_pair_3x3.v',HDL/'isp/edge_link_pair_3x3.v']
    with tempfile.TemporaryDirectory(prefix='quality-unit-') as tmp:
        d=Path(tmp);control.simulate(d,'tb_edge_quality_class',[ROOT/'tests/tb_edge_quality_class.v']+sources)
        for width in (64,68,72,76,1280):
            # All packed-word remainders plus all80 actual production addresses.
            stim,beats=unit_vectors(d,width)
            result=control.simulate(d,'tb_edge_link_pair',[ROOT/'tests/tb_edge_link_pair.v',sources[-1]],
                params=[f'-Ptb_edge_link_pair.W={width}'],plus=[f'+STIM={stim.as_posix()}'])
            assert f'beats={beats} ' in result
    cases=[(64,32,0,False),(64,32,1,False),(1280,96,1,False)]
    if args.small:cases=cases[:2]
    if args.full:cases.append((1280,720,1,True))
    for width,height,quality,full in cases:
        with tempfile.TemporaryDirectory(prefix='quality-stream-') as tmp:
            d=Path(tmp);old.model=Adapter(quality)
            stim,pack,words,beats=quality_vectors(d,width,height,True,full)
            trace=nms.append_intermediate_traces(stim,width,height)
            allsrc=[ROOT/'tests/tb_edge_quality_stream.v',HDL/'isp/edge_control_stream.v']+sources+[
                HDL/'edge_status_osd.v',HDL/'osd_char_lib.v',HDL/'data_96bit_to_128bit.v',HDL/'isp/isp_top.v',
                HDL/'isp/data128_96/data128_96.v',ROOT/'tests/isp_boundary_stubs.v']
            result=control.simulate(d,'tb_edge_quality_stream',allsrc,
                [f'-Ptb_edge_quality_stream.WIDTH={width}',f'-Ptb_edge_quality_stream.HEIGHT={height}',f'-Ptb_edge_quality_stream.QUALITY={quality}'],
                [f'+STIM={trace.as_posix()}',f'+PACK={pack.as_posix()}',f'+WORDS={words}'])
            assert f'valid_beats={beats} ' in result
            print(f'PASS QUALITY={quality} {width}x{height} beats={beats} words={words}',flush=True)
    frozen();print('PASS EDGE_QUALITY_V1 RTL; real-scene quality and board stability pending',flush=True)


# Adapted from the existing denoise stimulus generator; references are spatial.
def quality_vectors(directory,width,height,denoise,full):
    scenes=old.model.scenes(width,height)
    names={n:noisy for n,_,noisy in scenes}
    names['rgb_random']=np.random.default_rng(917).integers(0,256,(height,width,3),dtype=np.uint8)
    # Each tuple is a full frame, except the explicitly labeled abort sequence.
    configs=[(1,80,n) for n in names]
    configs += [(1,t,'low_step') for t in (10,20,30,40,50,60,70,80,120,160,250)]
    configs += [(0,10,'mixed_noise'),(1,40,'black'),(0,250,'white'),(1,20,'texture')]
    if full:configs=[(1,60,'glasses_n8'),(0,80,'rgb_random'),(1,50,'paper_n8'),(1,40,'black')]
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
            edge=old.model.edges(rgb,threshold,'gaussian' if denoise else 'sobel')
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


if __name__=='__main__':main()
