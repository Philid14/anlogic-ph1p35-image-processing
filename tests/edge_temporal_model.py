"""Existing QUALITY vs bounded one-frame support and three-frame voting.

SYNTHETIC labels are only evaluation truth, not camera truth. History always
stores raw current QUALITY, never recursively held output. No sensor changes.
"""
from pathlib import Path
import argparse,csv,json,hashlib
import numpy as np
import edge_nms_model as nms
import edge_quality_model as quality
import edge_denoise_model as den


def spatial(rgb, th):
    gx,gy,mag=nms.gradients(rgb,True)
    detail=nms.nms_details(mag,nms.direction(gx,gy),4)
    labels=quality.label_stages(detail['magnitude'],th)
    shift=lambda a,k:np.roll(a,(-k,-k),(0,1))
    return (shift(labels[-1][1],7),shift(labels[-1][0],7),shift(mag,2)>=th//2)


def candidates(seq,th):
    s=[spatial(f,th) for f in seq]
    raw=np.array([x[0] for x in s]);weak=np.array([x[1] for x in s]);support=np.array([x[2] for x in s])
    result=dict(quality=raw.copy(),weak_hold=raw.copy(),gradient_hold=raw.copy(),vote3=raw.copy())
    for f in range(1,len(raw)):
        result['weak_hold'][f]|=raw[f-1]&weak[f]
        result['gradient_hold'][f]|=raw[f-1]&support[f]
    for f in range(2,len(raw)):
        result['vote3'][f]=(raw[f].astype(int)+raw[f-1]+raw[f-2])>=2
    return result


def metrics(a,roi,truth=None):
    # Exclude first two frames in ALL comparisons (vote3 warm-up).
    a=a[2:];p,c=a[:-1],a[1:];u=(p|c)&roi;f=(p^c)&roi
    result=dict(flip_roi=float(f[:,roi].mean()),flip_union=float(f.sum()/u.sum()) if u.any() else None,
                mean_edges=float(a[:,roi].sum(1).mean()),edge_counts_by_frame=a[:,roi].sum(1).tolist())
    if truth is not None:
        gt=truth[2:];near=np.array([den.dilate(g,1) for g in gt]);det=np.array([den.dilate(v,1) for v in a])
        result['recall_1sample']=float((det&gt)[:,roi].sum()/gt[:,roi].sum()) if gt[:,roi].any() else None
        result['outside_truth_band_fraction']=float((a&~near)[:,roi].sum()/max(1,a[:,roi].sum()))
        result['tail_edge_samples']=a[-2:,roi].sum(1).tolist()
        # Synthetic truth correspondence only: row centers inside the truth
        # tolerance band. Never apply this as tracking to an unlabeled camera ROI.
        px=np.arange(a.shape[2])[None,None,:]*2
        chosen=a&near&roi;target=gt&roi
        dc=chosen.sum(2);gc=target.sum(2);ok=(dc>0)&(gc>0)
        residual=np.where(ok,(chosen*px).sum(2)/np.maximum(dc,1)-(target*px).sum(2)/np.maximum(gc,1),np.nan)
        valid_rows=np.all(ok,axis=0)
        result['truth_matched_row_center_temporal_std_px']=float(np.std(residual[:,valid_rows],axis=0).mean()) if valid_rows.any() else None
    return result


def study(output,real_paths):
    output.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(20261018)
    rows=[];sequences={};h,w=64,192;y,x=np.indices((h,w));roi=np.zeros((h,w//2),bool);roi[9:-9,9:-9]=1
    # Threshold-adjacent weak edges, strong edges, diagonal and motion; exact
    # noiseless QUALITY output is a reproducible synthetic spatial reference.
    for name,contrast,motion in [('weak_static',32,0),('strong_static',96,0),('diagonal_static',32,0),('moving_2px',48,2),('moving_8px',48,8),('appear_disappear',48,0)]:
        seq=[];truth=[]
        for f in range(12):
            boundary=72+motion*f
            step=(x>=boundary) if name!='diagonal_static' else (x>=72+(y-32)//2)
            gray=48+contrast*step
            if name=='appear_disappear' and (f<3 or f>=9):gray=np.full((h,w),48)
            clean=np.repeat(gray.astype(np.uint8)[:,:,None],3,2)
            noisy=np.clip(clean.astype(int)+rng.integers(-4,5,clean.shape),0,255).astype(np.uint8)
            seq.append(noisy);truth.append(spatial(clean,60)[0])
        seq=np.array(seq);truth=np.array(truth);sequences[name]=(seq,truth)
        for th in (40,60,80):
            # Truth uses the same threshold and existing noiseless spatial chain.
            clean_truth=[]
            for f in range(12):
                boundary=72+motion*f;step=(x>=boundary) if name!='diagonal_static' else (x>=72+(y-32)//2)
                gray=48+contrast*step
                if name=='appear_disappear' and (f<3 or f>=9):gray=np.full((h,w),48)
                clean_truth.append(spatial(np.repeat(gray.astype(np.uint8)[:,:,None],3,2),th)[0])
            for alg,a in candidates(seq,th).items():rows.append(dict(scene=name,input_kind='synthetic',threshold=th,algorithm=alg,**metrics(a,roi,np.array(clean_truth))))
    for path in real_paths:
        known={'0fc080aa2550f9bb77a058bd15ea22d0fa2b8cb18482487518e77aa1601c526c',
               'd50c47e6a099f234a18bfbde418b82991856ba8f708215251c46fcfd866d419a'}
        assert hashlib.sha256(path.read_bytes()).hexdigest() in known,'real data must match prior full CRC-validated capture'
        with np.load(path) as d:seq=d['post']
        r=np.zeros((seq.shape[1],seq.shape[2]//2),bool);r[7:-7,7:-7]=1
        for th in (40,60,80):
            for alg,a in candidates(seq,th).items():rows.append(dict(scene=path.stem,input_kind='validated_real_RGB_no_truth',threshold=th,algorithm=alg,**metrics(a,r)))
    (output/'comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (output/'comparison.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    for r in rows:
        if r['threshold']==60 and r['algorithm'] in ('quality','weak_hold','gradient_hold'):
            print(r)
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(4,3,figsize=(11,8),layout='constrained')
    for rr,name in enumerate(('weak_static','strong_static','moving_2px','appear_disappear')):
        seq,_=sequences[name];outputs=candidates(seq,60)
        f=4 if name!='appear_disappear' else 9
        for ax,image,title in zip(axes[rr],(seq[f],np.repeat(outputs['quality'][f],2,1),np.repeat(outputs['gradient_hold'][f],2,1)),('Noisy RGB','QUALITY','One-frame gradient support')):
            ax.imshow(image,cmap='gray',vmin=0,vmax=1 if image.ndim==2 else 255,interpolation='nearest')
            ax.set_title(name+' / '+title,fontsize=9);ax.axis('off')
    fig.suptitle('SYNTHETIC comparison at TH60; model evidence, not measured board improvement')
    fig.savefig(output/'model_comparison.png',dpi=140);plt.close(fig)
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--real',type=Path,nargs='*',default=[]);a=p.parse_args();study(a.output,a.real)
