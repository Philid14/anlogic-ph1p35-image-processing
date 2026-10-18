`timescale 1ns/1ps
// All observers share the MIPI byte clock. Separate SOF collectors preserve
// delayed metadata. Atomic panel publishes the previously completed collectors,
// normally two capture frames old; no combinational video/control feedback.
module probe_stream_monitor #(parameter IMG_WIDTH=1280,IMG_HEIGHT=720,SEQ_BITS=16)(
 input clk,rst_n,iv,iu,il,ev,eu,pv,pu,
 input [95:0] edge_rgb,input [7:0] edge_threshold,
 input [1:0] fifo_sticky,
 input [1:0] fifo_armed,
 output reg [319:0] panel
);
 localparam GROUPS=IMG_WIDTH/4,BEATS=GROUPS*IMG_HEIGHT,WORDS=BEATS*3/4;
 function [31:0] crc2;
  input[31:0] old;input[1:0] bits;
  reg[31:0] c;integer k;
  begin c=old;for(k=1;k>=0;k=k-1)c=(c[31]^bits[k])?{c[30:0],1'b0}^32'h04c11db7:{c[30:0],1'b0};crc2=c;end
 endfunction
 function[15:0] inc16;input[15:0]a;begin inc16=(&a)?a:a+1'b1;end endfunction
 reg seen_i,seen_e,seen_p,ready_i,ready_e,ready_p;
 reg[SEQ_BITS-1:0] seq_i,seq_e,seq_p,si,se,sp;
 reg[18:0] ic,ec,pc,isc,esc,psc;
 reg[9:0] line_beats,lines;
 reg[15:0] last_line,s_last_line,s_lines,lead,lead_hold,s_lead,bubbles,s_bubbles,line_errors,s_line_errors,phase_errors,s_phase_errors;
 reg waiting_first,prev_v,prev_l;reg[1:0] phase;
 reg[19:0] first_bad,s_first_bad;
 reg[31:0] crc,edge_crc,previous_crc;
 reg[7:0] eth,previous_th;
 reg previous_good;
 reg[15:0] changed,frame_bad;
 reg[7:0] sticky;
 wire[10:0] line_total={1'b0,line_beats}+iv;
 wire bubble=prev_v&&!iv&&!prev_l&&!il&&(line_beats>0)&&(line_beats<GROUPS);
 wire bad_phase=prev_v&&!iv&&(phase!=0);
 wire coherent=ready_i&&ready_e&&ready_p&&(si==se)&&(si==sp);
 wire bad_i=isc!=BEATS || s_lines!=IMG_HEIGHT || s_line_errors!=0;
 wire bad_p=psc!=WORDS;
 wire changed_now=seen_e && previous_good && ec==BEATS && previous_th==eth && previous_crc!=crc;
 wire[7:0] events={fifo_sticky,esc!=BEATS,s_phase_errors!=0,bad_p,s_bubbles!=0,bad_i,changed!=0};
 // Field order: row1 sequence, row2 IN, row3 PACK, row4 CRC,
 // row5 lines/last-line, row6 lead/bubbles, row7 line/phase errors,
 // row8 bad-frame/change counters, row9 flags/first-bad(valid)/readiness.
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   panel<=0;seen_i<=0;seen_e<=0;seen_p<=0;ready_i<=0;ready_e<=0;ready_p<=0;
   seq_i<=0;seq_e<=0;seq_p<=0;si<=0;se<=0;sp<=0;ic<=0;ec<=0;pc<=0;isc<=0;esc<=0;psc<=0;
   line_beats<=0;lines<=0;last_line<=0;s_last_line<=0;s_lines<=0;lead<=0;lead_hold<=0;s_lead<=0;
   bubbles<=0;s_bubbles<=0;line_errors<=0;s_line_errors<=0;phase_errors<=0;s_phase_errors<=0;
   waiting_first<=0;prev_v<=0;prev_l<=0;phase<=0;first_bad<=20'hfffff;s_first_bad<=20'hfffff;
   crc<=32'hffffffff;edge_crc<=0;previous_crc<=0;eth<=0;previous_th<=0;
   previous_good<=0;changed<=0;frame_bad<=0;sticky<=0;
  end else begin
   prev_v<=iv;prev_l<=il;
   if(iu)begin
    if(coherent)begin
     sticky<=sticky|events;
     if(bad_i||bad_p||esc!=BEATS)frame_bad<=inc16(frame_bad);
     panel<={32'h50524231,{{(32-SEQ_BITS){1'b0}},si},{13'd0,isc},{13'd0,psc},edge_crc,
       s_lines,s_last_line,s_lead,s_bubbles,s_line_errors,s_phase_errors,
       ((bad_i||bad_p||esc!=BEATS)?inc16(frame_bad):frame_bad),changed,sticky|events,s_first_bad,1'b0,fifo_armed,1'b1};
    end else panel[0]<=0; // explicitly not a valid measurement, never 'normal zero'
    if(seen_i)begin
     ready_i<=1;si<=seq_i;isc<=ic;s_lines<={6'd0,lines};s_last_line<=last_line;s_lead<=lead_hold;
     s_bubbles<=bubbles;s_line_errors<=line_errors;s_phase_errors<=phase_errors;s_first_bad<=first_bad;
    end
    seen_i<=1;seq_i<=seen_i?seq_i+1'b1:0;ic<=iv?1:0;
    line_beats<=iv?1:0;lines<=0;last_line<=0;lead<=0;lead_hold<=0;waiting_first<=!iv;
    bubbles<=0;line_errors<=0;phase_errors<=0;first_bad<=20'hfffff;phase<=iv?1:0;
   end else if(seen_i)begin
    if(iv)begin if(!(&ic))ic<=ic+1'b1;if(!(&line_beats))line_beats<=line_beats+1'b1;phase<=phase+1'b1;end
    else phase<=0;
    if(waiting_first)begin
     if(iv)begin lead_hold<=inc16(lead);waiting_first<=0;end
     else lead<=inc16(lead);
    end
    if(il)begin
     last_line<=line_total;
     if(line_total!=GROUPS)line_errors<=inc16(line_errors);
     if(!(&lines))lines<=lines+1'b1;
     line_beats<=0;
    end
    if(bubble)begin bubbles<=inc16(bubbles);if(first_bad==20'hfffff)first_bad<={lines,line_beats};end
    if(bad_phase)phase_errors<=inc16(phase_errors);
   end
   if(eu)begin
    if(seen_e)begin
     ready_e<=1;se<=seq_e;esc<=ec;edge_crc<=crc;
     if(changed_now)changed<=inc16(changed);
     previous_crc<=crc;previous_th<=eth;previous_good<=ec==BEATS;
    end
    seen_e<=1;seq_e<=seen_e?seq_e+1'b1:0;ec<=ev?1:0;
    crc<=ev?crc2(32'hffffffff,{edge_rgb[95],edge_rgb[47]}):32'hffffffff;
    eth<=edge_threshold;
   end else if(ev&&seen_e)begin if(!(&ec))ec<=ec+1'b1;crc<=crc2(crc,{edge_rgb[95],edge_rgb[47]});end
   if(pu)begin
    if(seen_p)begin ready_p<=1;sp<=seq_p;psc<=pc;end
    seen_p<=1;seq_p<=seen_p?seq_p+1'b1:0;pc<=pv?1:0;
   end else if(pv&&seen_p&&!(&pc))pc<=pc+1'b1;
  end
 end
endmodule

// Observer boot gate only. Bad/incomplete frames restart the three-frame wait;
// after arming, errors remain observable and do not disable the monitor.
module probe_capture_arm #(parameter WORDS=172800)(input clk,rst_n,v,u,output ready);
 reg[18:0] count;reg[1:0] complete;reg seen;
 assign ready=complete==3;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin count<=0;complete<=0;seen<=0;end
  else if(u)begin
   if(seen&&complete!=3)complete<=count==WORDS?complete+1'b1:2'd0;
   seen<=1;count<=v?19'd1:19'd0;
  end else if(v&&!(&count))count<=count+1'b1;
 end
endmodule
