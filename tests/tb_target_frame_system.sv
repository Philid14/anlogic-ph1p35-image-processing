`timescale 1ns/1ps
// Actual MAIN controller, vendor soft FIFOs, 96->128 packer, MC command FIFO,
// video_out and HDMI mixer. DDR storage/service is an explicit bounded model.
// RAW and post-AWB stimuli share one synthetic scene, not a sensor/ISP model.
module tb_target_frame_system;
    reg csi_clk=0,ddr_clk=0,hdmi_clk=0,rst_n=0;
    // Nominal clocks from the actual synthesized clock summary. The previous
    // incomplete run used 62.5/100/71.429 MHz; it is not nominal-clock evidence.
    always #8.334 csi_clk=~csi_clk;
    always #7.5 ddr_clk=~ddr_clk;
    always #6.6665 hdmi_clk=~hdmi_clk;
    reg raw_valid=0,raw_sof=0,raw_eol=0,native_frame_end=0;
    reg awb_user=0,awb_valid=0,awb_last=0;
    reg [95:0] awb_rgb=0;
    reg [95:0] rgb_delay[0:28];
    reg [28:0] vdelay=0,udelay=0;
    wire packed_valid,packed_user; wire [127:0] packed_rgb;
    data_96bit_to_128bit packer(.I_clk(csi_clk),.I_rst_n(rst_n),
        .I_96b_frame_start(udelay[28]),.I_96b_valid(vdelay[28]),.I_96b_data(rgb_delay[28]),
        .O_128b_frame_start(packed_user),.O_128b_valid(packed_valid),.O_128b_data(packed_rgb));
    wire user_ready,user_read_valid,user_write_enable,user_read_enable;
    wire [127:0] user_read_data,user_write_data; wire [24:0] user_address;
    wire [23:0] display_rgb;
    wire [31:0] fifo_counts; wire [63:0] display_tick;
    wire display_metadata_receive,display_metadata_online,display_scan_fault;
    wire [505:0] display_metadata;
    wire [15:0] dropped_frames,cancelled_frames,metadata_faults;
    wire vtvs,vths,vtde,vtuser,vtlast;
    wire rd_en;
    wire mc_en,mc_wren,mc_end;
    wire [24:0] mc_addr; wire [2:0] mc_cmd;
    wire [127:0] mc_data; wire [31:0] mc_mask;
    reg mc_ready=1;
    reg [7:0] read_pipe_valid=0;
    reg [127:0] read_pipe[0:7];
    target_frame_system dut(
        .rst_n(rst_n),.csi_clk(csi_clk),.ddr_clk(ddr_clk),.hdmi_clk(hdmi_clk),.calib_ready(1'b1),
        .raw_valid(raw_valid),.raw_sof(raw_sof),.raw_eol(raw_eol),.native_frame_end(native_frame_end),.packet_error(1'b0),
        .awb_user(awb_user),.awb_valid(awb_valid),.awb_last(awb_last),.awb_rgb(awb_rgb),
        .packed_user(packed_user),.packed_valid(packed_valid),.packed_rgb(packed_rgb),
        .user_ready(user_ready),.user_read_valid(user_read_valid),.user_read_data(user_read_data),
        .mc_write_accept(mc_en && mc_cmd==0 && mc_wren),.mc_write_address(mc_addr),
        .user_write_enable(user_write_enable),.user_read_enable(user_read_enable),.user_address(user_address),
        .user_write_data(user_write_data),.display_vsync(!vtvs),.display_read_enable(rd_en),.display_rgb(display_rgb),
        .fifo_counts(fifo_counts),.display_tick(display_tick),.display_metadata_receive(display_metadata_receive),
        .display_metadata(display_metadata),.display_metadata_online(display_metadata_online),.display_scan_fault(display_scan_fault),
        .dropped_frames(dropped_frames),.cancelled_frames(cancelled_frames),.metadata_faults(metadata_faults));
    mc_to_user_interface command_fifo(.I_clk(ddr_clk),.I_rst_n(rst_n),
        .I_ddr_user_wr_en(user_write_enable),.I_ddr_user_rd_en(user_read_enable),.I_ddr_user_addr(user_address),
        .I_ddr_user_wr_data(user_write_data),.O_ddr_user_ready(user_ready),.O_ddr_user_rd_valid(user_read_valid),.O_ddr_user_rd_data(user_read_data),
        .O_mc_app_en(mc_en),.O_mc_app_addr(mc_addr),.O_mc_app_cmd(mc_cmd),.I_mc_app_rdy(mc_ready),
        .O_mc_app_wdf_wren(mc_wren),.O_mc_app_wdf_data(mc_data),.O_mc_app_wdf_end(mc_end),.O_mc_app_wdf_mask(mc_mask),
        .I_mc_app_wdf_rdy(mc_ready),.I_mc_app_rd_data(read_pipe[7]),.I_mc_app_rd_data_end(read_pipe_valid[7]),
        .I_mc_app_rd_data_valid(read_pipe_valid[7]));
    uivtc #(.H_ActiveSize(1280),.H_FrameSize(1650),.H_SyncStart(1390),.H_SyncEnd(1430),
        .V_ActiveSize(720),.V_FrameSize(750),.V_SyncStart(725),.V_SyncEnd(730)) vtc(
        .I_vtc_rstn(rst_n),.I_vtc_clk(hdmi_clk),.O_vtc_vs(vtvs),.O_vtc_hs(vths),.O_vtc_de_valid(vtde),.O_vtc_user(vtuser),.O_vtc_last(vtlast));
    wire [23:0] mixed_rgb; wire mixed_de,mixed_hs,mixed_vs;
    hdmi_mixer #(.H_OFFSET(0),.V_OFFSET(0)) mixer(
        .I_clk(hdmi_clk),.I_rst_n(rst_n),.I_video_vsync(vtvs),.I_video_hsync(vths),.I_video_de(vtde),
        .I_video_user(vtuser),.I_video_last(vtlast),.I_debug_status(4'd0),.O_video_rd_en(rd_en),.I_video_rd_data(display_rgb),
        .O_hdmi_vsync(mixed_vs),.O_hdmi_hsync(mixed_hs),.O_hdmi_de(mixed_de),.O_hdmi_data(mixed_rgb));
    reg [127:0] memory[0:691199];
    integer slot_source[0:3]; integer key_source[0:63];
    integer native_cycle=0,source_frame=0,line_cycle,source_line,i,lane,x,y;
    integer dc=0,slot_index,word_index,byte_index,pixel_index,channel,pixel_x,pixel_y;
    integer checks=0,writes=0,reads=0,commits=0,metadata_packets=0;
    reg [23:0] expected_pixel;
    function [23:0] pixel(input integer f,input integer px,input integer py);
        reg [7:0] gray;
        begin
            gray=(f+1)*12;
            if(px>=400+(f%3)*40 && px<480+(f%3)*40 && py>=200 && py<240) pixel=24'he02020;
            else pixel={gray,gray,gray};
        end
    endfunction
    function integer address_slot(input [24:0] a);
        begin address_slot=(a>=21000000) ? 3 : (a>=14000000) ? 2 : (a>=7000000) ? 1 : 0; end
    endfunction
    function integer address_word(input [24:0] a);
        begin address_word=(a-address_slot(a)*7000000)/8; end
    endfunction
    task check(input bit good,input string label);
        begin checks=checks+1; if(!good) begin
            $display("FAIL %s t=%0t src=%0d addr=%0d words=%0d",label,$time,source_frame,mc_addr,word_index); $fatal(1);
        end end
    endtask
    always @(negedge csi_clk) begin
        if(rst_n) begin
            source_frame=native_cycle/500000; source_line=(native_cycle%500000)/500; line_cycle=native_cycle%500;
            raw_valid=source_frame<10 && source_line<720 && line_cycle<400 && line_cycle%5!=4;
            raw_sof=raw_valid && source_line==0 && line_cycle==0;
            raw_eol=raw_valid && line_cycle==398;
            native_frame_end=source_frame<10 && source_line==720 && line_cycle==0;
            awb_user=source_frame<10 && source_line==1 && line_cycle==0;
            awb_valid=source_frame<10 && source_line>=2 && source_line<722 && line_cycle<320;
            awb_last=awb_valid && line_cycle==319;
            for(lane=0;lane<4;lane=lane+1)
                awb_rgb[95-24*lane-:24]=pixel(source_frame,line_cycle*4+lane,source_line-2);
            native_cycle=native_cycle+1;
        end
    end
    always @(posedge csi_clk) begin
        rgb_delay[0]<=awb_rgb; vdelay<={vdelay[27:0],awb_valid}; udelay<={udelay[27:0],awb_user};
        for(i=1;i<29;i=i+1) rgb_delay[i]<=rgb_delay[i-1];
        if(dut.capture_start) begin
            check(dut.capture_frame<64,"bounded test identity map");
            key_source[dut.capture_frame]=source_frame;
        end
        if(dut.grant_receive && dut.grant[98]) begin
            check(dut.grant[65:34]<64,"grant key range");
            slot_source[dut.grant[33:32]]=key_source[dut.grant[65:34]];
        end
    end
    integer k;
    always @(posedge ddr_clk) begin
        dc=dc+1; mc_ready<=dc%29>=3;
        read_pipe_valid<={read_pipe_valid[6:0],mc_en && mc_cmd==1};
        for(k=1;k<8;k=k+1) read_pipe[k]<=read_pipe[k-1];
        if(mc_en) begin
            slot_index=address_slot(mc_addr); word_index=address_word(mc_addr);
            check(word_index>=0 && word_index<172800,"DDR requests remain inside selected frame");
            if(mc_cmd==0) begin
                check(slot_source[slot_index]>=0,"no writer before allocation/grant");
                for(byte_index=0;byte_index<16;byte_index=byte_index+1) begin
                    pixel_index=(word_index*16+byte_index)/3;
                    channel=(word_index*16+byte_index)%3;
                    expected_pixel=pixel(slot_source[slot_index],pixel_index%1280,pixel_index/1280);
                    check(mc_data[127-byte_index*8-:8]==(expected_pixel>>(8*(2-channel)) & 8'hff),"actual 96->128 bytes and MC write acceptance");
                end
                memory[slot_index*172800+word_index]<=mc_data; writes=writes+1;
            end else begin
                read_pipe[0]<=memory[slot_index*172800+word_index]; reads=reads+1;
            end
        end
        if(dut.committed) begin commits=commits+1; $display("COMMIT %0d source=%0d tick=%0d",commits,slot_source[dut.write_slot],dut.ddr_tick); end
    end
    integer output_x=0,output_y=0,output_frame=-1,output_checks=0;
    reg mixed_de_previous=0,mixed_vs_previous=0;
    integer selected_source=-1;
    always @(posedge hdmi_clk) begin
        if(display_metadata_receive) begin
            metadata_packets=metadata_packets+1;
            selected_source=key_source[display_metadata[247:216]];
        end
        #1;
        if(mixed_vs_previous && !mixed_vs) begin output_x=0; output_y=0; end
        mixed_vs_previous=mixed_vs;
        if(mixed_de) begin
            if(selected_source>=0 && !(output_x<160 && output_y<160) &&
               !(output_x>=375 && output_x<575 && output_y>=120 && output_y<144)) begin
                if(mixed_rgb!==pixel(selected_source,output_x,output_y))
                    $display("PIXEL_MISMATCH x=%0d y=%0d selected_source=%0d got=%h expected=%h read_rgb=%h",output_x,output_y,selected_source,mixed_rgb,pixel(selected_source,output_x,output_y),display_rgb);
                check(mixed_rgb===pixel(selected_source,output_x,output_y),"actual HDMI pixel matches selected acquisition frame and coordinate");
                output_checks=output_checks+1;
            end
            output_x=output_x+1;
        end
        if(mixed_de_previous && !mixed_de) begin output_x=0; output_y=output_y+1; end
        mixed_de_previous=mixed_de;
    end
    initial begin
        for(i=0;i<4;i=i+1) slot_source[i]=-1;
        for(i=0;i<64;i=i+1) key_source[i]=-1;
        #40; rst_n=1;
        #115000000;
        check(commits>=5 && metadata_packets>=3 && output_checks>921600,"multiple complete 720p frames checked");
        check(fifo_counts[15:0]==0 && metadata_faults==0,"no steady FIFO or metadata faults in bounded service model");
        $display("PASS TARGET_FRAME_SYSTEM checks=%0d writes=%0d reads=%0d commits=%0d",checks,writes,reads,commits); $finish;
    end
    initial begin #120000000; $fatal(1,"timeout"); end
endmodule
