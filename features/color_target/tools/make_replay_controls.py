"""Generate explicitly synthetic RGB controls; never a camera benchmark."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model.replay_data import sha256, write_ppm

RED=(230,30,30)
BG=(90,90,90)


def generate(root, width=64, height=48, full=False):
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    w,h=width,height
    manifest={"schema":1,"description":"Synthetic mechanism controls; camera conclusions reserved", "clips":[]}
    def clip(name, specs):
        ci=len(manifest["clips"])
        c={"clip_id":name,"group_id":name,"split":"validation","source_kind":"synthetic",
           "width":w,"height":h,"frames":[]}
        for index,spec in enumerate(specs):
            rgb=bytearray(BG*(w*h)); points=spec.get("points",set())
            tone=spec.get("tone",RED)
            for x,y in points:
                if 0<=x<w and 0<=y<h: rgb[(y*w+x)*3:(y*w+x)*3+3]=bytes(tone)
            for x,y in spec.get("noise",set()):
                if 0<=x<w and 0<=y<h: rgb[(y*w+x)*3:(y*w+x)*3+3]=bytes(RED)
            rel=f"{name}/{index:04d}.ppm"
            write_ppm(root/rel,w,h,rgb)
            ann=spec.get("annotation","auto")
            if ann=="auto":
                ann={"present":bool(points),"bbox":([min(x for x,y in points),min(y for x,y in points),
                       max(x for x,y in points),max(y for x,y in points)] if points else None)}
            frame={"path":rel,"session":ci+1,"frame":index,"annotation":ann,
                   "sha256":sha256((root/rel).read_bytes())}
            if "fault" in spec: frame["test_fault"]=spec["fault"]
            c["frames"].append(frame)
        manifest["clips"].append(c)
    rect=lambda x,y,bw,bh:{(xx,yy) for yy in range(y,min(y+bh,h)) for xx in range(x,min(x+bw,w))}
    if full:
        box=rect(w-12,h-10,12,10)
        clip("full_last_lanes",[{"points":box},{"points":set()},
                               {"points":rect(0,0,8,8)},{"points":set()}])
    else:
        box=lambda i:rect(8+(i%5)*3,12,8,8)
        clip("clean_motion",[{"points":box(i)} for i in range(6)])
        noise={(x,y) for y in range(0,h,5) for x in range(0,w,5)
               if not (5<=x<=32 and 9<=y<=23)}
        clip("isolated_noise",[{"points":box(i),"noise":noise} for i in range(6)])
        cluster=rect(0,0,2,2)|rect(w-2,h-2,2,2)
        clip("empty_clusters",[{"points":set(),"noise":cluster} for _ in range(4)])
        clip("thin_lane_alignment",[{"points":rect(8+i,8,1,16)} for i in range(4)])
        tones=[(230,30,30),(31,0,0),(32,0,0),(70,46,46),(69,46,46),(120,75,30),(120,76,30),(230,30,30)]
        clip("rgb_threshold_edges",[{"points":box(0),"tone":tone} for tone in tones])
        clip("loss_reappearance",[{"points":box(i)} for i in range(3)]+
             [{"points":set()} for _ in range(3)]+[{"points":box(0)} for _ in range(3)])
        clip("same_color_unknown",[{"points":rect(4,8,8,8)|rect(w-16,24,12,12),"annotation":None}
                                    for _ in range(4)])
        clip("session_restart",[{"points":box(i)} for i in range(6)])
        for i,f in enumerate(manifest["clips"][-1]["frames"]):
            f["session"]=800+i//3; f["frame"]=0xfffffffc+i if i<3 else i-3
        clip("complete_abort",[{"points":box(0)},{"points":box(1)},
             *[{"points":box(2),"fault":kind} for kind in ("abort_idle","abort_first","abort_last")],
             {"points":box(3)}])
        clip("protocol_faults",[{"points":box(i),"fault":fault}
             for i,fault in enumerate((None,"id","eol","xy","orphan",None))])
        clip("reset_cancellation",[{"points":box(0)},
             {"points":box(1),"fault":"truncate_reset"},{"points":box(2)},
             {"points":box(3),"fault":"reset_tail"},{"points":box(4)}])
        for i,f in enumerate(manifest["clips"][-1]["frames"]):
            if i>=2: f["session"]=1000+i//2; f["frame"]=i%2
    path=root/"manifest.json"
    path.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    return path


def generate_contracts(root):
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    data={"schema":1,"description":"Synthetic narrow-raster contract controls","clips":[]}
    for w,h in ((4,1),(4,2),(8,1),(8,3)):
        name=f"contract_{w}x{h}"
        clip={"clip_id":name,"group_id":name,"split":"validation","source_kind":"synthetic",
              "width":w,"height":h,"frames":[]}
        for i in range(6):
            present=i!=2
            rgb=bytes((RED if present else BG)*(w*h))
            rel=f"{name}/{i:04d}.ppm"; write_ppm(root/rel,w,h,rgb)
            f={"path":rel,"session":70+i//4,"frame":i%4,
               "annotation":{"present":present,"bbox":[0,0,w-1,h-1] if present else None},
               "sha256":sha256((root/rel).read_bytes())}
            if i==3: f["test_fault"]="abort_last"
            clip["frames"].append(f)
        data["clips"].append(clip)
    path=root/"manifest.json"; path.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    return path


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--full",action="store_true")
    a=p.parse_args()
    print(generate(a.out,1280 if a.full else 64,720 if a.full else 48,a.full))
