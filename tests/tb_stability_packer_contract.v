`timescale 1ns/1ps
// Characterize the EXISTING continuous-run contract. No repair in this task.
module tb_stability_packer_contract;
 reg clk=0,v=0,u=0;reg[95:0]data=0;
 always #5 clk=~clk;
 wire ov,ou;wire[127:0]od;
 data_96bit_to_128bit dut(.I_clk(clk),.I_rst_n(1'b1),.I_96b_frame_start(u),.I_96b_valid(v),.I_96b_data(data),
  .O_128b_frame_start(ou),.O_128b_valid(ov),.O_128b_data(od));
 reg[127:0] golden[0:5];integer count=0,kind=0,j,k;reg[95:0]d;
 always @(posedge clk)begin #1;
  if(ov)begin
   if(kind==0)golden[count]=od;
   if(kind==2 && od!==golden[count])$fatal(1,"FAIL aligned bubble should retain bytes");
   if(kind==1 && count==0 && od===golden[0])$fatal(1,"FAIL missing unaligned-bubble sensitivity");
   count=count+1;
  end
 end
 task tick;input tv;input[95:0]td;
 begin @(negedge clk);v=tv;data=td;end endtask
 initial begin
  repeat(8)tick(0,0);
  for(kind=0;kind<3;kind=kind+1)begin
   count=0;
   for(j=0;j<8;j=j+1)begin
    for(k=0;k<12;k=k+1)d[95-8*k-:8]=12*j+k;
    tick(1,d);
    if((kind==1 && j==0)||(kind==2 && j==3))tick(0,0);
   end
   repeat(4)tick(0,0);#2;
   if((kind==1 && count!=5)||(kind!=1 && count!=6))$fatal(1,"FAIL characterization count %0d kind%0d",count,kind);
   $display("PACKER contract case=%0d words=%0d expected_lossless=6",kind,count);
  end
  $display("PASS characterized packer: continuous=6, unaligned_bubble=5, aligned_four_beat_bubble=6; hardware trigger unproven");$finish;
 end
endmodule
