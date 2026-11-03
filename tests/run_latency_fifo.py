import json
from vision_sim import ROOT,HDL,simulate
IP=HDL.parent/'ip_source/w128_d512_fifo'
OUT=ROOT/'tmp/latency_performance/fifo'
def main():
    log=simulate(OUT,'tb_latency_tagged_fifo',[
        ROOT/'tests/tb_latency_tagged_fifo.sv',HDL/'vision/latency_tagged_fifo.v',
        IP/'w128_d512_fifo.v',IP/'soft_fifo_al_4057d6b76aa6.v'],eram=True)
    assert 'PASS tagged native FIFO' in log
    (OUT/'console.txt').write_text(log)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,native=True))+'\n')
    print(log[-500:])
if __name__=='__main__':main()
