"""Independent spatial EDGE_QUALITY research. All inputs are synthetic RGB.

No RTL/RAM/clock schedule is modeled. Bounded propagation is NOT full Canny.
"""
from pathlib import Path
from collections import deque
import csv,json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import edge_nms_model as nms
import edge_denoise_model as denoise

ROOT=Path(__file__).resolve().parents[1]
HOPS=4
SEED_SUPPORT=0


def neighbors(a):
    """Eight zero-padded neighbor planes, no wraparound."""
    h,w=a.shape;p=np.pad(a,1)
    return [p[1+dy:1+dy+h,1+dx:1+dx+w] for dy in (-1,0,1) for dx in (-1,0,1) if dx or dy]


def propagate(mag,high,hops=HOPS,support=SEED_SUPPORT,axis=None):
    weak=mag>=high//2;strong=mag>=high
    if support:strong &= np.stack(neighbors(weak)).sum(axis=0)>=support
    found=strong.copy()
    for _ in range(hops):
        near=neighbors(found)
        if axis is not None:
            # Axis modulo pi; permit at most one 45-degree bin difference.
            near=[v & (np.minimum(abs(axis.astype(int)-d.astype(int)),4-abs(axis.astype(int)-d.astype(int)))<=1)
                  for v,d in zip(near,neighbors(axis))]
        found=weak & (found | np.logical_or.reduce(near))
    return found


def full_connected(mag,high):
    return nms.hysteresis(mag,high)


def window_labels(weak,active,seed=False,border=6):
    """Causal output label(r,n) judges spatial input(r-1,n-1).

    Also used to generate complete expected per-stage images for RTL; output
    borders are conservative and match full-window validity, not a RAM model.
    """
    h,w=weak.shape;ow=np.zeros_like(weak);oa=np.zeros_like(active)
    cweak=weak[1:-1,1:-1];cactive=active[1:-1,1:-1]
    source=weak if seed else active
    tiles=[source[y:y+h-2,x:x+w-2] for y in range(3) for x in range(3) if (y,x)!=(1,1)]
    around=np.logical_or.reduce(tiles)
    ow[2:,2:]=cweak
    oa[2:,2:]=(cactive & around) if seed else (cweak & (cactive|around))
    ow[:border+2]=False;ow[:,:border+2]=False
    oa[:border+2]=False;oa[:,:border+2]=False
    return ow,oa


def label_stages(mag,high,hops=HOPS,support=SEED_SUPPORT,border=6):
    weak=mag>=high//2;active=mag>=high
    # Input NMS zero magnitude must not become a weak candidate at TH0/1.
    weak &= mag>0;active &= mag>0
    stages=[]
    if support:
        weak,active=window_labels(weak,active,True,border);border+=2;stages.append((weak,active))
    for _ in range(hops):
        weak,active=window_labels(weak,active,False,border);border+=2;stages.append((weak,active))
    return stages


def edges(rgb,threshold,enabled=True):
    if not enabled:return nms.edges(rgb,threshold)
    gx,gy,mag=nms.gradients(rgb)
    nm=nms.nms_details(mag,nms.direction(gx,gy))['magnitude']
    active=label_stages(nm,threshold)[-1][1]
    return np.repeat(active.astype(np.uint8)*255,2,axis=1)


