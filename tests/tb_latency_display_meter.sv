`timescale 1ns/1ps
module tb_latency_display_meter;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,vs=0,de=0,uf=0,ev=0,bad=0;reg[19:0]tick=1000;
 reg[84:0]tuple=0;
 wire[19:0]lat,mn,mx,age;wire[31:0]fid,sid;wire[15:0]n,err;wire[2:0]status;
 latency_display_meter #(.PIXELS(16))dut(clk,rst_n,tick,vs,de,uf,tuple,ev,bad,lat,mn,mx,age,fid,sid,n,err,status);
 task boundary;begin
  @(negedge clk);vs=1;repeat(8)@(negedge clk);vs=0;
 end endtask
 task image(input integer f,input integer t,input integer issue);
 begin
  @(negedge clk);tuple={32'd1,32'(f),20'(t),1'b1};ev=!ev;
  repeat(10)@(negedge clk);
  for(integer i=0;i<16;i=i+1)begin
   @(negedge clk);de=1;uf=(issue==1 && i==10);
  end
  @(negedge clk);de=0;uf=0;
  if(issue==2)bad=1;
  repeat(10)@(negedge clk);boundary();bad=0;
 end endtask
 initial begin
  repeat(6)@(negedge clk);rst_n=1;boundary();
  image(7,800,0);
  if(n!=1 || status!=1 || lat!=200 || fid!=7 || sid!=1 || mn!=200 || mx!=200)$fatal(1,"new %0d %0d",n,status);
  tick=1100;image(7,800,0);
  if(n!=1 || status!=2 || lat!=200 || age!=300)$fatal(1,"repeat counted as new");
  image(8,1000,1);
  if(n!=1 || status!=3 || err!=1)$fatal(1,"underflow accepted");
  image(9,1000,2);
  if(n!=1 || status!=3 || err!=2)$fatal(1,"overwrite accepted");
  image(10,1000,0);
  if(n!=2 || mn!=100 || mx!=200 || lat!=100)$fatal(1,"recovery");
  image(7,800,0);
  if(n!=2 || status!=3 || err!=3)$fatal(1,"old identity counted a second time");
  // Missing frame association is invalid, not current/latest-slot guessing.
  repeat(16)begin @(negedge clk);de=1;end
  @(negedge clk);de=0;repeat(10)@(negedge clk);boundary();
  if(n!=2 || status!=3 || err!=4)$fatal(1,"unmatched accepted");
  // Modulo timestamp wrap is safe for a fresh, bounded-age tuple.
  tick=20;image(11,1048500,0);
  if(n!=3 || lat!=96 || mn!=96)$fatal(1,"tick wrap");
  $display("PASS display meter same-frame timestamps, NEW/REP, min/max, underflow/overwrite/unmatched, wrap");$finish;
 end
endmodule
