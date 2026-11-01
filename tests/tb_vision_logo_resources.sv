`timescale 1ns/1ps
module tb_vision_logo_resources;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,vs=0,hs=0,de=0,user=0,last=0;reg[23:0] rgb=0;
    wire rv0,rv1,ov0,ov1,oh0,oh1,od0,od1;wire[23:0] p0,p1;
    reference_mixer reference(.I_clk(clk),.I_rst_n(rst_n),.I_video_vsync(vs),.I_video_hsync(hs),
      .I_video_de(de),.I_video_user(user),.I_video_last(last),.I_debug_status(4'hf),
      .O_video_rd_en(rv0),.I_video_rd_data(rgb),.O_hdmi_vsync(ov0),.O_hdmi_hsync(oh0),.O_hdmi_de(od0),.O_hdmi_data(p0));
    hdmi_mixer #(.LOGO_ERAM_ENABLE(1)) dut(.I_clk(clk),.I_rst_n(rst_n),.I_video_vsync(vs),.I_video_hsync(hs),
      .I_video_de(de),.I_video_user(user),.I_video_last(last),.I_debug_status(4'hf),
      .O_video_rd_en(rv1),.I_video_rd_data(rgb),.O_hdmi_vsync(ov1),.O_hdmi_hsync(oh1),.O_hdmi_de(od1),.O_hdmi_data(p1));
    reg [14:0] rom_addr=0;wire [24:0] old_pixel,new_pixel;
    reg [24:0] previous_pixel;reg rom_done=0;
    anlogic_logo_rom old_rom(.I_addr(rom_addr),.O_pixel(old_pixel));
    vision_logo_palette new_rom(.clk(clk),.address(rom_addr),.pixel(new_pixel));
    integer r;
    initial begin
      #100;
      for(r=0;r<32770;r=r+1)begin
        @(negedge clk);rom_addr=r[14:0];#1;
        @(posedge clk);#1;
        if(r>0 && new_pixel!==previous_pixel)$fatal(1,"ROM mismatch address%0d got%h expected%h",r-1,new_pixel,previous_pixel);
        previous_pixel=old_pixel;
      end
      rom_done=1;
    end
    integer x,y,f,n,cycles=0,pixels=0;reg[31:0] random_state=32'h9abc1234;
    task tick;input v,u,l,s,h;begin
      @(negedge clk);de=v;user=u;last=l;vs=s;hs=h;
      random_state={random_state[30:0],random_state[31]^random_state[21]^random_state[1]^random_state[0]};rgb=random_state[23:0];
      @(posedge clk);#1;
      if({rv0,ov0,oh0,od0,p0}!=={rv1,ov1,oh1,od1,p1})
        $fatal(1,"FAIL mixer cycle %0d old %h new %h",cycles,p0,p1);
      cycles=cycles+1;if(od1)pixels=pixels+1;
    end endtask
    initial begin
      repeat(4)tick(0,0,0,0,0);rst_n=1;
      for(f=0;f<2;f=f+1)begin
        tick(0,1,0,1,0);repeat(5)tick(0,0,0,0,0);
        for(y=0;y<720;y=y+1)begin
          for(x=0;x<1280;x=x+1)tick(1,0,x==1279,0,0);
          repeat(3)tick(0,0,0,0,1);
        end
        repeat(20)tick(0,0,0,0,0);
      end
      // Reset and recover from a partial, irregular stream as well.
      for(n=0;n<5000;n=n+1)tick(n%7!=3,n%1093==0,n%128==127,0,n%13==0);
      rst_n=0;repeat(4)tick(0,0,0,0,0);rst_n=1;
      for(n=0;n<5000;n=n+1)tick(n%5!=2,n==0,n%128==127,0,n%17==0);
      repeat(8)tick(0,0,0,0,0);
      if(!rom_done)$fatal(1,"ROM unfinished");
      $display("PASS mixer cycle equivalence %0d cycles / %0d active pixels; Logo/CNT, blanking, reset, unchanged sync/latency",cycles,pixels);$finish;
    end
endmodule
