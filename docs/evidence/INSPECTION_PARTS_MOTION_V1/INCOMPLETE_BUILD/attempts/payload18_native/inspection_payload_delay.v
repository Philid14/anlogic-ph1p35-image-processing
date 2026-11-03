`timescale 1ns/1ps
// Exact per-CLOCK delay, not per-valid delay. Out equals shift-register stage
// DELAY: an input sampled at edge0 appears after edgeDELAY. No payload reset;
// the existing resettable valid pipeline flushes all stale words before use.
module inspection_payload_delay #(parameter WIDTH=32,DELAY=26)(
 input clk,rst_n,input[WIDTH-1:0] data,output[WIDTH-1:0] delayed);
 localparam AW=$clog2(DELAY);
 reg[AW-1:0] address;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)address<=0;
  else if(address==DELAY-1)address<=0;
  else address<=address+1'b1;
 end
 generate for(genvar s=0;s<(WIDTH+17)/18;s=s+1)begin:g_word
  wire[17:0] in_word,out_word;
  for(genvar b=0;b<18;b=b+1)begin:g_bit
   if(s*18+b<WIDTH)begin:g_live
    assign in_word[b]=data[s*18+b];assign delayed[s*18+b]=out_word[b];
   end else begin:g_pad assign in_word[b]=0;end
  end
  PH1P_LOGIC_ERAM #(.DATA_WIDTH_A(18),.DATA_WIDTH_B(18),.ADDR_WIDTH_A(10),.ADDR_WIDTH_B(10),
   .DATA_DEPTH_A(1024),.DATA_DEPTH_B(1024),.MODE("SP"),.CLKMODE("ASYNC"),
   .REGMODE_A("NOREG"),.REGMODE_B("NOREG"),.WRITEMODE_A("READBEFOREWRITE"),
   .INIT_FILE("NONE"),.FILL_ALL("NONE"),.FORCE_KEEP("ON")) u_delay(
   .clka(clk),.cea(rst_n),.ocea(1'b1),.addra({{(10-AW){1'b0}},address}),
   .dia(in_word),.wea(1'b1),.rsta(1'b0),.bea(1'b1),.doa(out_word),
   .clkb(clk),.ceb(1'b0),.oceb(1'b0),.addrb(10'd0),.dib(18'd0),.web(1'b0),
   .rstb(1'b0),.beb(1'b1),.dob(),.ecc_sbiterrinj(1'b0),.ecc_dbiterrinj(1'b0),
   .ecc_sbiterr(),.ecc_dbiterr());
 end endgenerate
endmodule
