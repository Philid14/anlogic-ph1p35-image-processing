"""Real RTL NMS/debug-neighbor checks and actual ISP/DDR packer comparison."""
from pathlib import Path
import argparse,hashlib,json,tempfile
import numpy as np
import edge_nms_model as model
import edge_denoise_model as old_model
import run_edge_denoise_v1 as old

ROOT=Path(__file__).resolve().parents[1];HDL=old.HDL;control=old.control


def packed(values,bits):
    result=0
    for value in values:result=(result<<bits)|(int(value)&((1<<bits)-1))
    return result


def frozen():
    manifest=json.loads((ROOT/'tests/edge_nms_frozen_manifest.json').read_text(encoding='utf-8'))
    for kind in ('frozen_main','read_only_reference','hardware_sources'):
        for name,sha in manifest[kind].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
        print(f'PASS {kind}: {len(manifest[kind])} unchanged hashes',flush=True)
    old.frozen()
    assert '.DENOISE_ENABLE(1), .NMS_ENABLE(1)' in (HDL/'design_top_wrapper.v').read_text(encoding='utf-8')


def unit_vectors(directory):
    rng=np.random.default_rng(523);h,w=16,32
    cases=[]
    for value in (0,500):cases.append((np.full((h,w),value),np.zeros((h,w),dtype=int)))
    for start in (10,11):
        mag=np.zeros((h,w),dtype=int);mag[:,start:start+2]=1200
        tie=model.nms_details(mag,np.zeros_like(mag),0)
        assert int(tie['keep'].sum())==14 # one peak per valid row, both pair parities
        cases.append((mag,np.zeros_like(mag)))
    for axis in range(4):cases.append((rng.integers(0,16384,(h,w)),np.full((h,w),axis)))
    mag=rng.integers(0,16384,(h,w));mag[8,12]=16383
    cases.append((mag,rng.integers(0,4,(h,w))))
    path=directory/'unit.txt';beats=0
    with path.open('w') as f:
        def cycle(v=0,u=0,l=0,t=0,im=0,idir=0,em=0,keep=0,valid=0,center=0,axis=0,neg=0,pos=0):
            f.write(f'{v} {u} {l} {t:04x} {im:07x} {idir:x} {em:07x} {keep:x} {valid} {center:07x} {axis:x} {neg:07x} {pos:07x}\n')
        for frame,(mag,axis) in enumerate(cases):
            detail=model.nms_details(mag,axis,0);early=frame%2==0
            if early:
                cycle(u=1)
                for _ in range(8):cycle()
            for y in range(h):
                for x in range(0,w,2):
                    sel=(slice(x,x+2))
                    cycle(1,int(not early and y==0 and x==0),int(x==w-2),(y*81+x)%16384,
                        packed(mag[y,sel],14),packed(axis[y,sel],2),packed(detail['magnitude'][y,sel],14),
                        packed(detail['keep'][y,sel],1),int(detail['valid'][y,x]),packed(detail['center'][y,sel],14),
                        packed(detail['direction'][y,sel],2),packed(detail['negative'][y,sel],14),packed(detail['positive'][y,sel],14))
                    beats+=1
                    if frame==8 and x%6==0:cycle(t=2000)
                for _ in range(1+y%3):cycle()
        cycle(u=1)
        for _ in range(4):cycle(1,im=0xfffffff,idir=15);beats+=1
        cycle(u=1)
        for y in range(h):
            for x in range(0,w,2):cycle(1,l=int(x==w-2),valid=int(y>=2 and x>=2));beats+=1
            cycle()
    return path,beats


