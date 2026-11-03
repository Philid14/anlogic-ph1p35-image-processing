`timescale 1ns/1ps
module tb_awb_divider_equivalence;
 reg clk=0,rst=1,start=0;always #5 clk=~clk;
 reg[47:0]numerator=0;reg[31:0]denominator=1;
 wire[47:0]quotient,cq;wire[31:0]remainder,cr;wire done,cd;
 divider reference_ip(.*);
 awb_frame_divider48 compact(.clk(clk),.rst(rst),.start(start),.numerator(numerator),.denominator(denominator),.quotient(cq),.remainder(cr),.done(cd));
 integer cycle=0,checks=0,compares=0;always @(posedge clk)begin
  cycle=cycle+1;#1;
  if(!rst)begin
   if(done!==cd)$fatal(1,"done mismatch cycle%0d ref%b candidate%b",cycle,done,cd);
   if(done)begin
    if(quotient!==cq || remainder!==cr)$fatal(1,"native output mismatch cycle%0d ref%h/%h candidate%h/%h",cycle,quotient,remainder,cq,cr);
    compares=compares+1;
   end
  end
 end
 reg[31:0]seed=32'h72a54c39;
 function[31:0]rand32;input[31:0]v;begin rand32=(v^(v<<13));rand32=rand32^(rand32>>17);rand32=rand32^(rand32<<5);end endfunction
 task vector;input[47:0]n;input[31:0]d;
 integer launched,j,seen;reg[47:0]q;reg[31:0]r;
 begin
  q=n/d;r=n%d;seen=0;
  @(negedge clk);start=1;numerator=n;denominator=d;
  @(posedge clk);#2;launched=cycle;
  @(negedge clk);start=0;
  for(j=0;j<60;j=j+1)begin
   @(posedge clk);#2;
   if(done)begin
    if(quotient!==q || remainder!==r || cycle-launched!=49)$fatal(1,"reference math/latency mismatch n%h d%h",n,d);
    seen=seen+1;checks=checks+1;
   end
  end
  if(seen!=1)$fatal(1,"missing/duplicate done %0d",seen);
 end endtask
 task cancel;input integer offset;
 begin
  @(negedge clk);start=1;numerator=48'hfedcba987654;denominator=32'h01234567;
  @(negedge clk);start=0;repeat(offset)@(negedge clk);
  #2;rst=1;repeat(3)@(negedge clk);#2;rst=0;repeat(65)@(negedge clk);
 end endtask
 integer k;reg[47:0]n;reg[31:0]d;
 initial begin
  repeat(5)@(negedge clk);rst=0;repeat(80)@(negedge clk);
  vector(0,1);vector(48'hffffffffffff,1);vector(48'hffffffffffff,32'hffffffff);
  vector(48'h123456780000,32'h12345678);vector(48'h000000010000,32'hffffffff);
  for(k=0;k<256;k=k+1)begin seed=rand32(seed);d=seed|1;seed=rand32(seed);n={seed,16'd0};if(k[0])begin seed=rand32(seed);n[15:0]=seed[15:0];end vector(n,d);end
  for(k=0;k<50;k=k+1)begin cancel(k);vector(48'h123456780000,32'h12345678);end
  $display("PASS native frame-divider equivalence math%0d qualified_compares%0d cycles%0d all50 reset offsets; done age49",checks,compares,cycle);$finish;
 end
endmodule
