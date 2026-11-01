`timescale 1ns/1ps
module tb_light_compare_v4;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,user=0;reg[47:0]means=0;reg rv=0;reg[15:0]sid=0;
color_compare_osd #(.INSPECTION_V4(1)) dut(.clk(clk),.rst_n(rst_n),.rgb(96'd0),.valid(1'b0),.user(user),.last(1'b0),
 .means(means),.result_valid(rv),.sample_id(sid),.dimension_enable(1'b0));
integer f,rc,j,vr,st,checks=0;reg[47:0]m,norm;reg[15:0]id;reg[259:0]decimals;reg[2047:0]path;
initial begin
repeat(3)@(negedge clk);rst_n=1;
if(!$value$plusargs("STIM=%s",path))$fatal(1,"STIM");f=$fopen(path,"r");
while(!$feof(f))begin
rc=$fscanf(f,"%h %h %h %h %d %d\n",m,id,decimals,norm,st,vr);
if(rc==6)begin
@(negedge clk);user=1;means=m;sid=id;rv=vr;
@(negedge clk);user=0;means=~m;sid=~id;rv=~vr;
repeat(500)@(negedge clk);
if(!dut.formatted || dut.busy || dut.held_id!==id || dut.held_valid!==vr[0])$fatal(1,"snapshot %d",checks);
for(j=0;j<13;j=j+1)if(dut.digits[j]!==decimals[j*20+:20])$fatal(1,"field%d %h expected%h for%h",j,dut.digits[j],decimals[j*20+:20],m);
for(j=0;j<6;j=j+1)if(dut.normalized[j]!==norm[47-j*8-:8])$fatal(1,"normalization %d",j);
if(dut.comparison_status!==st[1:0])$fatal(1,"status got%0d expected%0d for%h",dut.comparison_status,st,m);
checks=checks+1;
end else if(!$feof(f))$fatal(1,"parse");
end
@(negedge clk);rst_n=0;@(negedge clk);
if(dut.held_valid || dut.formatted || dut.busy)$fatal(1,"reset");
$display("PASS light diagnostics %0d snapshots / %0d fields",checks,checks*13);$finish;
end
endmodule
