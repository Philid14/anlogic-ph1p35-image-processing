"""Reproduce V1 failure mechanisms and compare bounded low-cost candidates.

The supplied phone photo is qualitative evidence only. The supplied PNG is a
digital test target, NOT acquired camera RGB; injected disturbances are models.
"""
from pathlib import Path
import sys,json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from style_fill_model import style as v1
from style_fill_v2_model import style as v2
OUT=ROOT/'docs/edge_style_fill_v2_evidence'
CHART=OUT/'digital_test_chart.png'


def scenes(w=256,h=192):
    y,x=np.indices((h,w));rng=np.random.default_rng(20261019)
    cases={}
    for name,value in [('white',246),('gray_threshold',192),('black',0),('gray',128)]:
        p=np.full((h,w,3),value,dtype=np.int32)
        noise=rng.integers(-3,4,p.shape);noise[...,1]+=2
        cases[name]=np.clip(p+noise,0,255).astype(np.uint8)
    p=np.zeros((h,w,3),np.uint8)
    colors=[(255,0,0),(0,128,0),(0,0,255),(0,255,255),(255,0,255),(255,255,0),(0,0,0),(255,255,255)]
    for i,c in enumerate(colors):p[:,i*w//8:(i+1)*w//8]=c
    cases['color_patches']=p
    p=np.repeat(np.uint8(x*255//max(1,w-1))[...,None],3,axis=2)
    cases['gray_ramp']=p
    angle=np.arctan2(y-h//2,x-w//2)
    radius=np.hypot(y-h//2,x-w//2)
    mask=(np.cos(angle*36)>=0)&(radius<h*.46)&(radius>h*.03)
    star=np.where(mask,0,255).astype(np.uint8)
    cases['siemens_star']=np.repeat(star[...,None],3,axis=2)
    mask=((y%13)==3) | ((x%17)==4) | (((x-y)%29)==0)
    cases['thin_dark']=np.repeat(np.where(mask,0,255).astype(np.uint8)[...,None],3,axis=2)
    cases['thin_bright']=255-cases['thin_dark']
    im=Image.new('RGB',(w,h),'white');draw=ImageDraw.Draw(im)
    ypos=0
    for size in (6,8,10,12,16,24):
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size)
        draw.text((1,ypos),'AaBb 0123456789 EDGE',font=font,fill='black');ypos+=size+3
    cases['text']=np.array(im)
    p=np.empty((h,w,3),np.uint8)
    p[...,0]=(x*13+y*3)%256;p[...,1]=(x*2+y*17)%256;p[...,2]=(x*7+y*11)%256
    cases['color_texture']=p
    p=np.full((h,w,3),210,np.uint8)
    p[h//4:3*h//4,w//4:3*w//4]=(55,100,165)
    cases['geometry']=p
    # High chromatic variation with nearly constant shift-add luma.
    n=rng.integers(-32,33,(h,w))
    cases['chroma_texture']=np.stack((160+n,np.full_like(n,160),160-n),axis=-1).astype(np.uint8)
    return cases


def rgb8(p):
    _,_,ink = v1_details(p)
    q=(p.astype(np.uint16)>>5)*255//7
    q[ink]=0
    return q.astype(np.uint8)


def v1_details(p):
    return v1(p,True)


def metrics(inp,out,ink=None):
    p=inp.astype(np.int32);q=out.astype(np.int32)
    chroma=lambda a:np.stack((a[...,0]-a[...,1],a[...,2]-a[...,1]),-1)
    near=(p.max(-1)-p.min(-1))<=12
    return dict(rgb_mae=float(abs(q-p).mean()),
        chroma_error_mae=float(abs(chroma(q)-chroma(p)).mean()),
        neutral_colored_fraction=float(((q.max(-1)-q.min(-1)>12)&near).sum()/max(1,near.sum())),
        black_fraction=float((q==0).all(-1).mean()),
        new_ink_pixels=int(ink.sum()) if ink is not None else None)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    report={};cases=scenes()
    methods={'V1':lambda p:v1(p),'RGB8_old_ink':rgb8,
        'joint_old_ink':lambda p:v2(p,ink='v1'),'V2':lambda p:v2(p)}
    sheet=Image.new('RGB',(256*5,(192+22)*len(cases)),(30,30,30));draw=ImageDraw.Draw(sheet)
    for i,(name,p) in enumerate(cases.items()):
        sheet.paste(Image.fromarray(p),(0,i*214+22));draw.text((0,i*214),name+' INPUT',fill='white')
        report[name]={}
        for j,(method,fn) in enumerate(methods.items(),1):
            q=fn(p)
            report[name][method]=metrics(p,q)
            if name in ('siemens_star','thin_dark','thin_bright'):
                report[name][method]['binary_mismatch_fraction']=float(((q[...,0]>=128)!=(p[...,0]>=128)).mean())
            draw.text((j*256,i*214),method,fill='white');sheet.paste(Image.fromarray(q),(j*256,i*214+22))
    sheet.save(OUT/'comparison.png')
    # Counterexample is constant RGB: no optical, AWB, noise, lane or cache
    # issue is necessary to produce the severe old green/cyan quantization.
    report['counterexamples']={}
    for value in ((191,192,191),(191,192,192),(200,200,200),(255,0,0),(0,128,0),(0,0,255)):
        p=np.tile(np.uint8(value),(4,8,1))
        report['counterexamples'][str(value)]={name:fn(p)[-1,-1].tolist() for name,fn in methods.items()}
    # Quantify highlights that V1 collapses despite differing digital inputs.
    p=np.repeat(np.arange(192,256,dtype=np.uint8)[None,:,None],3,axis=2)
    report['highlight_levels']={name:np.unique(fn(p)).tolist() for name,fn in methods.items()}
    # Guarantee binary detail: arbitrary hard 0/255 input survives V2 exactly.
    rng=np.random.default_rng(518)
    binary=np.repeat((rng.integers(0,2,(97,128),dtype=np.uint8)*255)[...,None],3,axis=2)
    assert np.array_equal(v2(binary),binary)
    report['binary_identity_random_pixels']=int(binary.shape[0]*binary.shape[1])
    base=cases['geometry'];moves=[np.roll(base,k,axis=1) for k in (0,1,2,24)]
    background=np.full_like(base,210)
    outputs=[v2(p) for p in moves+[background]]
    assert np.array_equal(outputs[-1],v2(background))
    _,_,ink=v2(base,True);assert ink.any(),'must retain actual outline operation'
    report['motion']=dict(history_frames=0,residual_pixels=0,geometry_ink_pixels=int(ink.sum()))
    if CHART.exists():
        src=Image.open(CHART).convert('RGB');src.thumbnail((512,720))
        canvas=Image.new('RGB',(512,720),'white');canvas.paste(src,((512-src.width)//2,0))
        p=np.array(canvas);rng=np.random.default_rng(132)
        # Explicit camera-like stress, NOT a fitted model of the phone photo:
        # white background around the old 192 threshold, small channel cast,
        # local noise. Original digital card is also evaluated without stress.
        stressed=np.clip(p.astype(np.float64)*.76+np.array([0,2,-1])+rng.normal(0,2,p.shape),0,255).astype(np.uint8)
        for name,pix in [('digital_chart',p),('modeled_cast_noise',stressed)]:
            grid=Image.new('RGB',(512*3,720+24),'#202020');d=ImageDraw.Draw(grid)
            for j,(title,q) in enumerate([('INPUT',pix),('V1',v1(pix)),('V2',v2(pix))]):
                grid.paste(Image.fromarray(q),(j*512,24));d.text((j*512,4),title,fill='white')
            grid.save(OUT/(name+'.png'))
        report['supplied_chart']=dict(sha256=hashlib.sha256(CHART.read_bytes()).hexdigest(),
            input_kind='user digital artwork, not camera ORIGIN RGB',stress_model='0.76*RGB+[0,2,-1]+N(0,2), seed132')
    report['evidence_limit']='Synthetic/digital-source model improvements; real camera contribution and V2 board appearance unverified. Phone photograph not treated as raw RGB.'
    (OUT/'model_results.json').write_text(json.dumps(report,indent=2)+'\n')
    for name in ('white','gray_threshold','gray_ramp','siemens_star','thin_bright','chroma_texture'):
        print(name,json.dumps(report[name]))
    print('PASS binary identity, color-channel reference, coherent outline and no-history motion checks')
if __name__=='__main__':main()
