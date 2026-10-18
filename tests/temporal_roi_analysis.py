"""Analyze validated optical ROI data. No camera cause or quality ranking is
inferred without actual data and (for completeness/ghosting) independent labels.
No candidate in this file is connected to the FPGA video path.
"""
from pathlib import Path
import argparse,json
import numpy as np
import edge_stability_model as spatial
import edge_denoise_model as den
import temporal_transport as transport

def apply_gain(pre,gains):
    a=pre.astype(np.uint32).copy()
    for c,g in ((0,gains[0]),(2,gains[1])):a[:,:,c]=np.minimum(255,(a[:,:,c]*int(g))>>16)
    return a.astype(np.uint8)

def proposals(edges,gradient,th):
    e=np.asarray(edges,bool);vote=e.copy();hold=e.copy()
    for f in range(2,len(e)):vote[f]=(e[f].astype(int)+e[f-1]+e[f-2])>=2
    for f in range(1,len(e)):hold[f]=e[f]|(e[f-1]&(gradient[f]>=th//2))
    return dict(current=e,majority3=vote,one_frame_gradient_support=hold)

def distance_to(mask,max_pixels=4):
    # Coordinates are paired samples: dx=1 is TWO original horizontal pixels.
    h,w=mask.shape;pad=np.pad(mask,((max_pixels,max_pixels),(max_pixels,max_pixels)))
    d=np.full((h,w),max_pixels+1,int)
    for r in range(max_pixels,-1,-1):
        near=np.zeros((h,w),bool)
        for dy in range(-r,r+1):
            for dx in range(-(r//2),r//2+1):near|=pad[max_pixels+dy:max_pixels+dy+h,max_pixels+dx:max_pixels+dx+w]
        d[near]=r
    return d

def metrics(masks,roi,truth=None,flat=None):
    a=np.asarray(masks,bool);p=a[:-1];c=a[1:];union=(p|c)&roi;flip=(p^c)&roi
    result=dict(flip_per_union=float(flip.sum()/union.sum()) if union.any() else None,flip_per_roi=float(flip.sum()/((len(a)-1)*roi.sum())),mean_edge_samples=float(a[:,roi].sum(1).mean()))
    distances=[];unmatched=total=0
    for prev,cur in zip(p,c):
        for before,after in ((prev,cur),(cur,prev)):
            ds=distance_to(before)[after&roi];distances.extend(ds.tolist());unmatched+=int((ds>4).sum());total+=len(ds)
    result.update(mean_nearest_position_distance_original_pixels=float(np.mean(distances)) if distances else None,
                  unmatched_beyond_4px_fraction=unmatched/total if total else None,position_is_matching_proxy=True,
                  contour_recall=None,flat_false_positive_fraction=None,ghost_outside_truth_band=None)
    if truth is not None:
        gt=np.asarray(truth,bool)
        if gt.ndim==2:gt=np.repeat(gt[None],len(a),0)
        assert gt.shape==a.shape
        result['contour_recall']=float(sum(((distance_to(x)<=2)&g&roi).sum() for x,g in zip(a,gt))/max(1,(gt&roi).sum()))
        result['ghost_outside_truth_band']=float(sum((x&(distance_to(g)>2)&roi).sum() for x,g in zip(a,gt))/max(1,(a&roi).sum()))
    if flat is not None:result['flat_false_positive_fraction']=float(a[:,np.asarray(flat,bool)&roi].mean())
    return result

def analyze(pre,post,meta,th=80,truth=None,flat=None):
    n,h,w,_=pre.shape;roi=np.zeros((h,w//2),bool);roi[7:-7,7:-7]=True
    if n<3 or not roi.any():raise ValueError('need >=3 consecutive frames and seven-sample spatial halo')
    states=[spatial.stages(x,True,th) for x in post]
    shift=lambda a,k:np.roll(a,(-k,-k),(0,1))
    current=np.array([shift(s['labels'][-1][1],7) for s in states]);gradient=np.array([shift(s['mag'],2) for s in states])
    stage_arrays={
        'gray_pair':np.array([den.pairs(x) for x in post]),
        'gaussian':np.array([shift(s['source'],1) for s in states]),
        'sobel_magnitude':gradient,'direction':np.array([shift(s['axis'],2) for s in states]),
        'nms_keep':np.array([shift(s['detail']['keep'],3) for s in states]),
        'nms_strong':np.array([shift(s['detail']['magnitude']>=th,3) for s in states]),
        'nms_weak':np.array([shift(s['detail']['magnitude']>=th//2,3) for s in states]),
        'four_hop':current}
    stages={name:dict(changed_fraction=float((a[1:,roi]!=a[:-1,roi]).mean()),mean_abs_delta=float(np.abs(a[1:,roi].astype(float)-a[:-1,roi].astype(float)).mean())) for name,a in stage_arrays.items()}
    gains=meta[:,1:3].astype(np.uint32)
    # Same CURRENT pre-AWB input with previous-frame gain isolates transfer
    # change numerically. These absolute differences are NOT additive causes.
    same_input_gain_delta=[float(np.abs(post[f].astype(int)-apply_gain(pre[f],gains[f-1]).astype(int)).mean()) for f in range(1,n)]
    fixed=np.array([apply_gain(x,gains[0]) for x in pre])
    fixed_quality=np.array([spatial.outputs(x,th)['quality'] for x in fixed])
    candidates=proposals(current,gradient,th)
    results={name:metrics(a,roi,truth,flat) for name,a in candidates.items()}
    result=dict(frames=n,roi_pixels=[w,h],evaluation_internal_samples=int(roi.sum()),threshold=th,
        pre_rgb_mean_abs_delta=float(np.abs(pre[1:].astype(int)-pre[:-1].astype(int)).mean()),
        post_rgb_mean_abs_delta=float(np.abs(post[1:].astype(int)-post[:-1].astype(int)).mean()),
        gains_q16=gains.tolist(),awb_stats=meta[:,3:8].tolist(),same_current_input_previous_gain_mae=same_input_gain_delta,
        capture_sof_intervals_mipi_cycles=((meta[1:,15].astype(np.int64)-meta[:-1,15].astype(np.int64))%2**32).tolist(),
        fixed_gain_reference_q16=gains[0].tolist(),fixed_gain_is_proven_converged=False,
        fixed_gain_replay_metrics=metrics(fixed_quality,roi,truth,flat),stages=stages,candidates=results,
        fifo_historical_sticky=((meta[:,7]>>17)&3).tolist(),fifo_repeat_event_detection_available=False,
        ground_truth_available=truth is not None,motion_response_verified=False,
        causal_contribution_percentages=None,ranking='not selected: require scene labels, motion trials and repeated bursts')
    return result

def load_validated_capture(path):
    with np.load(path) as d:
        pre,post,meta,g=(d[k] for k in ('pre','post','meta','global_header'))
    if pre.dtype!=np.uint8 or post.dtype!=np.uint8:
        raise ValueError('RGB arrays must be uint8')
    # Revalidate all original quantities/checksums through the same raw format;
    # reject files with changed arrays, not just files with an .npz extension.
    flat_words=[]
    vectors=[int.from_bytes(b,'big') for b in pre.reshape(-1,12)]
    for plane in range(3):flat_words.extend((x>>(32*plane))&0xffffffff for x in vectors)
    words=np.array(flat_words+meta.ravel().tolist()+g.tolist(),np.uint32)
    _,validated_post,_,_=transport.unpack_capture(words)
    if not np.array_equal(post,validated_post):
        raise ValueError('post array differs from CRC-validated AWB reconstruction')
    return pre,post,meta,g

def main():
    ap=argparse.ArgumentParser();ap.add_argument('capture',type=Path);ap.add_argument('--threshold',type=int,default=80);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--labels',type=Path);a=ap.parse_args()
    pre,post,meta,g=load_validated_capture(a.capture)
    labels=np.load(a.labels) if a.labels else {}
    assert a.threshold in range(10,251,10)
    result=analyze(pre,post,meta,a.threshold,labels.get('truth'),labels.get('flat'))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
