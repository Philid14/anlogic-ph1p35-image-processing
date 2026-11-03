`timescale 1ns/1ps
// Same official FIFO core, reset, pointer width, thresholds and latency as the
// existing RGB FIFO. Wider words attach metadata without a second set of CDC
// pointers or any change to the 128-bit data sent to DDR.
module latency_tagged_fifo(
 input rst,clkw,clkr,we,re,input[127:0] data,input[86:0] tag,
 output[127:0] out_data,output[86:0] out_tag,
 output full,output[8:0] rdused);
 soft_fifo_al_4057d6b76aa6 #(
  .DATA_WIDTH_W(215),.DATA_WIDTH_R(215),.ADDR_WIDTH_W(9),.ADDR_WIDTH_R(9),
  .AL_FULL_NUM(253),.AL_EMPTY_NUM(2),.SHOW_AHEAD_EN(0),.OUTREG_EN("NOREG")) u_fifo(
  .rst(rst),.clkw(clkw),.clkr(clkr),.we(we),.di({tag,data}),.re(re),
  .dout({out_tag,out_data}),.full_flag(full),.rdusedw(rdused),
  .valid(),.empty_flag(),.afull(),.aempty(),.wrusedw());
endmodule
