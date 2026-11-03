"""A1 public-result contract; literal gold, independent of production models.

Negative controls: point --rtl-root at an archived pre-fix source directory.
Outputs are append-only by requiring a fresh --out directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'tools'))
from simlib import add_args,simulate

# Literal reviewed table: parameter, expected physical color index/label.
# No low-bit truncation and no production normalization/model import.
GOLD=[(-2147483648,0),(-3,0),(-1,0),(0,0),(1,1),(2,2),
      (3,0),(4,0),(5,0),(6,0),(7,0),(2147483647,0)]
KEYS=('session','frame','valid','present','cls','count','xmin','xmax','ymin','ymax','cx','cy')

def expected(color):
    paths={p:[] for p in range(4)}
    for frame in range(1,6):
        for path in paths:
            valid=int(frame!=5)
            present=int(valid and (frame==color+1 if path<3 else frame<=3))
            fields=[color,24,0,7,0,2,3,1] if present else [0]*8
            paths[path].append([0x1234,frame,valid,present]+fields)
    # Abort invalidates frame statistics, not the combinational classifier.
    return paths,[[1,int(color==0)],[2,int(color==1)],[3,int(color==2)],
                  [4,0],[5,int(color==0)]]

def check_models(outdir):
    # The model outputs are checked against the SAME literal external contract,
    # never used as RTL expected values.
    sys.path.insert(0,str(HERE))
    from model.ref_color_target import run
    from model.ref_color_target_stream import frame_result
    colors=(0xff0000,0x00ff00,0x0000ff,0xffffff,0xff0000)
    cases=[]
    for parameter,color in GOLD:
        beats=[];stream=[]
        for frame,rgb in enumerate(colors,1):
            pixels=rgb.to_bytes(3,'big')*24
            item,_=frame_result(pixels,8,3,0x1234,frame,params={'target_class':parameter,'min_count':1},invalid=frame==5)
            stream.append([item[k] for k in KEYS])
            for row in range(3):
                for col in (0,4):
                    beats.append(dict(valid=1,sof=int(row==0 and col==0),eol=int(col==4),
                        eof=int(row==2 and col==4),abort=int(frame==5),x0=col,y=row,
                        data96=int.from_bytes(rgb.to_bytes(3,'big')*4,'big'),session=0x1234,frame=frame))
        legacy=[[r[k] for k in KEYS] for r in run(beats,{'target_class':parameter,'min_count':1})]
        want=expected(color)[0][0]
        passed=legacy==want and stream==want
        cases.append(dict(parameter=parameter,passed=passed,legacy=legacy,stream=stream,expected=want))
        print('PASS' if passed else 'FAIL','models TARGET_CLASS='+str(parameter))
    report=dict(kind='Python models against literal gold; no RTL simulation',cases=cases,
                passed=sum(c['passed'] for c in cases),total=len(cases))
    (outdir/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if report['passed']==len(cases) else 1

def main():
    ap=argparse.ArgumentParser();add_args(ap)
    ap.add_argument('--rtl-root',type=Path,default=HERE/'rtl')
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--models-only',action='store_true')
    args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    if args.models_only:return check_models(args.out)
    names=('color_classify.v','color_target_detect.v','color_target_support3.v',
           'color_target_mask_stats.v','color_target_detect_stream.v')
    srcs=[args.rtl_root/n for n in names]+[HERE/'tb/tb_target_class_contract.v']
    cases=[]
    for parameter,color in GOLD:
        with tempfile.TemporaryDirectory(prefix='ct_class_contract_') as td:
            ok,out,err=simulate(srcs,'tb_target_class_contract',{'CLASS':parameter},{},
                requested=args.sim,msim_root=args.msim,workdir=td)
        (args.out/f'class-{parameter}.log').write_text(out+err,encoding='utf-8')
        got={p:[] for p in range(4)};got_c=[]
        for line in out.splitlines():
            match=re.match(r'(?:# )?R ([-0-9 ]+)$',line.strip())
            if match:
                fields=list(map(int,match[1].split()));got[fields[0]].append(fields[1:])
            match=re.match(r'(?:# )?C ([-0-9 ]+)$',line.strip())
            if match: got_c.append(list(map(int,match[1].split())))
        want,want_c=expected(color)
        good=ok and 'PASS target class probe completed' in out and 'Error:' not in out and got==want and got_c==want_c
        case=dict(parameter=parameter,expected_label=color,passed=good,
                  got=got,expected=want,classifier_got=got_c,classifier_expected=want_c)
        cases.append(case)
        print(('PASS' if good else 'FAIL'),f'TARGET_CLASS={parameter}: classifier / legacy / bypass / support3 / direct stats')
        if not good:
            for p in range(4):
                if got[p]!=want[p]:print(' path',p,'got',got[p],'expected',want[p])
            if not ok:print(err)
    summary=dict(schema=1,kind='RTL hard expected values',cases=cases,
        passed=sum(c['passed'] for c in cases),total=len(cases),
        source_sha256={str(p.relative_to(args.rtl_root)) if p.parent==args.rtl_root else p.name:
            hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in srcs})
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(f"{summary['passed']}/{len(cases)} parameter configurations; 4 result paths x 5 frames each")
    return 0 if summary['passed']==len(cases) else 1

if __name__=='__main__':raise SystemExit(main())
