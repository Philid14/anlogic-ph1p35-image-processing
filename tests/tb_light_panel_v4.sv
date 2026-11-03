`timescale 1ns/1ps
// Raster coordinates are an explicit test boundary. Actual video counters and
// stream alignment are exercised separately by the nine-frame ISP regression.
module tb_light_panel_v4;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,v=0,u=0;reg[95:0] rgb=0;reg[47:0] means=0;reg rv=0;reg[15:0]sid=0;
reg[10:0] xpos=0;reg[9:0]ypos=0;
wire[95:0]out_rgb;wire ov;
color_compare_osd #(.UI_ENABLE(1),.AUTO_DIMENSION(1),.USABILITY_ENABLE(1),.INSPECTION_V4(1),
 .REF_X(304),.TEST_X(944),.ROI_Y(304),.ROI_W(32),.ROI_H(32)) dut(
 .clk(clk),.rst_n(rst_n),.rgb(rgb),.valid(v),.user(u),.last(1'b0),.means(means),.result_valid(rv),.sample_id(sid),
 .display_enable(1'b1),.dimension_enable(1'b0),.cal_mode(1'b0),.axis_y(1'b0),.calibrated(1'b0),
 .span_x(11'd0),.span_y(11'd0),.cal_visited(2'd0),.dim_sizes(44'd0),.dim_box(44'd0),.dim_gap_coords(44'd0),
 .cal_status(3'd0),.dim_valid(1'b0),.dim_present(1'b0),.dim_gap_valid(2'd0),.dim_threshold(8'd0),.dim_id(16'd0),
 .out_rgb(out_rgb),.out_valid(ov));
reg ev=0;reg[95:0]ed=0;integer checks=0;
task step;input vv,uu;input[95:0]dd,expected;
begin
 @(negedge clk);v=vv;u=uu;rgb=dd;
 @(posedge clk);#1;
 if(ov!==ev || (ev && out_rgb!==ed))$fatal(1,"raster %0d rgb%h expected%h",checks,out_rgb,ed);
 if(ev)checks=checks+1;
 ev=vv;ed=expected;
end endtask
integer f,rc,command,xx,yy,valid_result;reg[95:0]input_rgb,golden;reg[47:0]m;reg[15:0]id;reg[2047:0]path;
initial begin
force dut.x=xpos;force dut.y=ypos;
repeat(3)@(negedge clk);rst_n=1;
if(!$value$plusargs("STIM=%s",path))$fatal(1,"STIM");f=$fopen(path,"r");
while(!$feof(f))begin
rc=$fscanf(f,"%d %d %d %h %h %h %h %d\n",command,xx,yy,input_rgb,golden,m,id,valid_result);
if(rc==8)begin
 if(command==0)begin
  means=m;rv=valid_result;sid=id;xpos=0;ypos=0;step(0,1,0,0);
  repeat(500)step(0,0,0,0);
 end else begin xpos=xx;ypos=yy;step(1,0,input_rgb,golden);end
end else if(!$feof(f))$fatal(1,"parse");
end
step(0,0,0,0);step(0,0,0,0);
$display("PASS LIGHT/DIFF/MATCH/CHECK/WAIT raster %0d four-pixel positions",checks);$finish;
end
endmodule
