"""Compare every public ledger output to the frozen implementation, full scale."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
HDL=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--words',type=int,default=172800);a=ap.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    rel=(HDL/'target/frame_transaction_ledger.v').relative_to(ROOT).as_posix()
    ref=subprocess.check_output(['git','show','4cc38ed:'+rel],cwd=ROOT).decode()
    rp=a.out/'ledger_reference.v';rp.write_text(ref.replace('module frame_transaction_ledger #(','module ledger_reference #(',1))
    header=ref.split(')(\n',1)[1].split('\n);',1)[0]
    header=re.sub(r'//[^\n]*','',header);ports=[];direction=None;width=''
    for token in header.split(','):
        token=token.strip();m=re.match(r'(input|output)\s+(?:(?:reg|wire)\s+)?(\[[^]]+\])?\s*(\w+)$',token)
        if m:direction,width,name=m[1],m[2] or '',m[3]
        else:
            assert re.fullmatch(r'\w+',token),token
            name=token
        ports.append((direction,width,name))
    outputs=[(w,n) for d,w,n in ports if d=='output']
    decl='\n'.join('wire '+w+' ref_'+n+';' for w,n in outputs)
    conn=','.join('.'+n+'('+('ref_'+n if d=='output' else n)+')' for d,w,n in ports)
    gold='{'+','.join('ref_'+n for w,n in outputs)+'}';dut='{'+','.join(n for w,n in outputs)+'}'
    text=(ROOT/'tests/tb_frame_transaction_ledger.sv').read_text()
    text=text.replace('    integer checks=0;',decl+'\nledger_reference #(.WORDS(FRAME_WORDS),.ANNOT_W(ANNOT_W)) ref_dut('+conn+');\ninteger gold_cycles=0;\nalways @(posedge clk) begin #2; if(rst_n) begin gold_cycles=gold_cycles+1; if('+dut+' !== '+gold+') $fatal(1,"ledger outputs differ from frozen reference"); end end\n    integer checks=0;')
    text=text.replace('$display("PASS FRAME_LEDGER checks=%0d",checks);','$display("PASS LEDGER_EQUIVALENCE checks=%0d cycles=%0d",checks,gold_cycles);')
    tb=a.out/'tb.sv';tb.write_text(text)
    sources=[tb,rp,a.source.resolve()];hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    commands=[['C:/iverilog/bin/iverilog.exe','-g2012','-s','tb_frame_transaction_ledger',f'-Ptb_frame_transaction_ledger.FRAME_WORDS={a.words}','-Ptb_frame_transaction_ledger.ANNOT_W=152','-o',str(a.out/'test.vvp'),*map(str,sources)],['C:/iverilog/bin/vvp.exe',str(a.out/'test.vvp')]]
    for i,cmd in enumerate(commands):
        r=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        (a.out/f'stage_{i}.txt').write_bytes(r.stdout);assert r.returncode==0,(i,r.stdout[-1500:])
    assert b'PASS LEDGER_EQUIVALENCE' in r.stdout
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    (a.out/'summary.json').write_text(json.dumps(dict(passed=True,reference_commit='4cc38ed',words=a.words,source_sha256=hashes),indent=2)+'\n')
    print(r.stdout.decode())
if __name__=='__main__':main()
