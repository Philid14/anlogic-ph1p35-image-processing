"""Temporal diagnosis, not an optimization. Synthetic RGB only; seed fixed.

Uses independently spatial models already checked against the candidate RTL.
All cross-algorithm metrics use a common ROI and compensate causal offsets.
"""
from pathlib import Path
import hashlib,json,csv
import numpy as np
import edge_denoise_model as den
import edge_nms_model as nms
import edge_quality_model as quality
import awb_v2_selection_model as awb

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/edge_stability_evidence'

def stages(rgb,filtered=True,th=60):
    pair=den.pairs(rgb);source=den.prefilter(pair,'gaussian' if filtered else 'sobel')
    gx,gy,mag=nms.gradients(rgb,filtered);axis=nms.direction(gx,gy)
    detail=nms.nms_details(mag,axis,4 if filtered else 2)
    labels=quality.label_stages(detail['magnitude'],th)
    return dict(pair=pair,source=source,gx=gx,gy=gy,mag=mag,axis=axis,detail=detail,labels=labels)

def outputs(rgb,th):
    raw=stages(rgb,False,th);s=stages(rgb,True,th)
    # Compensate each causal center into the same input coordinate system.
    shift=lambda a,k:np.roll(a,(-k,-k),(0,1))
    return dict(control=shift(raw['mag']>=th,1),denoise=shift(s['mag']>=th,2),
                nms=shift(s['detail']['magnitude']>=th,3),
                quality=shift(s['labels'][-1][1],7))

def temporal_metrics(seq,roi):
    a=np.asarray(seq,bool);prev=a[:-1];cur=a[1:]
    flips=(prev^cur)&roi;union=(prev|cur)&roi
    near_prev=np.array([den.dilate(x,1) for x in prev])
    near_cur=np.array([den.dilate(x,1) for x in cur])
    births=cur&~near_prev&roi;deaths=prev&~near_cur&roi
    relocation=((cur&~prev&near_prev)|(prev&~cur&near_cur))&roi
    # Matching within 1 internal Chebyshev sample is a proxy, NOT optical flow.
    return dict(flip_per_roi=float(flips.sum()/((len(a)-1)*roi.sum())),
                flip_per_union=float(flips.sum()/max(1,union.sum())),
                unmatched_birth_death_per_union=float((births.sum()+deaths.sum())/max(1,union.sum())),
                nearby_change_per_union=float(relocation.sum()/max(1,union.sum())),
                mean_edges=float(a[:,roi].sum(axis=1).mean()))

