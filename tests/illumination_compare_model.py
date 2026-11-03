"""Camera RGB diagnostics, not a reflectance/colorimetric calibration."""
import json,random
from pathlib import Path

def metrics(a,b):
    sums=[sum(a),sum(b)]
    normalized=[tuple((v*255+s//2)//max(s,1) for v in rgb) for rgb,s in zip((a,b),sums)]
    raw=[abs(x-y) for x,y in zip(a,b)]
    chroma=max(abs(x-y) for x,y in zip(*normalized))
    dv=abs(max(a)-max(b))
    reliable=min(sums)>=96 and min(max(a),max(b))>=32 and max(*a,*b)<254
    status=3 if not reliable else 0 if max(raw)<=12 else 2 if chroma<=6 else 1
    return dict(raw=raw,l1=sum(raw),maximum=max(raw),normalized=normalized,chr=chroma,dv=dv,
                reliable=reliable,status=status,name=('MATCH','DIFF','LIGHT','CHECK')[status])

def cases():
    directed=[('same', (149,152,95),(149,152,95)),
      ('multiplicative_shading',(140,150,90),(168,180,108)),
      ('hue_change',(140,150,90),(170,110,108)),
      ('neutral_different_reflectance_ambiguous',(100,100,100),(180,180,180)),
      ('clipped',(240,190,90),(255,220,110)),('dark',(10,12,8),(30,35,20)),
      ('raw_boundary12',(100,100,100),(112,112,112)),('raw_boundary13',(100,100,100),(113,113,113)),
      ('red_vs_green',(200,30,30),(30,200,30)),('zero',(0,0,0),(0,0,0))]
    rng=random.Random(20261101)
    for i in range(160):
        a=tuple(rng.randint(40,165) for _ in range(3));b=tuple(round(v*1.3) for v in a)
        directed.append((f'shading_{i}',a,b))
    for i in range(160):directed.append((f'random_{i}',tuple(rng.randrange(256) for _ in range(3)),tuple(rng.randrange(256) for _ in range(3))))
    return directed

def main():
    result=[dict(case=n,ref=a,test=b,**metrics(a,b)) for n,a,b in cases()]
    shade=[x for x in result if x['case'].startswith('shading_')]
    assert all(x['chr']<=1 and x['name']=='LIGHT' for x in shade)
    assert result[2]['name']=='DIFF' and result[3]['name']=='LIGHT'
    assert result[4]['name']==result[5]['name']=='CHECK'
    p=Path('tmp/inspection_v4');p.mkdir(parents=True,exist_ok=True)
    (p/'COLOR_MODEL.json').write_text(json.dumps(dict(passed=True,cases=result,
        limitation='LIGHT does not distinguish illumination from different material lightness; no raw camera sequence or calibrated reflectance ground truth',
        comparisons={'raw_absolute':'all 160 controlled shading cases exceed MAX12',
                     'normalized':'160/160 have CHR<=1; retain raw mismatch as LIGHT, never automatically MATCH',
                     'offset_correction':'not selected: an unknown single-color sample cannot calibrate channel-dependent illumination'}),indent=2)+'\n')
    print('PASS',len(result),'color model pairs; multiplicative shading separated without rewriting raw RGB')

if __name__=='__main__':main()
