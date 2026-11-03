`timescale 1ns/1ps
module tb_ruler_cm;
reg clk=0;always #5 clk=~clk;
reg rn=0,v=0,u=0,l=0,en=0,req=0;reg[31:0]gray=0;
wire[10:0]span;wire ok;wire[2:0]status;
ruler_area_calibration #(.WIDTH(896),.HEIGHT(128),.X0(64),.Y0(32),.SEARCH_HEIGHT(48)) dut(
 .clk(clk),.rst_n(rn),.gray(gray),.valid(v),.user(u),.last(l),.enable(en),.request_toggle(req),.span(span),.calibrated(ok),.status(status));
integer f,rc,rr,vv,uu,ll,ee,rq,check,es,eo,et,checks=0,cycles=0;reg[31:0]data;reg[2047:0]path;
initial begin
 if(!$value$plusargs("STIM=%s",path))$fatal(1,"STIM");f=$fopen(path,"r");
 while(!$feof(f))begin
  rc=$fscanf(f,"%d %d %d %d %d %d %h %d %d %d %d\n",rr,vv,uu,ll,ee,rq,data,check,es,eo,et);
  if(rc==11)begin
   @(negedge clk);rn=rr;v=vv;u=uu;l=ll;en=ee;req=rq;gray=data;
   @(posedge clk);#1;cycles=cycles+1;
   if(check)begin
    if(ok!==eo[0] || status!==et[2:0] || (eo && span!==es))$fatal(1,"FAIL check%0d cycle%0d got%0d/%0d/%0d expect%0d/%0d/%0d",checks,cycles,span,ok,status,es,eo,et);
    checks=checks+1;
   end
  end else if(!$feof(f))$fatal(1,"parse");
 end
 $display("PASS cm ruler %0d checks %0d cycles: cm vs half/mm, average, bounds, geometry, retry",checks,cycles);$finish;
end
endmodule
