"""Real vendor SP read-before-write compared to independent register delays."""
import json
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/latency_performance/payload'
def main():
    log=simulate(OUT,'tb_inspection_payload_delay',[
        ROOT/'tests/tb_inspection_payload_delay.sv',HDL/'vision/inspection_payload_delay.v'],eram=True)
    assert 'PASS exact SP payload delays' in log
    (OUT/'console.txt').write_text(log)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,native=True,delays=[21,24,26]))+'\n')
    print(log[-300:])
if __name__=='__main__':main()
