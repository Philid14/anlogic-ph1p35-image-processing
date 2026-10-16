"""Independent spatial NMS and SOFTWARE-ONLY hysteresis research.

Gy is top minus bottom in the existing RTL: positive Gy points UP on screen.
No real camera frame is available; every generated image is synthetic.
"""
from pathlib import Path
from collections import deque
import csv, json
import numpy as np
import edge_denoise_model as denoise

ROOT=Path(__file__).resolve().parents[1]


def gradients(rgb, filtered=True):
    a=denoise.prefilter(denoise.pairs(rgb),'gaussian' if filtered else 'sobel')
    h,w=a.shape;gx=np.zeros_like(a);gy=np.zeros_like(a)
    kx=((-1,0,1),(-2,0,2),(-1,0,1));ky=((1,2,1),(0,0,0),(-1,-2,-1))
    for y in range(3):
        for x in range(3):
            tile=a[y:y+h-2,x:x+w-2]
            gx[2:,2:]+=kx[y][x]*tile;gy[2:,2:]+=ky[y][x]*tile
    border=4 if filtered else 2
    gx[:border]=0;gx[:,:border]=0;gy[:border]=0;gy[:,:border]=0
    return gx,gy,np.abs(gx)+np.abs(gy)


def direction(gx,gy):
    """0=E/W, 1=NE/SW, 2=N/S, 3=NW/SE; 1/2 slope boundary."""
    ax=np.abs(gx);ay=np.abs(gy)
    return np.where(2*ay<=ax,0,np.where(2*ax<=ay,2,np.where((gx<0)==(gy<0),1,3))).astype(np.uint8)


def nms_details(mag,axis,border=4):
    """Output index(r,n) judges gradient center(r-1,n-1), not arrival point.

    One side strict, other inclusive; axis is polarity-independent. Neighbors
    are selected from spatial NumPy slices, unrelated to a streaming schedule.
    """
    h,w=mag.shape;center=np.zeros_like(mag);d=np.zeros((h,w),dtype=np.uint8)
    neg=np.zeros_like(mag);pos=np.zeros_like(mag)
    center[2:,2:]=mag[1:-1,1:-1];d[2:,2:]=axis[1:-1,1:-1]
    # strict/inclusive sides: W/E, SW/NE, N/S, NW/SE.
    offsets=(((1,0),(1,2)),((2,0),(0,2)),((0,1),(2,1)),((0,0),(2,2)))
    for code,(minus,plus) in enumerate(offsets):
        sel=d[2:,2:]==code
        for output,(y,x) in ((neg,minus),(pos,plus)):
            patch=mag[y:y+h-2,x:x+w-2]
            output[2:,2:][sel]=patch[sel]
    valid=np.zeros((h,w),dtype=bool);valid[border+2:,border+2:]=True
    keep=valid & (center>neg) & (center>=pos)
    return dict(center=center,direction=d,negative=neg,positive=pos,valid=valid,keep=keep,
                magnitude=np.where(keep,center,0))


def edges(rgb,threshold,nms=True,filtered=True):
    gx,gy,mag=gradients(rgb,filtered)
    if nms:
        detail=nms_details(mag,direction(gx,gy),4 if filtered else 2)
        result=detail['keep'] & (detail['magnitude']>=threshold)
    else:
        result=mag>=threshold;border=4 if filtered else 2
        result[:border]=False;result[:,:border]=False
    return np.repeat(result.astype(np.uint8)*255,2,axis=1)


def hysteresis(mag,high,ratio=.5,local=False):
    strong=mag>=high;weak=mag>=int(high*ratio)
    if local:return strong | (weak & denoise.dilate(strong,1))
    found=strong.copy();queue=deque(map(tuple,np.argwhere(strong)))
    h,w=mag.shape
    while queue:
        y,x=queue.popleft()
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                yy,xx=y+dy,x+dx
                if 0<=yy<h and 0<=xx<w and weak[yy,xx] and not found[yy,xx]:
                    found[yy,xx]=True;queue.append((yy,xx))
    return found


