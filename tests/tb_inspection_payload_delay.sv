`timescale 1ns/1ps
module tb_inspection_payload_delay;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[95:0] data;wire[95:0] d21;wire[31:0] d26;wire[22:0]d24;
 reg[95:0] q[0:26];integer age=0,j,k,checks=0;
 inspection_payload_delay #(.WIDTH(96),.DELAY(21)) a(clk,rst_n,data,d21);
 inspection_payload_delay #(.WIDTH(32),.DELAY(26)) b(clk,rst_n,data[31:0],d26);
 inspection_payload_delay #(.WIDTH(23),.DELAY(24)) c(clk,rst_n,data[22:0],d24);
 always @(posedge clk)begin
  q[0]<=data;for(j=1;j<27;j=j+1)q[j]<=q[j-1];
  if(!rst_n)age<=0;else age<=age+1;
  #1;
  if(age>27)begin
   if(d21!==q[21] || d26!==q[26][31:0] || d24!==q[24][22:0])
    $fatal(1,"Delay mismatch age%0d got%h expected%h",age,d21,q[21]);
   checks=checks+1;
  end
 end
 initial begin
  data=0;repeat(5)@(negedge clk);rst_n=1;
  for(k=0;k<3000;k=k+1)begin
   @(negedge clk);data={$random,$random,$random};
   if(k%491==0)rst_n=0;else if(k%491==4)rst_n=1;
  end
  $display("PASS exact SP payload delays checks=%0d reset/bubbles/random",checks);$finish;
 end
endmodule