def experiments():
    OUT.mkdir(exist_ok=True);rows=[];stage_rows=[];fixed={};rng=np.random.default_rng(20261018)
    # Exact repeated RGB includes frozen synthetic noise, NOT re-randomized noise.
    fixtures={n:rgb for n,_,rgb in quality.scenes(256,128) if n in ('glasses_n8','paper_n8','text_small_n8','blurred')}
    for name,rgb in fixtures.items():
        values=outputs(rgb,60);fixed[name]={}
        for alg,a in values.items():
            assert all(np.array_equal(a,outputs(rgb.copy(),60)[alg]) for _ in range(3))
            fixed[name][alg]=hashlib.sha256(a.tobytes()).hexdigest()
    for name,base in fixtures.items():
        h,w,_=base.shape;roi=np.zeros((h,w//2),bool);roi[18:-18,18:-18]=True
        for perturb in ('repeat','rgb_lsb1','noise_sigma4','global_scale_1pct','rb_gain_1pct'):
            seq=[]
            for frame in range(12):
                b=base.astype(float)
                if perturb=='rgb_lsb1':b+=rng.integers(-1,2,b.shape)
                if perturb=='noise_sigma4':b+=rng.normal(0,4,b.shape)
                if perturb=='global_scale_1pct':b*=1+(.01 if frame%2 else -.01)
                if perturb=='rb_gain_1pct':b[:,:,(0,2)]*=1+(.01 if frame%2 else -.01)
                seq.append(np.clip(np.rint(b),0,255).astype(np.uint8))
            evaluated=[stages(b,True,60) for b in seq]
            planes={
              'gray_pair':[den.pairs(b) for b in seq],
              'gaussian':[s['source'] for s in evaluated],
              'gradient_mag':[s['mag'] for s in evaluated],
              'gradient_axis':[s['axis'] for s in evaluated],
              'nms_keep':[s['detail']['keep'] for s in evaluated],
              'weak60':[s['detail']['magnitude']>=30 for s in evaluated],
              'strong60':[s['detail']['magnitude']>=60 for s in evaluated]}
            planes.update({f'hop{k+1}60':[s['labels'][k][1] for s in evaluated] for k in range(4)})
            for stage,arrays in planes.items():
                a=np.asarray(arrays).astype(int);delta=a[1:]-a[:-1]
                stage_rows.append(dict(scene=name,perturbation=perturb,stage=stage,
                    changed_fraction=float((delta[:,roi]!=0).mean()),mean_abs_delta=float(abs(delta[:,roi]).mean())))
            for th in (40,60,80):
                predicted=[outputs(b,th) for b in seq]
                for alg in predicted[0]:
                    metrics=temporal_metrics([x[alg] for x in predicted],roi)
                    if perturb=='repeat':assert metrics['flip_per_roi']==0
                    rows.append(dict(scene=name,perturbation=perturb,threshold=th,algorithm=alg,**metrics))
    # A: a fixed straight edge with contrast oscillating one RGB code near TH.
    x=np.indices((64,128))[1];near=[]
    for value in (61,62):
        gray=np.where(x<64,48,value).astype(np.uint8)
        near.append(np.repeat(gray[:,:,None],3,2))
    a,b=[outputs(rgb,60)['control'] for rgb in near]
    amplitude=dict(rgb_step=[61,62],threshold=60,changed=int((a^b)[10:-10,20:-20].sum()),
                   white=[int(z[10:-10,20:-20].sum()) for z in (a,b)])
    # Sweep actual RGB values to guarantee an exact threshold counterexample.
    if not amplitude['changed']:
        for value in range(49,90):
            images=[np.repeat(np.where(x<64,48,v).astype(np.uint8)[:,:,None],3,2) for v in (value,value+1)]
            a,b=[outputs(rgb,60)['control'] for rgb in images]
            if (a^b)[10:-10,20:-20].any():
                amplitude=dict(rgb_step=[value,value+1],threshold=60,changed=int((a^b)[10:-10,20:-20].sum()),white=[int(z[10:-10,20:-20].sum()) for z in (a,b)]);break
    assert amplitude['changed']>0
    # B: equal plateau vs one-code adjacent gradient perturbation, same direction.
    m=np.zeros((32,48),int);m[8:24,20:22]=100;axis=np.zeros_like(m,np.uint8)
    m2=m.copy();m2[8:24,21]=101
    k1=nms.nms_details(m,axis)['keep'];k2=nms.nms_details(m2,axis)['keep']
    peak=dict(input_delta=1,changed=int((k1^k2).sum()),rows=16,
              columns=[np.flatnonzero(k[16]).tolist() for k in (k1,k2)],
              internal_displacement=1,hdmi_horizontal_pixels=2)
    assert peak['columns']==[[21],[22]] and peak['changed']==32
    # C: only ONE high-threshold anchor changes; weak eligibility stays identical.
    m=np.zeros((32,48),int);m[16,10:19]=40;m[16,14]=59;m2=m.copy();m2[16,14]=60
    c1=quality.propagate(m,60,4);c2=quality.propagate(m2,60,4)
    anchor=dict(input_changed=1,weak_changed=int(((m>=30)^(m2>=30)).sum()),
                strong_changed=int(((m>=60)^(m2>=60)).sum()),output_changed=int((c1^c2).sum()))
    assert anchor==dict(input_changed=1,weak_changed=0,strong_changed=1,output_changed=9)
    # AWB: exact same statistics settle; input selection boundary can move gains.
    scene=[((96,112,104),4096)];g=(awb.ONE,awb.ONE);trajectory=[]
    for _ in range(16):g,count=awb.frame_target(scene,True,g);trajectory.append(g)
    assert trajectory[-4:]==[trajectory[-1]]*4
    # A neutral background + many near-chroma-gate pixels differing by 1 R code.
    sets=[[((100,100,100),4096),((r,96,96),4096)] for r in (65,64)]
    targets=[awb.frame_target(s,True) for s in sets]
    awb_result=dict(constant_stats_final_q16=list(trajectory[-1]),trajectory_q16=trajectory,
                    one_lsb_selection_cases=[dict(r=s[1][0][0],gain_q16=list(t[0]),samples=t[1]) for s,t in zip(sets,targets)],
                    board_gain_trace_available=False)
    assert targets[0]!=targets[1]
    with (OUT/'temporal_metrics.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    with (OUT/'stage_metrics.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=stage_rows[0]);w.writeheader();w.writerows(stage_rows)
    result=dict(input_kind='SYNTHETIC ONLY, not measured camera statistics',seed=20261018,
                frames_per_sequence=12,metric_rows=len(rows),fixed_output_sha256=fixed,
                threshold_crossing=amplitude,nms_peak_switch=peak,anchor_amplification=anchor,awb=awb_result)
    (OUT/'model_summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,3,figsize=(12,7),layout='constrained')
    # These are stage-isolation counterexamples, not a photograph comparison.
    pairs=[(a,b,'A: RGB 63 -> 64, Sobel TH60'),(k1,k2,'B: gradient 100 -> 101, NMS peak'),
           (c1,c2,'C: anchor 59 -> 60, four spatial hops')]
    for row,(before,after,title) in enumerate(pairs):
        for col,img in enumerate((before,after,before^after)):
            axes[row,col].imshow(np.repeat(img,2,axis=1),cmap='gray',vmin=0,vmax=1,interpolation='nearest')
            axes[row,col].set_title(title+' / '+('before','after','changed')[col],fontsize=9);axes[row,col].axis('off')
    fig.suptitle('SYNTHETIC mechanism isolation; B/C inject intermediate stage values, not RGB')
    fig.savefig(OUT/'mechanisms.png',dpi=130);plt.close(fig)
    print('PASS temporal model',json.dumps({k:v for k,v in result.items() if k not in ('fixed_output_sha256','awb')}),flush=True)
    return result

if __name__=='__main__':experiments()
