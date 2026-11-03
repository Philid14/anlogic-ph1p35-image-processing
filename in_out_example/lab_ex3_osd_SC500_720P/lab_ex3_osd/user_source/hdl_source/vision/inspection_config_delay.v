// Exact per-clock metadata delay. Same CSI clock, no resettable payload RAM.
// Reset flushes the existing external valid/SOF/last pipeline; stale RAM words
// cannot accompany an accepted beat. Handles arbitrary SOF spacing/data.
module inspection_config_delay #(parameter TAP=25,DEPTH=27)(
 input clk,rst_n,input[22:0]data,
 output reg[22:0]first,output[22:0]spatial,output[22:0]final_data);
 always @(posedge clk)first<=data;
 // Small, exact per-clock metadata shift. Deliberately trade a short23-bit
 // chain for scarce ERAM; payload/reset semantics stay identical.
 reg[22:0]pipe[0:TAP-1];integer p;
 always @(posedge clk)begin
  pipe[0]<=data;
  for(p=1;p<TAP;p=p+1)pipe[p]<=pipe[p-1];
 end
 assign spatial=pipe[TAP-1];
 generate if(DEPTH>TAP)begin:g_tail
  reg[22:0]tail[0:DEPTH-TAP-1];integer i;
  always @(posedge clk)begin
   tail[0]<=spatial;
   for(i=1;i<DEPTH-TAP;i=i+1)tail[i]<=tail[i-1];
  end
  assign final_data=tail[DEPTH-TAP-1];
 end else begin:g_equal assign final_data=spatial;end endgenerate
endmodule
