`timescale 1ns/1ps
module tb_probe_monitor;
 reg clk=0,rst=0,v=0,u=0,l=0;reg[95:0]data=0;reg[1:0]fifo=0;
 always #5 clk=~clk;
 reg[26:0]vp=0,up=0;reg[95:0]dp[0:26];integer k;
 always @(posedge clk)begin
  vp<={vp[25:0],v};up<={up[25:0],u};dp[0]<=data;
  for(k=1;k<27;k=k+1)dp[k]<=dp[k-1];
 end
 wire pv,pu;wire[127:0]pd;wire[319:0]panel;
 data_96bit_to_128bit packer(.I_clk(clk),.I_rst_n(rst),.I_96b_frame_start(up[26]),.I_96b_valid(vp[26]),.I_96b_data(dp[26]),
  .O_128b_frame_start(pu),.O_128b_valid(pv),.O_128b_data(pd));
 probe_stream_monitor #(.IMG_WIDTH(64),.IMG_HEIGHT(24),.SEQ_BITS(3)) dut(.clk(clk),.rst_n(rst),.iv(v),.iu(u),.il(l),
  .ev(vp[24]),.eu(up[24]),.edge_rgb(dp[24]),.edge_threshold(8'd80),.pv(pv),.pu(pu),.fifo_sticky(fifo),.fifo_armed(2'b11),.panel(panel));
 integer f,y,x;
 task tick;input tv,tu,tl;
 begin @(negedge clk);v=tv;u=tu;l=tl;data=(f==2)?{96{1'b1}}:96'd0;end endtask
 initial begin
  for(k=0;k<27;k=k+1)dp[k]=0;
  repeat(8)@(negedge clk);rst=1;
  for(f=0;f<13;f=f+1)begin
   fifo=f>=7?3:(f>=6?1:0);
   tick(0,1,0);@(posedge clk);#1;
   if(f<2 && panel[0]!==0)$fatal(1,"FAIL warmup reported valid");
   if(f>=2 && (panel[0]!==1 || panel[287:256]!==((f-2)%8)))$fatal(1,"FAIL coherent sequence/wrap %0d",f);
   if(f==2 && (panel[255:224]!=384 || panel[223:192]!=288 || panel[159:144]!=24 || panel[127:112]!=5 || panel[31:24]!=0))$fatal(1,"FAIL normal counts %h",panel);
   if(f==3 && (panel[255:224]!=384 || panel[223:192]!=287 || panel[111:96]!=1 || panel[79:64]!=2 || panel[23:4]!=20'h01001 || (panel[31:24]&8'h1c)!=8'h1c || panel[63:48]!=1))$fatal(1,"FAIL bubble/phase/pack characterization %h",panel);
   if(f==4 && (panel[159:144]!=23 || panel[95:80]!=1 || panel[47:32]!=1))$fatal(1,"FAIL tlast/CRC change %h",panel);
   if(f==5 && (panel[255:224]!=160 || panel[223:192]!=120 || panel[159:144]!=10 || panel[63:48]!=3 || (panel[31:24]&8'h3f)!=8'h3f))$fatal(1,"FAIL truncate %h",panel);
   if(f==8 && (panel[31:24]&8'hc0)!=8'hc0)$fatal(1,"FAIL FIFO sticky visibility");
   $display("MON frame=%0d panel=%h",f,panel);
   repeat(4)tick(0,0,0);
   for(y=0;y<(f==3?10:24);y=y+1)begin
    for(x=0;x<16;x=x+1)begin
     tick(1,0,x==15 && !(f==2&&y==3));
     if(f==1&&y==4&&x==0)tick(0,0,0);
    end
    repeat(4)tick(0,0,0);
   end
   repeat(80)tick(0,0,0);
  end
  $display("PASS probe monitor normal/bubble_position/packer_loss/tlast/truncation/CRC_change/FIFO_visibility/warmup");$finish;
 end
endmodule
