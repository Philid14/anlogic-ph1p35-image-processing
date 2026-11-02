// Exact per-clock metadata delay. Same CSI clock, no resettable payload RAM.
// Reset flushes the existing external valid/SOF/last pipeline; stale RAM words
// cannot accompany an accepted beat. Handles arbitrary SOF spacing/data.
module inspection_config_delay #(parameter TAP=25,DEPTH=27)(
 input clk,rst_n,input[22:0]data,
 output reg[22:0]first,output[22:0]spatial,output[22:0]final_data);
 reg[4:0]wp;wire[4:0]rp=wp-(TAP-1);
 wire[31:0]read_data;
 always @(posedge clk or negedge rst_n)if(!rst_n)wp<=0;else wp<=wp+1'b1;
 always @(posedge clk)first<=data;
 PH1P_LOGIC_ERAM #(.DATA_WIDTH_A(32),.DATA_WIDTH_B(32),.ADDR_WIDTH_A(9),.ADDR_WIDTH_B(9),
 .DATA_DEPTH_A(512),.DATA_DEPTH_B(512),.MODE("DP"),.CLKMODE("SYNC"),.REGMODE_A("NOREG"),.REGMODE_B("NOREG"),
 .INIT_FILE("NONE"),.FILL_ALL("NONE"),.FORCE_KEEP("ON")) u_delay(
 .clka(clk),.cea(rst_n),.ocea(1'b1),.addra({4'd0,wp}),.dia({9'd0,data}),.wea(1'b1),.rsta(1'b0),.bea(1'b1),.doa(),
 .clkb(clk),.ceb(rst_n),.oceb(1'b1),.addrb({4'd0,rp}),.dib(32'd0),.web(1'b0),.rstb(1'b0),.beb(1'b1),.dob(read_data),
 .ecc_sbiterrinj(1'b0),.ecc_dbiterrinj(1'b0),.ecc_sbiterr(),.ecc_dbiterr());
 assign spatial=read_data[22:0];
 generate if(DEPTH>TAP)begin:g_tail
  reg[22:0]tail[0:DEPTH-TAP-1];integer i;
  always @(posedge clk)begin
   tail[0]<=spatial;
   for(i=1;i<DEPTH-TAP;i=i+1)tail[i]<=tail[i-1];
  end
  assign final_data=tail[DEPTH-TAP-1];
 end else begin:g_equal assign final_data=spatial;end endgenerate
endmodule
