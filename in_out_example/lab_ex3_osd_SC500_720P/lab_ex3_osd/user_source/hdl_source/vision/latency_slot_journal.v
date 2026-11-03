`timescale 1ns/1ps
// MAIN DDR journal: observe transactions, never arbitrate or stall video.
// Completion means all exact, contiguous user writes have entered the ordered
// MC command FIFO. A later read of a committed slot queues behind these writes.
module latency_slot_journal #(
 parameter WORDS=172800,parameter EXPIRE_CYCLES=33333333,
 parameter HEARTBEAT_TIMEOUT=66667
)(
 input clk,rst_n,input wr_en,input[24:0] wr_addr,input[86:0] wr_tag,
 input rd_en,rd_valid,command_full,
 input read_select,input[1:0] read_slot,input reference_heartbeat,
 output reg[84:0] selected,output reg select_toggle,output reg read_bad,output[7:0] diagnostic);
 localparam[24:0] BASE0=0,BASE1=7000000,BASE2=14000000,BASE3=21000000;
 reg[83:0] records[0:3];reg[3:0] committed,recent;
 reg[25:0] expiry;
 reg writing,write_bad;reg[1:0] write_slot,leased_slot;
 reg[17:0] count;reg[24:0] next_address;reg[83:0] write_key;
 reg[10:0] outstanding;
 wire is_base=wr_addr==BASE0 || wr_addr==BASE1 || wr_addr==BASE2 || wr_addr==BASE3;
 wire[1:0] base_slot=wr_addr==BASE0?0:wr_addr==BASE1?1:wr_addr==BASE2?2:3;
 wire first=wr_tag[2],last=wr_tag[1],good=wr_tag[0];
 wire[83:0] key=wr_tag[86:3];
 (* async_reg="true" *)reg hb1,hb2;reg hb_old;
 reg[16:0] hb_age;reg hb_seen,hb_fault;
 wire clock_live=hb_age<HEARTBEAT_TIMEOUT && hb_seen && !hb_fault;
 assign diagnostic={committed, !clock_live,write_bad,read_bad,writing};
 wire commit_record=wr_en && !(first && is_base) && writing && last &&
   count==WORDS-1 && good && !write_bad && key==write_key &&
   wr_addr==next_address && !command_full && clock_live;
 // Unreset payload RAM is protected by resettable committed bits. Clearing
 // its contents on reset would need hundreds of FFs without improving safety.
 always @(posedge clk)if(rst_n && commit_record)records[write_slot]<=key;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin hb1<=0;hb2<=0;hb_old<=0;hb_age<=HEARTBEAT_TIMEOUT;hb_seen<=0;hb_fault<=0;end
  else begin
   hb1<=reference_heartbeat;hb2<=hb1;hb_old<=hb2;
   if(hb2!=hb_old)begin hb_age<=0;hb_seen<=1;end
   else if(hb_age<HEARTBEAT_TIMEOUT)hb_age<=hb_age+1'b1;
   else if(hb_seen)hb_fault<=1;
  end
 end
 integer i;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   committed<=0;recent<=0;expiry<=0;writing<=0;write_bad<=1;
   write_slot<=0;leased_slot<=0;count<=0;next_address<=0;write_key<=0;
   outstanding<=0;selected<=0;select_toggle<=0;read_bad<=1;
  end else begin
   // Two successive half-second windows bound untouched slot lifetime below
   // one second at configured DDR user66.667MHz, below the10.48s timestamp wrap.
   // Lost reference clears records and latches a fault until global reset:
   // a stopped reference cannot establish absolute timing across the outage.
   if(expiry==EXPIRE_CYCLES-1)begin
    expiry<=0;committed<=committed & recent;recent<=0;
   end else expiry<=expiry+1'b1;
   case({rd_en,rd_valid})
    2'b10:if(outstanding<2047)outstanding<=outstanding+1'b1;else read_bad<=1;
    2'b01:if(outstanding!=0)outstanding<=outstanding-1'b1;else read_bad<=1;
    default:;
   endcase
   if(read_select)begin
    leased_slot<=read_slot;select_toggle<=!select_toggle;
    selected<={records[read_slot],committed[read_slot] && clock_live &&
      outstanding==0 && !rd_en && !rd_valid && !command_full};
    read_bad<=outstanding!=0 || rd_en || rd_valid || command_full || !clock_live;
   end
   if(wr_en)begin
    if(first && is_base)begin
     committed[base_slot]<=0;recent[base_slot]<=0;
     write_slot<=base_slot;write_key<=key;next_address<=wr_addr+8;
     count<=1;writing<=1;write_bad<=!clock_live || command_full;
     if(base_slot==leased_slot || (read_select && base_slot==read_slot))read_bad<=1;
    end else if(writing)begin
     next_address<=next_address+8;
     if(count<WORDS)count<=count+1'b1;
     if(key!=write_key || wr_addr!=next_address || command_full)write_bad<=1;
     if(write_slot==leased_slot || (read_select && write_slot==read_slot))read_bad<=1;
     if(last)begin
      writing<=0;
      if(count==WORDS-1 && good && !write_bad && key==write_key &&
        wr_addr==next_address && !command_full && clock_live)begin
       committed[write_slot]<=1;recent[write_slot]<=1;
      end
     end
    end else begin
     // Unknown/extra write cannot be assigned safely to a generation.
     committed<=0;recent<=0;read_bad<=1;
    end
   end
   if(command_full || !clock_live)begin
    committed<=0;recent<=0;write_bad<=1;read_bad<=1;
   end
  end
 end
endmodule

// HDMI domain. The selected tuple is held from actual DDR read selection until
// the next selection. A 2FF toggle plus one settling cycle transfers it atomically.
// It must arrive in blanking before the first real HDMI pixel. Missing, duplicate,
// late or invalid records are excluded. Results publish only after the full image
// and its trailing blanking, at the next HDMI VSYNC (not at guessed ISP EOF).
module latency_display_meter #(parameter PIXELS=921600,MAX_AGE=100000)(
 input clk,rst_n,input[19:0] tick,input vsync,input pixel_valid,input fifo_underflow,
 input[84:0] selected,input select_toggle,input read_bad,
 output reg[19:0] latency,minimum,maximum,age,
 output reg[31:0] frame_id,session_id,
 output reg[15:0] samples,errors,output reg[2:0] status,output reg[7:0] diagnostic);
 (* async_reg="true" *)reg st1,st2,rb1,rb2;
 reg st3,st_seen,vs_old;
 reg[84:0] tuple;
 reg tuple_ready,frame_bad,seen_pixel;
 reg[19:0] pixels,start_age;
 reg[63:0] previous_key;reg have_previous;
 wire vstart=vsync && !vs_old;
 wire event_pending=st3!=st_seen;
 wire[19:0] delta=tick-tuple[20:1];
 wire[63:0] key=tuple[84:21];
 wire same=have_previous && previous_key==key;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   st1<=0;st2<=0;st3<=0;st_seen<=0;rb1<=1;rb2<=1;vs_old<=0;
   tuple<=0;tuple_ready<=0;frame_bad<=1;seen_pixel<=0;pixels<=0;start_age<=0;
   previous_key<=0;have_previous<=0;latency<=0;minimum<=0;maximum<=0;age<=0;
   frame_id<=0;session_id<=0;samples<=0;errors<=0;status<=0;diagnostic<=0;
  end else begin
   st1<=select_toggle;st2<=st1;st3<=st2;
   rb1<=read_bad;rb2<=rb1;vs_old<=vsync;
   if(vstart)begin
    if(seen_pixel)begin
     diagnostic<={1'b0,(have_previous && key<previous_key),(start_age>=MAX_AGE),(pixels!=PIXELS),rb2,frame_bad,!tuple[0],!tuple_ready};
     if(tuple_ready && tuple[0] && !frame_bad && !rb2 && pixels==PIXELS && start_age<MAX_AGE &&
       (!have_previous || key>=previous_key))begin
      session_id<=key[63:32];frame_id<=key[31:0];age<=start_age;
      status<=same?3'd2:3'd1; // NEW / REP; age still updates for repetitions.
      if(!same)begin
       latency<=start_age;
       if(samples==0 || start_age<minimum)minimum<=start_age;
       if(samples==0 || start_age>maximum)maximum<=start_age;
       if(samples!=16'hffff)samples<=samples+1'b1;
       previous_key<=key;have_previous<=1;
      end
     end else begin
      status<=3'd3;
      if(errors!=16'hffff)errors<=errors+1'b1;
     end
    end
    tuple_ready<=0;frame_bad<=0;seen_pixel<=0;pixels<=0;
   end
   if(event_pending)begin
    st_seen<=st3;tuple<=selected;tuple_ready<=1;
    if((tuple_ready && !vstart) || (seen_pixel && !vstart))frame_bad<=1;
   end
   if(fifo_underflow)frame_bad<=1;
   if(pixel_valid)begin
    seen_pixel<=1;
    if(!seen_pixel)begin
     start_age<=delta;
     if(!tuple_ready || !tuple[0] || event_pending || vstart)frame_bad<=1;
    end
    if(pixels<PIXELS+1)pixels<=pixels+1'b1;
    if(rb2)pixels<=PIXELS+1; // Persistent corruption; no valid sample this frame.
   end
  end
 end
endmodule
