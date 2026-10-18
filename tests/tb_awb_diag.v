`timescale 1ns/1ps
module tb_awb_diag;
 reg clk=0,rst=0,v=0,u=0,l=0;reg[95:0] data=0;
 always #5 clk=~clk;
 wire ov,ou,ol,gv,gu,gl;wire[95:0] od,gd,pre;wire[39:0] gain;wire[143:0] stats;
 awb #(.IMG_WIDTH(1280),.IMG_HEIGHT(8)) dut(.I_clk(clk),.I_rst_n(rst),.I_tvalid(v),.I_tuser(u),.I_tlast(l),.I_tdata(data),.I_tready(),
  .O_tdata(od),.O_tvalid(ov),.O_tuser(ou),.O_tlast(ol),.O_tready(1'b1),.O_diag_pre(pre),.O_diag_gain(gain),.O_diag_stats(stats));
 awb_baseline #(.IMG_WIDTH(1280),.IMG_HEIGHT(8)) gold(.I_clk(clk),.I_rst_n(rst),.I_tvalid(v),.I_tuser(u),.I_tlast(l),.I_tdata(data),.I_tready(),
  .O_tdata(gd),.O_tvalid(gv),.O_tuser(gu),.O_tlast(gl),.O_tready(1'b1));
 integer f,y,x,k,checks=0,r,b;reg[23:0] p;
 always @(posedge clk)begin #1;
  if(rst)begin
   if({ov,ou,ol,od}!=={gv,gu,gl,gd})$fatal(1,"read-only taps changed formal AWB outputs");
   if(ov)begin
    for(k=0;k<4;k=k+1)begin
     p=pre[k*24+:24];r=(p[23:16]*gain[39:20])>>16;if(r>255)r=255;
     b=(p[7:0]*gain[19:0])>>16;if(b>255)b=255;
     if(od[k*24+:24]!=={8'(r),p[15:8],8'(b)})$fatal(1,"pre/gain/post alignment");
    end
    checks=checks+1;
   end
  end
 end
 task tick;input tv,tu,tl;
  begin @(negedge clk);v=tv;u=tu;l=tl;end
 endtask
 initial begin
  repeat(8)@(negedge clk);rst=1;
  for(f=0;f<14;f=f+1)begin
   tick(0,1,0);repeat(65)tick(0,0,0);
   for(y=0;y<8;y=y+1)begin
    for(x=0;x<320;x=x+1)begin tick(1,0,x==319);data={24'(32'h607068+x%19+f),24'hff8040,24'h444444,24'h687068};end
    repeat(80+y)tick(0,0,0);
   end
   repeat(120)tick(0,0,0);
  end
  if(checks!=14*2560)$fatal(1,"count %d",checks);
  $display("PASS AWB baseline equality, exact pre/gain/post beats=%0d; gains not frozen or reset",checks);$finish;
 end
endmodule