def scenes(width=256,height=128):
    rng=np.random.default_rng(20261016);y,x=np.indices((height,width))
    low=48;high=112
    vertical=np.where(x>=width//2,high,low)
    horizontal=np.where(y>=height//2,high,low)
    diagonal=np.where(x-width//2>=y-height//2,high,low)
    slope=np.where((x-width//2)*2+(y-height//2)*3>=0,high,low)
    blurred=np.rint(low+(high-low)*np.clip((x-width//2+6)/12,0,1))
    double=np.where((x>=width//2-7)&(x<width//2+7),high,low)
    thin=np.where((x==width//2)|(x==width//2+16),high,low)
    curve=np.where(((x-width*.5)/(.27*width))**2+((y-height*.5)/(.3*height))**2<1,high,low)
    from PIL import Image,ImageDraw,ImageFont
    text=Image.new('L',(width,height),low)
    ImageDraw.Draw(text).text((width//8,height//3),'ANLOGIC 128',fill=high,font=ImageFont.load_default(size=max(12,height//5)))
    weave=low+(((x+y)//5%2)^((x-y)//7%2))*32
    mixed=np.where(x<width//2,48+((x+y)//7%2)*12,64)
    noise=np.rint(rng.normal(0,4,(height,width))).astype(int)
    fixed=rng.integers(-5,6,(1,width))+rng.integers(-2,3,(height,1))
    point=np.full((height,width),48);point[height//2,width//2]=255
    dots=np.full((height,width),48);dots[rng.random((height,width))<.01]=180
    uniform=np.full((height,width),48)
    values=[('black',np.zeros_like(x),np.zeros_like(x)),('white',np.full_like(x,255),np.full_like(x,255)),
        ('uniform',uniform,uniform),('point',uniform,point),('random_points',uniform,dots),
        ('vertical',vertical,vertical),('horizontal',horizontal,horizontal),('diagonal45',diagonal,diagonal),
        ('slope',slope,slope),('blurred',blurred,blurred),('double',double,double),('thin',thin,thin),
        ('curve',curve,curve),('text',np.asarray(text),np.asarray(text)),('weave',weave,weave),
        ('random_noise',uniform,uniform+noise),('fixed_noise',uniform,uniform+fixed),
        ('low_contrast',np.where(x>=width//2,60,48),np.where(x>=width//2,60,48)+noise),
        ('texture_weak',mixed,mixed+noise)]
    return [(name,np.repeat(np.clip(clean,0,255)[:,:,None],3,axis=2).astype(np.uint8),
             np.repeat(np.clip(image,0,255)[:,:,None],3,axis=2).astype(np.uint8)) for name,clean,image in values]


def research():
    out=ROOT/'docs/edge_nms_evidence';out.mkdir(exist_ok=True)
    # Reproduce the already RTL-verified denoise model before researching NMS.
    for _,_,rgb in scenes():
        _,_,mag=gradients(rgb)
        assert np.array_equal(mag,denoise.magnitude(rgb,'gaussian'))
        for threshold in (10,20,40,60,80,120,250):
            assert np.array_equal(edges(rgb,threshold,False),denoise.edges(rgb,threshold,'gaussian'))
    print('PASS baseline: 19 gradient fields and 133 Gaussian/Sobel binary images match prior verified integer model',flush=True)
    # Equal adjacent peaks, polarity axes and long connected weak chain.
    for code in range(4):
        m=np.zeros((16,16),dtype=int);m[4:12,4:12]=300
        a=np.full_like(m,code);detail=nms_details(m,a,0)
        assert not detail['keep'][7,7] # flat interior cannot all survive
    m=np.zeros((12,40),dtype=int);m[4,3]=100;m[4,4:30]=50;m[8,3:30]=50
    full=hysteresis(m,80);local=hysteresis(m,80,local=True)
    chain={'full_connected':int(full.sum()),'one_hop':int(local.sum()),'unanchored_component_kept':int(full[8].sum())}
    assert chain==dict(full_connected=27,one_hop=2,unanchored_component_kept=0)
    (out/'weak_chain.json').write_text(json.dumps(chain,indent=2)+'\n')
    rows=[];images={}
    for name,clean,rgb in scenes():
        cgx,cgy,cm=gradients(clean);cd=nms_details(cm,direction(cgx,cgy))
        truth=np.roll(cd['magnitude']>=10,(-3,-3),(0,1))
        gx,gy,mag=gradients(rgb);detail=nms_details(mag,direction(gx,gy));nm=detail['magnitude']
        roi=np.zeros(mag.shape,dtype=bool);roi[8:-8,8:-8]=True
        flat=roi & ~denoise.dilate(truth,4);gt=truth&roi;band=roi&denoise.dilate(truth,3)
        for th in (20,40,60,80,120,160):
            base=np.roll(mag>=th,(-2,-2),(0,1))
            nms=np.roll(detail['keep']&(nm>=th),(-3,-3),(0,1))
            hf=np.roll(hysteresis(nm,th),(-3,-3),(0,1))
            hl=np.roll(hysteresis(nm,th,local=True),(-3,-3),(0,1))
            for algorithm,pred in [('sobel',base),('nms',nms),('full_hysteresis',hf),('one_hop',hl)]:
                recall=float(denoise.dilate(pred,1)[gt].mean()) if gt.any() else None
                thickness=float(pred[band].sum()/gt.sum()) if gt.any() else None
                # Thickness proxy: response area / clean NMS reference length.
                rowcoverage=None;maxgap=None;runs=None
                if name in ('vertical','blurred','low_contrast','double'):
                    center=pred.shape[1]//2
                    strip=pred[8:-8,center-9:center+10]
                    present=strip.any(axis=1);rowcoverage=float(present.mean());gap=maxgap=0
                    for ok in present:gap=0 if ok else gap+1;maxgap=max(maxgap,gap)
                    runs=float((strip[:,0].astype(int)+(strip[:,1:]&~strip[:,:-1]).sum(axis=1)).mean())
                rows.append(dict(scene=name,algorithm=algorithm,threshold=th,white_fraction=float(pred[roi].mean()),
                    flat_false_rate=float(pred[flat].mean()) if flat.any() else None,
                    contour_recall_tol1=recall,thickness_area_per_reference_point=thickness,
                    step_row_coverage=rowcoverage,longest_gap_rows=maxgap,mean_separated_runs=runs))
            if name in ('blurred','double','weave','low_contrast') and th==40:images[name]=(rgb,base,nms,hf,hl)
    with (out/'synthetic_metrics.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(len(images),5,figsize=(15,10),layout='constrained')
    for row,(name,values) in enumerate(images.items()):
        for col,value in enumerate(values):
            axes[row,col].imshow(value,cmap='gray',vmin=0,vmax=1 if col else 255,aspect='auto')
            axes[row,col].set_title(name+' / '+('input','Sobel','NMS','full hysteresis','one-hop')[col]);axes[row,col].axis('off')
    fig.suptitle('SYNTHETIC, TH40 / LOW20, offset compensated; no real camera-input claim')
    fig.savefig(out/'comparison.png',dpi=125);plt.close(fig)
    print('PASS 456 comparison rows, four methods, six thresholds; software hysteresis only',flush=True)
    for name in ('vertical','blurred','double','weave','low_contrast'):
        print(json.dumps([r for r in rows if r['scene']==name and r['threshold']==40]),flush=True)


if __name__=='__main__':research()
