`timescale 1ns/1ps
// One acquisition-frame RAW QUALITY mask. No recursive temporal feedback.
// Output=current OR (previous_raw AND current_gradient_support).
// DDR/HDMI repetitions never reach this block. SOF may precede valid.
// Two registers; no extra image-center displacement or backpressure.
module edge_temporal_hold #(parameter IMG_WIDTH=1280,IMG_HEIGHT=720)(
 input clk,rst_n,input[1:0] I_edge,I_support,input I_valid,I_user,I_last,
 input[7:0] I_threshold,output reg[1:0] O_edge,output reg O_valid,O_user,O_last
);
 localparam GROUPS=IMG_WIDTH/4,BEATS=GROUPS*IMG_HEIGHT,WORDS=(BEATS+7)/8;
 localparam CB=$clog2(BEATS+2),AB=(WORDS>1)?$clog2(WORDS):1;
 // Eight 2-bit beats per word: no read/write collision. Read only phase0,
 // write only phase7 (or a partial LAST word). Memory is not reset.
 (* ram_style="block" *) reg[15:0] history[0:WORDS-1];
 reg[15:0] old_word,pending;
 reg[CB-1:0] count;reg[10:0] line_pos,line_count;
 reg seen,bad,eligible,pending_eol;reg[7:0] frame_threshold;
 wire complete=seen&&!bad&&!pending_eol&&count==BEATS&&line_count==IMG_HEIGHT;
 wire new_eligible=complete&&frame_threshold==I_threshold;
 wire[CB-1:0] index=I_user?0:count;
 wire[AB-1:0] address=index>>3;
 wire[2:0] phase=index[2:0];
 wire[10:0] lx=I_user?0:line_pos;
 wire access_ok=I_valid&&(I_user||seen)&&index<BEATS;
 wire row_end=I_valid && lx==GROUPS-1;
 wire line_bad=I_last && !(row_end || (!I_user && pending_eol));
 wire format_bad=line_bad || (!I_user && pending_eol && I_valid && !I_last);
 wire use_history=(I_user?new_eligible:eligible)&&!format_bad&&index<BEATS;
 wire[15:0] assembled={I_edge,pending[15:2]};
 always @(posedge clk)begin
  if(access_ok)begin
   if(phase==0)old_word<=history[address];
   pending<=assembled;
   if(phase==7 || index==BEATS-1)history[address]<=assembled >> (2*(7-phase));
  end
 end
 reg[1:0] raw1,support1;reg[2:0] phase1;reg allow1,v1,u1,l1;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   count<=0;line_pos<=0;line_count<=0;seen<=0;bad<=0;eligible<=0;pending_eol<=0;frame_threshold<=0;
   raw1<=0;support1<=0;phase1<=0;allow1<=0;
   v1<=0;u1<=0;l1<=0;O_valid<=0;O_user<=0;O_last<=0;O_edge<=0;
  end else begin
   v1<=I_valid;u1<=I_user;l1<=I_last;
   raw1<=I_edge;support1<=I_support;phase1<=phase;allow1<=use_history;
   O_valid<=v1;O_user<=u1;O_last<=l1;
   O_edge<=v1 ? raw1 | ((old_word >> (2*phase1)) & support1 & {2{allow1}}):2'd0;
   if(I_user)begin
    seen<=1;bad<=format_bad;pending_eol<=row_end&&!I_last;eligible<=new_eligible;frame_threshold<=I_threshold;
    count<=I_valid?1:0;line_count<=I_last?1:0;
    line_pos<=I_valid?(GROUPS==1?0:1):0;
   end else if(seen)begin
    if(row_end)pending_eol<=!I_last;else if(I_last)pending_eol<=0;
    if(format_bad)begin bad<=1;eligible<=0;end
    if(I_valid)begin
     if(count<BEATS+1)count<=count+1'b1;
     if(line_pos==GROUPS-1)line_pos<=0;else line_pos<=line_pos+1'b1;
     if(count>=BEATS)begin bad<=1;eligible<=0;end
    end
    if(I_last)begin
     if(line_count<IMG_HEIGHT+1)line_count<=line_count+1'b1;
     if(format_bad || line_count>=IMG_HEIGHT)begin bad<=1;eligible<=0;end
    end
   end
  end
 end
endmodule
