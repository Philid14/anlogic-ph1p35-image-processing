"""Independent boundary/error tests for MAIN capture/journal/display adapters."""
import json,hashlib
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/latency_performance/units'
def main():
    results={}
    for name,rtl in [('capture_tag','latency_capture_tag.v'),('slot_journal','latency_slot_journal.v'),('display_meter','latency_slot_journal.v')]:
        src=[ROOT/f'tests/tb_latency_{name}.sv',HDL/'vision'/rtl]
        folder=OUT/name
        log=simulate(folder,'tb_latency_'+name,src)
        assert 'PASS ' in log
        (folder/'console.txt').write_text(log)
        results[name]=dict(passed=True,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src})
        print(name,log[log.index('# PASS '):].splitlines()[0],flush=True)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,cases=results),indent=2)+'\n')
if __name__=='__main__':main()
