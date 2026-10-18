`timescale 1ns/1ps
// One immutable burst. Capture at actual post-AWB valid beats; pre RGB and the
// gains used by the multiplier are aligned by read-only AWB taps. No backpressure.
module temporal_roi_capture #(
 parameter WIDTH=1280,HEIGHT=720,X0=576,Y0=344,RW=128,RH=32,FRAMES=8,WARMUP=600
)(
 input clk,rst_n,v,u,l,pv,pu,
 input[95:0] pre_rgb,post_rgb,input[39:0] gains,input[143:0] stats,
 input[1:0] fifo_sticky,fifo_armed,
 input[14:0] read_addr,output[31:0] read_data,
 output reg done,output reg[31:0] first_frame,output reg[31:0] capture_id
);
 localparam GROUPS=WIDTH/4,RG=RW/4,ROI_BEATS=RG*RH,RAW_DEPTH=FRAMES*ROI_BEATS;
 localparam META_BASE=RAW_DEPTH*3,GLOBAL_BASE=META_BASE+FRAMES*16,TOTAL=GLOBAL_BASE+16;
 function[31:0] crc96;
  input[31:0] c0;input[95:0] d;reg[31:0] c;integer k;
  begin c=c0;for(k=95;k>=0;k=k-1)c=(c[31]^d[k])?{c[30:0],1'b0}^32'h04c11db7:{c[30:0],1'b0};crc96=c;end
 endfunction
 // ROI beats are consecutive: parallel CRC has no video feedback. Its actual
 // resource/timing cost must be checked in the new full routed build.
 reg[95:0] raw_mem[0:RAW_DEPTH-1];
 reg[31:0] meta_mem[0:FRAMES*16-1];
 reg[95:0] raw_q;reg[31:0] meta_q;reg[14:0] addr_q;
 wire[12:0] raw_read=read_addr%RAW_DEPTH;
 always @(posedge clk)begin
  raw_q<=raw_mem[raw_read];meta_q<=meta_mem[read_addr% (FRAMES*16)];addr_q<=read_addr;
 end
 reg[31:0] global_word;
 always @*begin
  case(addr_q-GLOBAL_BASE)
   0:global_word=32'h54524f31;1:global_word=32'h00010000;2:global_word=first_frame;
   3:global_word=(RW<<16)|RH;4:global_word=(X0<<16)|Y0;5:global_word=FRAMES;
   6:global_word=ROI_BEATS;7:global_word=WARMUP;8:global_word=RAW_DEPTH*3;
   9:global_word=META_BASE;10:global_word=FRAMES*16;11:global_word=GLOBAL_BASE;
   12:global_word=TOTAL;13:global_word=WIDTH;14:global_word=HEIGHT;15:global_word=capture_id;
   default:global_word=0;
  endcase
 end
 assign read_data=addr_q<RAW_DEPTH?raw_q[31:0]:
  addr_q<RAW_DEPTH*2?raw_q[63:32]:addr_q<META_BASE?raw_q[95:64]:
  addr_q<GLOBAL_BASE?meta_q:global_word;
 reg seen,collect;reg[3:0] next_slot,slot;
 reg[31:0] seq,current_seq;
 reg[31:0] cycle_count,current_cycle;
 reg[10:0] x,y,lines,line_beats,last_line;
 reg[18:0] count,pack_count;
 reg[15:0] bubbles,line_errors,phase_errors,roi_count;
 reg[1:0] phase;reg prev_v,prev_l;
 reg[31:0] pre_crc,post_crc;
 reg[31:0] burst_crc;
 reg gain_changed;
 reg[39:0] frame_gains;reg[143:0] frame_stats;
 wire[10:0] xn=u?0:x,yn=u?0:y;
 wire roi=v && xn>=X0/4 && xn<X0/4+RG && yn>=Y0 && yn<Y0+RH;
 wire[12:0] write_address=slot*ROI_BEATS+(yn-Y0)*RG+xn-X0/4;
 wire[11:0] line_total={1'b0,line_beats}+v;
 reg queued;reg[3:0] queued_slot;
 reg[31:0] qs,qpcrc,qocrc,qcount,qline,qerrors,qroi,qpack,qfifo,qcycle;
 reg[39:0] qgains;reg[143:0] qstats;
 reg writing;reg[3:0] mw;
 reg[31:0] meta_word;
 always @*begin
  case(mw)
   0:meta_word=qs;1:meta_word={12'd0,qgains[39:20]};2:meta_word={12'd0,qgains[19:0]};
   3:meta_word=qstats[95:64];4:meta_word=qstats[63:32];5:meta_word=qstats[31:0];
   6:meta_word={11'd0,qstats[116:96]};7:meta_word={10'd0,qfifo[4:0],qstats[133:117]};
   8:meta_word=qpcrc;9:meta_word=qocrc;10:meta_word=qcount;11:meta_word=qline;
   12:meta_word=qerrors;13:meta_word=qroi;14:meta_word=qpack;15:meta_word=qcycle;
  endcase
 end
 always @(posedge clk)if(writing)meta_mem[queued_slot*16+mw]<=meta_word;
 always @(posedge clk)if(collect && roi && !done)raw_mem[write_address]<=pre_rgb;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   done<=0;first_frame<=0;capture_id<=0;burst_crc<=32'hffffffff;gain_changed<=0;seen<=0;collect<=0;next_slot<=0;slot<=0;seq<=0;current_seq<=0;
   cycle_count<=0;current_cycle<=0;qcycle<=0;x<=0;y<=0;lines<=0;line_beats<=0;last_line<=0;count<=0;pack_count<=0;
   bubbles<=0;line_errors<=0;phase_errors<=0;roi_count<=0;phase<=0;prev_v<=0;prev_l<=0;
   pre_crc<=32'hffffffff;post_crc<=32'hffffffff;frame_gains<=0;frame_stats<=0;
   queued<=0;queued_slot<=0;writing<=0;mw<=0;
   qs<=0;qpcrc<=0;qocrc<=0;qcount<=0;qline<=0;qerrors<=0;qroi<=0;qpack<=0;qfifo<=0;qgains<=0;qstats<=0;
  end else begin
   cycle_count<=cycle_count+1'b1;
   prev_v<=v;prev_l<=l;
   if(u)begin
    if(collect)begin
     queued<=1;queued_slot<=slot;qs<=current_seq;qgains<=frame_gains;qstats<=frame_stats;
     qpcrc<=pre_crc;qocrc<=post_crc;qcount<={13'd0,count};qline<={5'd0,lines,5'd0,last_line};
     qerrors<={bubbles,line_errors};qroi<={roi_count,phase_errors};qfifo<={27'd0,gain_changed,fifo_armed,fifo_sticky};
     qcycle<=current_cycle;
    end
    seen<=1;current_seq<=seq;current_cycle<=cycle_count;seq<=seq+1'b1;
    collect<=seq>=WARMUP && next_slot<FRAMES;
    if(seq>=WARMUP && next_slot<FRAMES)begin
     slot<=next_slot;next_slot<=next_slot+1'b1;if(next_slot==0)first_frame<=seq;
    end
    x<=v?1:0;y<=0;count<=v?1:0;line_beats<=v?1:0;lines<=0;last_line<=0;
    bubbles<=0;line_errors<=0;phase_errors<=0;roi_count<=0;phase<=v?1:0;
    pre_crc<=32'hffffffff;post_crc<=32'hffffffff;gain_changed<=0;
   end else if(seen)begin
    if(v)begin
     count<=count+1'b1;line_beats<=line_beats+1'b1;phase<=phase+1'b1;
     if(x==GROUPS-1)begin x<=0;y<=y+1'b1;end else x<=x+1'b1;
    end else phase<=0;
    if(l)begin
     last_line<=line_total;lines<=lines+1'b1;line_beats<=0;
     if(line_total!=GROUPS)line_errors<=line_errors+1'b1;
    end
    if(prev_v&&!v&&!prev_l&&!l && line_beats>0 && line_beats<GROUPS)bubbles<=bubbles+1'b1;
    if(prev_v&&!v && phase!=0)phase_errors<=phase_errors+1'b1;
    if(collect && roi)begin
     roi_count<=roi_count+1'b1;pre_crc<=crc96(pre_crc,pre_rgb);post_crc<=crc96(post_crc,post_rgb);
     burst_crc<=crc96(burst_crc,pre_rgb);
     if(roi_count==0)begin frame_gains<=gains;frame_stats<=stats;end
     else if(gains!=frame_gains)gain_changed<=1;
    end
   end
   if(pu)begin
    pack_count<=pv?1:0;
    if(queued)begin qpack<={13'd0,pack_count};writing<=1;mw<=0;queued<=0;end
   end else if(pv)pack_count<=pack_count+1'b1;
   if(writing)begin
    if(mw==15)begin writing<=0;if(queued_slot==FRAMES-1)begin done<=1;capture_id<=burst_crc;end end
    else mw<=mw+1'b1;
   end
  end
 end
endmodule
