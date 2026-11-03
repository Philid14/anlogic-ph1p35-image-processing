`timescale 1ns/1ps
module tb_parts_all_drawing;
reg clk=0;always #5 clk=~clk;
reg rst=0,v=0,u=0,l=0,enable=1;reg[33:0]pc;
wire[95:0]od;wire ov,ou,ol;
color_compare_osd #(.UI_ENABLE(1),.AUTO_DIMENSION(1),.USABILITY_ENABLE(1),.INSPECTION_V4(1),.COMPACT_FONT(1),.INSPECTION_V5(1),.PARTS_ENABLE(1)) dut(
 .clk(clk),.rst_n(rst),.rgb({4{24'h606060}}),.valid(v),.user(u),.last(l),.means(48'd0),.result_valid(1'b1),.sample_id(16'd1),
 .display_enable(1'b0),.dimension_enable(enable),.cal_mode(1'b0),.axis_y(1'b0),.calibrated(1'b1),.span_x(11'd500),.span_y(11'd500),.cal_visited(2'd0),
 .dim_round(1'b0),.background_applied(1'b1),.background_status(3'd3),.dim_sizes({11'd400,11'd240,22'd0}),
 .dim_box({11'd400,11'd799,11'd240,11'd479}),.dim_gap_coords(44'd0),.cal_status(3'd3),.dim_valid(1'b1),.dim_present(1'b1),
 .dim_gap_valid(2'd0),.dim_threshold(8'd130),.dim_id(16'd1),.dim_part_valid(1'b1),.dim_part_coords(pc),
 .out_rgb(od),.out_valid(ov),.out_user(ou),.out_last(ol));
reg[95:0]gold[0:230399];reg[19:0]digits[0:6];string dir,path;integer f,r,x,y,n=0,ptr=0,frame,j,en;
reg v0=0,u0=0,l0=0;reg[95:0]e0=0;
task step(input vv,uu,ll,input[95:0]expected);
 begin @(negedge clk);v=vv;u=uu;l=ll;@(posedge clk);#1;
 if(ov!==v0||ou!==u0||ol!==l0)$fatal(1,"metadata%0d",n);
 if(ov&&od!==e0)$fatal(1,"frame%d pixel%0d got%h exp%h x%d y%d",frame,ptr,od,e0,x,y);
 v0=vv;u0=uu;l0=ll;e0=expected;n=n+1;end
endtask
initial begin
 if(!$value$plusargs("DIR=%s",dir))$fatal(1,"dir");f=$fopen({dir,"/metadata.txt"},"r");
 repeat(8)@(negedge clk);rst=1;
 for(frame=0;frame<7;frame=frame+1)begin
  r=$fscanf(f,"%d %h %h %h %h %h %h %h %h\n",en,pc,digits[0],digits[1],digits[2],digits[3],digits[4],digits[5],digits[6]);
  if(r!=9)$fatal(1,"metadata read");enable=en;
  path=$sformatf("%s/gold_%0d.txt",dir,frame);$readmemh(path,gold);
  step(0,1,0,0);repeat(600)step(0,0,0,0);
  if(enable)for(j=0;j<7;j=j+1)if(dut.digits[j]!==digits[j])$fatal(1,"formatter field%d %h expected%h",j,dut.digits[j],digits[j]);
  ptr=0;for(y=0;y<720;y=y+1)begin
   for(x=0;x<1280;x=x+4)begin step(1,0,x==1276,gold[ptr]);ptr=ptr+1;end
   step(0,0,0,0);
  end
 end
 repeat(4)step(0,0,0,0);
 $display("PASS T/L seven fields, flips, zero overhang, 7 native720p overlay frames and off; %d cycles",n);$finish;
end
endmodule
