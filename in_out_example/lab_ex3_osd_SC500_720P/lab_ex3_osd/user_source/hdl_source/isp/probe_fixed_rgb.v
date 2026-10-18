`timescale 1ns/1ps
// No latency and no replacement of video control. Coordinates consume valid
// beats only; early SOF resets even when no pixel accompanies the notification.
module probe_fixed_rgb #(parameter IMG_WIDTH=1280,IMG_HEIGHT=720)(
 input clk,rst_n,v,u,output [95:0] rgb
);
 reg [10:0] group_x,y;
 wire [10:0] xn=u?11'd0:group_x,yn=u?11'd0:y;
 wire [10:0] sample0={xn[9:0],1'b0};
 function [7:0] shade;
  input [10:0] x,z;
  begin
   shade=48;
   case(z[9:7])
    0: if(z>=32 && z<96 && x>=64 && x<512)shade=192;
    1: if(x>=320)shade=64; // low contrast step, TH-sensitive by design
    2: if(x>={2'b00,z[6:0],2'b00})shade=128;
    3: if((z[6:0]>=16 && z[6:0]<112 && (x>=96 && x<100 || x>=500 && x<504)) ||
          ((z[6:0]>=16 && z[6:0]<20 || z[6:0]>=108 && z[6:0]<112) && x>=96 && x<504))shade=160;
    4: shade=(x[3]^z[3])?96:48;
    default: shade=x[5]?112:48;
   endcase
  end
 endfunction
 wire[7:0] a=shade(sample0,yn),b=shade(sample0+11'd1,yn);
 assign rgb={{6{a}},{6{b}}};
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin group_x<=0;y<=0;end
  else begin
   if(u)begin group_x<=0;y<=0;end
   if(v)begin
    if(xn==IMG_WIDTH/4-1)begin group_x<=0;y<=yn==IMG_HEIGHT-1?11'd0:yn+1'b1;end
    else begin group_x<=xn+1'b1;y<=yn;end
   end
  end
 end
endmodule
