`timescale 1ns/1ps
module tb_edge_center_pair_delay;
 parameter W=64,H=24,BORDER=6;
 reg clk=0,rst=0,v=0,u=0,l=0;reg[1:0] data=0;
 wire[1:0] od;always #5 clk=~clk;
 edge_center_pair_delay #(.IMG_WIDTH(W),.IMG_HEIGHT(H),.INPUT_BORDER(BORDER)) dut(clk,rst,data,v,u,l,od);
 reg[1023:0] name;integer f,rc,iv,iu,il,d,e,cycles=0;reg[2:0] vp=0;reg[1:0] expected[0:2];
 initial begin
  expected[0]=0;expected[1]=0;expected[2]=0;
  if(!$value$plusargs("STIM=%s",name))$fatal(1,"STIM");f=$fopen(name,"r");
  repeat(4)@(negedge clk);rst=1;
  while(!$feof(f))begin
   rc=$fscanf(f,"%d %d %d %d %d\n",iv,iu,il,d,e);
   if(rc==5)begin
    @(negedge clk);v=iv;u=iu;l=il;data=d;@(posedge clk);#1;
    vp={vp[1:0],iv[0]};expected[2]=expected[1];expected[1]=expected[0];expected[0]=e;
    if(vp[2] && od!==expected[2])$fatal(1,"confidence center cycle%0d got%0d expected%0d",cycles,od,expected[2]);
    cycles=cycles+1;
   end
  end
  $display("PASS confidence centers width=%0d cycles=%0d",W,cycles);$finish;
 end
endmodule
