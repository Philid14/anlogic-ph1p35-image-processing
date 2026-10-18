`timescale 1ns/1ps
// Actual AWB_V2 + actual signal_delay; behavioral RAM and divider arithmetic.
// Not a validation of the vendor primitive or physical latency/CDC behavior.
module tb_awb_stability;
 reg clk=0,rst=0,v=0,u=0,l=0;reg[95:0] data=0;
 always #5 clk=~clk;
 wire ov,ou,ol;wire[95:0] od;
 awb #(.IMG_WIDTH(1280),.IMG_HEIGHT(8)) dut(
  .I_clk(clk),.I_rst_n(rst),.I_tvalid(v),.I_tuser(u),.I_tlast(l),.I_tdata(data),.I_tready(),
  .O_tdata(od),.O_tvalid(ov),.O_tuser(ou),.O_tlast(ol),.O_tready(1'b1));
 integer f,y,x,outn=0,lines=0,last_count=0,stable=0,updates=0;
 reg[19:0] fr,fb,prev_r=0,prev_b=0;reg[95:0] golden;
 always @(posedge clk)begin #1;
  if(rst)begin
   if(ou)begin outn=0;lines=0;end
   if(ov)begin
    if(outn==0)begin fr=dut.gain_r;fb=dut.gain_b;end
    if(fr!==dut.gain_r || fb!==dut.gain_b)$fatal(1,"FAIL AWB mid-frame gain");
    if(f>=4 && f<12 && od!==golden)$fatal(1,"FAIL repeated AWB pixel");
    if(f==3)golden=od;
    outn=outn+1;
   end
   if(ol)lines=lines+1;
  end
 end
 task tick;input tv,tu,tl;input[23:0] pixel;
  begin @(negedge clk);v=tv;u=tu;l=tl;data={4{pixel}};end
 endtask
 initial begin
  repeat(8)@(negedge clk);rst=1;
  for(f=0;f<18;f=f+1)begin
   tick(0,1,0,0);repeat(65)tick(0,0,0,0);
   for(y=0;y<8;y=y+1)begin
    for(x=0;x<320;x=x+1)begin
     if(f<12)tick(1,0,x==319,24'h607068);
     else if(x<160)tick(1,0,x==319,24'h646464);
     else tick(1,0,x==319,(f%2)?24'h406060:24'h416060);
    end
    repeat(80+y+f%3)tick(0,0,0,0);
   end
   repeat(120)tick(0,0,0,0);#2;
   if(outn!=2560 || lines!=8)$fatal(1,"FAIL AWB counts %0d %0d",outn,lines);
   if(f>=4 && f<12)begin
    if(dut.gain_r!=76458 || dut.gain_b!=70577)$fatal(1,"FAIL AWB stable target");stable=stable+1;
   end
   if(f>=14 && (dut.gain_r!=prev_r || dut.gain_b!=prev_b))updates=updates+1;
   $display("AWB frame=%0d count=%0d gain_r=%0d gain_b=%0d selected=%0d",f,outn,dut.gain_r,dut.gain_b,dut.sample_count);
   prev_r=dut.gain_r;prev_b=dut.gain_b;
  end
  if(updates<3)$fatal(1,"FAIL expected controlled selection-induced AWB variation");
  $display("PASS AWB stable_frames=%0d controlled_gain_changes=%0d frame_constant counts=18x2560",stable,updates);$finish;
 end
endmodule

module divider(input clk,rst,start,input[31:0]denominator,input[47:0]numerator,output reg[47:0]quotient,output reg done);
 reg[47:0] q;integer count=0;
 always @(posedge clk)begin
  done<=0;
  if(rst)begin count<=0;quotient<=0;end
  else if(start)begin q<=denominator ? numerator/denominator:48'hffffffffffff;count<=48;end
  else if(count>0)begin count<=count-1;if(count==1)begin quotient<=q;done<=1;end end
 end
endmodule
module blk_mem_gen_awb_delay_signal(input clka,wea,input[10:0]addra,input[95:0]dia,input clkb,input[10:0]addrb,output reg[95:0]dob);
 reg[95:0] mem[0:2047];
 always @(posedge clka)if(wea)mem[addra]<=dia;
 always @(posedge clkb)dob<=mem[addrb];
endmodule