def scenes(width=320,height=160):
    base=nms.scenes(width,height)
    rng=np.random.default_rng(20261017);x,y=np.meshgrid(np.arange(width),np.arange(height))
    for name in ('glasses','face','paper','text_small','thin_curve'):
        canvas=Image.new('L',(width,height),48);d=ImageDraw.Draw(canvas)
        if name=='glasses':
            for box in ((width*.13,height*.28,width*.45,height*.68),(width*.52,height*.28,width*.84,height*.68)):
                d.rounded_rectangle(tuple(map(int,box)),radius=height//9,outline=100,width=3)
            d.arc((int(width*.42),int(height*.35),int(width*.55),int(height*.55)),180,360,fill=100,width=3)
            d.line((int(width*.04),int(height*.3),int(width*.15),int(height*.38)),fill=100,width=2)
        elif name=='face':
            d.ellipse((width//4,height//10,width*3//4,height*9//10),outline=96,width=3)
            d.arc((width*3//10,height//4,width*7//10,height*3//4),20,160,fill=78,width=2)
        elif name=='paper':
            d.polygon([(width//5,height//5),(width*4//5,height//3),(width*3//4,height*4//5),(width//6,height*2//3)],fill=78)
            d.line((width//3,height//2,width*2//3,height*3//5),fill=48,width=2)
        elif name=='text_small':
            font=ImageFont.load_default(size=max(12,height//7))
            d.text((width//8,height//4),'FPGA 1280x720',fill=96,font=font)
            d.text((width//8,height//2),'Edge quality .,:!',fill=78,font=font)
        else:
            pts=[(i,int(height*.5+height*.2*np.sin(i/float(max(1,width//12))))) for i in range(width//8,width*7//8)]
            d.line(pts,fill=92,width=2)
        clean=np.asarray(canvas).astype(float)
        # Contrast changes along the contour; no painted-in binary gap.
        modulation=.45+.55*(.5+.5*np.sin(y/5+x/30))
        clean=48+(clean-48)*modulation
        for sigma in (4,8):
            noisy=clean+rng.normal(0,sigma,clean.shape)+rng.normal(0,1.5,(height,1))
            cv=lambda a:np.repeat(np.clip(np.rint(a),0,255).astype(np.uint8)[:,:,None],3,axis=2)
            base.append((name+f'_n{sigma}',cv(clean),cv(noisy)))
    return base


def research():
    out=ROOT/'docs/edge_quality_evidence';out.mkdir(exist_ok=True)
    rows=[];pictures={};aggregates={}
    for name,clean,rgb in scenes():
        gx,gy,mag=nms.gradients(rgb);axis=nms.direction(gx,gy)
        nm=np.roll(nms.nms_details(mag,axis)['magnitude'],(-3,-3),(0,1))
        cgx,cgy,cm=nms.gradients(clean)
        truth=np.roll(nms.nms_details(cm,nms.direction(cgx,cgy))['magnitude']>=10,(-3,-3),(0,1))
        roi=np.zeros(nm.shape,bool);roi[18:-18,18:-18]=True
        gt=truth&roi;flat=roi&~denoise.dilate(truth,4)
        # More accurate angle boundaries as a separate alternative.
        ax=np.abs(gx);ay=np.abs(gy)
        accurate=np.where(10000*ay<=4142*ax,0,np.where(10000*ax<=4142*ay,2,np.where((gx<0)==(gy<0),1,3)))
        am=np.roll(nms.nms_details(mag,accurate)['magnitude'],(-3,-3),(0,1))
        for th in (20,30,40,50,60,70,80,100):
            staged=label_stages(nms.nms_details(mag,axis)['magnitude'],th)[-1][1]
            compensated=np.roll(staged,(-3-HOPS,-3-HOPS),(0,1))
            assert np.array_equal(compensated[roi],propagate(nm,th,HOPS,0)[roi])
            candidates={'nms':nm>=th,'lower_single':nm>=th//2,'angle_4142':am>=th,
                        'full':full_connected(nm,th)}
            for k in (1,2,4,8):candidates[f'hop{k}']=propagate(nm,th,k,0)
            for s in (1,2):
                for k in (2,4):candidates[f'support{s}_hop{k}']=propagate(nm,th,k,s)
            candidates['oriented4']=propagate(nm,th,4,1,np.roll(axis,(-2,-2),(0,1)))
            for alg,pred in candidates.items():
                recall=float(denoise.dilate(pred,1)[gt].mean()) if gt.any() else None
                false=float(pred[flat].mean()) if flat.any() else None
                precision=float(denoise.dilate(truth,1)[pred&roi].mean()) if (pred&roi).any() else None
                band=pred[18:-18,pred.shape[1]//2-4:pred.shape[1]//2+5]
                coverage=float(band.any(axis=1).mean()) if name=='low_contrast' else None
                rows.append(dict(scene=name,algorithm=alg,threshold=th,recall_tol1=recall,
                                 precision_tol1=precision,flat_false_rate=false,white_fraction=float(pred[roi].mean()),step_coverage=coverage))
            if name in ('glasses_n8','paper_n8','text_small_n8','low_contrast') and th==60:
                pictures[name]=[rgb,candidates['nms'],nm>=40,candidates['hop2'],candidates['hop4'],candidates['full']]
    with (out/'metrics.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    noisy=[r for r in rows if '_n' in r['scene'] or r['scene'] in ('random_noise','fixed_noise','low_contrast')]
    for alg in sorted({r['algorithm'] for r in rows}):
        aggregates[alg]={}
        for th in (20,30,40,50,60,70,80,100):
            selected=[r for r in noisy if r['algorithm']==alg and r['threshold']==th]
            aggregates[alg][th]={k:float(np.mean([r[k] for r in selected if r[k] is not None])) for k in ('recall_tol1','precision_tol1','flat_false_rate','white_fraction')}
    # Prove finite-hop limit and seed-support behavior without an image model.
    chain=np.zeros((20,50),int);chain[5,5]=100;chain[5,6:36]=50;chain[12,5:36]=50;chain[15,40]=100
    counts={f'hop{k}':int(propagate(chain,80,k,1).sum()) for k in (1,2,4,8)}
    counts['full']=int(full_connected(chain,80).sum())
    assert counts=={'hop1':2,'hop2':3,'hop4':5,'hop8':9,'full':32},counts
    # A two-point true feature is preserved by support1 and rejected by support2.
    tiny=np.zeros((12,16),int);tiny[5,5:7]=100
    assert propagate(tiny,80,4,1).sum()==2 and propagate(tiny,80,4,2).sum()==0
    raw_counts={f'hop{k}':int(propagate(chain,80,k,0).sum()) for k in (1,2,4,8)}
    assert raw_counts=={'hop1':3,'hop2':4,'hop4':6,'hop8':10},raw_counts
    # Pair averaging is non-injective: a spatial detail and its phase inverse
    # can have identical paired gray. No downstream algorithm can restore it.
    detail=np.full((64,128,3),64,dtype=np.uint8);detail[20:44,32:96:2]=32;detail[20:44,33:96:2]=96
    flat=np.full_like(detail,64)
    assert np.array_equal(denoise.pairs(detail),denoise.pairs(flat))
    # A separately evaluated full-resolution front-end keeps all gray pixels.
    fullgx,fullgy,fullmag=nms.gradients(np.repeat(detail,2,axis=1))
    fullnm=nms.nms_details(fullmag,nms.direction(fullgx,fullgy))['magnitude']
    halfgx,halfgy,halfmag=nms.gradients(detail)
    halfnm=nms.nms_details(halfmag,nms.direction(halfgx,halfgy))['magnitude']
    sampling=dict(half_response=int((halfnm>=20).sum()),full_response=int((fullnm>=20).sum()))
    assert sampling['half_response']==0 and sampling['full_response']>0,sampling
    result=dict(input_kind='SYNTHETIC ONLY; no camera RGB',scenes=len(scenes()),rows=len(rows),aggregate=aggregates,
                chain_with_support1=counts,chain_selected_raw=raw_counts,sampling_nullspace=sampling)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(len(pictures),6,figsize=(17,9),layout='constrained')
    for row,(name,values) in enumerate(pictures.items()):
        for col,value in enumerate(values):
            # Match the actual HDMI geometry: each internal sample becomes
            # two original-width pixels. Metrics remain on the internal grid.
            shown=value if col==0 else np.repeat(value,2,axis=1)
            axes[row,col].imshow(shown,cmap='gray',vmin=0,vmax=255 if col==0 else 1)
            axes[row,col].set_title(name+' / '+('RGB','NMS60','NMS40','2hop60','4hop60','full60')[col],fontsize=8);axes[row,col].axis('off')
    fig.suptitle('SYNTHETIC ONLY, common ROI and spatial offset compensated; full = software-only connectivity')
    fig.savefig(out/'comparison.png',dpi=125);plt.close(fig)
    print('PASS research',len(rows),'rows;',len(scenes()),'synthetic scenes; chain',counts,flush=True)
    for alg in ('nms','lower_single','angle_4142','hop2','hop4','hop8','support1_hop2','support1_hop4','support2_hop4','oriented4','full'):
        print(alg,json.dumps(aggregates[alg]),flush=True)


if __name__=='__main__':research()
