"""Strict, dependency-free RGB replay manifests and frame metrics.

Bounding boxes are inclusive [xmin,ymin,xmax,ymax]. Unknown annotations are
never treated as absence. A group cannot cross dataset splits.
"""
import hashlib
import json
from pathlib import Path


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_ppm(path):
    raw = Path(path).read_bytes()
    pos, tokens = 0, []
    while len(tokens) < 4:
        while pos < len(raw) and raw[pos] in b" \t\r\n": pos += 1
        if pos < len(raw) and raw[pos] == 35:
            end = raw.find(b"\n", pos)
            if end < 0: raise ValueError("Unterminated PPM comment")
            pos = end + 1
            continue
        end = pos
        while end < len(raw) and raw[end] not in b" \t\r\n": end += 1
        if end == pos: raise ValueError("Truncated PPM header")
        tokens.append(raw[pos:end]); pos = end
    if tokens[0] != b"P6" or tokens[3] != b"255":
        raise ValueError("Only single-frame P6 RGB8 PPM is supported")
    w, h = int(tokens[1]), int(tokens[2])
    if pos >= len(raw) or raw[pos] not in b" \t\r\n": raise ValueError("Missing PPM separator")
    # Consume exactly one separator (or CRLF), not leading pixel whitespace/#.
    pos += 2 if raw[pos:pos+2] == b"\r\n" else 1
    rgb = raw[pos:]
    if w < 1 or h < 1 or len(rgb) != w*h*3: raise ValueError("PPM byte count mismatch")
    return w, h, rgb, sha256(raw)


def write_ppm(path, w, h, rgb):
    if len(rgb) != w*h*3: raise ValueError("RGB byte count mismatch")
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f"P6\n{w} {h}\n255\n".encode("ascii") + rgb)


def load_manifest(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1 or not isinstance(data.get("clips"), list) or not data["clips"]:
        raise ValueError("Expected schema=1 and a nonempty clips array")
    groups, clips, identities, pixel_splits = {}, set(), set(), {}
    for clip in data["clips"]:
        cid, group, split = clip["clip_id"], clip["group_id"], clip["split"]
        if not isinstance(cid, str) or not cid or cid in clips: raise ValueError("Duplicate/empty clip_id")
        clips.add(cid)
        if not isinstance(group, str) or not group: raise ValueError("Missing group_id")
        if split not in ("tune", "validation", "heldout"): raise ValueError("Unknown split")
        if group in groups and groups[group] != split: raise ValueError("Scene group crosses splits")
        groups[group] = split
        if clip["source_kind"] not in ("synthetic", "camera"): raise ValueError("Unknown source_kind")
        w, h = clip["width"], clip["height"]
        if type(w) is not int or type(h) is not int or w < 4 or w % 4 or h < 1 or w > 2048 or h > 1024:
            raise ValueError("Geometry must fit the 4PPC XW=11/YW=10 contract")
        if w*h > 1048575: raise ValueError("Geometry exceeds the 20-bit count range")
        if not clip.get("frames"): raise ValueError("Empty clip")
        previous = None
        for f in clip["frames"]:
            if f.get("test_fault") and clip["source_kind"] != "synthetic":
                raise ValueError("Fault injection belongs only in synthetic controls")
            sid, fid = f["session"], f["frame"]
            if any(type(v) is not int or not 0 <= v <= 0xffffffff for v in (sid, fid)):
                raise ValueError("Identity must be uint32")
            key = (cid, sid, fid)
            if key in identities: raise ValueError("Duplicate frame identity within clip")
            identities.add(key)
            if previous and sid == previous[0] and fid <= previous[1]:
                raise ValueError("Frame ID must increase within a session; start a new session before wrap")
            previous = sid, fid
            ann = f.get("annotation")
            if ann is not None:
                if type(ann.get("present")) is not bool: raise ValueError("Annotation present must be boolean")
                box = ann.get("bbox")
                if ann["present"]:
                    if not isinstance(box, list) or len(box) != 4 or any(type(v) is not int for v in box):
                        raise ValueError("Expected inclusive bbox")
                    x0,y0,x1,y1 = box
                    if not 0 <= x0 <= x1 < w or not 0 <= y0 <= y1 < h: raise ValueError("bbox outside frame")
                elif box is not None: raise ValueError("Absent annotation must have null bbox")
            rel = Path(f["path"])
            if rel.is_absolute() or ".." in rel.parts: raise ValueError("Frame paths must stay inside manifest root")
            frame_path = (path.parent / rel).resolve()
            if not frame_path.is_relative_to(path.parent): raise ValueError("Frame symlink escapes manifest root")
            iw, ih, rgb, digest = read_ppm(frame_path)
            if (iw,ih) != (w,h): raise ValueError("Frame geometry differs from manifest")
            if f.get("sha256") and f["sha256"] != digest: raise ValueError("Frame SHA-256 mismatch")
            pixel_hash=sha256(rgb)
            if pixel_hash in pixel_splits and pixel_splits[pixel_hash] != split:
                raise ValueError("Identical RGB pixels cross dataset splits")
            pixel_splits[pixel_hash]=split
            f["resolved_path"], f["actual_sha256"] = frame_path, digest
            f["pixel_sha256"] = pixel_hash
            # Keep RGB off the manifest object; a long clip is read frame-by-frame.
    return data


def metrics(annotation, result, width, height):
    if annotation is None: return None
    truth, predicted = annotation["present"], bool(result["valid"] and result["present"])
    if not truth:
        return {"truth_present":False,"false_positive":int(predicted),"miss":0,
                "iou":None,"center_l1":None}
    gt = annotation["bbox"]
    if not predicted:
        return {"truth_present":True,"false_positive":0,"miss":1,"iou":0.0,
                "center_l1":width+height}
    box = [result[k] for k in ("xmin","ymin","xmax","ymax")]
    iw = max(0, min(box[2],gt[2])-max(box[0],gt[0])+1)
    ih = max(0, min(box[3],gt[3])-max(box[1],gt[1])+1)
    inter = iw*ih
    area = lambda b:(b[2]-b[0]+1)*(b[3]-b[1]+1)
    cx,cy = (gt[0]+gt[2])//2, (gt[1]+gt[3])//2
    return {"truth_present":True,"false_positive":0,"miss":0,
            "iou":inter/(area(box)+area(gt)-inter),
            "center_l1":abs(result["cx"]-cx)+abs(result["cy"]-cy)}


def summarize(rows):
    annotated = [r for r in rows if r.get("metric") is not None]
    positive = [r["metric"] for r in annotated if r["metric"]["truth_present"]]
    negative = [r["metric"] for r in annotated if not r["metric"]["truth_present"]]
    errors = sorted(r["center_l1"] for r in positive)
    # Nearest-rank P95, including width+height penalties for missing boxes.
    p95 = errors[max(0,(95*len(errors)+99)//100-1)] if errors else None
    unknown=sum(r.get("annotation") is None for r in rows)
    return {"frames":len(rows),"annotated":len(rows)-unknown,"unknown":unknown,
            "evaluated_frames":len(annotated),"excluded_known_frames":len(rows)-unknown-len(annotated),
            "positive_frames":len(positive),"negative_frames":len(negative),
            "misses":sum(r["miss"] for r in positive),
            "false_positives":sum(r["false_positive"] for r in negative),
            "mean_positive_iou":sum(r["iou"] for r in positive)/len(positive) if positive else None,
            "center_l1_p95":p95}
