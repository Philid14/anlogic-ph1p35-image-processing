`timescale 1ns/1ps
// Row1 read is retimed to G1/N1. At G2/N2, read-before-write row2 and register
// old row1. The stage2 window and total algorithm latency remain unchanged.
module edge_row_history #(parameter MID_WIDTH=16,TOP_WIDTH=16)(
 input clk,input read_en,input[9:0]read_address,input[MID_WIDTH-1:0]data,
 input copy_en,input[9:0]copy_address,input[TOP_WIDTH-1:0]copy_data,
 output reg[MID_WIDTH-1:0]middle,output[TOP_WIDTH-1:0]top,
 output[MID_WIDTH-1:0]early_middle);
 localparam BANKS=(MID_WIDTH+15)/16;
 wire[BANKS*16-1:0]write_mid=data,write_top=copy_data;
 wire[BANKS*16-1:0]old_mid,old_top;
 assign early_middle=old_mid[MID_WIDTH-1:0];
 assign top=old_top[TOP_WIDTH-1:0];
 always @(posedge clk)if(copy_en)middle<=early_middle;
 generate for(genvar b=0;b<BANKS;b=b+1)begin:g_bank
  PH1P_LOGIC_ERAM #(.DATA_WIDTH_A(16),.DATA_WIDTH_B(16),.ADDR_WIDTH_A(10),.ADDR_WIDTH_B(10),
   .DATA_DEPTH_A(1024),.DATA_DEPTH_B(1024),.MODE("DP"),.CLKMODE("SYNC"),
   .REGMODE_A("NOREG"),.REGMODE_B("NOREG"),.WRITEMODE_A("READBEFOREWRITE"),
   .WRITEMODE_B("READBEFOREWRITE"),.INIT_FILE("NONE"),.FILL_ALL("NONE"),.FORCE_KEEP("ON")) u_rows(
   .clka(clk),.cea(read_en),.ocea(1'b1),.addra({1'b0,read_address[8:0]}),
   .dia(write_mid[b*16+:16]),.wea(1'b1),.rsta(1'b0),.bea(1'b1),.doa(old_mid[b*16+:16]),
   .clkb(clk),.ceb(copy_en),.oceb(1'b1),.addrb({1'b1,copy_address[8:0]}),
   .dib(write_top[b*16+:16]),.web(1'b1),.rstb(1'b0),.beb(1'b1),.dob(old_top[b*16+:16]),
   .ecc_sbiterrinj(1'b0),.ecc_dbiterrinj(1'b0),.ecc_sbiterr(),.ecc_dbiterr());
 end endgenerate
endmodule
