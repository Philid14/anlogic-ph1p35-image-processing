`timescale 1ns/1ps
// Delay two confidence bits by the SAME causal center (one row/one sample)
// and three registers as one existing edge_link_pair_3x3. No new filtering.
module edge_center_pair_delay #(parameter IMG_WIDTH=1280,IMG_HEIGHT=720,INPUT_BORDER=6)(
 input clk,rst_n,input[1:0] I_pair,input I_valid,I_user,I_last,output reg[1:0] O_pair
);
 localparam GROUPS=IMG_WIDTH/4,WORDS=(GROUPS+3)/4,AB=(WORDS>1)?$clog2(WORDS):1;
 reg[2:0] vp,up;reg[10:0] x,y,x1,y1,x2,y2;reg[1:0] pair1;
 wire[10:0] xn=I_user?0:x,yn=I_user?0:y;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin vp<=0;up<=0;x<=0;y<=0;x1<=0;y1<=0;x2<=0;y2<=0;pair1<=0;end
  else begin
   vp<={vp[1:0],I_valid};up<={up[1:0],I_user};x2<=x1;y2<=y1;
   if(I_user)begin x<=0;y<=0;end
   if(I_valid)begin
    pair1<=I_pair;x1<=xn;y1<=yn;
    if(xn==GROUPS-1)begin x<=0;y<=yn==IMG_HEIGHT-1?0:yn+1'b1;end
    else begin x<=xn+1'b1;y<=yn;end
   end
  end
 end
 reg[7:0] row[0:WORDS-1];reg[7:0] old_word;reg[5:0] pending;
 wire[AB-1:0] address=x1[AB+1:2];
 wire[7:0] assembled=(GROUPS%4==0)?{pending,pair1}:({pending,pair1} << (2*(3-x1[1:0])));
 always @(posedge clk)if(vp[0])begin
  old_word<=row[address];pending<={pending[3:0],pair1};
  if(x1[1:0]==3 || x1==GROUPS-1)row[address]<=assembled;
 end
 wire[1:0] mid=old_word >> (2*(3-x2[1:0]));reg previous;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin O_pair<=0;previous<=0;end
  else begin
   O_pair<=vp[1]&&!up[1]&&y2>=INPUT_BORDER+2&&x2>=(INPUT_BORDER+2)/2 ? {previous,mid[1]}:2'd0;
   if(vp[1])previous<=mid[0];
   if(up[1]||(vp[1]&&x2==GROUPS-1))previous<=0;
  end
 end
endmodule
