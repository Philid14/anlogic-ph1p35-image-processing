`timescale 1ns/1ps
module tb_color_compare_formatter;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,user=0;reg[47:0]means=0;reg rv=0;reg[15:0]sid=0;
wire[95:0] out_rgb;wire out_valid,out_user,out_last;
color_compare_osd dut(.clk(clk),.rst_n(rst_n),.rgb(96'd0),.valid(1'b0),.user(user),.last(1'b0),
.means(means),.result_valid(rv),.sample_id(sid));
integer f,rc,n,j,vr,checks=0;reg[47:0]m;reg[15:0]id;reg[7:0]classes;reg[131:0]decimal_expected;reg[2047:0]path;
initial begin
repeat(3)@(negedge clk);rst_n=1;
if(!$value$plusargs("STIM=%s",path))$fatal(1,"STIM");f=$fopen(path,"r");
while(!$feof(f))begin
rc=$fscanf(f,"%h %h %h %h %d\n",m,id,classes,decimal_expected,vr);
if(rc==5)begin
@(negedge clk);user=1;means=m;sid=id;rv=vr;
@(negedge clk);user=0;
// Changing the live source during conversion must not mix frames/fields.
means=~m;sid=~id;rv=~vr;
repeat(250)@(negedge clk);
if(!dut.formatted || dut.busy || dut.held_id!==id || dut.held_valid!==vr[0])$fatal(1,"FAIL snapshot %d",checks);
if({dut.class_ref,dut.class_test}!==classes)$fatal(1,"FAIL class %h expected %h for %h",{dut.class_ref,dut.class_test},classes,m);
for(j=0;j<11;j=j+1)if(dut.digits[j]!==decimal_expected[j*12+:12])$fatal(1,"FAIL decimal field%d %h/%h",j,dut.digits[j],decimal_expected[j*12+:12]);
checks=checks+1;
end else if(!$feof(f))$fatal(1,"parse");
end
@(negedge clk);rst_n=0;@(negedge clk);
if(dut.held_valid || dut.formatted || dut.busy)$fatal(1,"FAIL reset");
$display("PASS COLOR_FORMATTER snapshots=%d fields=%d",checks,checks*11);$finish;
end
endmodule
