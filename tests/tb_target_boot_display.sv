`timescale 1ns/1ps
module tb_target_boot_display;
reg clk=0,rst_n=0;always #6.6665 clk=~clk;
reg [23:0] video_rgb=0;reg video_de=0,video_hs=0,video_vs=0;
wire [7:0] glyph_char;wire [3:0] glyph_row;wire [15:0] glyph_bits;
wire [23:0] out_rgb;wire out_de,out_hs,out_vs,display_enable,first_pixel;
wire [31:0] pixel_session,pixel_frame;
target_display_commit #(.PIPELINE_GLYPH(1),.BOOT_DIAG_ENABLE(1)) dut(
.clk(clk),.rst_n(rst_n),.now_tick(64'd0),.metadata_receive(1'b0),.metadata(506'd0),
.metadata_online(1'b0),.scan_fault(1'b1),.boot_diagnostics(96'h123456789abcdef013572468),
.video_rgb(video_rgb),.video_de(video_de),.video_hs(video_hs),.video_vs(video_vs),.blanking_start(1'b0),
.out_rgb(out_rgb),.out_de(out_de),.out_hs(out_hs),.out_vs(out_vs),.glyph_char(glyph_char),
.glyph_row(glyph_row),.glyph_bits(glyph_bits),.display_enable(display_enable),.first_pixel(first_pixel),
.pixel_session(pixel_session),.pixel_frame(pixel_frame));
osd_char_lib font(.I_char(glyph_char),.I_row(glyph_row),.O_row_bits(glyph_bits));
reg [7:0] gold_char;reg [3:0] gold_row;wire [15:0] gold_bits;
osd_char_lib reference_font(.I_char(gold_char),.I_row(gold_row),.O_row_bits(gold_bits));
string line0="C:1234  D:5678  R:9ABC                            ";
string line1="D:DEF0  C:1357  Q:2468                            ";
reg [26:0] expected=0;reg [23:0] gold_rgb;integer x,y,col,nwhite=0,checks=0;
initial begin
 repeat(4)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
 for(y=0;y<750;y=y+1)begin
  for(x=0;x<1650;x=x+1)begin
   video_de=x<1280 && y<720;video_hs=x>=1390 && x<1430;video_vs=y>=725 && y<730;
   video_rgb={y[7:0],x[7:0],8'h35};gold_rgb=video_rgb;gold_char=32;gold_row=0;
   if(video_de && x>=24 && x<888 && y>=680 && y<712)begin
    col=(x-24)/16;gold_char=y<696 ? line0.getc(col):line1.getc(col);gold_row=(y-680)%16;
    #0.01;gold_rgb=gold_bits[15-((x-24)%16)] ? 24'hfff200:24'h101010;
    if(gold_rgb==24'hfff200)nwhite=nwhite+1;
   end
   @(posedge clk);#0.1;checks=checks+1;
   if({out_rgb,out_de,out_hs,out_vs}!==expected)$fatal(1,"boot pixel/control mismatch x=%0d y=%0d got=%h expected=%h",x,y,{out_rgb,out_de,out_hs,out_vs},expected);
   if(display_enable || pixel_session!=0 || pixel_frame!=0)$fatal(1,"boot must not forge genuine FrameRef/visibility");
   expected={gold_rgb,video_de,video_hs,video_vs};@(negedge clk);
  end
 end
 if(nwhite<100)$fatal(1,"no independent boot text pixels");
 $display("PASS BOOT_DISPLAY checks=%0d visible_text_pixels=%0d no_metadata=1 scan_fault=1",checks,nwhite);$finish;
end
endmodule
