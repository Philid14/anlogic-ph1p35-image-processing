"""Independent image and monitor contract checks; no vendor PHY simulation."""
from pathlib import Path
import argparse,tempfile,json,hashlib,subprocess
import numpy as np
import edge_quality_model as quality
from run_edge_control_v1 import ROOT,HDL,simulate,glyph_table,overlay

BASE='8b3b9853cb900ca2305872b4ad9e129274efdbdf'
OUT=ROOT/'docs/edge_stability_probe_evidence'

def pattern(w,h):
    y,x=np.indices((h,w//2));zone=(y//128)%8;g=np.full((h,w//2),48,np.uint8)
    g[(zone==0)&(y>=32)&(y<96)&(x>=64)&(x<512)]=192
    g[(zone==1)&(x>=320)]=64
    g[(zone==2)&(x>=4*(y%128))]=128
    border=(((y%128>=16)&(y%128<112)&(((x>=96)&(x<100))|((x>=500)&(x<504))))|
           ((((y%128>=16)&(y%128<20))|((y%128>=108)&(y%128<112)))&(x>=96)&(x<504)))
    g[(zone==3)&border]=160
    g[zone==4]=np.where(((x//8)^(y//8))%2,96,48)[zone==4]
    g[zone>=5]=np.where((x//32)%2,112,48)[zone>=5]
    return np.repeat(np.repeat(g,2,axis=1)[:,:,None],3,axis=2)

def checksum(edge):
    # Sample order is left then right per beat, one bit per unique binary pair.
    c=0xffffffff
    for bit in (edge[:,::2].ravel()!=0):
        c=((c<<1)&0xffffffff)^(0x04c11db7 if ((c>>31)^int(bit)) else 0)
    return c

def panel_for(seq,w,h,crc,lead):
    fields=[0x50524231,seq,w*h//4,w*h*3//16,crc,(h<<16)|(w//4),lead<<16,0,0,0x00fffff7]
    return int.from_bytes(b''.join(int(x).to_bytes(4,'big') for x in fields),'big')

def diagnostic_overlay(pixels,x,y,panel,font):
    if not(16<=x<528 and 352<=y<672):return pixels
    row=(y-352)//32;column=(x-16)//32
    fields=[(panel>>(32*(9-i)))&0xffffffff for i in range(10)]
    if row==0:text='PROBE FIXED V1 '+('V' if panel&1 else 'W')
    else:text=('SEQ     ','IN      ','PACK    ','CRC     ','LINE    ','GAP     ','ERR     ','COUNT   ','FLAG    ')[row-1]+f'{fields[row]:08X}'
    char=ord(text[column]);bits=font.get(char,[0]*16)[((y-352)%32)//2]
    return b''.join(bytes((255,255,0) if bits&(1<<(15-((x-16)%32+lane)//2)) else (16,16,16)) for lane in range(4))

def vectors(d,w,h):
    fixed=pattern(w,h);font=glyph_table();rng=np.random.default_rng(91018)
    specs=[(1,80),(0,80),(1,80),(1,60),(0,60),(1,60)]
    edges={t:quality.edges(fixed,t) for t in (60,80)};crcs={t:checksum(a) for t,a in edges.items()}
    stim=d/'stim.txt';pack=d/'pack.txt';words=beats=0;requested=336;panels=[]
    with stim.open('w') as sf,pack.open('w') as pf:
        def cycle(v=0,u=0,l=0,data=0,expected=b'\0'*12,source=0,panel=0):
            sf.write(f'{v} {u} {l} {requested:03x} {data:024x} {expected.hex()} {source:024x} {panel:080x}\n')
        for frame,(mode,th) in enumerate(specs):
            rgb=rng.integers(0,256,(h,w,3),dtype=np.uint8);requested=(mode<<8)|th
            early=frame%2==0
            panel=0 if frame<2 else panel_for(frame-2,w,h,crcs[specs[frame-2][1]],61 if (frame-2)%2==0 else 0)
            panels.append(f'{panel:080x}')
            if early:
                cycle(u=1,panel=panel)
                for _ in range(60):cycle()
            for y in range(h):
                row=bytearray()
                for x in range(0,w,4):
                    # Requests churn during the frame; only SOF may latch them.
                    if x==4:requested=266 if mode else 506
                    pixels=rgb[y,x:x+4] if not mode else [(e,e,e) for e in edges[th][y,x:x+4]]
                    expected=diagnostic_overlay(overlay(pixels,x,y,mode,th,font),x,y,panel,font)
                    cycle(1,int(not early and y==0 and x==0),int(x==w-4),int.from_bytes(rgb[y,x:x+4].tobytes(),'big'),expected,
                          int.from_bytes(fixed[y,x:x+4].tobytes(),'big'),panel)
                    beats+=1;row.extend(expected)
                for off in range(0,len(row),16):pf.write(row[off:off+16].hex()+'\n');words+=1
                for _ in range(4+y%5):cycle()
            for _ in range(80):cycle()
        for _ in range(40):cycle()
    return stim,pack,beats,words,dict(threshold_crc={str(k):f'{v:08X}' for k,v in crcs.items()},panel_hex=panels)

def frozen():
    allowed={'design_top_wrapper.v','video_in.v','video_out.v','edge_status_osd.v','isp/isp_top.v','isp/edge_control_stream.v'}
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'in_out_example','edge_example','artifacts/bitstreams','features'],cwd=ROOT,text=True).splitlines()
    count=0
    for n in names:
        path=ROOT/n
        if path.is_relative_to(HDL) and path.relative_to(HDL).as_posix() in allowed:continue
        if n.endswith('td_project/camera_to_dsi_display.al'):continue
        original=subprocess.check_output(['git','show',BASE+':'+n],cwd=ROOT)
        assert path.read_bytes().replace(b'\r\n',b'\n')==original.replace(b'\r\n',b'\n'),n
        count+=1
    print('PASS probe frozen files',count,'including algorithm/sensor/AWB/SDC/15 old bits/teammates',flush=True)
    return count

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--full',action='store_true');args=ap.parse_args();OUT.mkdir(exist_ok=True)
    frozen();logs=[];summary={}
    with tempfile.TemporaryDirectory(prefix='probe-units-') as temp:
        d=Path(temp)
        logs.append(simulate(d,'tb_probe_monitor',[ROOT/'tests/tb_probe_monitor.v',HDL/'isp/probe_stream_monitor.v',HDL/'data_96bit_to_128bit.v']))
        logs.append(simulate(d,'tb_probe_fifo_events',[ROOT/'tests/tb_probe_fifo_events.v',HDL/'video_in.v',HDL/'video_out.v']))
        logs.append(simulate(d,'tb_probe_capture_arm',[ROOT/'tests/tb_probe_fifo_events.v',HDL/'isp/probe_stream_monitor.v']))
    sources=[HDL/'isp'/n for n in ('edge_control_stream.v','edge_detect_96.v','gaussian_pair_3x3.v','nms_gradient_pair_3x3.v','edge_link_pair_3x3.v','probe_fixed_rgb.v','probe_stream_monitor.v')]
    sources += [HDL/n for n in ('edge_status_osd.v','osd_char_lib.v','data_96bit_to_128bit.v','isp/isp_top.v','isp/data128_96/data128_96.v')]+[ROOT/'tests/isp_boundary_stubs.v']
    cases=[(256,160)]
    if args.full:cases.append((1280,720))
    for w,h in cases:
        with tempfile.TemporaryDirectory(prefix='edge-probe-') as tmp:
            d=Path(tmp);stim,pack,beats,words,meta=vectors(d,w,h)
            result=simulate(d,'tb_edge_probe_stream',[ROOT/'tests/tb_edge_probe_stream.v']+sources,
                [f'-Ptb_edge_probe_stream.W={w}',f'-Ptb_edge_probe_stream.H={h}'],
                [f'+STIM={stim.as_posix()}',f'+PACK={pack.as_posix()}',f'+WORDS={words}'])
            assert f'valid_beats={beats} packed_words={words}' in result
            logs.append(result);summary[f'{w}x{h}']=meta
    frozen()
    (OUT/('rtl_full.json' if args.full else 'rtl_small.json')).write_text(json.dumps(dict(logs=logs,expected=summary),indent=2)+'\n',encoding='utf-8')
    print('PASS PROBE RTL; actual board evidence pending',flush=True)

if __name__=='__main__':main()
