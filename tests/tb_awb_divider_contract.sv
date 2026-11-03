`timescale 1ns/1ps
// Native official IP is the oracle for fixed-latency unsigned frame division.
module tb_awb_divider_contract;
 reg clk=0,rst=1,start=0;always #5 clk=~clk;
 reg[47:0]numerator=0;reg[31:0]denominator=1;
 wire[47:0]quotient;wire[31:0]remainder;wire done;
 divider reference_ip(.*);
 integer cycle=0,checks=0,age=-1;always @(posedge clk)cycle=cycle+1;
 reg[31:0]seed=32'h72a54c39;
 function[31:0]rand32;input[31:0]v;begin rand32=(v^(v<<13));rand32=rand32^(rand32>>17);rand32=rand32^(rand32<<5);end endfunction
 task vector;input[47:0]n;input[31:0]d;
 integer launched,j,seen;reg[47:0]q;reg[31:0]r;
 begin
  q=n/d;r=n%d;seen=0;
  @(negedge clk);start=1;numerator=n;denominator=d;
  @(posedge clk);#1;launched=cycle;
  @(negedge clk);start=0;
  for(j=0;j<60;j=j+1)begin
   @(posedge clk);#1;
   if(done)begin
    if(quotient!==q || remainder!==r)$fatal(1,"reference math n=%h d=%h q=%h expected=%h r=%h expected=%h",n,d,quotient,q,remainder,r);
    if(age<0)begin age=cycle-launched;$display("NATIVE_DONE_AGE=%0d",age);end
    if(cycle-launched!=age)$fatal(1,"native variable latency");
    seen=seen+1;checks=checks+1;
   end
  end
  if(seen!=1)$fatal(1,"missing/duplicate done %0d",seen);
 end endtask
 integer k;
 initial begin
  repeat(5)@(negedge clk);rst=0;repeat(80)@(negedge clk);
  vector(0,1);vector(48'hffffffffffff,1);vector(48'hffffffffffff,32'hffffffff);
  vector(48'h123456780000,32'h12345678);vector(48'h000000010000,32'hffffffff);
  for(k=0;k<64;k=k+1)begin seed=rand32(seed);denominator=seed|1;seed=rand32(seed);vector({seed,16'd0},denominator);end
  $display("PASS native divider contract checks=%0d latency=%0d",checks,age);$finish;
 end
endmodule
