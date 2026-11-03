`timescale 1ns/1ps
module tb_latency_blanking;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,rv=0,ru=0,rl=0,re=0,pv=0,pu=0,full=0;
 reg[19:0] tick=100;wire[86:0]tag;
 latency_capture_tag #(.WIDTH(64),.HEIGHT(8)) dut(clk,rst_n,(tick>>1)^tick,rv,ru,rl,re,pv,pu,full,tag);
 integer n,j,frame=0;
 task raw_frame(input integer fault,input integer inline_sof);
 begin
  @(negedge clk);ru=1;rv=inline_sof;rl=0;re=0;
  @(negedge clk);ru=0;rv=0;
  for(n=inline_sof;n<128;n=n+1)begin
   @(negedge clk);rv=1;rl=n%16==15;re=(fault==1 && n==45);
   if(fault==2 && n==63)rl=0;
  end
  @(negedge clk);rv=0;rl=0;re=(fault==4);
 end endtask
 task packed_frame(input integer fault);
 begin
  @(negedge clk);pu=1;@(negedge clk);pu=0;
  for(j=0;j<96;j=j+1)begin
   // Read tag before the consuming edge: exactly how FIFO samples payload.
   @(negedge clk);pv=1;full=(fault==3 && j==7);#1;
   if(tag[86:55]!==32'd1 || tag[54:23]!==frame || tag[22:3]!==tick)
    $fatal(1,"Wrong identity/timestamp frame%0d tag%h",frame,tag);
   if(tag[2] !== (j==0) || tag[1] !== (j==95))$fatal(1,"Wrong boundaries %0d",j);
   if(j==95 && tag[0] !== (fault==0 || fault==4))$fatal(1,"Wrong qualification fault%0d tag%h",fault,tag);
   if(j%5==0)begin @(negedge clk);pv=0;full=0;end
  end
  @(negedge clk);pv=0;full=0;frame=frame+1;
 end endtask
 initial begin
  repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
  for(integer f=0;f<5;f=f+1)begin raw_frame(f,f%2);packed_frame(f);re=0;end
  // Frame-ID rollover issues a new session; no truncation of canonical fields.
  @(negedge clk);dut.source_key[83:20]=64'h00000006fffffffe;
  raw_frame(0,0);
  if(dut.source_key[83:20]!==64'h00000006ffffffff)$fatal(1,"pre-wrap");
  raw_frame(0,1);
  if(dut.source_key[83:20]!==64'h0000000700000000)$fatal(1,"session wrap");
  $display("PASS blanking error bounded to RAW acquisition; active errors still reject; capture tags early/inline SOF, geometry, source errors, overflow, bubbles, session rollover");$finish;
 end
endmodule
