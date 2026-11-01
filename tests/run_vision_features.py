"""Independent full 720p TRACK/MOTION pixel, status and actual ISP packer test."""
import json,hashlib
import numpy as np
from run_vision_legacy import sources
from vision_sim import ROOT
import run_inspection_v4_stream as old
from vision_models import motion
OUT=ROOT/'tmp/vision_track_motion/features'
def draw_text(out,x,y,text,font,adaptive=False):
    for i,c in enumerate(text):
        for row,bits in font.get(ord(c),{}).items():
            for col in range(16):
                if bits & (1<<(15-col)):
                    a=out[y+row*2:y+row*2+2,x+i*32+col*2:x+i*32+col*2+2]
                    if adaptive:a[:]=np.where((a[:,:,1]>=128)[:,:,None],(16,16,48),(255,255,0))
                    else:a[:]=(255,255,0)
def main():
    OUT.mkdir(parents=True,exist_ok=True);font=old.c.glyph_table();seqv=[];seqd=[];beats=0
    previous=None;last_n=last_ms=last_count=0;last_xy=(0,0);last_ts=0;last_valid=False
    results=[]
    with (OUT/'stim.txt').open('w') as sf:
        def emit(v=0,u=0,l=0,rgb=b'\0'*12,ex=b'\0'*12):
            sf.write(f'{v} {u} {l} {cfg:05x} {rgb.hex()} {ex.hex()} 0 0 400 200 0\n')
            seqv.append(v);seqd.append(int.from_bytes(ex,'big') if v else 0)
        for f,shift in enumerate((0,0,0,64,128,128,None,None)):
            mode=5 if f<4 else 6;cfg=(mode<<16)|(80<<8)|130
            rgb=np.full((720,1280,3),230,np.uint8);mask=np.zeros((720,1280),bool)
            if shift is not None:rgb[320:512,256+shift:512+shift]=(220,40,40);mask[320:512,256+shift:512+shift]=True
            changes,n,ms=motion(rgb,previous);expected=rgb.copy()
            if mode==5 and f>=3:expected[mask]=(0,255,128)
            if mode==6:
                yy,xx=np.where(changes)
                for by,bx in zip(yy,xx):expected[by*16+15,bx*32+28:bx*32+32]=(255,0,255)
            for y,text in ((16,'MODE: '+('TRACK' if mode==5 else 'MOTION')),(56,'THRESHOLD:'),(96,'B:1234 S:ABCD')):
                draw_text(expected,800,y,text.ljust(14),font)
            draw_text(expected,800,136,'SW:0000 R:0 - ',font,True)
            state=('SEARCH','ACQUIRE','TRACK','HOLD')[last_ts] if mode==5 else ('INVALID','WARMUP','STILL','MOTION','GLOBAL')[last_ms]
            lines=[f'RED TRACK: {state:8}' if mode==5 else f'GRID32X16: {state:8} TH012',
                   f'LAST HEX X:{last_xy[0]:03X} Y:{last_xy[1]:03X} N:{last_count:05X}' if mode==5 else f'LAST CHANGED HEX:{last_n:03X}',
                   f'FRAME:{f:08X} VALID:{int(last_valid if mode==5 else f>0)} ERR:0']
            for row,line in enumerate(lines):draw_text(expected,32,192+row*32,line.ljust(32),font,True)
            emit(u=1)
            for _ in range(300):emit()
            for y in range(720):
                for x in range(0,1280,4):
                    emit(1,0,int(x==1276),rgb[y,x:x+4].tobytes(),expected[y,x:x+4].tobytes());beats+=1
                emit();emit()
            last_xy=(383+shift,415) if shift is not None else (0,0);last_count=int(mask.sum())
            last_ts=1 if f<2 else 2 if shift is not None else 3
            last_valid=shift is not None and last_ts==2
            last_n,last_ms=n,ms;previous=rgb
            results.append(dict(frame=f+1,mode=mode,changed_cells=n,motion_state=ms,target_count=last_count))
            if f in (3,4):
                from PIL import Image
                Image.fromarray(expected).save(OUT/f'frame_{f+1}_expected.png')
        for _ in range(40):emit()
    words=old.old.pack_model(seqv,seqd);(OUT/'pack.txt').write_text(''.join(f'{w:032x}\n' for w in words))
    src=[ROOT/'tests/tb_vision_feature_stream.sv']+sources()
    print('Feature vectors ready',beats,len(words),flush=True)
    log=old.c.simulate(OUT,'tb_vision_feature_stream',src,params=['-Ptb_vision_feature_stream.'+x for x in ('WIDTH=1280','HEIGHT=720','COMPARE=1','INSPECTION=1','AUTO_DIMENSION=1','USABILITY_ENABLE=1','INSPECTION_V4=1')],plus=[f'+STIM={(OUT/"stim.txt").as_posix()}',f'+PACK={(OUT/"pack.txt").as_posix()}',f'+WORDS={len(words)}'])
    (OUT/'console.txt').write_text(log)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,beats=beats,words=len(words),frames=8,model=results,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n')
if __name__=='__main__':main()
