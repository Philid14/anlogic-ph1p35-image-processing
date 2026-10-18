`timescale 1ns/1ps
module tb_temporal_osd;
 reg clk=0,rst=0,v=0,u=0,l=0,show=0;reg[95:0] data=0;reg[10:0] x=0,y=0;
 always #5 clk=~clk;
 wire[7:0] addr;reg[31:0] wd;
 wire[95:0] od,gd;wire ov,ou,ol,gv,gu,gl;
 edge_status_osd #(.TEMPORAL_ENABLE(1)) dut(.clk(clk),.rst_n(rst),.I_data(data),.I_valid(v),.I_user(u),.I_last(l),.I_config(9'd80),.I_probe_panel(320'd0),
  .I_temporal_show(show),.I_temporal_word(wd),.O_temporal_addr(addr),.O_data(od),.O_valid(ov),.O_user(ou),.O_last(ol));
 edge_status_osd_baseline gold(.clk(clk),.rst_n(rst),.I_data(data),.I_valid(v),.I_user(u),.I_last(l),.I_config(9'd80),.I_probe_panel(320'd0),
  .O_data(gd),.O_valid(gv),.O_user(gu),.O_last(gl));
 function[31:0] pattern;input[7:0] a;begin pattern=32'ha5c30017^(a*32'h045d9f3b);end endfunction
 always @(posedge clk)wd<=pattern(addr);
 reg[10:0] qx[0:1],qy[0:1];reg[1:0] qs=0;reg[31:0] word;reg white,outer,border,body,roi;reg[95:0] expected;
 integer j,k,f,yy,xx,checked=0,tx,ty;
 always @(posedge clk)begin
  qx[0]<=x;qx[1]<=qx[0];qy[0]<=y;qy[1]<=qy[0];qs<={qs[0],show};
  #1;
  if(rst)begin
   if({ov,ou,ol}!=={gv,gu,gl})$fatal(1,"metadata latency changed");
   if(ov)begin
    xx=qx[1]*4;yy=qy[1];tx=xx-128;ty=yy-168;expected=gd;
    outer=qs[1]&&xx>=112&&xx<1168&&yy>=152&&yy<696;
    border=xx>=120&&xx<1160&&yy>=160&&yy<688&&(xx<128||xx>=1152||yy<168||yy>=680);
    body=xx>=128&&xx<1152&&yy>=168&&yy<680;
    roi=!qs[1]&&xx>=572&&xx<708&&yy>=340&&yy<380&&(xx<576||xx>=704||yy<344||yy>=376);
    word=pattern(((ty/8)*4+tx/256)&255);
    if(outer)expected={4{(border||(body&&word[31-((tx/8)&31)]))?24'hffffff:24'h000000}};
    else if(roi)expected={4{24'h00ff00}};
    if(od!==expected)$fatal(1,"overlay x%0d y%0d show%b got%h expected%h",xx,yy,qs[1],od,expected);
    checked=checked+1;
   end
  end
 end
 initial begin
  repeat(8)@(negedge clk);rst=1;
  for(f=0;f<3;f=f+1)begin
   @(negedge clk);show=f==1;v=0;u=1;l=0;x=0;y=0;
   repeat(64)begin @(negedge clk);u=0;end
   for(j=0;j<720;j=j+1)begin
    for(k=0;k<320;k=k+1)begin
     @(negedge clk);x=k;y=j;v=1;l=k==319;data={4{8'(j),8'(k),8'(j^k)}};
    end
    repeat(4)begin @(negedge clk);v=0;l=0;end
   end
   repeat(80)@(negedge clk);
  end
  if(checked!=691200)$fatal(1,"counts %d",checked);
  $display("PASS temporal OSD all pixels=%0d, original outside diagnostic overlays, two-stage metadata",checked);$finish;
 end
endmodule
