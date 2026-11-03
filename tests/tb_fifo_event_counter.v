`timescale 1ns/1ps
module tb_fifo_event_counter;
 reg clk=0,rst=0,u=0,fr=0,v=0,full=0;wire[31:0] counts;
 always #5 clk=~clk;
 fifo_event_counter #(.WARMUP(2)) dut(clk,rst,u,fr,v,full,counts);
 task tick;input tu,treset,tv,tf;
 begin @(negedge clk);u=tu;fr=treset;v=tv;full=tf;@(posedge clk);#1;end endtask
 initial begin
  tick(0,0,1,1);rst=1;tick(0,0,1,1); // before arming, ignored
  tick(1,0,0,0);tick(0,1,1,1);tick(0,0,1,0);tick(1,0,0,0);
  if(counts!=0)$fatal(1,"reset/idle falsely counted");
  repeat(4)tick(0,0,1,1);tick(1,0,0,0);
  if(counts!=32'h00010000)$fatal(1,"boot frame not counted once");
  repeat(3)begin tick(0,0,1,1);tick(0,0,1,1);tick(1,0,0,0);end
  if(counts!=32'h00010003)$fatal(1,"repeated steady overflow not counted");
  force dut.counts=32'hffffffff;tick(0,0,1,1);release dut.counts;tick(1,0,0,0);
  if(counts!=32'hffffffff)$fatal(1,"counter wrapped");
  @(negedge clk);rst=0;#1;if(counts!=0)$fatal(1,"system reset failed");
  $display("PASS FIFO monitor boot/steady, repeat events, masking, saturation and reset");$finish;
 end
endmodule
