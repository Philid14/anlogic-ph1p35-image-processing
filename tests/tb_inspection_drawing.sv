`timescale 1ns/1ps
module tb_inspection_drawing;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,v=0,u=0,l=0,enable=1;reg[95:0]rgb={4{24'h606060}};
 wire[95:0]od;wire ov,ou,ol;
 color_compare_osd #(.UI_ENABLE(1),.AUTO_DIMENSION(1),.USABILITY_ENABLE(1),.INSPECTION_V4(1),.COMPACT_FONT(0),.INSPECTION_V5(1)) dut(
 .clk(clk),.rst_n(rst),.rgb(rgb),.valid(v),.user(u),.last(l),.means(48'd0),.result_valid(1'b1),.sample_id(16'd1),
 .display_enable(1'b0),.dimension_enable(enable),.cal_mode(1'b0),.axis_y(1'b0),.calibrated(1'b1),.span_x(11'd1000),.span_y(11'd1000),.cal_visited(2'd0),
 .dim_round(1'b1),.background_applied(1'b1),.background_status(3'd3),.dim_sizes({11'd100,11'd100,22'd0}),
 .dim_box({11'd500,11'd599,11'd300,11'd399}),.dim_gap_coords(44'd0),.cal_status(3'd3),.dim_valid(1'b1),.dim_present(1'b1),
 .dim_gap_valid(2'd0),.dim_threshold(8'd130),.dim_id(16'd1),.out_rgb(od),.out_valid(ov),.out_user(ou),.out_last(ol));
 reg[95:0]gold[0:230399];reg[2047:0]path;integer x,y,n=0,ptr=0,frame;
 reg v0=0,u0=0,l0=0;reg[95:0]e0=0;
 task step;input vv,uu,ll;input[95:0]expected;
 begin
  @(negedge clk);v=vv;u=uu;l=ll;
  @(posedge clk);#1;
  if(ov!==v0||ou!==u0||ol!==l0)$fatal(1,"drawing metadata%0d",n);
  if(ov&&od!==e0)$fatal(1,"drawing pixel%0d got%h exp%h",n,od,e0);
  v0=vv;u0=uu;l0=ll;e0=expected;n=n+1;
 end endtask
 initial begin
  if(!$value$plusargs("GOLD=%s",path))$fatal(1,"missing gold");$readmemh(path,gold);
  repeat(8)@(negedge clk);rst=1;
  for(frame=0;frame<2;frame=frame+1)begin
   enable=frame==0;step(0,1,0,0);repeat(350)step(0,0,0,0);
   if(frame==0&&(dut.digits[0]!==20'h00100||dut.digits[1]!==20'h00050))$fatal(1,"D/R formatter %h %h",dut.digits[0],dut.digits[1]);
   ptr=0;for(y=0;y<720;y=y+1)begin
    for(x=0;x<1280;x=x+4)begin step(1,0,x==1276,frame==0?gold[ptr]:{4{24'h606060}});ptr=ptr+1;end
    step(0,0,0,0);
   end
  end
  repeat(4)step(0,0,0,0);
  $display("PASS D10.0/R5.0 correct scale and radial geometry, native font bit exact720p, transparent background, dimension off %0d",n);$finish;
 end
endmodule
