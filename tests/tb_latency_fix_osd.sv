`timescale 1ns/1ps
module tb_latency_fix_osd;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,update=0;reg[11:0]x1=0,y1=0,x2=0,y2=0;
 wire hit;wire[23:0]color;
 latency_osd dut(clk,rst_n,update,20'd200,20'd123,20'd45678,20'd300,
  32'hdeadbeef,16'h0123,16'h0002,3'd1,x1,y1,x2,y2,hit,color,24'h12a534);
 always @(posedge clk)begin x2<=x1;y2<=y1;end
 integer out;string path;
 initial begin
  if(!$value$plusargs("OUT=%s",path))$fatal(1,"OUT required");
  out=$fopen(path,"w");
  repeat(8)@(negedge clk);rst_n=1;update=1;@(negedge clk);update=0;
  repeat(120)@(negedge clk);
  if(dut.bcd[0]!==24'h000200 || dut.bcd[1]!==24'h000123 ||
   dut.bcd[2]!==24'h045678 || dut.bcd[3]!==24'h000300)$fatal(1,"BCD conversion");
  for(integer y=16;y<96;y=y+1)for(integer x=256;x<640;x=x+1)begin
   @(negedge clk);x1=x;y1=y;@(posedge clk);#1;
   $fdisplay(out,"%0d",hit);
   if(hit && color!==24'h00e6ff)$fatal(1,"wrong color");
  end
  $fclose(out);$display("PASS latency OSD exact original glyph raster and serial decimal conversion");$finish;
 end
endmodule
