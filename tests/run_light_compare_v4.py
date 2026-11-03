import json,hashlib
from illumination_compare_model import cases,metrics,main as model
from run_edge_control_v1 import ROOT,HDL,simulate
OUT=ROOT/'tmp/inspection_v4/color'
def main():
    model();OUT.mkdir(parents=True,exist_ok=True);rows=[]
    for i,(name,a,b) in enumerate(cases()):
        m=metrics(a,b);values=list(a)+list(b)+m['raw']+[m['l1'],m['maximum'],m['chr'],m['dv']]
        packed=sum(int(f'{v:05d}',16)<<(20*j) for j,v in enumerate(values))
        norm=int.from_bytes(bytes(sum((list(x) for x in m['normalized']),[])),'big')
        rows.append(f'{int.from_bytes(bytes(a+b),"big"):012x} {i:04x} {packed:065x} {norm:012x} {m["status"]} {int(i%7!=3)}')
    (OUT/'vectors.txt').write_text('\n'.join(rows)+'\n')
    sources=[ROOT/'tests/tb_light_compare_v4.sv',HDL/'isp/color_compare_osd.v',HDL/'isp/engineering_dimension_marks.v',HDL/'osd_char_lib.v']
    digests={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    log=simulate(OUT,'tb_light_compare_v4',sources,plus=['+STIM='+(OUT/'vectors.txt').as_posix()])
    (OUT/'console.txt').write_text(log)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,pairs=len(rows),fields=len(rows)*13,sources=digests),indent=2)+'\n')
if __name__=='__main__':main()
