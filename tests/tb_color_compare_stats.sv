`timescale 1ns/1ps
module tb_color_compare_stats;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,v=0,u=0,l=0;reg[95:0]rgb=0;
wire[47:0] means;wire rv;wire[15:0] sid;
color_compare_stats #(.WIDTH(16),.HEIGHT(8),.REF_X(0),.TEST_X(12),.ROI_Y(0),.W_LOG(2),.H_LOG(3)) dut(
.clk(clk),.rst_n(rst_n),.rgb(rgb),.valid(v),.user(u),.last(l),.means(means),.result_valid(rv),.sample_id(sid));
integer f,rc,a,b,c,d,er,ei,checks=0;reg[95:0]din;reg[47:0]em;reg[2047:0]path;
initial begin
if(!$value$plusargs("STIM=%s",path))$fatal(1,"STIM");f=$fopen(path,"r");
while(!$feof(f))begin
rc=$fscanf(f,"%d %d %d %d %h %d %d %h\n",a,b,c,d,din,er,ei,em);
if(rc==8)begin
@(negedge clk);rst_n=a;v=b;u=c;l=d;rgb=din;
@(posedge clk);#1;
if(rv!==er[0] || sid!==ei[15:0] || (er && means!==em))$fatal(1,"FAIL stats check %0d valid %b/%b id %d/%d mean %h/%h",checks,rv,er,sid,ei,means,em);
checks=checks+1;
end else if(!$feof(f))$fatal(1,"vector parse");
end
$display("PASS COLOR_STATS checks=%0d",checks);$finish;
end
endmodule
