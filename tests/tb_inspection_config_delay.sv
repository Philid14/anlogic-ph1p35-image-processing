`timescale 1ns/1ps
module tb_inspection_config_delay;
 reg clk=0;always #5 clk=~clk;reg rst=0;reg[22:0]data=0;
 wire[22:0]first,spatial,last;
 inspection_config_delay dut(.clk(clk),.rst_n(rst),.data(data),.first(first),.spatial(spatial),.final_data(last));
 reg[22:0]gold[0:26];reg[31:0]seed=32'hfa74587;integer i,n,age=0;
 initial begin
  repeat(8)@(negedge clk);
  for(n=0;n<2000;n=n+1)begin
   @(negedge clk);rst=n!=71&&n!=72&&n!=598;seed={seed[30:0],seed[31]^seed[21]^seed[1]^seed[0]};data=seed;
   @(posedge clk);#1;
   if(!rst)age=0;else begin
    for(i=26;i>0;i=i-1)gold[i]=gold[i-1];gold[0]=data;age=age+1;
    if(first!==gold[0])$fatal(1,"config first");
    if(age>=25&&spatial!==gold[24])$fatal(1,"config spatial %0d %h %h",n,spatial,gold[24]);
    if(age>=27&&last!==gold[26])$fatal(1,"config last %0d",n);
   end
  end
  $display("PASS exact23-bit per-clock first/spatial/final taps, wraps, arbitrary SOF payload and mid-stream resets2000");$finish;
 end
endmodule
