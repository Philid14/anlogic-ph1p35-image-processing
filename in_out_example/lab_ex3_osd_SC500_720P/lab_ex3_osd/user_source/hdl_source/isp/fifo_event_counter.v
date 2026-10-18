`timescale 1ns/1ps
// Read-only camera-clock monitor: frames containing write/full events.
// First WARMUP acquisition frames and later frames have separate saturating
// counters. No control of FIFO writes, reset, arbitration or constraints.
module fifo_event_counter #(parameter WARMUP=600)(
 input clk,rst_n,sof,fifo_reset,write_valid,full,output reg [31:0] counts
);
 reg armed,event_in_frame;reg [9:0] frame_age;
 wire event_now=armed && !fifo_reset && write_valid && full;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin counts<=0;armed<=0;event_in_frame<=0;frame_age<=0;end
  else begin
   if(sof)begin
    if(armed && event_in_frame)begin
     if(frame_age<WARMUP)begin if(counts[31:16]!=16'hffff)counts[31:16]<=counts[31:16]+1'b1;end
     else begin if(counts[15:0]!=16'hffff)counts[15:0]<=counts[15:0]+1'b1;end
    end
    armed<=1;event_in_frame<=event_now;
    if(armed && frame_age<WARMUP)frame_age<=frame_age+1'b1;
   end else if(event_now)event_in_frame<=1;
  end
 end
endmodule
