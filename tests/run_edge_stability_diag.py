"""Reproduce diagnostic evidence without changing any TD build input.

python -X utf8 tests/run_edge_stability_diag.py [--full]
--full adds production 720p repeated frames, exact OSD/packer/isp_top routing.
"""
from pathlib import Path
import argparse,tempfile,json,hashlib,subprocess
import numpy as np
import edge_stability_model as model
import edge_denoise_model as den
import edge_quality_model as quality
import run_edge_quality_v1 as old
import run_edge_nms_v1 as nms
from run_edge_control_v1 import ROOT,HDL,simulate,glyph_table,overlay

BASE='b64daf39af09980621adb1138df1674a8501ea09'

def protected():
    # Protect ALL tracked files under the project, all historical bits and tags.
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'in_out_example','edge_example','artifacts/bitstreams'],cwd=ROOT,text=True).splitlines()
    changed=subprocess.check_output(['git','diff',BASE,'--name-only','--','in_out_example','edge_example','artifacts/bitstreams'],cwd=ROOT,text=True).splitlines()
    assert not changed,changed
    bits={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'artifacts/bitstreams').glob('*/*.bit'))}
    assert len(bits)==15,len(bits)
    return dict(baseline=BASE,protected_tracked_files=len(names),historical_bit_sha256=bits,
                formal_tracked_diff=[])

