"""Production ISP + five algorithms + overlays + exact DDR packing.

Explicit post-AWB RGB and already-synchronized controls/calibration are test
boundaries. Real debounce/calibration are separately tested with actual RTL.
No physical sensor/DDR/HDMI or board accuracy claim.
"""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import run_edge_style_fill_v2 as old
import run_edge_control_v1 as c
from style_fill_v2_model import style
from color_compare_model import patch_means
from planar_measure_model import measure
import inspection_osd_model as screen
import auto_dimension_model as drawing

OUT=c.ROOT/'tmp/auto_dimension_v2'
def scene(w,h,f):
    rgb=np.full((h,w,3),230,np.uint8)
    if w==1280:
        rgb[240:460,400:820]=25
        rgb[314:390,600:680]=230
        if f>=4:rgb=255-rgb
    else:
        rgb[h//4:3*h//4,w//4:3*w//4]=25
    return rgb

def vectors(directory,w,h,full):
    # Six frames cover five modes plus X/Y ruler guides and both polarities.
    specs=[(0,0,False),(1,1,False),(2,3,False),(3,3,True),(4,11,False),(0,15,False)]
    if not full:specs +=[(0,7,True),(4,0,False)]
    font=c.glyph_table();stim=directory/'stim.txt';packed=directory/'pack.txt'
    seq_v=[];seq_data=[];previous=None;previous_raw=None;beats=0;cfg=0;ui=0;cal=False
    with stim.open('w') as sf:
        def emit(v=0,u=0,l=0,rgb=0,ex=bytes(12),ui_override=None):
            actual_ui=ui if ui_override is None else ui_override
            sf.write(f'{v} {u} {l} {cfg:05x} {rgb:024x} {ex.hex()} {actual_ui} {int(cal)} 400 200\n')
            seq_v.append(v);seq_data.append(int.from_bytes(ex,'big') if v else 0)
        for f,(mode,ui,cal) in enumerate(specs):
            rgb=scene(w,h,f);cfg=(mode<<16)|(80<<8)|130
            active,raw=old.expected_edge(rgb,80,previous_raw,80 if previous_raw is not None else None)
            edge=np.repeat(active.astype(np.uint8)*255,2,axis=1);styled=style(rgb)
            means=patch_means(previous[0]) if previous is not None and full else None
            if previous is not None and full:
                prev,prev_ui=previous;yy=(77*prev[:,:,0].astype(np.uint16)+150*prev[:,:,1].astype(np.uint16)+29*prev[:,:,2].astype(np.uint16)+128)>>8
                m=measure(yy>=130,bool(prev_ui&4));m['valid']=bool(prev_ui&4)==bool(ui&4)
            else:m=dict(present=False,sizes=(0,0,0,0),box=(0,0,0,0),gap=(False,False),valid=False)
            if full:
                gray=(77*rgb[:,:,0].astype(np.uint16)+150*rgb[:,:,1].astype(np.uint16)+29*rgb[:,:,2].astype(np.uint16)+128)>>8
                base=rgb if mode==0 else np.repeat(gray[:,:,None],3,axis=2).astype(np.uint8) if mode==1 else np.repeat((gray>=130)[:,:,None]*255,3,axis=2).astype(np.uint8) if mode==2 else np.repeat(edge[:,:,None],3,axis=2) if mode==3 else styled
                gaps=drawing.gap_coordinates(previous[0],bool(previous[1]&4)) if previous is not None else (0,0,0,0)
                drawn=drawing.draw(base,m,font,cal,400,200,bool(ui&8),status=0,gaps=gaps)
            # Always early SOF here. Inline SOF, malformed geometry and valid
            # gaps are independently covered by unit and legacy stream tests.
            emit(u=1)
            for _ in range(300):emit()
            for y in range(h):
                for x in range(0,w,4):
                    original=[tuple(int(z) for z in p) for p in rgb[y,x:x+4]]
                    if mode==0:pixels=original
                    elif mode in (1,2):
                        pixels=[]
                        for p in original:
                            yy=old.luma(p);q=yy if mode==1 else 255 if yy>=130 else 0
                            pixels.append((q,q,q))
                    elif mode==4:pixels=[tuple(int(z) for z in p) for p in styled[y,x:x+4]]
                    else:pixels=[(int(edge[y,x+k]),)*3 for k in range(4)]
                    if full:
                        if ui&2:
                            pixels=[tuple(int(v) for v in p) for p in drawn[y,x:x+4]]
                        else:pixels=screen.overlay(pixels,x,y,ui,means,f,m,font,cal,400,200,130)
                    expected=screen.status(pixels,x,y,mode,80,130,font)
                    data=int.from_bytes(rgb[y,x:x+4].tobytes(),'big')
                    # Mid-frame switch changes cannot tear the current overlays.
                    emit(1,0,int(x==w-4),data,expected,ui_override=ui^3 if 200<=y<250 else ui)
                    beats+=1
                    if not full and (x//4)%23==9:emit()
                emit();emit()
            previous=(rgb,ui);previous_raw=raw
        for _ in range(40):emit()
    words=old.pack_model(seq_v,seq_data)
    packed.write_text(''.join(f'{v:032x}\n' for v in words))
    return stim,packed,len(words),beats

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--full',action='store_true');a=ap.parse_args()
    w,h=(1280,720) if a.full else (64,32)
    d=OUT/('full' if a.full else 'small');d.mkdir(parents=True,exist_ok=True)
    stim,packed,words,beats=vectors(d,w,h,a.full)
    names=['isp/edge_control_stream.v','isp/rgb_effects_96.v','isp/style_fill_96.v',
      'isp/edge_detect_96.v','isp/gaussian_pair_3x3.v','isp/nms_gradient_pair_3x3.v',
      'isp/edge_link_pair_3x3.v','isp/edge_center_pair_delay.v','isp/edge_temporal_hold.v',
      'isp/color_compare_stats.v','isp/color_compare_osd.v','isp/inspection_control.v',
      'isp/inspection_calibration.v','isp/ruler_auto_calibration.v','isp/engineering_dimension_marks.v','isp/planar_measure_stats.v','edge_key_control.v',
      'edge_status_osd.v','osd_char_lib.v','data_96bit_to_128bit.v','isp/isp_top.v',
      'isp/data128_96/data128_96.v']
    sources=[c.ROOT/'tests/tb_edge_style_stream.v']+[c.HDL/n for n in names]+[c.ROOT/'tests/isp_boundary_stubs.v']
    print(f'Vectors ready: {w}x{h} {beats} beats / {words} words; running actual RTL',flush=True)
    log=c.simulate(d,'tb_edge_style_stream',sources,[f'-Ptb_edge_style_stream.WIDTH={w}',f'-Ptb_edge_style_stream.HEIGHT={h}',
        '-Ptb_edge_style_stream.COMPARE=1','-Ptb_edge_style_stream.INSPECTION=1','-Ptb_edge_style_stream.AUTO_DIMENSION=1'],
        [f'+STIM={stim.as_posix()}',f'+PACK={packed.as_posix()}',f'+WORDS={words}'])
    (d/'console.txt').write_text(log)
    result=dict(passed=True,width=w,height=h,beats=beats,words=words,frames=6 if a.full else 8,
      sources={p.relative_to(c.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
      boundary='post-AWB RGB + synchronized UI/calibration; debounce/calibration separately tested; board NOT_RUN')
    (OUT/('full_results.json' if a.full else 'small_results.json')).write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
