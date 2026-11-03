"""RGB file replay through optional filter, statistics, track, box and text RTL.

Without --manifest generate synthetic mechanism controls, not camera evidence.
Actual camera material and production policy remain pending.
"""
import argparse
import bisect
import csv
import hashlib
import importlib.util
import json
import random
import tempfile
from pathlib import Path

from model.ref_color_target_stream import frame_result, RESULT_KEYS, TRACK_KEYS
from model.ref_color_target_track import sim_track
from model.ref_color_target_overlay import overlay_pixel
from model.ref_color_target_text import text_lines, overlay_pixel as text_pixel
from model.replay_data import load_manifest, read_ppm, metrics, summarize
from tools.make_replay_controls import generate, generate_contracts

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("replay_simlib",HERE/"tools/simlib.py")
simlib=importlib.util.module_from_spec(spec); spec.loader.exec_module(simlib)


class Stimulus:
    def __init__(self, path):
        self.f=path.open("w",encoding="ascii"); self.n=0; self.resets=[]; self.accepted_pixels=0
    def put(self, *, reset=False, valid=0, data=0, x=0, y=0, sof=0,eol=0,eof=0,
            session=0,frame=0,abort=0,probe=0,dx=0,dy=0):
        n=self.n
        self.f.write(f"{int(not reset)} {valid} {data:024x} {x} {y} {sof} {eol} {eof} "
                     f"{session} {frame} {abort} {probe} {dx} {dy}\n")
        if reset: self.resets.append(n)
        if valid and not reset: self.accepted_pixels+=4
        self.n+=1
        return n
    def idle(self,n):
        for _ in range(n): self.put()


