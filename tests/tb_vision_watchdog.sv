`timescale 1ns/1ps
module tb_vision_watchdog;
reg clk=0;always #5 clk=~clk;
reg rn=0,toggle=0;
wire[23:0]out;wire[15:0]font;
hdmi_mixer #(.VISION_WATCHDOG(1),.STALE_CYCLES(20)) dut(
 .I_clk(clk),.I_rst_n(rn),.I_capture_toggle(toggle),.I_video_vsync(1'b0),.I_video_hsync(1'b0),
 .I_video_de(1'b0),.I_video_user(1'b0),.I_video_last(1'b0),.I_debug_status(4'hf),
 .I_video_rd_data(24'h123456),.O_hdmi_data(out));
reg[3:0]row=0;osd_char_lib reference_font(.I_char(8'h56),.I_row(row),.O_row_bits(font));
integer x,y;
initial begin
 repeat(4)@(negedge clk);rn=1;repeat(3)@(negedge clk);
 if(!dut.video_stale)$fatal(1,"FAIL startup not stale");
 toggle=1;repeat(5)@(negedge clk);
 if(dut.video_stale)$fatal(1,"FAIL source heartbeat not received");
 repeat(25)@(negedge clk);
 if(!dut.video_stale)$fatal(1,"FAIL stalled source not detected");
 force dut.S_video_de_2d=1;
 for(y=0;y<16;y=y+1)begin
  row=y;force dut.S_y_2d=680+y;
  for(x=0;x<16;x=x+1)begin
   force dut.S_x_2d=32+x;#1;
   if(dut.S_osd_hit!==font[15-x] || (font[15-x] && dut.S_osd_color!==24'hff4040))$fatal(1,"FAIL stale glyph");
  end
 end
 release dut.S_video_de_2d;release dut.S_y_2d;release dut.S_x_2d;
 toggle=0;repeat(5)@(negedge clk);
 if(dut.video_stale)$fatal(1,"FAIL source resume did not clear");
 rn=0;repeat(3)@(negedge clk);rn=1;repeat(3)@(negedge clk);
 if(!dut.video_stale)$fatal(1,"FAIL reset age invalidation");
 $display("PASS source heartbeat synchronizer, stale timeout/resume/reset and exact warning glyph");$finish;
end
endmodule
