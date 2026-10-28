`timescale 1ns/1ps
module tb_target_boot_probe;
reg c=0,d=0,h=0,r=0;always #3 c=~c;always #5 d=~d;always #7 h=~h;
reg [15:0] ce=0,de=0,live=0,drops=0,cancels=0,faults=0;wire [95:0] value;
target_boot_probe p(.rst_n(r),.csi_clk(c),.ddr_clk(d),.hdmi_clk(h),.csi_events(ce),.ddr_events(de),.live_status(live),.drops(drops),.cancels(cancels),.faults(faults),.diagnostics(value));
reg [95:0] expected; integer checks=0;
task verify(input bit b);begin checks=checks+1;if(!b)$fatal(1,"probe mismatch value=%h expected=%h",value,expected);end endtask
initial begin
 #50;r=1;@(negedge c);ce=16'h8001;@(negedge c);ce=0;
 @(negedge d);de=16'h0021;live=16'h0571;drops=2;cancels=3;faults=4;@(negedge d);de=0;
 expected=96'h800100210571000200030004;#5000;verify(value===expected);
 @(negedge c);ce=16'h0200;@(negedge c);ce=0;
 @(negedge d);live=16'h0038;faults=5;expected=96'h820100210038000200030005;
 #5000;verify(value===expected);
 r=0;#30;verify(value===0);r=1;expected=96'h000000000038000200030005;#5000;verify(value===expected);
 $display("PASS BOOT_PROBE checks=%0d",checks);$finish;
end
endmodule
