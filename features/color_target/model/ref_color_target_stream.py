"""Frame-level oracle for the experimental RGB replay path, no RTL pipeline."""
from model.ref_color_target import DEFAULTS, classify, clamp_min_count
from model.ref_color_target_support3 import support3


RESULT_KEYS = ("session","frame","valid","present","cls","count",
               "xmin","xmax","ymin","ymax","cx","cy")
TRACK_KEYS = ("session","frame","state","show","count","xmin","xmax","ymin","ymax","cx","cy","change")


def frame_result(rgb, width, height, session, frame, filtered=False, params=None, invalid=False):
    p = dict(DEFAULTS, **(params or {}))
    hits = {(i%width,i//width) for i in range(width*height)
            if classify(*rgb[i*3:i*3+3],p)}
    kept = support3(hits) if filtered else hits
    present = not invalid and len(kept) >= clamp_min_count(p["min_count"])
    result = dict(session=session,frame=frame,valid=int(not invalid),present=int(present),
                  cls=p["target_class"] & 3 if present else 0,
                  count=len(kept) if present else 0,xmin=0,xmax=0,ymin=0,ymax=0,cx=0,cy=0)
    if present:
        result.update(xmin=min(x for x,y in kept),xmax=max(x for x,y in kept),
                      ymin=min(y for x,y in kept),ymax=max(y for x,y in kept))
        result["cx"]=(result["xmin"]+result["xmax"])//2
        result["cy"]=(result["ymin"]+result["ymax"])//2
    return result, {"raw_hits":len(hits),"kept_hits":len(kept)}
