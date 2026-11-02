`timescale 1ns/1ps
module tb_measure_background_full;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,v=0,u=0,l=0,req=0,clear=0;
 reg[31:0]gray=0;reg[3:0]fb=0;wire[3:0]p;
 wire ov,ou,ol,applied,ready;wire[2:0]status;
 measure_background dut(.clk(clk),.rst_n(rst),.gray(gray),.fallback_pixels(fb),.valid(v),.user(u),.last(l),.bright(1'b0),
 .learn_enable(1'b1),.clear(clear),.request_toggle(req),.pixels(p),.out_valid(ov),.out_user(ou),.out_last(ol),.applied(applied),.ready(ready),.status(status));
 integer f,x,y,k,b,a,n=0;reg check_enabled=0;reg[31:0]g;reg[3:0]bin,ex,ex0;reg v0=0,u0=0,l0=0;
 task step;input vv,uu,ll;input[31:0]gg;input[3:0]bb,ee;
 begin
  @(negedge clk);v=vv;u=uu;l=ll;gray=gg;fb=bb;
  @(posedge clk);#1;
  if(ov!==v0||ou!==u0||ol!==l0)$fatal(1,"full BG metadata%0d",n);
  if(check_enabled&&ov&&p!==ex0)$fatal(1,"full BG data%0d got%h exp%h",n,p,ex0);
  v0=vv;u0=uu;l0=ll;ex0=ee;n=n+1;
 end endtask
 initial begin
  repeat(8)@(negedge clk);rst=1;req=1;repeat(4)step(0,0,0,0,0,0);
  for(f=0;f<4;f=f+1)begin
   check_enabled=f>=2;
   // Inline SOF on first valid pixel; no extra frame or coordinate shift.
   for(y=0;y<720;y=y+1)begin
    for(x=0;x<1280;x=x+4)begin
     g=0;bin=0;ex=0;
     if(f==3&&y==350&&x==0)clear=1;else clear=0;
     for(k=0;k<4;k=k+1)begin
      b=120+((x+k)/16+y/16)%80;a=b;
      if(f>=2&&x+k>=680&&x+k<820&&y>=260&&y<410)a=b+((x+k<750)?-25:25);
      g[31-k*8-:8]=a;bin[3-k]=a>=130;
      ex[3-k]=x>=256&&x<1024&&y>=160&&y<544?!(a!=b):bin[3-k];
     end
     step(1,x==0&&y==0,x==1276,g,bin,ex);
     if(x==100&&y%71==0)step(0,0,0,0,0,0);
    end
    step(0,0,0,0,0,0);
   end
  end
  repeat(4)step(0,0,0,0,0,0);
  if(ready)$fatal(1,"clear did not invalidate reference");
  $display("PASS 1280x720 inline SOF/gaps/all1152 cells/gradient reference, mixed polarities exact mask, mid-frame clear keeps current mask until SOF %0d cycles",n);$finish;
 end
endmodule
