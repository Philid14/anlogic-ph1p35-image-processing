`timescale 1ns/1ps
// Actual video_in, ordered MC command FIFO, video_out, mixer and native RAMs.
// Small height retains production1280-pixel line and240-word DDR bursts.
module tb_latency_video_path;
 reg cc=0,dc=0,hc=0;always #20 cc=~cc;always #4 dc=~dc;always #6.667 hc=~hc;
 reg rst_n=0,rv=0,ru=0,rl=0,pv=0,pu=0;
 reg[127:0]rgb=0;
 wire[19:0]tick,gray;wire[86:0]tag,wr_tag;
 wire wf,wb,rb,wren,rden,ready,rvalid,cmdfull;
 wire[1:0]rp,read_slot;wire[24:0]wa,ra,ua;
 wire[127:0]wd,rdata;
 wire read_select,underflow;
 wire[84:0]selected;wire event_toggle,read_bad;
 reg vs=0,de=0,user=0,last=0;
 wire[23:0]pixel,hdmi_rgb;wire hdmi_de;
 wire[19:0]lat,mn,mx,age;wire[31:0]fid,sid;wire[15:0]samples,errors;wire[2:0]status;
 wire app_en,app_we;wire[24:0]app_addr;wire[2:0]app_cmd;wire[127:0]app_data;
 reg[31:0]dcycle=0;
 wire app_ready=dcycle%11!=0;
 reg[39:0]response_valid=0;reg[24:0]response_addr[0:39];
 reg[127:0]memory[0:16383];
 function integer index_for(input[24:0]a);
  integer s,offset;
  begin s=a/7000000;offset=(a-s*7000000)/8;index_for=s*4096+(offset%4096);end
 endfunction
 assign ua=wren?wa:rden?ra:25'd0;
 assign rdata=memory[index_for(response_addr[39])];assign rvalid=response_valid[39];
 latency_timebase timebase(hc,rst_n,tick,gray);
 latency_capture_tag #(.WIDTH(1280),.HEIGHT(4)) capture(cc,rst_n,gray,rv,ru,rl,1'b0,pv,pu,wf,tag);
 video_in #(.LATENCY_ENABLE(1)) vi(.I_rst_n(rst_n),.I_camera_clk(cc),.I_camera_frame_start(pu),
  .I_camera_valid(pv),.I_camera_data(rgb),.I_mipi_rx_error(1'b0),.I_ddr_clk(dc),
  .I_display_pause(1'b0),.I_video_out_rd_busy(rb),.O_video_in_wr_busy(wb),.O_video_out_rp(rp),
  .O_ddr_user_wr_en(wren),.O_ddr_user_addr(wa),.O_ddr_user_wr_data(wd),.I_ddr_user_ready(ready),
  .O_fifo_event_counts(),.I_latency_tag(tag),.O_latency_tag(wr_tag),.O_camera_fifo_full(wf));
 video_out vo(.I_rst_n(rst_n),.I_ddr_clk(dc),.O_video_out_rd_busy(rb),.I_video_in_wr_busy(wb),
  .I_video_out_rp(rp),.O_ddr_user_rd_en(rden),.O_ddr_user_addr(ra),.I_ddr_user_ready(ready),
  .I_ddr_user_rd_valid(rvalid),.I_ddr_user_rd_data(rdata),.I_dsi_clk(hc),.I_video_vsync(vs),
  .I_video_rd_en(de),.O_vdieo_data(pixel),.O_read_select(read_select),.O_selected_slot(read_slot),.O_fifo_underflow(underflow));
 mc_to_user_interface mc(.I_clk(dc),.I_rst_n(rst_n),.I_ddr_user_wr_en(wren),.I_ddr_user_rd_en(rden),
  .I_ddr_user_addr(ua),.I_ddr_user_wr_data(wd),.O_ddr_user_ready(ready),
  .O_ddr_user_rd_valid(),.O_ddr_user_rd_data(),.O_mc_app_en(app_en),.O_mc_app_addr(app_addr),
  .O_mc_app_cmd(app_cmd),.I_mc_app_rdy(app_ready),.O_mc_app_wdf_wren(app_we),.O_mc_app_wdf_data(app_data),
  .O_mc_app_wdf_end(),.O_mc_app_wdf_mask(),.I_mc_app_wdf_rdy(app_ready),
  .I_mc_app_rd_data(rdata),.I_mc_app_rd_data_end(rvalid),.I_mc_app_rd_data_valid(rvalid),.O_command_full(cmdfull));
 latency_slot_journal #(.WORDS(960))journal(dc,rst_n,wren,wa,wr_tag,rden,rvalid,
  cmdfull||(wren&&rden),read_select,read_slot,gray[0],selected,event_toggle,read_bad);
 hdmi_mixer #(.IMG_WIDTH(1280),.IMG_HEIGHT(4)) mixer(.I_clk(hc),.I_rst_n(rst_n),.I_capture_toggle(1'b0),
  .I_video_vsync(!vs),.I_video_hsync(1'b0),.I_video_de(de),.I_video_user(user),.I_video_last(last),
  .I_debug_status(4'b1111),.O_video_rd_en(),.I_video_rd_data(pixel),.O_hdmi_vsync(),.O_hdmi_hsync(),
  .O_hdmi_de(hdmi_de),.O_hdmi_data(hdmi_rgb));
 latency_display_meter #(.PIXELS(5120))meter(hc,rst_n,tick,vs,hdmi_de,underflow,selected,event_toggle,read_bad,
  lat,mn,mx,age,fid,sid,samples,errors,status);
 integer n;integer committed=0,checked_images=0,checked_pixels=0,repetitions=0;
 realtime capture_time[0:31],first_display;
 integer out_x=0,out_count=0;reg active=0,vs_old=0;
 always @(posedge dc)begin
  if(!rst_n)begin dcycle<=0;response_valid<=0;end
  else begin
   dcycle<=dcycle+1;
   if(app_en && app_we)memory[index_for(app_addr)]<=app_data;
   response_valid<={response_valid[38:0],app_en && app_cmd==1};
   response_addr[0]<=app_addr;
   for(integer i=1;i<40;i=i+1)response_addr[i]<=response_addr[i-1];
   if(wren && wr_tag[1] && wr_tag[0])committed=committed+1;
  end
 end
 always @(posedge hc)begin
  if(rst_n)begin
   vs_old<=vs;
   if(vs && !vs_old)begin
    if(active && meter.tuple[0] && !meter.frame_bad && !read_bad && out_count==5120)begin
     if(meter.tuple[84:53]!==32'd1)$fatal(1,"session mismatch");
     if(meter.tuple[52:21]>=12)$fatal(1,"impossible frame identity");
     if($abs((first_display-capture_time[meter.tuple[52:21]])/10000.0-meter.start_age)>2.1)
      $fatal(1,"timestamp mismatch actual%f tag%0d",(first_display-capture_time[meter.tuple[52:21]])/10000.0,meter.start_age);
     checked_images=checked_images+1;
     if(meter.same)repetitions=repetitions+1;
    end
    active=0;out_count=0;out_x=0;
   end
   if(hdmi_de)begin
    if(!active)first_display=$realtime;
    active=1;out_count=out_count+1;
    if(meter.tuple_ready && meter.tuple[0] && !meter.frame_bad && !read_bad && out_x>200)begin
     if(hdmi_rgb!=={3{8'(meter.tuple[52:21]+1)}})
      $fatal(1,"wrong actual displayed payload fid%0d x%0d got%h",meter.tuple[52:21],out_x,hdmi_rgb);
     checked_pixels=checked_pixels+1;
    end
    out_x=out_x==1279?0:out_x+1;
   end
  end
 end
 initial begin
  for(n=0;n<16384;n=n+1)memory[n]=0;
  repeat(20)@(negedge hc);rst_n=1;
  fork
   begin
    for(integer f=0;f<12;f=f+1)begin
     @(negedge cc);ru=1;rv=1;rl=0;capture_time[f]=$realtime+20;
     for(integer b=1;b<1280;b=b+1)begin @(negedge cc);ru=0;rv=1;rl=b%320==319;end
     @(negedge cc);rv=0;rl=0;pu=1;
     @(negedge cc);pu=0;repeat(40)@(negedge cc);
     rgb={16{8'(f+1)}};
     for(integer b=0;b<960;b=b+1)begin @(negedge cc);pv=1;end
     @(negedge cc);pv=0;repeat(4000)@(negedge cc);
    end
   end
   begin
    for(integer f=0;f<17;f=f+1)begin
     @(negedge hc);vs=1;repeat(10)@(negedge hc);vs=0;
     repeat(1000)@(negedge hc);
     for(integer y=0;y<4;y=y+1)begin
      for(integer x=0;x<1280;x=x+1)begin @(negedge hc);de=1;user=x==0 && y==0;last=x==1279;end
      @(negedge hc);de=0;user=0;last=0;repeat(369)@(negedge hc);
     end
     repeat(12000)@(negedge hc);
    end
    @(negedge hc);vs=1;repeat(20)@(negedge hc);
   end
  join
  if(committed!=12 || checked_images<8 || checked_pixels<20000 || repetitions<1 || samples<6)
   $fatal(1,"insufficient qualified images commits%0d images%0d pixels%0d repeats%0d samples%0d",committed,checked_images,checked_pixels,repetitions,samples);
  $display("PASS native complete DDR/mixer latency path commits=%0d images=%0d pixels=%0d repeats=%0d samples=%0d",committed,checked_images,checked_pixels,repetitions,samples);$finish;
 end
 initial begin #6000000;$fatal(1,"timeout");end
endmodule
