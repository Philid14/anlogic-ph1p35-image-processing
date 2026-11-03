`timescale 1ns/1ps
module tb_planar_measure;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,v=0,u=0,l=0,b=0;reg[3:0] mask=0;reg[7:0] cut=130;
    wire rv,present,rb;wire[1:0] gap;wire[43:0] sizes,box_coords;wire[15:0] sid;wire[7:0] rc;
    planar_measure_stats #(.WIDTH(64),.HEIGHT(32),.X0(8),.X1(56),.Y0(4),.Y1(28)) dut(
      .clk(clk),.rst_n(rst_n),.binary_pixels(mask),.valid(v),.user(u),.last(l),.bright(b),.threshold(cut),
      .result_valid(rv),.present(present),.gap_valid(gap),.sizes(sizes),.box_coords(box_coords),
      .sample_id(sid),.result_threshold(rc),.result_bright(rb));
    integer fd,n,tr,tv,tu,tl,tb,tm,tc,er,ep,eg,ei,ec,eb,checks=0;
    reg[43:0] es,ex;reg[2047:0] path;
    initial begin
      if(!$value$plusargs("STIM=%s",path))$fatal(1,"FAIL no input");fd=$fopen(path,"r");
      while(!$feof(fd))begin
        n=$fscanf(fd,"%d %d %d %d %d %h %d %d %d %d %h %h %d %d %d\n",tr,tv,tu,tl,tb,tm,tc,er,ep,eg,es,ex,ei,ec,eb);
        if(n==15)begin
          @(negedge clk);rst_n=tr;v=tv;u=tu;l=tl;b=tb;mask=tm;cut=tc;
          @(posedge clk);#1;
          if(rv!==er[0] || present!==ep[0] || gap!==eg[1:0] || sid!==ei[15:0] || rc!==ec[7:0] || rb!==eb[0])
            $fatal(1,"FAIL stats metadata check %0d rv%0d/%0d present%0d/%0d gap%0d/%0d id%0d/%0d",checks,rv,er,present,ep,gap,eg,sid,ei);
          if(present && (sizes!==es || box_coords!==ex))$fatal(1,"FAIL stats geometry %0d sizes %h/%h box %h/%h",checks,sizes,es,box_coords,ex);
          checks=checks+1;
        end else if(!$feof(fd))$fatal(1,"FAIL parse %0d",n);
      end
      $display("PASS planar stats %0d cycles: runs, lanes, polarity, gaps, malformed frames, reset",checks);$finish;
    end
endmodule

module tb_inspection_calibration;
    reg clk=0;always #5 clk=~clk;reg rst_n=0;reg[3:0] sw=0;reg short_t=0,up_t=0;
    wire[10:0] sx,sy;wire calibrated;wire[1:0] visited;
    inspection_calibration dut(.clk(clk),.rst_n(rst_n),.switches(sw),.short_toggle(short_t),.up_toggle(up_t),
       .span_x(sx),.span_y(sy),.calibrated(calibrated),.visited(visited));
    task tick;begin @(negedge clk);@(posedge clk);#1;end endtask
    integer k;
    initial begin
      tick();rst_n=1;tick();if(sx!==256 || sy!==256 || calibrated)$fatal(1,"FAIL startup");
      sw=10;tick();short_t=1;tick();if(sx!==252 || sy!==256)$fatal(1,"FAIL X decrement");
      up_t=1;tick();if(sx!==256)$fatal(1,"FAIL X increment");
      sw=2;tick();if(calibrated)$fatal(1,"FAIL single axis confirmation");
      sw=10;tick();sw=14;tick();short_t=0;tick();if(sy!==252)$fatal(1,"FAIL Y decrement");
      sw=6;tick();if(!calibrated || visited!==3)$fatal(1,"FAIL two axis confirm");
      sw=10;tick();for(k=0;k<220;k=k+1)begin short_t=~short_t;tick();end
      if(sx!==16)$fatal(1,"FAIL minimum clamp");
      for(k=0;k<220;k=k+1)begin up_t=~up_t;tick();end
      if(sx!==736)$fatal(1,"FAIL X maximum clamp");
      sw=14;tick();for(k=0;k<220;k=k+1)begin up_t=~up_t;tick();end
      if(sy!==352)$fatal(1,"FAIL Y maximum clamp");
      sw=0;tick();if(calibrated)$fatal(1,"FAIL disabling is not confirmation");
      rst_n=0;tick();if(calibrated || sx!==256 || sy!==256)$fatal(1,"FAIL reset");
      $display("PASS ruler calibration two axes, explicit confirm, bounds and reset");$finish;
    end
endmodule

module tb_dimension_formatter;
    reg clk=0;always #5 clk=~clk;reg rst_n=0,user=0;
    reg[43:0] sizes=0;reg[10:0] sx=256,sy=256;reg cal=0;
    wire[95:0] out_rgb;wire out_valid,out_user,out_last;
    color_compare_osd #(.UI_ENABLE(1)) dut(.clk(clk),.rst_n(rst_n),.rgb(96'd0),.valid(1'b0),.user(user),.last(1'b0),
      .means(48'd0),.result_valid(1'b1),.sample_id(16'd0),.display_enable(1'b0),.dimension_enable(1'b1),
      .cal_mode(1'b0),.axis_y(1'b0),.calibrated(cal),.span_x(sx),.span_y(sy),.cal_visited(2'b11),
      .dim_sizes(sizes),.dim_box(44'd0),.dim_valid(1'b1),.dim_present(1'b1),.dim_gap_valid(2'b11),
      .dim_threshold(8'd130),.dim_id(16'h9876),.out_rgb(out_rgb),.out_valid(out_valid),.out_user(out_user),.out_last(out_last));
    reg[2047:0] path;integer fd,n,ic,ix,iy,j,checks=0;reg[43:0] vals;reg[79:0] expected;
    initial begin
      repeat(3)@(negedge clk);rst_n=1;
      if(!$value$plusargs("STIM=%s",path))$fatal(1,"FAIL no vectors");fd=$fopen(path,"r");
      while(!$feof(fd))begin
        n=$fscanf(fd,"%d %d %d %h %h\n",ic,ix,iy,vals,expected);
        if(n==5)begin
          @(negedge clk);user=1;cal=ic;sx=ix;sy=iy;sizes=vals;
          @(negedge clk);user=0;cal=~cal;sx=16;sy=16;sizes=~vals;
          repeat(260)@(negedge clk);
          if(!dut.formatted || dut.busy)$fatal(1,"FAIL not ready");
          for(j=0;j<4;j=j+1)if(dut.digits[j]!==expected[79-j*20 -:20])
            $fatal(1,"FAIL metric%d %h/%h",j,dut.digits[j],expected[79-j*20 -:20]);
          checks=checks+1;
        end else if(!$feof(fd))$fatal(1,"FAIL parse");
      end
      $display("PASS metric conversion %0d snapshots, rounded two-axis mm, px and snapshot isolation",checks);$finish;
    end
endmodule
