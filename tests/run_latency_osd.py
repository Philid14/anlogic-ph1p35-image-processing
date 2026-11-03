import json,sys,shutil,hashlib
from vision_sim import ROOT,HDL,simulate
sys.path.insert(0,str(ROOT/'scripts'))
from generate_inspection_font import GLYPHS
OUT=ROOT/'tmp/latency_performance/osd'
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    shutil.copy2(HDL/'vision/latency_font.dath',OUT/'latency_font.dath')
    raster=OUT/'pixels.txt'
    log=simulate(OUT,'tb_latency_osd',[ROOT/'tests/tb_latency_osd.sv',HDL/'vision/latency_osd.v'],
                 plus=['+OUT='+raster.as_posix()],eram=True)
    rows=['LAT: 002.00MS  NEW','MIN: 001.23 MAX: 456.78',
          'F:DEADBEEF N:0123 E:0002','AGE: 003.00MS  10US HEX']
    expected=[]
    for y in range(64):
        line=rows[y//16].ljust(24);sy=y%16
        for x in range(384):
            c=line[x//16];sx=x%16
            ink=0
            if 1<=sy<15 and 3<=sx<13:
                ink=int(GLYPHS.get(c,['00000']*7)[(sy-1)//2][(sx-3)//2])
            expected.append(ink)
    actual=[int(v) for v in raster.read_text().split()]
    assert actual==expected,[(i,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b][:8]
    (OUT/'console.txt').write_text(log)
    inputs=[HDL/'vision/latency_font.dath',ROOT/'scripts/generate_inspection_font.py']
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,native=True,pixels=len(actual),rows=rows,
        sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}),indent=2)+'\n')
    print('PASS native OSD',len(actual),'pixels / original glyph reference / decimal units')
if __name__=='__main__':main()
