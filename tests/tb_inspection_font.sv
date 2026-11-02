`timescale 1ns/1ps
module tb_inspection_font;
reg clk=0;always #5 clk=~clk;
reg[7:0]c=0;reg[3:0]r=0;wire[15:0]native_bits,truth;
inspection_font_rom dut(.clk(clk),.character(c),.row(r),.bits(native_bits));
osd_char_lib reference(.I_char(c),.I_row(r),.O_row_bits(truth));
integer i;reg[15:0]expected;
initial begin
 #100;
 for(i=0;i<4096;i=i+1)begin
  @(negedge clk);c=i>>4;r=i;#1;expected=truth;
  @(posedge clk);#1;if(native_bits!==expected)$fatal(1,"font%h/%h got%h expected%h",c,r,native_bits,expected);
 end
 $display("PASS exact font4096 character/row combinations; synchronous early lookup");$finish;
end
endmodule
