`timescale 1ns/1ps
// MAIN integration OSD. Existing mixer3-stage timing is reused, no video delay.
// 10us ticks are rendered as decimal milliseconds with two fractional digits.
// F/N/E are explicitly hexadecimal frame/sample/error counters (not decimal).
module latency_osd(
 input clk,rst_n,input update,
 input[19:0] latency,minimum,maximum,age,
 input[31:0] frame_id,input[15:0] samples,errors,input[2:0] status,
 input[11:0] x1,y1,x2,y2,output hit,output[23:0] color);
 reg update_d;reg busy;reg[1:0] which;reg[4:0] bit_count;
 reg[19:0] binary;reg[23:0] working,bcd[0:3];
 reg[23:0] adjusted;integer d;
 always @*begin
  adjusted=working;
  for(d=0;d<6;d=d+1)if(working[d*4+:4]>=5)adjusted[d*4+:4]=working[d*4+:4]+4'd3;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   update_d<=0;busy<=0;which<=0;bit_count<=0;binary<=0;working<=0;
   bcd[0]<=0;bcd[1]<=0;bcd[2]<=0;bcd[3]<=0;
  end else begin
   update_d<=update;
   if(update_d && !busy)begin busy<=1;which<=0;bit_count<=0;binary<=latency;working<=0;end
   else if(busy)begin
    working<={adjusted[22:0],binary[19]};binary<={binary[18:0],1'b0};
    if(bit_count==19)begin
     bcd[which]<={adjusted[22:0],binary[19]};working<=0;bit_count<=0;
     which<=which+1'b1;
     case(which)
      0:binary<=minimum;1:binary<=maximum;2:binary<=age;3:busy<=0;
     endcase
    end else bit_count<=bit_count+1'b1;
   end
  end
 end
 // CHARS matches generate_latency_font.py: digits/hex occupy their natural
 // nibble index; all remaining indices are a compact ASCII subset.
 localparam L=18,M=19,N=20,P=21,R=22,S=23,T=24,W=25,X=26,COLON=27,DOT=28,SPACE=29;
 wire[4:0] col=(x1-12'd256)>>4;
 wire[1:0] row=(y1-12'd16)>>4;
 reg[4:0] code;reg[23:0] number;reg[3:0] digit;
 always @*begin
  code=SPACE;number=0;digit=0;
  case(row)
   0:begin
    case(col)
     0:code=L;1:code=10;2:code=T;3:code=COLON;
     5,6,7,9,10:begin number=bcd[0];digit=col<=7?(4'd9-col):(4'd10-col);code={1'b0,number[digit*4+:4]};end
     8:code=DOT;11:code=M;12:code=S;
     15:code=status==1?N:status==2?R:status==3?11:W;
     16:code=status==1?14:status==2?14:status==3?10:10;
     17:code=status==1?W:status==2?P:status==3?13:17;
     18:code=status==0?T:SPACE;
    endcase
   end
   1:begin
    case(col)
     0:code=M;1:code=17;2:code=N;3:code=COLON;
     5,6,7,9,10:begin number=bcd[1];digit=col<=7?(4'd9-col):(4'd10-col);code={1'b0,number[digit*4+:4]};end
     8:code=DOT;
     12:code=M;13:code=10;14:code=X;15:code=COLON;
     17,18,19,21,22:begin number=bcd[2];digit=col<=19?(5'd21-col):(5'd22-col);code={1'b0,number[digit*4+:4]};end
     20:code=DOT;
    endcase
   end
   2:begin
    case(col)
     0:code=15;1:code=COLON;
     2,3,4,5,6,7,8,9:code={1'b0,frame_id[(9-col)*4+:4]};
     11:code=N;12:code=COLON;
     13,14,15,16:code={1'b0,samples[(16-col)*4+:4]};
     18:code=14;19:code=COLON;
     20,21,22,23:code={1'b0,errors[(23-col)*4+:4]};
    endcase
   end
   3:begin
    case(col)
     0:code=10;1:code=16;2:code=14;3:code=COLON;
     5,6,7,9,10:begin number=bcd[3];digit=col<=7?(4'd9-col):(4'd10-col);code={1'b0,number[digit*4+:4]};end
     8:code=DOT;11:code=M;12:code=S;
     15:code=1;16:code=0;17:code=30;18:code=S;
     20:code=31;21:code=14;22:code=X;
    endcase
   end
  endcase
 end
 wire[17:0] glyph;
 PH1P_LOGIC_ERAM #(.DATA_WIDTH_A(18),.DATA_WIDTH_B(18),.ADDR_WIDTH_A(10),.ADDR_WIDTH_B(10),
  .DATA_DEPTH_A(1024),.DATA_DEPTH_B(1024),.MODE("SP"),.CLKMODE("ASYNC"),
  .REGMODE_A("NOREG"),.REGMODE_B("NOREG"),.INIT_FILE("latency_font.dath"),
  .FILL_ALL("NONE"),.FORCE_KEEP("ON")) u_font(
  .clka(clk),.cea(1'b1),.ocea(1'b1),.addra({1'b0,code,y1[3:0]}),.dia(18'd0),
  .wea(1'b0),.rsta(1'b0),.bea(1'b1),.doa(glyph),
  .clkb(clk),.ceb(1'b0),.oceb(1'b0),.addrb(10'd0),.dib(18'd0),.web(1'b0),
  .rstb(1'b0),.beb(1'b1),.dob(),.ecc_sbiterrinj(1'b0),.ecc_dbiterrinj(1'b0),
  .ecc_sbiterr(),.ecc_dbiterr());
 assign hit=x2>=256 && x2<640 && y2>=16 && y2<80 && glyph[15-x2[3:0]];
 assign color=status==3?24'hff4040:24'h00e6ff;
endmodule
