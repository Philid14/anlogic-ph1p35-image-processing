`timescale 1ns/1ps
module tb_inspection_select;
 reg clk=0;always #5 clk=~clk;reg rst=0,en=0,toggle=0,sof=0;wire selected;
 inspection_shape_select dut(.clk(clk),.rst_n(rst),.enable(en),.long_toggle(toggle),.frame_start(sof),.result_circle(selected));
 task tick;begin @(negedge clk);@(posedge clk);#1;end endtask
 task frame;begin sof=1;tick();sof=0;tick();end endtask
 initial begin
  repeat(4)tick();rst=1;tick();toggle=1;tick();en=1;frame();frame();if(selected)$fatal(1,"inactive long event replayed");
  toggle=0;tick();if(selected)$fatal(1,"tearing midframe");frame();if(selected)$fatal(1,"result identity");
  frame();if(!selected)$fatal(1,"round selection");repeat(30)tick();frame();if(!selected)$fatal(1,"hold retrigger");
  toggle=1;tick();frame();if(!selected)$fatal(1,"prior result not held");frame();if(selected)$fatal(1,"box selection");
  rst=0;tick();if(selected)$fatal(1,"reset");
  $display("PASS explicit W/H-D/R long-press selection, inactive events, no repeat, frame identity, reset");$finish;
 end
endmodule