def fixture(w,h):
    y,x=np.indices((h,w));gray=48+(x>=w//3)*15+(y>=h//2)*35+(((2*x+3*y)//17)%2)*8
    gray+=((x-w//2)**2+(y-h//2)**2<(min(h,w)//4)**2)*24
    # Distinct channels/lanes expose ordering and rounding errors.
    return np.stack([gray+(x%7),gray+(y%5),gray+((x+y)%3)],axis=-1).astype(np.uint8)

def frames(w,h):
    fixed=fixture(w,h);rng=np.random.default_rng(531)
    # Different predecessor fills caches; fixed frames vary only legal timing.
    return [rng.integers(0,256,fixed.shape,dtype=np.uint8)]+[fixed.copy() for _ in range(4)]+[np.zeros_like(fixed),fixed.copy()]

def isolated_stage_vectors(path,link=False):
    h=24;w=32
    m=np.zeros((h,w),int)
    if link:m[12,10:19]=40;m[12,14]=59
    else:m[8:20,14:16]=100
    m2=m.copy()
    if link:m2[12,14]=60
    else:m2[8:20,15]=101
    with path.open('w') as f:
        def cycle(v=0,u=0,l=0,fields=None):
            if fields is None:fields=['0']*(5 if link else 10)
            f.write(f'{v} {u} {l} '+' '.join(fields)+'\n')
        for mag in (m,m2,m,m2):
            axis=np.zeros_like(mag);detail=model.nms.nms_details(mag,axis,0)
            weak=mag>=30;active=mag>=60;labels=[]
            for k in range(4):
                weak,active=quality.window_labels(weak,active,False,2*k)
                labels.append((weak.astype(int)<<1)|active)
            cycle(u=1)
            for _ in range(60):cycle()
            for y in range(h):
                for x in range(0,w,2):
                    sl=slice(x,x+2)
                    if link:
                        initial=((mag>=30).astype(int)<<1)|(mag>=60)
                        fields=[f'{nms.packed(a[y,sl],2):x}' for a in [initial]+labels]
                    else:
                        fields=['003c',f'{nms.packed(mag[y,sl],14):07x}','0',
                          f"{nms.packed(detail['magnitude'][y,sl],14):07x}",f"{nms.packed(detail['keep'][y,sl],1):x}",str(int(detail['valid'][y,x]))]
                        fields += [f'{nms.packed(detail[name][y,sl],bits):x}' for name,bits in (('center',14),('direction',2),('negative',14),('positive',14))]
                    cycle(1,0,int(x==w-2),fields)
                cycle()
            for _ in range(30):cycle()
    return path

def historic_checks(logs,sources):
    for tag,d,n in (('edge-control-v1-candidate',0,0),('edge-denoise-v1-candidate',1,0),('edge-nms-v1-candidate',1,1)):
        with tempfile.TemporaryDirectory(prefix='stability-history-') as temp:
            path=Path(temp);srcs=[]
            # Export only actual version modules, leaving the checkout intact.
            for current in sources:
                name=current.relative_to(ROOT).as_posix()
                got=subprocess.run(['git','show',f'{tag}:{name}'],cwd=ROOT,capture_output=True)
                if got.returncode==0:
                    dest=path/current.name;dest.write_bytes(got.stdout);srcs.append(dest)
            stim,_,beats,_,_=vectors(path,64,64,d,n,0)
            bench=path/'tb_edge_stability.v'
            # Adapt only TB parameter binding for historical module interfaces.
            binding='.RUNTIME_THRESHOLD(1)'+(', .DENOISE_ENABLE(D)' if d else '')+(', .NMS_ENABLE(N)' if n else '')
            text=(ROOT/'tests/tb_edge_stability.v').read_text().replace(
                '.RUNTIME_THRESHOLD(1),\n  .DENOISE_ENABLE(D),.NMS_ENABLE(N),.QUALITY_ENABLE(Q)',binding)
            bench.write_text(text)
            result=simulate(path,'tb_edge_stability',[bench]+srcs,
                [f'-Ptb_edge_stability.{k}={v}' for k,v in dict(W=64,H=64,D=d,N=n,Q=0).items()],[f'+STIM={stim.as_posix()}'])
            assert f'beats={beats} ' in result
            logs.append('HISTORICAL '+tag+'\n'+result)

def vectors(d,w,h,filtered,nm,qual,integrated=False):
    stim=d/'stim.txt';pack=d/'pack.txt';traces=[];beats=words=0;font=glyph_table()
    with stim.open('w') as sf,pack.open('w') as pf:
        def cycle(v=0,u=0,l=0,fields=None):
            if fields is None:fields=['0']*(3 if integrated else 10)
            sf.write(f'{v} {u} {l} '+' '.join(fields)+'\n')
        for frame,rgb in enumerate(frames(w,h)):
            s=model.stages(rgb,filtered,60);m=s['mag'];detail=s['detail']
            a=s['labels'][-1][1] if qual else ((detail['magnitude']>=60) if nm else m>=60)
            edge=np.repeat(a.astype(np.uint8)*255,2,1)
            hashes={k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in dict(source=s['source'],gx=s['gx'],gy=s['gy'],mag=m,nms=detail['magnitude'],**{f'hop{k+1}':x[1] for k,x in enumerate(s['labels'])}).items()}
            traces.append(hashes)
            # Compare same input coordinate across different predecessors/timing.
            if frame in (2,3,4,6):assert hashes==traces[1]
            early=frame%2==0
            if early:
                cycle(u=1,fields=['13c','0','0'] if integrated else None)
                for _ in range(60+frame):cycle()
            for y in range(h):
                row=bytearray()
                for x in range(0,w,4):
                    n=x//2;v=int.from_bytes(rgb[y,x:x+4].tobytes(),'big')
                    eo=int.from_bytes(bytes(np.repeat(edge[y,x:x+4],3)),'big')
                    if integrated:
                        out=overlay([(e,e,e) for e in edge[y,x:x+4]],x,y,1,60,font)
                        fields=['13c',f'{v:024x}',out.hex()];row.extend(out)
                    else:
                        fields=[f'{v:024x}',f'{eo:024x}',f"{nms.packed(s['source'][y,n:n+2],8):04x}",
                            f"{nms.packed((s['gx'][y,n],s['gy'][y,n],s['gx'][y,n+1],s['gy'][y,n+1]),13):013x}",
                            f'{nms.packed(m[y,n:n+2],14):07x}',f"{nms.packed(s['axis'][y,n:n+2],2):x}",
                            f"{nms.packed(detail['magnitude'][y,n:n+2],14):07x}",f"{nms.packed(detail['keep'][y,n:n+2],1):x}",
                            f"{nms.packed([nms.packed(((weak[y,n:n+2].astype(int)<<1)|active[y,n:n+2]),2) for weak,active in s['labels']],4):04x}",
                            str(int(y>=(4 if filtered else 2) and x>=(8 if filtered else 4)))]
                    cycle(1,int(not early and y==0 and x==0),int(x==w-4),fields);beats+=1
                    # Legal bubbles INSIDE a row, tlast is still at real row end.
                    # The Edge interface tolerates bubbles; the existing packer
                    # requires continuous runs in multiples of four beats.
                    # Its separate contract test records the counterexample.
                    if not integrated and frame in (3,6) and x%52==0:cycle()
                if integrated:
                    for off in range(0,len(row),16):pf.write(row[off:off+16].hex()+'\n');words+=1
                for _ in range(1+(y+frame)%7):cycle()
            for _ in range(35+frame):cycle()
        for _ in range(40):cycle()
    return stim,pack,beats,words,traces

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--full',action='store_true');args=ap.parse_args()
    model.OUT.mkdir(exist_ok=True);before=protected();model.experiments();logs=[];trace_summary={}
    with tempfile.TemporaryDirectory(prefix='stability-awb-') as temp:
        logs.append(simulate(Path(temp),'tb_awb_stability',[ROOT/'tests/tb_awb_stability.v',HDL/'awb.v',HDL/'signal_delay.v']))
        logs.append(simulate(Path(temp),'tb_stability_packer_contract',[ROOT/'tests/tb_stability_packer_contract.v',HDL/'data_96bit_to_128bit.v']))
    sources=[HDL/'isp'/name for name in ('edge_detect_96.v','gaussian_pair_3x3.v','nms_gradient_pair_3x3.v','edge_link_pair_3x3.v')]
    historic_checks(logs,sources)
    with tempfile.TemporaryDirectory(prefix='stability-isolate-') as temp:
        path=Path(temp)
        logs.append(simulate(path,'tb_nms_gradient_pair',[ROOT/'tests/tb_nms_gradient_pair.v',sources[2]],
            ['-Ptb_nms_gradient_pair.HEIGHT=24'],[f'+STIM={isolated_stage_vectors(path/"nms.txt").as_posix()}']))
        logs.append(simulate(path,'tb_edge_link_pair',[ROOT/'tests/tb_edge_link_pair.v',sources[3]],
            plus=[f'+STIM={isolated_stage_vectors(path/"link.txt",True).as_posix()}']))
    cases=[(64,64,d,n,q) for d,n,q in ((0,0,0),(1,0,0),(1,1,0),(1,1,1))]
    cases += [(1280,96,1,1,1)]
    for w,h,d,n,q in cases:
        with tempfile.TemporaryDirectory(prefix='stability-stage-') as temp:
            path=Path(temp);stim,_,beats,_,traces=vectors(path,w,h,d,n,q)
            result=simulate(path,'tb_edge_stability',[ROOT/'tests/tb_edge_stability.v']+sources,
                [f'-Ptb_edge_stability.{k}={v}' for k,v in dict(W=w,H=h,D=d,N=n,Q=q).items()], [f'+STIM={stim.as_posix()}'])
            assert f'beats={beats} ' in result
            logs.append(result);trace_summary[f'{w}x{h}_D{d}N{n}Q{q}']=traces
    if args.full:
        with tempfile.TemporaryDirectory(prefix='stability-isp-') as temp:
            path=Path(temp);stim,pack,beats,words,traces=vectors(path,1280,720,1,1,1,True)
            trace=nms.append_intermediate_traces(stim,1280,720)
            allsrc=[ROOT/'tests/tb_edge_quality_stream.v',HDL/'isp/edge_control_stream.v']+sources+[
                HDL/'edge_status_osd.v',HDL/'osd_char_lib.v',HDL/'data_96bit_to_128bit.v',HDL/'isp/isp_top.v',
                HDL/'isp/data128_96/data128_96.v',ROOT/'tests/isp_boundary_stubs.v']
            result=simulate(path,'tb_edge_quality_stream',allsrc,
                ['-Ptb_edge_quality_stream.WIDTH=1280','-Ptb_edge_quality_stream.HEIGHT=720'],
                [f'+STIM={trace.as_posix()}',f'+PACK={pack.as_posix()}',f'+WORDS={words}'])
            assert f'valid_beats={beats} ' in result;logs.append(result)
            trace_summary['1280x720_integration']=traces
    after=protected();assert before==after
    report=dict(**after,full=args.full,rtl_results=logs,expected_frame_stage_sha256=trace_summary,
                limitation='Synthetic temporal schedules, not recorded camera timing; no physical DDR/HDMI simulation')
    (model.OUT/('rtl_full_summary.json' if args.full else 'rtl_summary.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('PASS diagnostic integrity, formal RTL/constraints/IP and 15 historical bits unchanged',flush=True)

if __name__=='__main__':main()
