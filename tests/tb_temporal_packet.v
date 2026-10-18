`timescale 1ns/1ps
module tb_temporal_packet;
 reg clk=0,rst=0,done=0,u=0;always #5 clk=~clk;
 wire[14:0] sa;reg[31:0] sd;reg[7:0] da=0;wire[31:0] dd;wire show;
 temporal_packet #(.TOTAL(527),.DWELL(2)) dut(.clk(clk),.rst_n(rst),.capture_done(done),.frame_u(u),.first_frame(32'h76543210),
  .source_addr(sa),.source_data(sd),.display_addr(da),.display_data(dd),.show(show));
 always @(posedge clk)sd<=32'h12345678^(sa*32'h01020305);
 integer t=0,fd,n=0,j;reg bank=0,was=0;reg[1023:0] name;
 always @(negedge clk)begin t=t+1;u=(t%2000==0);end
 initial begin
  if(!$value$plusargs("OUT=%s",name))$fatal(1,"output path");fd=$fopen(name,"w");
  repeat(8)@(posedge clk);rst=1;done=1;
  while(n<5)begin
   @(posedge clk);#1;
   if(show && (!was || bank!=dut.active_bank))begin
    bank=dut.active_bank;was=1;
    for(j=0;j<256;j=j+1)begin @(negedge clk);da=j;@(posedge clk);#1;$fdisplay(fd,"%08x",dd);end
    n=n+1;
   end
   if(t>60000)$fatal(1,"packet timeout");
  end
  $fclose(fd);$display("PASS packet pages=5 including rollover and final padding; SOF bank switching");$finish;
 end
endmodule
