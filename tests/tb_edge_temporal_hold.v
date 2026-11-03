`timescale 1ns/1ps
module tb_edge_temporal_hold;
 parameter W=64,H=16;
 reg clk=0,rst=0,v=0,u=0,l=0;reg[1:0] e=0,s=0;reg[7:0] th=60;
 wire[1:0] oe;wire ov,ou,ol;always #5 clk=~clk;
 edge_temporal_hold #(.IMG_WIDTH(W),.IMG_HEIGHT(H)) dut(clk,rst,e,s,v,u,l,th,oe,ov,ou,ol);
 reg[1023:0] name;integer fd,rc,iv,iu,il,ir,it,ie,is,ix,cycles=0;
 reg[1:0] expected1=0,expected2=0;reg[1:0] vp=0,up=0,lp=0;
 initial begin
  if(!$value$plusargs("STIM=%s",name))$fatal(1,"STIM");fd=$fopen(name,"r");
  repeat(4)@(negedge clk);
  while(!$feof(fd))begin
   rc=$fscanf(fd,"%d %d %d %d %d %d %d %d\n",ir,iv,iu,il,it,ie,is,ix);
   if(rc==8)begin
    @(negedge clk);rst=ir;v=iv;u=iu;l=il;th=it;e=ie;s=is;
    @(posedge clk);#1;
    if(!ir)begin vp=0;up=0;lp=0;expected1=0;expected2=0;end
    else begin vp={vp[0],iv[0]};up={up[0],iu[0]};lp={lp[0],il[0]};expected2=expected1;expected1=ix;end
    if({ov,ou,ol}!={vp[1],up[1],lp[1]} || (ov && oe!==expected2))
     $fatal(1,"temporal unit cycle%0d data%0d expected%0d meta%b%b%b",cycles,oe,expected2,ov,ou,ol);
    cycles=cycles+1;
   end
  end
  $display("PASS temporal history cycles=%0d",cycles);$finish;
 end
endmodule
