`timescale 1ns/1ps
module tb_temporal_capture;
 parameter W=64,H=32,RW=16,RH=8,RX=16,RY=12,N=2,INTEGRATION=0;
 reg clk=0,rst=0,v=0,u=0,l=0;reg[95:0] pre=0,post=0;reg[39:0] gains=0;reg[143:0] stats=0;
 always #5 clk=~clk;
 wire pv,pu;wire[127:0] pd;wire done;wire[31:0] first,id,rd;
 reg[14:0] addr=0;
 generate if(INTEGRATION)begin:g_isp
  isp_top #(.EDGE_CONTROL_ENABLE(1),.DENOISE_ENABLE(1),.NMS_ENABLE(1),.QUALITY_ENABLE(1),.PROBE_ENABLE(1),.TEMPORAL_ENABLE(1)) dut(
   .axi4s_video_aclk(clk),.I_rst_n(rst),.I_edge_config(9'd80),.I_probe_fifo_sticky(2'd0),.I_probe_fifo_armed(2'd3),
   .I_tlast(1'b0),.I_tuser(1'b0),.I_tvalid(1'b0),.I_tdata(40'd0),.I_tdest(10'd0),.O_tready(1'b1),
   .O_tdata(pd),.O_tvalid(pv),.O_tuser(pu),.O_tlast(),.I_tready());
  defparam dut.g_temporal.u_capture.WIDTH=W,dut.g_temporal.u_capture.HEIGHT=H,
   dut.g_temporal.u_capture.RW=RW,dut.g_temporal.u_capture.RH=RH,
   dut.g_temporal.u_capture.X0=RX,dut.g_temporal.u_capture.Y0=RY,dut.g_temporal.u_capture.FRAMES=N,dut.g_temporal.u_capture.WARMUP=1,
   dut.g_control.u_control.IMG_WIDTH=W,dut.g_control.u_control.IMG_HEIGHT=H;
  initial begin
   force dut.awb_O_tvalid=v;force dut.awb_O_tuser=u;force dut.awb_O_tlast=l;force dut.awb_O_tdata=post;
   force dut.diag_pre=pre;force dut.diag_gain=gains;force dut.diag_stats=stats;
   force dut.g_temporal.read_addr=addr;
  end
  assign done=dut.g_temporal.done;assign first=dut.g_temporal.first_frame;
  assign id=dut.g_temporal.capture_id;assign rd=dut.g_temporal.read_data;
 end else begin:g_unit
 temporal_roi_capture #(.WIDTH(W),.HEIGHT(H),.RW(RW),.RH(RH),.X0(RX),.Y0(RY),.FRAMES(N),.WARMUP(1)) dut(
  .clk(clk),.rst_n(rst),.v(v),.u(u),.l(l),.pv(pv),.pu(pu),.pre_rgb(pre),.post_rgb(post),.gains(gains),.stats(stats),
  .fifo_sticky(2'd0),.fifo_armed(2'd3),.read_addr(addr),.read_data(rd),.done(done),.first_frame(first),.capture_id(id));
 data_96bit_to_128bit pack(.I_clk(clk),.I_rst_n(rst),.I_96b_frame_start(u),.I_96b_valid(v),.I_96b_data(post),
  .O_128b_frame_start(pu),.O_128b_valid(pv),.O_128b_data(pd));
 end endgenerate
 integer f,y,x,k,r,g,b,ar,ab,pr,pb,j,fd;reg[1023:0] name;
 task tick;input tv,tu,tl;
  begin @(negedge clk);v=tv;u=tu;l=tl;end
 endtask
 initial begin
  if(!$value$plusargs("OUT=%s",name))$fatal(1,"output path");
  repeat(8)@(negedge clk);rst=1;
  for(f=0;f<N+2;f=f+1)begin
   ar=65536+f*512;ab=73728+f*256;gains={20'(ar),20'(ab)};
   stats={10'd0,1'b1,16'(f),21'd2048,32'(1000+f),32'(2000+f),32'(3000+f)};
   tick(0,1,0);repeat(64)tick(0,0,0);
   for(y=0;y<H;y=y+1)begin
    for(x=0;x<W/4;x=x+1)begin
     @(negedge clk);v=1;u=0;l=x==W/4-1;
     for(k=0;k<4;k=k+1)begin
      r=(f*13+y*3+x*4+k)%256;g=(f*7+y+x*8+k*2)%256;b=(f*11+y*2+x*3+k)%256;
      pr=(r*ar)>>16;if(pr>255)pr=255;pb=(b*ab)>>16;if(pb>255)pb=255;
      pre[95-k*24-:24]={8'(r),8'(g),8'(b)};post[95-k*24-:24]={8'(pr),8'(g),8'(pb)};
     end
    end
    repeat(8)tick(0,0,0);
   end
   repeat(100)tick(0,0,0);
  end
  if(!done || first!=1)$fatal(1,"capture complete %b %d",done,first);
  fd=$fopen(name,"w");
  for(j=0;j<N*(RW/4)*RH*3+N*16+16;j=j+1)begin
   @(negedge clk);addr=j;@(posedge clk);#1;$fdisplay(fd,"%08x",rd);
  end
  $fclose(fd);$display("PASS capture frames=%0d ROI=%0dx%0d id=%08x integration=%0d",N,RW,RH,id,INTEGRATION);$finish;
 end
endmodule
