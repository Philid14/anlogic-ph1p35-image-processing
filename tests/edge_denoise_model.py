"""Independent integer image model and synthetic-only denoise comparison.

No sensor frames are supplied. NumPy spatial slices are intentionally unrelated
to the RTL pipeline/RAM schedule. Coordinates below are 640-sample coordinates.
"""
from pathlib import Path
import csv
import importlib.util
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def pairs(rgb):
    rgb = np.asarray(rgb, dtype=np.int32)
    gray = rgb[:, :, 0] // 4 + rgb[:, :, 1] // 2 + rgb[:, :, 2] // 4
    return (gray[:, 0::2] + gray[:, 1::2]) // 2


def prefilter(samples, kind):
    a = np.asarray(samples, dtype=np.int32)
    if kind == "sobel":
        return a.copy()
    out = np.zeros_like(a)
    if kind == "gaussian":
        # Single floor after the entire 12-bit weighted sum. No horizontal
        # truncation: two separate >>2 operations would not be equivalent.
        weights = ((1, 2, 1), (2, 4, 2), (1, 2, 1))
        total = np.zeros((a.shape[0]-2, a.shape[1]-2), dtype=np.int32)
        for y in range(3):
            for x in range(3):
                total += weights[y][x] * a[y:y+a.shape[0]-2, x:x+a.shape[1]-2]
        out[2:, 2:] = total // 16
    elif kind == "median":
        out[2:, 2:] = np.median(np.lib.stride_tricks.sliding_window_view(a, (3, 3)), axis=(-1, -2)).astype(np.int32)
    else:
        raise ValueError(kind)
    return out


def magnitude(rgb, kind="sobel"):
    a = prefilter(pairs(rgb), kind)
    h, w = a.shape
    gx = np.zeros((h-2, w-2), dtype=np.int32)
    gy = gx.copy()
    kx = ((-1, 0, 1), (-2, 0, 2), (-1, 0, 1))
    ky = ((1, 2, 1), (0, 0, 0), (-1, -2, -1))
    for y in range(3):
        for x in range(3):
            tile = a[y:y+h-2, x:x+w-2]
            gx += kx[y][x] * tile
            gy += ky[y][x] * tile
    out = np.zeros_like(a)
    out[2:, 2:] = np.abs(gx) + np.abs(gy)
    border = 2 if kind == "sobel" else 4
    out[:border] = 0
    out[:, :border] = 0
    return out


def edges(rgb, threshold, kind="sobel"):
    mag = magnitude(rgb, kind)
    out = mag >= threshold
    border = 2 if kind == "sobel" else 4
    out[:border] = False
    out[:, :border] = False
    return np.repeat(out.astype(np.uint8)*255, 2, axis=1)


def centered(mag, kind):
    shift = 1 if kind == "sobel" else 2
    return np.roll(mag, (-shift, -shift), axis=(0, 1))


def dilate(mask, radius):
    return np.lib.stride_tricks.sliding_window_view(np.pad(mask, radius), (2*radius+1, 2*radius+1)).max(axis=(-1, -2))