def query_points(w,h,box):
    # Probe all four lane phases near true geometry, plus virtual text plane.
    xs={0,1,2,3,w-4,w-3,w-2,w-1}; ys={0,h-1}
    if box:
        for x in (box[0],box[2],(box[0]+box[2])//2): xs.update(range(max(0,x-4),min(w,x+5)))
        for y in (box[1],box[3],(box[1]+box[3])//2): ys.update(range(max(0,y-4),min(h,y+5)))
    grid={(x,y) for x in xs for y in ys}
    # Text foreground/background, row boundaries and outside-region samples.
    grid.update((x,y) for x in (15,16,17,31,32,127,239,240)
                for y in (599,600,601,615,616,617,618,633,634))
    return sorted(grid,key=lambda p:(p[1],p[0]))


def run_geometry(clips, mode, args, params):
    w,h=clips[0]["width"],clips[0]["height"]
    rng=random.Random(5501+w+h)
    candidates,probes,records,legacy_results,legacy_orphans=[],{},[],{},[]
    label=f"{'support3' if mode else 'bypass'}-{w}x{h}"
    with tempfile.TemporaryDirectory(prefix="ct_replay_") as temp:
        temp=Path(temp); stim=Stimulus(temp/"stim.txt")
        for clip in clips:
            stim.put(reset=True)
            for index,f in enumerate(clip["frames"]):
                _,_,rgb,_=read_ppm(f["resolved_path"])
                fault=f.get("test_fault")
                if fault not in (None,"id","eol","xy","orphan","abort_idle","abort_first",
                                 "abort_last","truncate_reset","reset_tail"):
                    raise ValueError(f"Unknown test fault: {fault}")
                invalid=fault in ("id","eol","xy","orphan","abort_idle","abort_first","abort_last")
                gold,counts=frame_result(rgb,w,h,f["session"],f["frame"],mode,params,invalid)
                legacy_gold,_=frame_result(rgb,w,h,f["session"],f["frame"],False,params,
                    fault in ("abort_idle","abort_first","abort_last"))
                row={"clip_id":clip["clip_id"],"group_id":clip["group_id"],"split":clip["split"],
                     "source_kind":clip["source_kind"],"session":f["session"],"frame":f["frame"],
                     "pixel_sha256":f["pixel_sha256"],"fault":fault,"annotation":f.get("annotation"),
                     "result":gold,**counts}
                records.append(row)
                eof_cycle=None
                for i in range(w*h//4):
                    x=(i%(w//4))*4; y=i//(w//4)
                    first=i==0; last=i==w*h//4-1
                    data=int.from_bytes(rgb[(y*w+x)*3:(y*w+x+4)*3],"big")
                    cycle=stim.put(valid=1,data=data,x=x ^ int(fault=="xy" and i==1),y=y,
                        sof=int(first and fault!="orphan"),eol=int(x==w-4) ^ int(fault=="eol" and i==1),
                        eof=int(last),session=f["session"],frame=f["frame"] ^ int(fault=="id" and i==1),
                        abort=int((fault=="abort_first" and first) or (fault=="abort_last" and last)))
                    if (fault=="orphan" and first) or (fault in ("id","eol","xy") and i==1):
                        row["error_due"]=cycle+(0 if mode else 1)
                    if last: eof_cycle=cycle
                    if fault=="truncate_reset" and i==0:
                        stim.put(reset=True); row["status"]="reset_cancelled_partial"; break
                    if fault=="abort_idle" and i==0: stim.put(abort=1)
                    # Gaps are deterministic and do not change coordinates.
                    if index>=3 and not last and i%97==11: stim.idle(rng.randrange(3))
                if eof_cycle is not None:
                    due=eof_cycle+(w//4+3 if mode else 1)
                    candidates.append({"cycle":due,"row":row,"result":gold,"input_eof":eof_cycle})
                    row["input_eof_cycle"]=eof_cycle
                    if not mode and fault not in ("id","eol","xy","orphan"):
                        legacy_results[eof_cycle]=legacy_gold
                    if not mode and fault=="orphan": legacy_orphans.append(eof_cycle)
                if fault=="reset_tail": stim.put(reset=True)
                # First two frames run without any blanking; last frame in each
                # burst is followed by a display replay after all conversions.
                if index<2: continue
                stim.idle(w//4+160)
                for x,y in query_points(w,h,f.get("annotation",{}).get("bbox") if f.get("annotation") else None):
                    cycle=stim.put(probe=1,dx=x,dy=y)
                    probes[cycle]=(x,y)
            stim.idle(w//4+160)
        stim.f.close()
        end=stim.n
        resets=stim.resets+[end]
        expected_r,expected_t={},{}
        for item in candidates:
            cycle=item["cycle"]; eof=item["input_eof"]
            next_reset=resets[bisect.bisect_right(resets,eof)]
            if cycle>=next_reset:
                item["row"]["status"]="reset_cancelled_pending"
            else:
                expected_r[cycle]=item
                item["row"]["status"]="published"
                item["row"]["result_cycle"]=cycle
        zero={"session":0,"frame":0,"state":0,"show":0,"count":0,"xmin":0,"xmax":0,
              "ymin":0,"ymax":0,"cx":0,"cy":0,"change":0}
        for begin,stop in zip(resets,resets[1:]):
            emitted=[(c,item) for c,item in sorted(expected_r.items()) if begin<c and c+1<stop]
            trkin=[dict(strobe=1,rvalid=r["result"]["valid"],**r["result"]) for c,r in emitted]
            golds=sim_track(trkin,dict(acq_frames=2,lost_frames=2,max_jump=0))
            for (cycle,item),gold in zip(emitted,golds):
                expected_t[cycle+1]=gold; item["row"]["track"]=gold
                item["row"]["track_cycle"]=cycle+1
        sources=["color_classify.v","color_target_detect.v","color_target_support3.v","color_target_mask_stats.v",
                 "color_target_detect_stream.v","color_target_track.v","color_target_overlay.v","color_target_text_overlay.v"]
        overrides={"color_target_mask_stats.v":args.stats_rtl,"color_target_detect_stream.v":args.stream_rtl}
        ok,transcript,err=simlib.simulate([overrides.get(s) or HERE/"rtl"/s for s in sources]+
                [HERE/"tb/ct_text_font_stub.v",HERE/"tb/tb_color_target_replay.v"],
            "tb_color_target_replay",dict(WIDTH=w,HEIGHT=h,FILTER_ENABLE=mode,
                TARGET_CLASS=params["target_class"],HUE_HALF_WIDTH_DEG=params["hue_half_width_deg"],
                C_MIN=params["c_min"],V_MIN=params["v_min"],MIN_COUNT=params["min_count"]),
            dict(STIM=(temp/"stim.txt").as_posix(),OUT=(temp/"dut.txt").as_posix()),
            args.sim,args.msim,temp,"replay")
        args.out.mkdir(parents=True,exist_ok=True)
        (args.out/f"{label}-sim.txt").write_text(err+transcript,encoding="utf-8")
        if not ok or "FAIL" in transcript or "PASS color_target_replay" not in transcript:
            raise AssertionError(err+transcript)
        got_r,got_t,got_p,got_l={},{},{},{}
        for line in (temp/"dut.txt").read_text(encoding="ascii").splitlines():
            fields=line.split(); kind=fields[0]; cycle=int(fields[1])
            dest={"R":got_r,"T":got_t,"P":got_p,"L":got_l}[kind]
            assert cycle not in dest,(kind,cycle,"duplicate event")
            dest[cycle]=fields[2:]
        assert set(got_r)==set(expected_r),(label,"result cycles",sorted(set(got_r)^set(expected_r))[:8])
        assert set(got_t)==set(expected_t),(label,"track cycles",sorted(set(got_t)^set(expected_t))[:8])
        assert set(got_p)==set(probes),(label,"probe cycles")
        for cycle,gold in legacy_results.items():
            assert list(map(int,got_l[cycle]))==[gold[k] for k in RESULT_KEYS],(label,cycle,"legacy bypass")
        for cycle in legacy_orphans:
            assert list(map(int,got_l[cycle][2:]))==[0]*10,(label,cycle,"legacy orphan EOF")
        protocol_error=False
        for cycle,item in sorted(expected_r.items()):
            begin=resets[bisect.bisect_right(resets,cycle)-1]
            protocol_error=any(begin<r["row"].get("error_due",end+1)<=cycle
                               for r in candidates)
            got=list(map(int,got_r[cycle])); want=[item["result"][k] for k in RESULT_KEYS]+[int(protocol_error)]
            assert got==want,(label,cycle,"result",got,want)
        for cycle,gold in expected_t.items():
            got=list(map(int,got_t[cycle])); want=[gold[k] for k in TRACK_KEYS]
            assert got==want,(label,cycle,"track",got,want)
        tcycles=sorted(expected_t)
        for cycle,(x,y) in probes.items():
            begin=resets[bisect.bisect_right(resets,cycle)-1]
            i=bisect.bisect_right(tcycles,cycle)-1
            track=expected_t[tcycles[i]] if i>=0 and tcycles[i]>begin else zero
            box=overlay_pixel(x,y,track["show"],track["show"],
                track["xmin"],track["xmax"],track["ymin"],track["ymax"],track["cx"],track["cy"],
                dict(box_thick=1,cross_arm=3))
            l0,l1=text_lines(track["state"],track["count"],track["cx"],track["cy"])
            tv,trgb,_,_=text_pixel(x,y,l0,l1,track["show"])
            got=got_p[cycle]
            assert (int(got[0]),int(got[1]))==(x,y)
            assert int(got[2])==bool(box) and (not box or int(got[3],16)==box),(label,cycle,"box",got,box)
            assert int(got[4])==tv and (not tv or int(got[5],16)==trgb),(label,cycle,"text pixel")
            assert bytes.fromhex(got[6]).decode("ascii")==l0,(label,cycle,"text line0",got[6],l0)
            assert bytes.fromhex(got[7]).decode("ascii")==l1,(label,cycle,"text line1",got[7],l1)
        for row in records:
            row["metric"]=metrics(row["annotation"],row["result"],w,h) if row["status"]=="published" and row["result"]["valid"] else None
            row["expected_result"]=row["result"]
            if row["status"]!="published": row["result"]=None
        result={"mode":label,"width":w,"height":h,"input_cycles":end,
                "accepted_pixels":stim.accepted_pixels,
                "result_events":len(got_r),"track_events":len(got_t),"display_probes":len(got_p),
                "legacy_results_compared":len(legacy_results),
                "cancelled_frames":sum(r["status"]!="published" for r in records),
                "event_sha256":hashlib.sha256((temp/"dut.txt").read_bytes()).hexdigest(),
                "metrics_by_source_and_split":{},"records":records}
        for source in ("synthetic","camera"):
            for split in ("tune","validation","heldout"):
                selected=[r for r in records if r["source_kind"]==source and r["split"]==split]
                if selected: result["metrics_by_source_and_split"][source+"/"+split]=summarize(selected)
        (args.out/f"{label}.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
        print("PASS",label,"cycles",end,"results",len(got_r),"probes",len(got_p))
        return result


def main():
    ap=simlib.add_args(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("--manifest",type=Path)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--full",action="store_true",help="generate extra synthetic 1280x720 controls")
    ap.add_argument("--min-count",type=int,help="default: 64 for supplied manifests, 4 for generated controls")
    ap.add_argument("--mode",choices=("both","bypass","support3"),default="both")
    ap.add_argument("--stats-rtl",type=Path,help="alternate statistics RTL for negative controls")
    ap.add_argument("--stream-rtl",type=Path,help="alternate stream RTL for negative controls")
    args=ap.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    path=args.manifest or generate(args.out/"synthetic-controls")
    data=load_manifest(path)
    manifests=[{"label":"primary","sha256":hashlib.sha256(path.read_bytes()).hexdigest()}]
    if not args.manifest:
        narrow=generate_contracts(args.out/"contract-controls")
        data["clips"]+=load_manifest(narrow)["clips"]
        manifests.append({"label":"narrow_controls","sha256":hashlib.sha256(narrow.read_bytes()).hexdigest()})
    if args.full and args.manifest: raise ValueError("--full generates controls; do not combine with --manifest")
    if args.full:
        full_path=generate(args.out/"full-controls",1280,720,True)
        data["clips"]+=load_manifest(full_path)["clips"]
        manifests.append({"label":"full_controls","sha256":hashlib.sha256(full_path.read_bytes()).hexdigest()})
    params=dict(target_class=0,hue_half_width_deg=30,c_min=24,v_min=32,
                min_count=args.min_count if args.min_count is not None else (64 if args.manifest else 4))
    groups={}
    for clip in data["clips"]: groups.setdefault((clip["width"],clip["height"]),[]).append(clip)
    modes=[0,1] if args.mode=="both" else [int(args.mode=="support3")]
    results=[run_geometry(clips,mode,args,params) for clips in groups.values() for mode in modes]
    summary={"schema":1,"manifests":manifests,
             "camera_material_used":any(c["source_kind"]=="camera" for c in data["clips"]),
             "parameters":params,"quality_note":"Synthetic controls establish mechanism correctness only; camera policy reserved",
             "declared_unique_rgb_frames":len({(c["width"],c["height"],f["pixel_sha256"])
                 for c in data["clips"] for f in c["frames"]}),
             "results":[{k:v for k,v in r.items() if k!="records"} for r in results]}
    (args.out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    paired={}
    for geometry in groups:
        by_mode={r["mode"].split("-")[0]:r for r in results if (r["width"],r["height"])==geometry}
        if not {"bypass","support3"}<=by_mode.keys(): continue
        raw={(r["clip_id"],r["session"],r["frame"]):r for r in by_mode["bypass"]["records"]}
        for row in by_mode["support3"]["records"]:
            base=raw[(row["clip_id"],row["session"],row["frame"])]
            if row["metric"] is None or base["metric"] is None: continue
            p=paired.setdefault(row["clip_id"],{"paired_frames":0,"positive_frames":0,
                "raw_positive_iou_sum":0.0,"filtered_positive_iou_sum":0.0,
                "raw_false_positives":0,"filtered_false_positives":0})
            p["paired_frames"]+=1
            for r,prefix in ((base,"raw"),(row,"filtered")):
                p[prefix+"_false_positives"]+=r["metric"]["false_positive"]
                if r["metric"]["truth_present"]: p[prefix+"_positive_iou_sum"]+=r["metric"]["iou"]
            p["positive_frames"]+=int(row["metric"]["truth_present"])
    for p in paired.values():
        for prefix in ("raw","filtered"):
            p[prefix+"_mean_positive_iou"]=(p.pop(prefix+"_positive_iou_sum")/p["positive_frames"]
                if p["positive_frames"] else None)
    (args.out/"paired-ablation.json").write_text(json.dumps(paired,indent=2)+"\n",encoding="utf-8")
    columns=["mode","clip_id","source_kind","split","session","frame","status","fault",
             "raw_hits","kept_hits","valid","present","count","xmin","ymin","xmax","ymax",
             "track_state","track_show","track_session","track_frame","current_observation",
             "annotated","evaluated","miss","false_positive","iou","center_l1"]
    with (args.out/"frames.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=columns); writer.writeheader()
        for result in results:
            for row in result["records"]:
                entry={k:row.get(k) for k in columns if k in row}; entry["mode"]=result["mode"]
                if row["result"]:
                    entry.update({k:row["result"][k] for k in ("valid","present","count","xmin","ymin","xmax","ymax")})
                t=row.get("track")
                if t:
                    entry.update(track_state=t["state"],track_show=t["show"],track_session=t["session"],track_frame=t["frame"],
                        current_observation=int(bool(row["result"] and row["result"]["valid"] and row["result"]["present"])
                            and t["count"]>0 and (t["session"],t["frame"])==(row["session"],row["frame"]) and t["state"]!=3))
                entry["annotated"]=int(row["annotation"] is not None)
                entry["evaluated"]=int(row["metric"] is not None)
                if row["metric"]: entry.update({k:row["metric"][k] for k in ("miss","false_positive","iou","center_l1")})
                writer.writerow(entry)
    print("PASS RGB replay: results, identities, cancellation, track, box and text")


if __name__=="__main__": main()
