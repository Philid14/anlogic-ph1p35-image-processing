`timescale 1ns/1ps
// Digital RTL only. No sensor, DDR PHY, clock jitter or metastability model.
module tb_edge_stability;
 parameter W=64,H=64,D=1,N=1,Q=1;
 localparam F=D?4:0, DEPTH=F+(N?9:5)+(Q?12:0);
 reg clk=0,rst=0,v=0,u=0,l=0;
 always #5 clk=~clk;
 reg [95:0] data=0;
 wire ov,ou,ol;wire [95:0] od;
 edge_detect_96 #(.IMG_WIDTH(W),.IMG_HEIGHT(H),.RUNTIME_THRESHOLD(1),
  .DENOISE_ENABLE(D),.NMS_ENABLE(N),.QUALITY_ENABLE(Q)) dut (
  .I_clk(clk),.I_rst_n(rst),.I_tdata(data),.I_tvalid(v),.I_tuser(u),.I_tlast(l),
  .I_threshold(8'd60),.I_tready(),.O_tready(1'b0),.O_tdata(od),.O_tvalid(ov),.O_tuser(ou),.O_tlast(ol));
 reg [95:0] ex[0:24]; reg [15:0] src[0:24],labs[0:24];
 reg [51:0] gg[0:24];reg [27:0] mm[0:24],nm[0:24];reg [3:0] axis[0:24];reg [1:0] keep[0:24];
 reg [24:0] vp=0,up=0,lp=0,win=0;
 integer i,j,rc,fd,iv,iu,il,iw,cycles=0,beats=0,stage_checks=0;
 reg [95:0] td,te;reg [15:0] ts,tlab;reg [51:0] tg;
 reg [27:0] tm,tn;reg [3:0] ta;reg [1:0] tk;reg [2047:0] path;
 generate if(N) begin: check_n
  always @(posedge clk) begin #2;
   if(vp[F+7]) begin
    if({dut.nms_magnitude,dut.nms_keep}!=={nm[F+7],keep[F+7]})
     $fatal(1,"FAIL NMS cycle %0d got %h/%h expected %h/%h",cycles,dut.nms_magnitude,dut.nms_keep,nm[F+7],keep[F+7]);
   end
   if(vp[F+3] && win[F+3] && {dut.g_nms.dir0_s4,dut.g_nms.dir1_s4}!==axis[F+3]) $fatal(1,"FAIL axis");
  end
 end endgenerate
 generate if(D)begin: check_gaussian
  always @(posedge clk)begin #2;
   if(vp[F-1] && dut.source_pair!==src[F-1])$fatal(1,"FAIL Gaussian cycle %0d",cycles);
  end
 end endgenerate
 genvar k;
 generate if(Q) begin: check_q
  for(k=1;k<=4;k=k+1) begin: hops
   always @(posedge clk) begin #2;
    if(vp[F+8+3*k] && dut.g_quality.labels[k]!==labs[F+8+3*k][16-4*k+:4])
     $fatal(1,"FAIL hop %0d cycle %0d",k,cycles);
   end
  end
 end endgenerate
 initial begin
  if(!$value$plusargs("STIM=%s",path)) $fatal(1,"FAIL missing STIM");
  fd=$fopen(path,"r");if(!fd)$fatal(1,"FAIL open");
  for(j=0;j<25;j=j+1) begin ex[j]=0;src[j]=0;gg[j]=0;mm[j]=0;nm[j]=0;axis[j]=0;keep[j]=0;labs[j]=0;end
  repeat(8) @(negedge clk);rst=1;
  while(!$feof(fd)) begin
   rc=$fscanf(fd,"%d %d %d %h %h %h %h %h %h %h %h %h %d\n",iv,iu,il,td,te,ts,tg,tm,ta,tn,tk,tlab,iw);
   if(rc==13) begin
    @(negedge clk);v=iv!=0;u=iu!=0;l=il!=0;data=td;
    @(posedge clk);#1;
    for(j=24;j>0;j=j-1)begin ex[j]=ex[j-1];src[j]=src[j-1];gg[j]=gg[j-1];mm[j]=mm[j-1];nm[j]=nm[j-1];axis[j]=axis[j-1];keep[j]=keep[j-1];labs[j]=labs[j-1];end
    ex[0]=te;src[0]=ts;gg[0]=tg;mm[0]=tm;nm[0]=tn;axis[0]=ta;keep[0]=tk;labs[0]=tlab;
    vp={vp[23:0],v};up={up[23:0],u};lp={lp[23:0],l};win={win[23:0],iw!=0};
    if({ov,ou,ol}!=={vp[DEPTH-1],up[DEPTH-1],lp[DEPTH-1]})$fatal(1,"FAIL metadata cycle %0d",cycles);
    if(ov) begin
     if(od!==ex[DEPTH-1]) $fatal(1,"FAIL output cycle %0d got %h expected %h",cycles,od,ex[DEPTH-1]);
     beats=beats+1;
    end
    if(vp[F+2] && win[F+2] && {dut.gx0_s3,dut.gy0_s3,dut.gx1_s3,dut.gy1_s3}!==gg[F+2])$fatal(1,"FAIL gradient cycle %0d",cycles);
    if(vp[F+3] && win[F+3] && {dut.mag0_s4,dut.mag1_s4}!==mm[F+3])$fatal(1,"FAIL magnitude cycle %0d",cycles);
    if(vp[F+3] && win[F+3])stage_checks=stage_checks+1;
    cycles=cycles+1;
   end else if(!$feof(fd))$fatal(1,"FAIL vector fields %0d",rc);
  end
  // Let delayed generate assertions sample the last vector.
  #3;
  $display("PASS deterministic stages W=%0d H=%0d D=%0d N=%0d Q=%0d beats=%0d gradients=%0d cycles=%0d",W,H,D,N,Q,beats,stage_checks,cycles);$finish;
 end
endmodule
