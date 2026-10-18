`timescale 1ns/1ps
module tb_probe_fifo_events;
 reg clk=0,rst=0,sof=0,valid=0,vs=0,rd=0,capture_ready=0;
 always #5 clk=~clk;
 wire oflow,uflow,wa,ra;
 video_in #(.PROBE_ENABLE(1)) vin(.I_rst_n(rst),.I_camera_clk(clk),.I_camera_frame_start(sof),.I_camera_valid(valid),.I_camera_data(128'd0),
  .I_mipi_rx_error(1'b0),.I_ddr_clk(clk),.I_display_pause(1'b0),.I_video_out_rd_busy(1'b0),.I_ddr_user_ready(1'b0),.O_probe_overflow(oflow),.O_probe_armed(wa));
 video_out #(.PROBE_ENABLE(1)) vout(.I_rst_n(rst),.I_ddr_clk(clk),.I_video_in_wr_busy(1'b0),.I_video_out_rp(2'b0),.I_ddr_user_ready(1'b0),
  .I_ddr_user_rd_valid(1'b0),.I_ddr_user_rd_data(128'd0),.I_dsi_clk(clk),.I_video_vsync(vs),.I_video_rd_en(rd),.I_probe_capture_ready(capture_ready),.O_probe_underflow(uflow),.O_probe_armed(ra));
 initial begin
  repeat(8)@(negedge clk);rst=1;
  rd=1;vout.U_w128_d512_fifo.test_empty=1;
  repeat(4)@(negedge clk);rd=0;
  if(uflow!==0||ra!==0||wa!==0)$fatal(1,"FAIL warmup not distinguished");
  @(negedge clk);sof=1;
  @(negedge clk);sof=0;
  repeat(35)@(negedge clk);
  vin.U_w128_d512_fifo.test_full=1;valid=1;
  repeat(3)@(negedge clk);valid=0;
  if(oflow!==1||wa!==1)$fatal(1,"FAIL actual write-full observer");
  // Several HDMI refreshes BEFORE the camera is ready must remain unmeasured.
  repeat(3)begin vs=1;rd=1;repeat(3)@(negedge clk);vs=0;repeat(35)@(negedge clk);end
  rd=0;if(uflow!==0||ra!==0)$fatal(1,"FAIL pre-camera false underflow");
  capture_ready=1;repeat(5)@(negedge clk);
  vs=1;repeat(3)@(negedge clk);vs=0;repeat(35)@(negedge clk);
  vs=1;repeat(3)@(negedge clk);vs=0;repeat(35)@(negedge clk);
  vout.U_w128_d512_fifo.test_empty=1;rd=1;
  repeat(5)@(negedge clk);rd=0;
  if(uflow!==1||ra!==1)$fatal(1,"FAIL actual read-empty observer");
  rst=0;@(negedge clk);if(oflow!==0||uflow!==0)$fatal(1,"FAIL reset sticky");
  $display("PASS actual video_in/out FIFO event taps, local sticky/reset; behavioral FIFO flags, no vendor PHY");$finish;
 end
endmodule
module tb_probe_capture_arm;
 reg clk=0,rst=0,v=0,u=0;always #5 clk=~clk;wire ready;
 probe_capture_arm #(.WORDS(4)) dut(.clk(clk),.rst_n(rst),.v(v),.u(u),.ready(ready));
 integer f,k;
 initial begin
  repeat(4)@(negedge clk);rst=1;
  for(f=0;f<7;f=f+1)begin
   @(negedge clk);u=1;v=0;@(posedge clk);#1;
   if(f<6 && ready!==0)$fatal(1,"FAIL premature capture arm %0d",f);
   if(f==6 && ready!==1)$fatal(1,"FAIL capture arm after three consecutive full frames");
   @(negedge clk);u=0;
   for(k=0;k<(f==2?3:4);k=k+1)begin v=1;@(negedge clk);end
   v=0;repeat(4)@(negedge clk);
  end
  rst=0;@(negedge clk);if(ready!==0)$fatal(1,"FAIL arm reset");
  $display("PASS actual capture arm: incomplete restarts wait, three complete frames, reset");$finish;
 end
endmodule
module w128_d512_fifo(input rst,clkw,we,input[127:0]di,output[8:0]wrusedw,output afull,full_flag,
 input clkr,re,output[127:0]dout,output[8:0]rdusedw,output valid,empty_flag,aempty);
 reg test_full=0,test_empty=0;
 assign wrusedw=0;assign rdusedw=0;assign afull=0;assign full_flag=test_full;
 assign dout=0;assign valid=0;assign empty_flag=test_empty;assign aempty=0;
endmodule
