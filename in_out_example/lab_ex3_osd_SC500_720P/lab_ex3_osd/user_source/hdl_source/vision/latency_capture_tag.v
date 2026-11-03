`timescale 1ns/1ps
// MAIN observational adapter. Tag bits: {session32,frame32,tick20,first,last,good}.
// The complete tag travels IN THE SAME FIFO WORD as its 128-bit RGB payload.
// No data/valid/control feedback to the video path. Clock frequency is configured,
// not physically calibrated. Tick quantization is 10us at 75MHz (DIVIDER=750).
module latency_timebase #(parameter DIVIDER=750)(
 input clk,rst_n,output reg[19:0] tick,output reg[19:0] gray);
 reg[$clog2(DIVIDER)-1:0] divide;
 wire[19:0] next_tick=tick+1'b1;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin divide<=0;tick<=0;gray<=0;end
  else if(divide==DIVIDER-1)begin
   divide<=0;tick<=next_tick;gray<=(next_tick>>1)^next_tick;
  end else divide<=divide+1'b1;
 end
endmodule

module latency_capture_tag #(parameter WIDTH=1280,HEIGHT=720)(
 input clk,rst_n,input[19:0] tick_gray,
 input raw_valid,raw_user,raw_last,raw_error,
 input packed_valid,packed_user,fifo_full,
 output[86:0] tag,output reg[7:0] diagnostic);
 localparam GROUPS=WIDTH/4,WORDS=WIDTH*HEIGHT*3/16;
 // Only the registered Gray timebase crosses domains. All tag fields are then
 // captured in this clock domain and cross with their actual pixel FIFO word.
 (* async_reg="true" *)reg[19:0] time_sync1,time_sync2;
 wire[19:0] source_tick;
 genvar k;
 generate for(k=0;k<20;k=k+1)begin:g_decode
  assign source_tick[k]=^time_sync2[19:k];
 end endgenerate
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin time_sync1<=0;time_sync2<=0;end
  else begin time_sync1<=tick_gray;time_sync2<=time_sync1;end
 end
 reg[83:0] source_key;
 reg source_armed,source_started,source_done,source_bad,identity_exhausted;
 reg[10:0] rx;reg[9:0] ry;
 wire raw_first=raw_valid && (raw_user || source_armed);
 wire[10:0] x_now=raw_first?0:rx;
 wire[9:0] y_now=raw_first?0:ry;
 // PHY acquisition errors outside this RAW frame do not belong to its
 // already-completed pixels. Active-frame errors remain hard rejection.
 wire frame_raw_error=raw_error && (raw_first || (source_started && !source_done));
 reg lane_bad,shape_bad;
 wire raw_shape_ok=raw_last==(x_now==GROUPS-1);
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   source_key<={32'd0,32'hffffffff,20'd0};
   source_armed<=0;source_started<=0;source_done<=0;source_bad<=1;lane_bad<=0;shape_bad<=0;
   identity_exhausted<=0;rx<=0;ry<=0;
  end else begin
   if(raw_user)begin
    source_armed<=1;source_started<=0;source_done<=0;source_bad<=0;lane_bad<=0;shape_bad<=0;
    rx<=0;ry<=0;
   end
   if(frame_raw_error)begin source_bad<=1;lane_bad<=1;end
   if(raw_valid)begin
    if(raw_first)begin
     source_armed<=0;source_started<=1;source_done<=0;
     source_bad<=raw_error || !raw_shape_ok || identity_exhausted;
     lane_bad<=raw_error;shape_bad<=!raw_shape_ok;
     source_key[19:0]<=source_tick;
     if(source_key[51:20]==32'hffffffff)begin
      source_key[51:20]<=0;source_key[83:52]<=source_key[83:52]+1'b1;
      if(source_key[83:52]==32'hffffffff)identity_exhausted<=1;
     end else source_key[51:20]<=source_key[51:20]+1'b1;
    end else if(!source_started || source_done || !raw_shape_ok)begin source_bad<=1;shape_bad<=1;end
    if(x_now==GROUPS-1)begin
     rx<=0;
     if(y_now==HEIGHT-1)begin source_done<=1;ry<=0;end
     else ry<=y_now+1'b1;
    end else begin rx<=x_now+1'b1;ry<=y_now;end
   end
  end
 end
 reg packed_armed,packed_started,packed_bad;
 reg[17:0] word_count;
 wire first_word=packed_valid && (packed_user || packed_armed);
 wire last_word=packed_valid && !first_word && word_count==WORDS-1;
 // Exact word count + source geometry + matching source identity. Extra words
 // carry no FIRST and invalidate the DDR journal rather than aliasing a frame.
 wire qualified=source_started && !source_bad && !frame_raw_error && !identity_exhausted &&
  !fifo_full && !packed_bad && source_done && packed_started;
 // Source key is held through the packed frame. If a premature next RAW SOF
 // changes it, the DDR journal's per-word identity check rejects that frame.
 assign tag={source_key,first_word,last_word,qualified};
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   packed_armed<=0;packed_started<=0;packed_bad<=1;word_count<=0;diagnostic<=0;
  end else begin
   if(last_word)diagnostic<={identity_exhausted,fifo_full,!packed_started,packed_bad,!source_done,!source_started,shape_bad,lane_bad|frame_raw_error};
   if(packed_user)begin packed_armed<=1;packed_started<=0;packed_bad<=0;word_count<=0;end
   if(packed_valid && fifo_full)packed_bad<=1;
   if(packed_valid)begin
    if(first_word)begin
     packed_armed<=0;packed_started<=1;word_count<=1;
     packed_bad<=!source_started || source_bad || identity_exhausted || fifo_full;
    end else begin
     if(!packed_started || word_count>=WORDS)packed_bad<=1;
     if(word_count<WORDS)word_count<=word_count+1'b1;
    end
   end
  end
 end
endmodule
