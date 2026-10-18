`timescale 1ns/1ps
module tb_edge_probe_stream;
 parameter W=256,H=160;
 localparam DEPTH=27;
 reg clk=0,rst=0,v=0,u=0,l=0,ready=0;reg[95:0]data=0;reg[8:0]cfg=336;
 always #5 clk=~clk;
 wire[95:0]od;wire ov,ou,ol,ir,pv,pu;wire[127:0]pd;
 edge_control_stream #(.IMG_WIDTH(W),.IMG_HEIGHT(H),.DENOISE_ENABLE(1),.NMS_ENABLE(1),.QUALITY_ENABLE(1),.PROBE_ENABLE(1)) dut(
  .clk(clk),.rst_n(rst),.requested_config(cfg),.I_data(data),.I_valid(v),.I_user(u),.I_last(l),.O_ready(ready),
  .I_probe_pack_valid(pv),.I_probe_pack_user(pu),.I_probe_fifo_sticky(2'b00),.I_probe_fifo_armed(2'b11),
  .O_data(od),.O_valid(ov),.O_user(ou),.O_last(ol),.I_ready(ir));
 data_96bit_to_128bit packer(.I_clk(clk),.I_rst_n(rst),.I_96b_frame_start(ou),.I_96b_valid(ov),.I_96b_data(od),
  .O_128b_frame_start(pu),.O_128b_valid(pv),.O_128b_data(pd));
 wire[127:0]ipd;wire ipv,ipu,ipl;
 isp_top #(.EDGE_CONTROL_ENABLE(1),.DENOISE_ENABLE(1),.NMS_ENABLE(1),.QUALITY_ENABLE(1),.PROBE_ENABLE(1)) integrated(
  .axi4s_video_aclk(clk),.I_rst_n(rst),.I_edge_config(cfg),.I_probe_fifo_sticky(2'b00),.I_probe_fifo_armed(2'b11),.I_tlast(1'b0),.I_tuser(1'b0),
  .I_tdata(40'b0),.I_tvalid(1'b0),.I_tdest(10'b0),.O_tready(ready),.I_tready(),.O_tdata(ipd),.O_tvalid(ipv),.O_tuser(ipu),.O_tlast(ipl));
 reg[95:0]ex[0:26];reg[26:0]vp=0,up=0,lp=0;
 integer fd,pf,rc,j,iv,iu,il,beats=0,words=0,expected_words,cycles=0,panels=0;
 reg[95:0]td,te,tp;reg[8:0]tc;reg[319:0]panel;reg[127:0]word;
 reg[2047:0]stim_path,pack_path;
 initial begin
  if(!$value$plusargs("STIM=%s",stim_path)||!$value$plusargs("PACK=%s",pack_path)||!$value$plusargs("WORDS=%d",expected_words))$fatal(1,"FAIL paths");
  fd=$fopen(stim_path,"r");pf=$fopen(pack_path,"r");
  for(j=0;j<27;j=j+1)ex[j]=0;
  force integrated.awb_O_tdata=data;force integrated.awb_O_tvalid=v;force integrated.awb_O_tuser=u;force integrated.awb_O_tlast=l;
  repeat(8)@(negedge clk);rst=1;
  while(!$feof(fd))begin
   rc=$fscanf(fd,"%d %d %d %h %h %h %h %h\n",iv,iu,il,tc,td,te,tp,panel);
   if(rc==8)begin
    @(negedge clk);v=iv!=0;u=iu!=0;l=il!=0;cfg=tc;data=td;ready=~ready;
    @(posedge clk);
    if(v && dut.edge_input!==tp)$fatal(1,"FAIL fixed source cycle%0d",cycles);
    #1;
    for(j=26;j>0;j=j-1)ex[j]=ex[j-1];ex[0]=te;
    vp={vp[25:0],v};up={up[25:0],u};lp={lp[25:0],l};
    if({ov,ou,ol,ir}!=={vp[26],up[26],lp[26],1'b1})$fatal(1,"FAIL metadata %0d",cycles);
    if(ov)begin
     beats=beats+1;
     if(od!==ex[26])$fatal(1,"FAIL pixel cycle%0d got%h expected%h",cycles,od,ex[26]);
    end
    if(u)begin
     panels=panels+1;
     if(dut.probe_panel!==panel)$fatal(1,"FAIL panel frame%0d got%h expected%h",panels,dut.probe_panel,panel);
    end
    if(W==1280&&H==720 && (ipv!==pv||ipu!==pu||(pv&&ipd!==pd)))$fatal(1,"FAIL actual ISP");
    if(pv)begin
     rc=$fscanf(pf,"%h\n",word);
     if(rc!=1||pd!==word)$fatal(1,"FAIL pack word%0d got%h expected%h",words,pd,word);
     words=words+1;
    end
    cycles=cycles+1;
   end else if(!$feof(fd))$fatal(1,"FAIL vectors");
  end
  if(words!=expected_words)$fatal(1,"FAIL count");
  $display("PASS PROBE W=%0d H=%0d valid_beats=%0d packed_words=%0d panels=%0d cycles=%0d fixed_RGB/raw_ORIGIN/OSD/markers",W,H,beats,words,panels,cycles);$finish;
 end
endmodule
