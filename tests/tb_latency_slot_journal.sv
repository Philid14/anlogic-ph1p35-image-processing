`timescale 1ns/1ps
module tb_latency_slot_journal;
 reg clk=0;always #4 clk=~clk;
 reg rst_n=0,we=0,rden=0,rdv=0,full=0,sel=0,hb=0;
 reg[24:0]addr=0;reg[86:0]tag=0;reg[1:0]slot=0;
 wire[84:0]selected;wire toggle,bad;
 always #80 hb=~hb;
 latency_slot_journal #(.WORDS(8),.EXPIRE_CYCLES(500),.HEARTBEAT_TIMEOUT(100))
  dut(clk,rst_n,we,addr,tag,rden,rdv,full,sel,slot,hb,selected,toggle,bad);
 task write_frame(input integer s,input integer fid,input integer fault);
 begin
  for(integer i=0;i<8;i=i+1)begin
   @(negedge clk);we=1;addr=s*7000000+i*8;
   tag={32'd1,32'(fid),20'd100,(i==0),(i==7),(fault!=1)};
   if(fault==2 && i==4)addr=addr+8;
  end
  @(negedge clk);we=0;
 end endtask
 task select_frame(input integer s,input integer valid_expected,input integer fid);
 begin
  @(negedge clk);sel=1;slot=s;@(negedge clk);sel=0;
  if(selected[0]!==valid_expected)$fatal(1,"slot%0d valid%0d got%h",s,valid_expected,selected);
  if(valid_expected && selected[52:21]!==fid)$fatal(1,"identity %h",selected);
 end endtask
 initial begin
  repeat(8)@(negedge clk);rst_n=1;repeat(30)@(negedge clk);
  select_frame(0,0,0);
  write_frame(0,1,0);select_frame(0,1,1);
  if(bad)$fatal(1,"healthy selected read rejected");
  write_frame(0,2,0);if(!bad)$fatal(1,"overwrite lease not rejected");
  select_frame(0,1,2);
  write_frame(1,3,1);select_frame(1,0,0);
  write_frame(2,4,2);select_frame(2,0,0);
  write_frame(3,5,0);
  @(negedge clk);rden=1;@(negedge clk);rden=0;
  select_frame(3,0,0); // pre-reset old read still outstanding
  @(negedge clk);rdv=1;@(negedge clk);rdv=0;
  select_frame(3,1,5);
  repeat(1010)@(negedge clk);select_frame(3,0,0); // expires, no timestamp alias
  write_frame(0,6,0);@(negedge clk);full=1;@(negedge clk);full=0;
  select_frame(0,0,0);
  $display("PASS slot journal exact writes, errors, overwrites, pending reads, expiration, command full");$finish;
 end
endmodule
