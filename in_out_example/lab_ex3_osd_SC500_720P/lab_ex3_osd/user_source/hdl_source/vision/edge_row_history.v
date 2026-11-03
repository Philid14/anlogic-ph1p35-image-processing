`timescale 1ns/1ps
// Exact replacement of two synchronous old-data row arrays. No video stages
// added: read first/second histories at read_en; copy registered old row1 one
// clock later via independent row2 write port. Payload has no reset and remains
// protected by the algorithm's existing row/frame border masks.
module edge_row_history #(parameter MID_WIDTH=16,TOP_WIDTH=16)(
 input clk,input read_en,input[9:0]read_address,input[MID_WIDTH-1:0]data,
 input copy_en,input[9:0]copy_address,input[TOP_WIDTH-1:0]copy_data,
 output[MID_WIDTH-1:0]middle,output[TOP_WIDTH-1:0]top);
 PH1P_LOGIC_ERAM #(.DATA_WIDTH_A(MID_WIDTH),.DATA_WIDTH_B(MID_WIDTH),
  .ADDR_WIDTH_A(10),.ADDR_WIDTH_B(10),.DATA_DEPTH_A(1024),.DATA_DEPTH_B(1024),
  .MODE("SP"),.CLKMODE("ASYNC"),.REGMODE_A("NOREG"),.REGMODE_B("NOREG"),
  .WRITEMODE_A("READBEFOREWRITE"),.INIT_FILE("NONE"),.FILL_ALL("NONE"),.FORCE_KEEP("ON")) u_middle(
  .clka(clk),.cea(read_en),.ocea(1'b1),.addra(read_address),.dia(data),.wea(1'b1),
  .rsta(1'b0),.bea(1'b1),.doa(middle),
  .clkb(clk),.ceb(1'b0),.oceb(1'b0),.addrb(10'd0),.dib({MID_WIDTH{1'b0}}),.web(1'b0),
  .rstb(1'b0),.beb(1'b1),.dob(),.ecc_sbiterrinj(1'b0),.ecc_dbiterrinj(1'b0),.ecc_sbiterr(),.ecc_dbiterr());
 PH1P_LOGIC_ERAM #(.DATA_WIDTH_A(TOP_WIDTH),.DATA_WIDTH_B(TOP_WIDTH),
  .ADDR_WIDTH_A(10),.ADDR_WIDTH_B(10),.DATA_DEPTH_A(1024),.DATA_DEPTH_B(1024),
  .MODE("DP"),.CLKMODE("SYNC"),.REGMODE_A("NOREG"),.REGMODE_B("NOREG"),
  .INIT_FILE("NONE"),.FILL_ALL("NONE"),.FORCE_KEEP("ON")) u_top(
  .clka(clk),.cea(read_en),.ocea(1'b1),.addra(read_address),.dia({TOP_WIDTH{1'b0}}),.wea(1'b0),
  .rsta(1'b0),.bea(1'b1),.doa(top),
  .clkb(clk),.ceb(copy_en),.oceb(1'b1),.addrb(copy_address),.dib(copy_data),.web(1'b1),
  .rstb(1'b0),.beb(1'b1),.dob(),.ecc_sbiterrinj(1'b0),.ecc_dbiterrinj(1'b0),.ecc_sbiterr(),.ecc_dbiterr());
endmodule
