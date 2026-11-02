`timescale 1ns/1ps
module tb_inspection_shape;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,v=0,u=0,l=0,bright=0,learn=1,clear=0,request=0;
 reg[31:0]gray=0;reg[3:0]fb=0;
 wire[3:0]pixels;wire ov,ou,ol,applied,ready;wire[2:0]status;
 measure_background #(.WIDTH(128),.HEIGHT(128),.X0(16),.X1(112),.Y0(16),.Y1(96)) bg(
 .clk(clk),.rst_n(rst),.gray(gray),.fallback_pixels(fb),.valid(v),.user(u),.last(l),.bright(bright),
 .learn_enable(learn),.clear(clear),.request_toggle(request),.pixels(pixels),.out_valid(ov),.out_user(ou),.out_last(ol),
 .applied(applied),.ready(ready),.status(status));
 reg[1:0]bp=0;always @(posedge clk)bp<={bp[0],bright};
 wire complete,present,round_present;wire[43:0]sizes,box_coords,gaps;wire[1:0]gapv;
 planar_measure_stats #(.WIDTH(128),.HEIGHT(128),.X0(16),.X1(112),.Y0(16),.Y1(96),.MIN_ROW(6),.SHAPE_ENABLE(1)) stats(
 .clk(clk),.rst_n(rst),.binary_pixels(pixels),.valid(ov),.user(ou),.last(ol),.bright(bp[1]),.threshold(8'd130),
 .result_valid(complete),.present(present),.round_present(round_present),.sizes(sizes),.box_coords(box_coords),
 .gap_coords(gaps),.gap_valid(gapv),.sample_id(),.result_threshold(),.result_bright());
 integer f,x,y,k,n=0,kind,grayval,expect_present,expect_round;reg primed=0;
 reg[3:0]e0,e1;reg ev0=0,ev1=0,eu0=0,eu1=0,el0=0,el1=0;
 reg check_pixels=0;
 // Independent per-pixel reference: plane190, synthetic object with both
 // dark and bright facets and a background-valued specular hole.
 function integer intensity;input integer t,xx,yy;integer dx,dy;begin
  intensity=190;dx=xx-64;dy=yy-56;
  case(t)
   1:if(xx>=38&&xx<90&&yy>=30&&yy<82)begin
       intensity=xx<64?40:240;
       if(xx>=54&&xx<74&&yy>=44&&yy<66)intensity=190;
     end
   2:if(dx*dx+dy*dy<=625)intensity=xx<64?40:240;
   3:if(xx>=38&&xx<90&&yy>=30&&yy<82)intensity=40;
   4:if((dx<0?-dx:dx)+(dy<0?-dy:dy)<=25)intensity=40;
   5:if((xx>=38&&xx<90&&yy>=30&&yy<42)||(xx>=52&&xx<76&&yy>=42&&yy<82))intensity=40;
  endcase
 end endfunction
 task step;input tv,tu,tl;input[31:0]g;input[3:0]binary,expected;
 begin
  @(negedge clk);v=tv;u=tu;l=tl;gray=g;fb=binary;
  @(posedge clk);#1;
  if(ov!==ev0||ou!==eu0||ol!==el0)$fatal(1,"two-cycle metadata %0d",n);
  if(check_pixels&&ov&&pixels!==e0)$fatal(1,"background pixel %0d got%h expected%h",n,pixels,e0);
  e1=e0;e0=expected;ev1=ev0;ev0=tv;eu1=eu0;eu0=tu;el1=el0;el0=tl;n=n+1;
 end endtask
 reg[31:0]g;reg[3:0]binary,expected;
 task frame;input integer t,badframe;
 begin
  if(!primed)step(0,1,0,0,0,0);primed=0;repeat(3)step(0,0,0,0,0,0);
  for(y=0;y<128;y=y+1)begin
   for(x=0;x<128;x=x+4)begin
    g=0;binary=0;expected=0;
    for(k=0;k<4;k=k+1)begin
     grayval=intensity(t,x+k,y);g[31-k*8-:8]=grayval;
     binary[3-k]=grayval>=130;
     expected[3-k]=(x>=16&&x<112&&y>=16&&y<96)?((grayval<178||grayval>202)^!bright):binary[3-k];
    end
    step(1,0,(x==124)^(badframe&&x==60&&y==20),g,binary,expected);
    if(x==60&&y[2:0]==3)step(0,0,0,0,0,0);
   end
   step(0,0,0,0,0,0);
  end
  repeat(4)step(0,0,0,0,0,0);
 end endtask
 task publish;input ep,er;input integer w,h;
 begin
  step(0,1,0,0,0,0);primed=1;repeat(5)step(0,0,0,0,0,0);
  if(complete!==1||present!==ep||round_present!==er)$fatal(1,"shape got %b%b%b expected1%b%b",complete,present,round_present,ep,er);
  if(ep&&(sizes[43:33]!==w||sizes[32:22]!==h))$fatal(1,"size %h expected%0dx%0d",sizes,w,h);
 end endtask
 initial begin
  repeat(8)@(negedge clk);rst=1;
  step(0,0,0,0,0,0);request=1;repeat(3)step(0,0,0,0,0,0);
  frame(0,0); // training starts
  frame(0,0); // commit, next frame will apply
  check_pixels=1;frame(1,0);publish(1,0,52,52);
  frame(2,0);publish(1,1,51,49); // top/bottom single pixel tips rejected by 3px rule
  frame(2,0);publish(1,1,51,49);
  frame(3,0);publish(1,0,52,52);
  frame(4,0);publish(1,0,51,45);
  frame(5,0);publish(1,0,52,52);
  bright=1;primed=0;frame(1,0);publish(1,0,52,52);
  check_pixels=0;frame(0,1);step(0,1,0,0,0,0);repeat(5)step(0,0,0,0,0,0);
  if(complete||present||round_present)$fatal(1,"malformed frame published");
  clear=1;step(0,0,0,0,0,0);clear=0;if(ready)$fatal(1,"clear");
  request=0;repeat(3)step(0,0,0,0,0,0);frame(0,1);frame(0,0);if(ready||status!=4)$fatal(1,"bad training accepted");
  $display("PASS background mixed reflectance, polarity, shape circle/square/diamond/T, malformed capture, clear, 2-cycle metadata %0d cycles",n);$finish;
 end
endmodule

