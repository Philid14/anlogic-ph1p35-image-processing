`timescale 1ns/1ps
// Actual native divider and RAM against unchanged baseline AWB, every cycle.
module tb_awb_frame_equivalence;
 parameter WIDTH=256,HEIGHT=64;
 reg clk=0,rst_n=0,user=0,last=0,valid=0,ready=1;
 reg[95:0]data=0;always #5 clk=~clk;
 wire[95:0]gold_data,dut_data;wire gold_v,dut_v,gold_u,dut_u,gold_l,dut_l,gold_r,dut_r;
 awb_reference_baseline #(.IMG_WIDTH(WIDTH),.IMG_HEIGHT(HEIGHT)) u_gold(
  .I_clk(clk),.I_rst_n(rst_n),.I_tlast(last),.I_tuser(user),.I_tdata(data),.I_tvalid(valid),.O_tready(ready),
  .O_tdata(gold_data),.O_tvalid(gold_v),.O_tuser(gold_u),.O_tlast(gold_l),.I_tready(gold_r));
 awb #(.IMG_WIDTH(WIDTH),.IMG_HEIGHT(HEIGHT),.FRAME_SERIAL_DIV(1)) u_dut(
  .I_clk(clk),.I_rst_n(rst_n),.I_tlast(last),.I_tuser(user),.I_tdata(data),.I_tvalid(valid),.O_tready(ready),
  .O_tdata(dut_data),.O_tvalid(dut_v),.O_tuser(dut_u),.O_tlast(dut_l),.I_tready(dut_r));
 integer cycles=0,pixels=0,completed=0,changes=0,reset_checks=0;
 reg[39:0]previous_gain=0;
 always @(posedge clk)begin
  #2;cycles=cycles+1;
  if({gold_v,gold_u,gold_l,gold_r}!=={dut_v,dut_u,dut_l,dut_r})$fatal(1,"AWB stream control mismatch cycle%0d",cycles);
  if(gold_data!==dut_data)$fatal(1,"AWB RGB mismatch cycle%0d gold%h candidate%h",cycles,gold_data,dut_data);
  if({u_gold.gain_r,u_gold.gain_b,u_gold.target_r,u_gold.target_b,u_gold.pending_gain}!==
     {u_dut.gain_r,u_dut.gain_b,u_dut.target_r,u_dut.target_b,u_dut.pending_gain})$fatal(1,"AWB gain/state mismatch cycle%0d",cycles);
  if(rst_n)begin
   if({u_gold.done_r,u_gold.done_b}!=={u_dut.done_r,u_dut.done_b})$fatal(1,"AWB done mismatch cycle%0d",cycles);
   if(u_gold.done_r)begin
    completed=completed+1;
    if({u_gold.quotient_r,u_gold.quotient_b}!=={u_dut.quotient_r,u_dut.quotient_b})$fatal(1,"AWB quotient mismatch");
   end
   if(gold_v)begin if(^gold_data===1'bx)$fatal(1,"Baseline valid RGB unknown");pixels=pixels+4;end
   if(previous_gain!={u_gold.gain_r,u_gold.gain_b})changes=changes+1;
   previous_gain={u_gold.gain_r,u_gold.gain_b};
  end
 end
 function[23:0]pixel;input integer kind,row,col;
 integer r,g,b,z;
 begin
  z=(row+col)%8;
  case(kind)
   0:begin r=100;g=120;b=110;end
   1:begin r=120;g=100;b=110;end
   2:begin r=200;g=20;b=20;end
   3:begin r=245;g=245;b=245;end
   4:begin r=8;g=9;b=8;end
   5:begin r=24+z;g=32+z;b=26+z;end
   default:begin r=100+z;g=120-z;b=112+z;if(col%11==0)begin r=220;g=25;b=20;end end
  endcase
  pixel={r[7:0],g[7:0],b[7:0]};
 end endfunction
 task frame;input integer kind,gap,inline_sof;
 integer y,x,l,k;
 begin
  @(negedge clk);user=1;valid=0;last=0;
  @(negedge clk);user=0;repeat(gap)@(negedge clk);
  for(y=0;y<HEIGHT;y=y+1)begin
   for(x=0;x<WIDTH/4;x=x+1)begin
    @(negedge clk);valid=1;last=x==WIDTH/4-1;user=inline_sof && y==0 && x==0;
    ready=(x%7!=0);
    for(l=0;l<4;l=l+1)data[l*24+:24]=pixel(kind,y,x*4+l);
   end
   @(negedge clk);valid=0;last=0;user=0;
   repeat(3)@(negedge clk);
  end
 end endtask
 task reset_inflight;input integer offset;
 begin
  repeat(offset)@(negedge clk);#1;rst_n=0;valid=0;user=0;last=0;
  repeat(3)@(negedge clk);#1;rst_n=1;repeat(6)@(negedge clk);reset_checks=reset_checks+1;
 end endtask
 initial begin
  repeat(8)@(negedge clk);rst_n=1;repeat(80)@(negedge clk);
  frame(0,8,0);frame(0,0,0);frame(1,2,0);frame(2,5,0);
  frame(3,0,0);frame(4,3,0);frame(5,0,0);frame(6,0,0);
  reset_inflight(13);frame(0,0,0);frame(1,0,0);
  reset_inflight(35);frame(5,4,0);frame(6,0,1);
  repeat(200)@(negedge clk);
  if(pixels<WIDTH*HEIGHT || completed<5 || changes<3)$fatal(1,"insufficient qualified AWB coverage pixels%0d divisions%0d gain_changes%0d",pixels,completed,changes);
  $display("PASS native whole-AWB equivalent cycles%0d pixels%0d complete_divisions%0d gain_changes%0d reset_inflight%0d dimensions%0dx%0d",cycles,pixels,completed,changes,reset_checks,WIDTH,HEIGHT);$finish;
 end
endmodule
