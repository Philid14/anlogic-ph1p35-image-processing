`timescale 1ns/1ps
module tb_ruler_cm_full_roi;
reg clk=0;always #5 clk=~clk;
reg rn=0,v=0,u=0,l=0,en=1,req=0;reg[31:0]gray=0;
wire[10:0]span;wire ok;wire[2:0]status;
ruler_area_calibration dut(.clk(clk),.rst_n(rn),.gray(gray),.valid(v),.user(u),.last(l),.enable(en),.request_toggle(req),.span(span),.calibrated(ok),.status(status));
integer x,y,k,f,c,test_y,checks=0,cycles=0;
task tick;begin @(posedge clk);#1;cycles=cycles+1;@(negedge clk);end endtask
task frame;begin
 v=0;u=1;l=0;tick();u=0;
 repeat(18000)tick();
 for(y=0;y<720;y=y+1)begin
  for(x=0;x<1280;x=x+4)begin
   gray=32'he1e1e1e1;
   // Five or more complete centimeter lines at50px, near either ROI edge.
   if(y>=test_y && y<test_y+3)for(k=0;k<4;k=k+1)begin
    if(x+k>=263 && x+k<1018 && ((x+k-263)%50)==0)gray[31-k*8-:8]=25;
   end
   v=1;l=x==1276;tick();
  end
  v=0;l=0;tick();
 end
end endtask
initial begin
 repeat(4)tick();rn=1;tick();
 for(c=0;c<2;c=c+1)begin
  test_y=c==0?194:477;req=!req;v=0;u=0;tick();
  for(f=0;f<55;f=f+1)frame();
  u=1;tick();u=0;repeat(20000)tick();
  if(!ok || status!=3 || span!=500)$fatal(1,"FAIL full ROI case%0d span%0d status%0d",c,span,status);
  checks=checks+1;
 end
 $display("PASS full production720p/768x288 cm search, top and bottom placement, %0d checks %0d cycles",checks,cycles);$finish;
end
endmodule
