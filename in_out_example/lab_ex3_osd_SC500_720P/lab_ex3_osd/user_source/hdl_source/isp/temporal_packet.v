`timescale 1ns/1ps
// Double-buffered, checksummed optical pages. All logic uses the existing
// MIPI byte clock. Page RAM changes bank only at an actual video frame pulse.
module temporal_packet #(parameter TOTAL=24720,DWELL=60)(
 input clk,rst_n,capture_done,frame_u,input[31:0] first_frame,
 output[14:0] source_addr,input[31:0] source_data,
 input[7:0] display_addr,output reg[31:0] display_data,output reg show
);
 localparam PAYLOAD=247,PAGES=(TOTAL+PAYLOAD-1)/PAYLOAD;
 reg[31:0] pages[0:511];reg active_bank,build_bank;
 reg[3:0] state;reg[7:0] wi;reg[1:0] byte_n;
 reg[15:0] page_n;reg[14:0] pointer;
 reg[31:0] word_hold,crc,payload_crc;
 reg[7:0] dwell;reg[31:0] header_word;
 wire[31:0] data_word=pointer<TOTAL?source_data:32'd0;
 function[31:0] crc8;
  input[31:0] c0;input[7:0] d;reg[31:0] c;integer k;
  begin c=c0;for(k=7;k>=0;k=k-1)c=(c[31]^d[k])?{c[30:0],1'b0}^32'h04c11db7:{c[30:0],1'b0};crc8=c;end
 endfunction
 wire[31:0] updated_crc=crc8(crc,word_hold>>(24-byte_n*8));
 assign source_addr=pointer;
 wire[15:0] valid_words=(page_n+1)*PAYLOAD>TOTAL?TOTAL-page_n*PAYLOAD:PAYLOAD;
 always @*begin
  case(wi)
   0:header_word=32'h54525031;1:header_word=32'h00010000;2:header_word=TOTAL;
   3:header_word=first_frame;4:header_word={16'd0,page_n};5:header_word=PAGES;
   6:header_word={16'd0,valid_words};7:header_word=payload_crc;
   default:header_word=0;
  endcase
 end
 always @(posedge clk)display_data<=pages[{active_bank,display_addr}];
 // 0 wait, 1 RAM request, 2 consume, 3 payload CRC, 4 header, 5 header CRC,
 // 6 finish header, 7 ready/await SOF. No buffer is written while displayed.
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   active_bank<=0;build_bank<=1;show<=0;state<=0;wi<=0;byte_n<=0;
   page_n<=0;pointer<=0;word_hold<=0;crc<=32'hffffffff;payload_crc<=0;dwell<=0;
  end else begin
   if(show && frame_u && dwell<DWELL-1)dwell<=dwell+1'b1;
   case(state)
    0:if(capture_done)begin state<=1;wi<=0;pointer<=0;crc<=32'hffffffff;end
    1:state<=2;
    2:begin
     pages[{build_bank,wi+8'd8}]<=data_word;
     word_hold<=data_word;byte_n<=0;state<=3;
    end
    3:begin
     crc<=updated_crc;
     if(byte_n==3)begin
      pointer<=pointer+1'b1;
      if(wi==PAYLOAD-1)begin payload_crc<=updated_crc;wi<=0;state<=4;crc<=32'hffffffff;end
      else begin wi<=wi+1'b1;state<=1;end
     end else byte_n<=byte_n+1'b1;
    end
    4:begin pages[{build_bank,wi}]<=header_word;word_hold<=header_word;byte_n<=0;state<=5;end
    5:begin
     crc<=updated_crc;
     if(byte_n==3)begin
      if(wi==7)state<=6;else begin wi<=wi+1'b1;state<=4;end
     end else byte_n<=byte_n+1'b1;
    end
    6:begin pages[{build_bank,8'hff}]<=crc;state<=7;end
    7:if(frame_u && (!show || dwell==DWELL-1))begin
     active_bank<=build_bank;build_bank<=active_bank;show<=1;dwell<=0;
     page_n<=page_n==PAGES-1?0:page_n+1'b1;
     pointer<=page_n==PAGES-1?0:(page_n+1'b1)*PAYLOAD;
     wi<=0;crc<=32'hffffffff;state<=1;
    end
   endcase
  end
 end
endmodule
