`timescale 1ns/1ps
module tb_latency_tagged_fifo;
 reg cw=0,cr=0;always #7 cw=~cw;always #4 cr=~cr;
 reg rst=1,we=0,re=0;reg[127:0]data=0;reg[86:0]tag=0;
 wire[127:0]od,nd;wire[86:0]nt;wire of,nf,valid,empty;wire[8:0]onum,nnum;
 latency_tagged_fifo dut(rst,cw,cr,we,re,data,tag,nd,nt,nf,nnum);
 w128_d512_fifo old(.rst(rst),.clkw(cw),.clkr(cr),.we(we),.re(re),.di(data),
  .dout(od),.full_flag(of),.rdusedw(onum),.valid(valid),.empty_flag(empty));
 integer sent=0,checks=0,epoch=0,cycle=0;
 function[86:0] tag_for(input[127:0] d);
  tag_for={d[31:0],d[63:32],d[86:64]};
 endfunction
 always @(negedge cw)begin
  cycle=cycle+1;
  // Bursts, oversubscription (full), pauses, FIFO resets, asynchronous clocks.
  we=cycle%1800<1200 && cycle%7!=0 && !rst;
  data={32'(epoch),32'(cycle),32'(sent),32'(sent^32'h5aabccdd)};
  tag=tag_for(data);
  if(we && !of)sent=sent+1;
 end
 always @(negedge cr)re=!rst && cycle%1800>850 && cycle%5!=0;
 always @(posedge cw)begin
  #1;if(!rst && of!==nf)$fatal(1,"full flag changed");
 end
 always @(posedge cr)begin
  #1;
  if(!rst && onum!==nnum)$fatal(1,"read occupancy changed");
  if(!rst && valid)begin
   if(nd!==od || nt!==tag_for(od))$fatal(1,"metadata/data desync %h/%h tag%h",nd,od,nt);
   checks=checks+1;
  end
 end
 initial begin
  #200;rst=0;
  repeat(4)begin #40000;rst=1;epoch=epoch+1;#170;rst=0;end
  #40000;
  if(checks<1000)$fatal(1,"insufficient reads");
  $display("PASS tagged native FIFO bit-exact legacy data/flags and same-word metadata checks=%0d",checks);$finish;
 end
endmodule
