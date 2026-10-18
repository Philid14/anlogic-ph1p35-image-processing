"""Independent bit/center/stream tests. Real PHY and board are outside simulation."""
from pathlib import Path
import argparse,json,subprocess
import numpy as np
import edge_temporal_model as model
import edge_nms_model as nms
import edge_quality_model as quality
import run_edge_control_v1 as control

ROOT=control.ROOT;HDL=control.HDL;OUT=ROOT/'tmp/edge_temporal_v1'


def causal_fields(rgb,th):
    gx,gy,mag=nms.gradients(rgb,True)
    d=nms.nms_details(mag,nms.direction(gx,gy),4)
    active=quality.label_stages(d['magnitude'],th)[-1][1]
    support=(d['center']>=th//2)&d['valid']
    for hop in range(4):support,_=quality.window_labels(support,support,False,6+2*hop)
    return active,support


def unit_test(hold_source=None):
    rng=np.random.default_rng(105);w,h=64,16;b=w*h//4;last=None;lastth=None
    p=OUT/'unit.txt';lines=[]
    def put(r=1,v=0,u=0,l=0,th=60,e=0,s=0,ex=0):lines.append(f'{r} {v} {u} {l} {th} {e} {s} {ex}\n')
    put(r=0);put()
    # Blank, random, repeated, alternating raw mask and support dropout expose
    # unknown startup RAM, phase boundaries, nonrecursive storage and release.
    for frame in range(12):
        th=80 if frame in (7,8) else 60
        raw=rng.integers(0,4,b) if frame%3==0 else np.zeros(b,int)
        support=np.full(b,3) if frame%4 else np.zeros(b,int)
        if frame==5:put(r=0);last=None
        if frame%2==0:
            put(u=1,th=th)
            for _ in range(3):put(th=th)
        for i,(e,s) in enumerate(zip(raw,support)):
            ex=int(e | ((last[i]&s) if last is not None and th==lastth else 0))
            put(v=1,u=int(frame%2==1 and i==0),l=int(i%(w//4)==w//4-1),th=th,e=e,s=s,ex=ex)
            if i%13==8:put(th=th)
        last=raw.copy();lastth=th
        for _ in range(4):put(th=th)
        if frame==9:
            # Short, then malformed full frame: neither may seed history.
            put(u=1,th=th)
            for i in range(7):put(v=1,th=th,e=3,s=0,ex=3)
            last=None
    for _ in range(4):put()
    # Balanced duplicate+missing EOL must not pass a total-count-only gate.
    put(u=1)
    for i in range(b):
        put(v=1,l=int(i%(w//4)==w//4-1 and i!=2*(w//4)-1),e=3,s=0,ex=3)
        if i==w//4-1:put(l=1)
    put(u=1)
    for i in range(b):put(v=1,l=int(i%(w//4)==w//4-1),e=0,s=3,ex=0)
    # Legal late EOL, after the last valid beat, still produces trusted history.
    put(u=1)
    for i in range(b):
        put(v=1,e=3,s=0,ex=3)
        if i%(w//4)==w//4-1:put(l=1)
    put(u=1)
    for i in range(b):put(v=1,l=int(i%(w//4)==w//4-1),e=0,s=3,ex=3)
    for _ in range(4):put()
    # Explicitly poison all history bits in a frame with one missing EOL;
    # next complete all-zero frame with support=3 must not use that memory.
    put(u=1)
    for i in range(b):put(v=1,l=int(i%(w//4)==w//4-1 and i>=w//4),e=3,s=0,ex=3)
    put(u=1)
    for i in range(b):put(v=1,l=int(i%(w//4)==w//4-1),e=0,s=3,ex=0)
    # Overlong frame is invalid even though its first BEATS were complete.
    put(u=1)
    for i in range(b+1):put(v=1,l=int(i%(w//4)==w//4-1),e=3,s=0,ex=3)
    put(u=1)
    for i in range(b):put(v=1,l=int(i%(w//4)==w//4-1),e=0,s=3,ex=0)
    for _ in range(4):put()
    p.write_text(''.join(lines))
    return control.simulate(OUT,'tb_edge_temporal_hold',[ROOT/'tests/tb_edge_temporal_hold.v',hold_source or HDL/'isp/edge_temporal_hold.v'],plus=[f'+STIM={p.as_posix()}'])


def stream_test(w,h,reliability=0,frames=10,hold_source=None):
    import run_edge_quality_v1 as q
    rng=np.random.default_rng(271);x=np.indices((h,w))[1];prev=None;prevth=None;tag=f'{w}_{h}_{reliability}';stim=OUT/f'stream{tag}.txt';pack=OUT/f'pack{tag}.txt'
    beats=words=0;font=control.glyph_table()
    with stim.open('w') as sf,pack.open('w') as pf:
        def cycle(v=0,u=0,l=0,cfg=316,data=0,ex=b'\0'*12):sf.write(f'{v} {u} {l} {cfg:03x} {data:024x} {ex.hex()}\n')
        for f in range(frames):
            mode=0 if f in (4,8) else 1;th=40 if f in (6,7) else 60;cfg=(mode<<8)|th
            gray=np.where(x>=w//2+(2 if f in (3,4,5) else 0),144,48)
            rgb=np.clip(np.repeat(gray[:,:,None],3,2)+rng.integers(-4,5,(h,w,3)),0,255).astype(np.uint8)
            if f in (7,9):rgb[:]=48
            raw,support=causal_fields(rgb,th)
            active=raw | (prev&support) if prev is not None and prevth==th else raw.copy()
            edge=np.repeat(active.astype(np.uint8)*255,2,axis=1)
            early=f%2==0
            if early:
                cycle(u=1,cfg=cfg)
                for _ in range(40):cycle(cfg=cfg)
            for y in range(h):
                row=bytearray()
                for xx in range(0,w,4):
                    pixels=rgb[y,xx:xx+4] if mode==0 else [(e,e,e) for e in edge[y,xx:xx+4]]
                    out=control.overlay(pixels,xx,y,mode,th,font)
                    if reliability and 800<=xx<1248 and 96<=y<128:
                        line='B:1234 S:ABCD ';col=(xx-800)//32;ry=(y-96)//2
                        mask=font.get(ord(line[col]),{}).get(ry,0)
                        out=bytes(c for lane in range(4) for c in ((255,255,0) if mask & (1 << (15-((xx-800)%32)//2-lane//2)) else (16,16,16)))
                    row.extend(out)
                    # Requested changes in-frame must not change current TH or mode.
                    requested=cfg if y==0 and xx==0 else (266 if xx%20==4 else cfg)
                    cycle(1,int(not early and y==0 and xx==0),int(xx==w-4),requested,int.from_bytes(rgb[y,xx:xx+4].tobytes(),'big'),out);beats+=1
                for pos in range(0,len(row),16):pf.write(row[pos:pos+16].hex()+'\n');words+=1
                for _ in range(2+y%3):cycle(cfg=cfg)
            prev=raw;prevth=th
        for _ in range(60):cycle()
    # Reuse the established frame/OSD/packer scoreboard; only depth and params
    # differ. Intermediate gradient checks remain independent and enabled.
    tb=(ROOT/'tests/tb_edge_quality_stream.v').read_text().replace('module tb_edge_quality_stream;','module tb_edge_temporal_stream;').replace('+(QUALITY ? 12:0);','+(QUALITY ? 12:0)+2;')
    tb=tb.replace('.QUALITY_ENABLE(QUALITY))','.QUALITY_ENABLE(QUALITY),.TEMPORAL_ENABLE(1))')
    if reliability:
        tb=tb.replace('.TEMPORAL_ENABLE(1))','.TEMPORAL_ENABLE(1),.RELIABILITY_ENABLE(1))')
        tb=tb.replace('.I_data(data),.I_valid(v),','.I_fifo_event_counts(32\'h1234abcd),.I_data(data),.I_valid(v),')
        tb=tb.replace('.I_edge_config(cfg),','.I_edge_config(cfg),.I_fifo_event_counts(32\'h1234abcd),')
    p=OUT/'tb_edge_temporal_stream.v';p.write_text(tb)
    trace=q.nms.append_intermediate_traces(stim,w,h)
    sources=[p,HDL/'isp/edge_control_stream.v',HDL/'isp/edge_detect_96.v',HDL/'isp/gaussian_pair_3x3.v',HDL/'isp/nms_gradient_pair_3x3.v',HDL/'isp/edge_link_pair_3x3.v',HDL/'isp/edge_center_pair_delay.v',hold_source or HDL/'isp/edge_temporal_hold.v',HDL/'edge_status_osd.v',HDL/'osd_char_lib.v',HDL/'data_96bit_to_128bit.v',HDL/'isp/isp_top.v',HDL/'isp/data128_96/data128_96.v',ROOT/'tests/isp_boundary_stubs.v']
    log=control.simulate(OUT,'tb_edge_temporal_stream',sources,[f'-Ptb_edge_temporal_stream.WIDTH={w}',f'-Ptb_edge_temporal_stream.HEIGHT={h}'],[f'+STIM={trace.as_posix()}',f'+PACK={pack.as_posix()}',f'+WORDS={words}'])
    assert f'valid_beats={beats} ' in log
    return dict(width=w,height=h,reliability=reliability,frames=frames,beats=beats,packed_words=words,log=log)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--full',action='store_true');a=p.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    result=dict(unit=unit_test(),streams=[stream_test(64,32)])
    if a.full:result['streams'].append(stream_test(1280,720))
    (OUT/'rtl_results.json').write_text(json.dumps(result,indent=2)+'\n')