class ImageAdapter:
    def __init__(self,nms):self.nms=nms
    def scenes(self,width,height):
        combined={name:(name,clean,noisy) for name,clean,noisy in old_model.scenes(width,height)}
        combined.update({name:(name,clean,noisy) for name,clean,noisy in model.scenes(width,height)})
        # An internal-grid 45-degree edge complements the ORIGINAL-pixel
        # 45-degree edge (horizontal pair sampling makes the grids anisotropic).
        yy,xx=np.indices((height,width));v=np.where(xx-width//2>=2*(yy-height//2),160,48).astype(np.uint8)
        rgb=np.repeat(v[:,:,None],3,axis=2);combined['sample45']=('sample45',rgb,rgb)
        return list(combined.values())
    def edges(self,rgb,threshold,kind):return model.edges(rgb,threshold,self.nms,kind=='gaussian')


def append_intermediate_traces(stim,width,height):
    """Process complete input frames spatially, no RTL stage/RAM model.

    Extra fields judge Gx/Gy at S3 and mag/axis at S4 separately from output.
    Partial frames are padded for modeling but their incomplete borders are
    invalid. The original stimulus and output data are never changed.
    """
    output=stim.with_suffix('.trace');segment=[]
    def flush(f):
        if not segment:return
        valid=[line for line in segment if line[0]=='1']
        rgbbytes=b''.join(bytes.fromhex(line[4]) for line in valid)
        image=np.zeros(width*height*3,dtype=np.uint8)
        image[:len(rgbbytes)]=np.frombuffer(rgbbytes,dtype=np.uint8)
        gx,gy,mag=model.gradients(image.reshape(height,width,3));axis=model.direction(gx,gy)
        index=0
        for fields in segment:
            gg=mm=dd=window=0
            if fields[0]=='1':
                y,x=divmod(index,width//4);n=2*x;index+=1
                gg=packed((gx[y,n],gy[y,n],gx[y,n+1],gy[y,n+1]),13)
                mm=packed(mag[y,n:n+2],14);dd=packed(axis[y,n:n+2],2)
                window=int(y>=4 and x>=2)
            f.write(' '.join(fields)+f' {gg:013x} {mm:07x} {dd:x} {window}\n')
    with stim.open() as inf,output.open('w') as outf:
        for line in inf:
            fields=line.split()
            if fields[1]=='1':flush(outf);segment=[]
            segment.append(fields)
        flush(outf)
    return output


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--full',action='store_true');args=parser.parse_args()
    frozen()
    with tempfile.TemporaryDirectory(prefix='nms-unit-') as temp:
        d=Path(temp)
        control.simulate(d,'tb_nms_axis',[ROOT/'tests/tb_nms_axis.v',HDL/'isp/edge_detect_96.v'])
        stim,beats=unit_vectors(d)
        result=control.simulate(d,'tb_nms_gradient_pair',[ROOT/'tests/tb_nms_gradient_pair.v',HDL/'isp/nms_gradient_pair_3x3.v'],plus=[f'+STIM={stim.as_posix()}'])
        assert f'beats={beats} ' in result
    cases=[(64,16,0,False),(64,16,1,False),(1280,96,1,False)]
    if args.full:cases.append((1280,720,1,True))
    for width,height,nms,full in cases:
        with tempfile.TemporaryDirectory(prefix='nms-stream-') as temp:
            d=Path(temp);old.model=ImageAdapter(nms)
            stim,pack,words,beats=old.vectors(d,width,height,True,full)
            traced=append_intermediate_traces(stim,width,height)
            sources=[ROOT/'tests/tb_edge_nms_stream.v',HDL/'isp/edge_control_stream.v',HDL/'isp/edge_detect_96.v',
                HDL/'isp/gaussian_pair_3x3.v',HDL/'isp/nms_gradient_pair_3x3.v',HDL/'edge_status_osd.v',HDL/'osd_char_lib.v',
                HDL/'data_96bit_to_128bit.v',HDL/'isp/isp_top.v',HDL/'isp/data128_96/data128_96.v',ROOT/'tests/isp_boundary_stubs.v']
            result=control.simulate(d,'tb_edge_nms_stream',sources,
                [f'-Ptb_edge_nms_stream.WIDTH={width}',f'-Ptb_edge_nms_stream.HEIGHT={height}',f'-Ptb_edge_nms_stream.NMS={nms}'],
                [f'+STIM={traced.as_posix()}',f'+PACK={pack.as_posix()}',f'+WORDS={words}'])
            assert f'valid_beats={beats} ' in result
            print(f'PASS NMS={nms} {width}x{height} Gx/Gy/magnitude/axis and output/OSD/packing beats={beats} words={words}',flush=True)
    frozen();print('PASS EDGE_NMS_V1 RTL; real-scene thinning and long-run behavior pending',flush=True)


if __name__=='__main__':main()