def scenes(width=256, height=128):
    rng = np.random.default_rng(20261016)
    yy, xx = np.indices((height, width))
    uniform = np.full((height, width), 48, dtype=np.int32)
    step = np.where(xx >= width//2, 72, 48)
    strong = np.where(xx >= width//2, 224, 16)
    horizontal = np.where(yy >= height//2, 72, 48)
    diagonal = np.where(xx*height >= yy*width, 72, 48)
    thin = uniform + np.where((xx == width//2) | (xx == width//2+16), 32, 0)
    texture = uniform + ((xx//6 + yy//8) % 2)*12
    noise = np.rint(rng.normal(0, 6, uniform.shape)).astype(np.int32)
    fixed = rng.integers(-6, 7, (1, width)) + rng.integers(-3, 4, (height, 1))
    impulse = uniform.copy()
    impulse[height//2, width//2] = 255
    salt = rng.random(uniform.shape)
    salt_noise = np.where(salt < .006, 100, np.where(salt > .994, -100, 0))
    values = [
        ("black", np.zeros_like(uniform), np.zeros_like(uniform)),
        ("white", np.full_like(uniform, 255), np.full_like(uniform, 255)),
        ("uniform", uniform, uniform),
        ("flat_random", uniform, uniform+noise),
        ("flat_fixed", uniform, uniform+fixed),
        ("single_bright", uniform, impulse),
        ("strong_step", strong, strong+noise),
        ("low_step", step, step+noise),
        ("horizontal", horizontal, horizontal+noise),
        ("diagonal", diagonal, diagonal+noise),
        ("thin_lines", thin, thin+noise),
        ("texture", texture, texture+noise),
        ("mixed_noise", step, step+noise+fixed+salt_noise),
    ]
    return [(n, np.repeat(np.clip(c,0,255)[:,:,None],3,axis=2).astype(np.uint8),
             np.repeat(np.clip(a,0,255)[:,:,None],3,axis=2).astype(np.uint8)) for n,c,a in values]


def baseline_equivalence():
    spec=importlib.util.spec_from_file_location("old_edge", ROOT/"tests/run_edge_v1.py")
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    cases=0
    for pattern in ("uniform","vertical","horizontal","diagonal","channels","threshold","random"):
        rgb=old.scene(64,16,pattern,17)
        for threshold in (0,10,20,40,60,80,100,160,250,2025):
            assert np.array_equal(edges(rgb,threshold),np.asarray(old.spatial_edges(rgb,threshold)))
            cases+=1
    print(f"PASS model equivalence: {cases} independent comparisons against prior 2D reference (already RTL-verified)",flush=True)


def research():
    baseline_equivalence()
    out=ROOT/"docs/edge_denoise_evidence";out.mkdir(exist_ok=True)
    rows=[]
    for name,clean,noisy in scenes():
        gt=centered(magnitude(clean),"sobel")>=10
        roi=np.zeros(gt.shape,dtype=bool);roi[6:-6,6:-6]=True
        flat=roi & ~dilate(gt,3)
        for kind in ("sobel","gaussian","median"):
            mag=centered(magnitude(noisy,kind),kind)
            for th in (10,20,30,40,50,60,70,80,100,120,160,200,250):
                pred=mag>=th
                hits=gt & roi
                recall=float(dilate(pred,1)[hits].mean()) if hits.any() else None
                distance=None
                if hits.any():
                    dist=np.full(gt.shape,5)
                    for r in range(4,-1,-1):dist[dilate(pred,r)]=r
                    distance=float(dist[hits].mean())
                continuity=None;maxgap=None
                if name in ("strong_step","low_step","mixed_noise"):
                    found=pred[6:-6,pred.shape[1]//2-2:pred.shape[1]//2+3].any(axis=1)
                    continuity=float(found.mean());gap=0;maxgap=0
                    for present in found:
                        gap=0 if present else gap+1;maxgap=max(maxgap,gap)
                rows.append(dict(scene=name,algorithm=kind,threshold=th,
                    flat_false_rate=float(pred[flat].mean()) if flat.any() else None,edge_recall_tol1=recall,
                    mean_gt_distance_chebyshev_cap5=distance,step_row_coverage=continuity,longest_step_gap_rows=maxgap))
    with (out/"synthetic_metrics.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    # Select the most sensitive threshold meeting <=1% flat false-positive
    # rate on the same low-step scene. No one-threshold winner declaration.
    selections={}
    for kind in ("sobel","gaussian","median"):
        candidates=[r for r in rows if r["scene"]=="low_step" and r["algorithm"]==kind and r["flat_false_rate"]<=.01]
        selections[kind]=max(candidates,key=lambda r:(r["edge_recall_tol1"],r["step_row_coverage"],-r["threshold"])) if candidates else None
    (out/"selection.json").write_text(json.dumps(selections,indent=2)+"\n")
    print(json.dumps(selections,indent=2),flush=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,4,figsize=(13,7),layout="constrained")
    for row,name in enumerate(("low_step","thin_lines")):
        _,clean,noisy=next(s for s in scenes() if s[0]==name)
        axes[row,0].imshow(noisy);axes[row,0].set_title(name+" synthetic input")
        for col,kind in enumerate(("sobel","gaussian","median"),1):
            th=selections[kind]["threshold"]
            image=centered(magnitude(noisy,kind),kind)>=th
            axes[row,col].imshow(image,cmap="gray",vmin=0,vmax=1)
            axes[row,col].set_title(kind+f" threshold={th}")
        for ax in axes[row]:ax.axis("off")
    fig.suptitle("Synthetic comparison; same scene, integer model, compensated causal offsets")
    fig.savefig(out/"synthetic_comparison.png",dpi=140);plt.close(fig)
    print(f"PASS research: {len(rows)} metric rows; no real sensor frame claim",flush=True)


if __name__=="__main__":research()
