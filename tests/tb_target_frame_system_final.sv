`timescale 1ns/1ps
// Actual MAIN controller, vendor soft FIFOs, 96->128 packer, MC command FIFO,
// video_out and HDMI mixer. DDR storage/service is an explicit bounded model.
// RAW and post-AWB stimuli share one synthetic scene, not a sensor/ISP model.
module tb_target_frame_system;
    reg csi_clk=0,ddr_clk=0,hdmi_clk=0,rst_n=0,run_csi=1;
    // Nominal clocks from the actual synthesized clock summary. The previous
    // incomplete run used 62.5/100/71.429 MHz; it is not nominal-clock evidence.
    always begin #8.334;if(run_csi)csi_clk=~csi_clk;end
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
    wire [23:0] base_rgb;wire base_de,base_hs,base_vs;
    wire [7:0] glyph_char;wire [3:0] glyph_row;wire[15:0] glyph_bits;wire glyph_request;
    wire av,ah,ad,au,al;
    video_read_controls alignment(.clk(hdmi_clk),.rst_n(rst_n),
        .vs(vtvs),.hs(vths),.de(vtde),.user(vtuser),.last(vtlast),.read_enable(rd_en),
        .aligned_vs(av),.aligned_hs(ah),.aligned_de(ad),.aligned_user(au),.aligned_last(al));
    hdmi_mixer #(.H_OFFSET(0),.V_OFFSET(0),.TARGET_FONT_ENABLE(1)) mixer(
        .I_clk(hdmi_clk),.I_rst_n(rst_n),.I_video_vsync(av),.I_video_hsync(ah),.I_video_de(ad),
        .I_video_user(au),.I_video_last(al),.I_debug_status(4'd0),.I_video_rd_data(display_rgb),
        .O_hdmi_vsync(base_vs),.O_hdmi_hsync(base_hs),.O_hdmi_de(base_de),.O_hdmi_data(base_rgb),
        .I_target_glyph_request(glyph_request),.I_target_glyph_char(glyph_char),.I_target_glyph_row(glyph_row),.O_target_glyph_bits(glyph_bits));
    reg base_vs_previous=0;
    always @(posedge hdmi_clk) base_vs_previous<=base_vs;
    wire final_first,final_enabled;
    wire [31:0] final_session,final_frame,final_generation;wire[1:0] final_slot;
    target_display_commit #(.PIPELINE_GLYPH(1)) final_commit(
        .clk(hdmi_clk),.rst_n(rst_n),.now_tick(display_tick),
        .metadata_receive(display_metadata_receive),.metadata(display_metadata),
        .metadata_online(display_metadata_online),.scan_fault(display_scan_fault),
        .video_rgb(base_rgb),.video_de(base_de),.video_hs(base_hs),.video_vs(base_vs),
        .blanking_start(base_vs_previous && !base_vs),
        .out_rgb(mixed_rgb),.out_de(mixed_de),.out_hs(mixed_hs),.out_vs(mixed_vs),
        .glyph_char(glyph_char),.glyph_row(glyph_row),.glyph_request(glyph_request),.glyph_bits(glyph_bits),
        .first_pixel(final_first),.display_enable(final_enabled),.pixel_session(final_session),.pixel_frame(final_frame),
        .pixel_slot(final_slot),.pixel_generation(final_generation));
    wire [23:0] baseline_rgb;wire baseline_de,baseline_hs,baseline_vs;
    hdmi_mixer #(.TARGET_FONT_ENABLE(0)) baseline_mixer(
        .I_clk(hdmi_clk),.I_rst_n(rst_n),.I_video_vsync(av),.I_video_hsync(ah),.I_video_de(ad),
        .I_video_user(au),.I_video_last(al),.I_debug_status(4'd0),.I_video_rd_data(display_rgb),
        .O_hdmi_vsync(baseline_vs),.O_hdmi_hsync(baseline_hs),.O_hdmi_de(baseline_de),.O_hdmi_data(baseline_rgb),
        .I_target_glyph_request(1'b0),.I_target_glyph_char(8'd0),.I_target_glyph_row(4'd0));
    reg [26:0] baseline_d1=0,baseline_d2=0;
    always @(posedge hdmi_clk) begin
        baseline_d1<={baseline_rgb,baseline_de,baseline_hs,baseline_vs};baseline_d2<=baseline_d1;
    end
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
            if(f!=2 && f!=7 && px>=400+(f%3)*40 && px<480+(f%3)*40 && py>=200 && py<240) pixel=24'he02020;
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
    reg[505:0] selected_packet=0;
    reg gold_visible=0;
    integer visible_scans=0,absence_scans=0,expired_scans=0;
    integer bx,cx,box_source,char_column,char_row,char_bit;
    string text0,text1,diag0,diag1,font_path;
    reg[15:0] reference_font[0:4095];reg[7:0] gold_char;
    reg[23:0] gold_rgb;
    initial begin
        if(!$value$plusargs("FONT=%s",font_path))$fatal(1,"missing independent font data");
        $readmemh(font_path,reference_font);
    end
    always @(posedge hdmi_clk) begin
        if(display_metadata_receive) begin
            metadata_packets=metadata_packets+1;
            selected_source=key_source[display_metadata[247:216]];
            selected_packet=display_metadata;
            diag0=$sformatf("S%08h F%08h G%08h L%1h D%04h C%04h Q%04h    ",display_metadata[279:248],display_metadata[247:216],display_metadata[311:280],display_metadata[313:312],display_metadata[361:346],display_metadata[345:330],display_metadata[329:314]);
            diag1=$sformatf("D%04h R%04h W%04h I%04h V%04h C%04h S%04h T%04h O%04h ",display_metadata[505:490],display_metadata[489:474],display_metadata[473:458],display_metadata[457:442],display_metadata[441:426],display_metadata[425:410],display_metadata[409:394],display_metadata[393:378],display_metadata[377:362]);
            diag0=diag0.toupper();diag1=diag1.toupper();
            check(diag0.len()==54 && diag1.len()==54,"diagnostic text independent formatting length");
            if(display_metadata[87]) begin
                box_source=key_source[display_metadata[119:88]];bx=400+(box_source%3)*40;
                check(display_metadata[82:63]==3200 && display_metadata[62:52]==bx && display_metadata[51:41]==bx+79 && display_metadata[40:30]==bx+39 && display_metadata[29:20]==200 && display_metadata[19:10]==239 && display_metadata[9:0]==219,"full-resolution detector bounds/count/center retain positive source identity");
            end
        end
        #1;
        check({mixed_de,mixed_hs,mixed_vs}===baseline_d2[2:0],"final RGB/control pipeline exact length");
        if(final_first && selected_source>=0) begin
            gold_visible=selected_source>=5 && selected_source!=7 && display_tick>=selected_packet[215:152] && display_tick-selected_packet[215:152]<=83499;
            check(final_enabled==gold_visible,"actual final first-pixel visibility, same-frame hold and age");
            check(final_session==selected_packet[279:248] && final_frame==selected_packet[247:216] && final_generation==selected_packet[311:280] && final_slot==selected_packet[313:312],"final HDMI FrameRef equals actual leased read selection");
            if(gold_visible)visible_scans=visible_scans+1;
            if(selected_source==7 && !gold_visible)absence_scans=absence_scans+1;
            if(display_tick-selected_packet[215:152]>83499 && !gold_visible)expired_scans=expired_scans+1;
        end
        if(mixed_vs_previous && !mixed_vs) begin output_x=0; output_y=0; end
        mixed_vs_previous=mixed_vs;
        if(mixed_de) begin
            if(selected_source>=0) begin
                gold_rgb=pixel(selected_source,output_x,output_y);
                bx=400+(selected_source%3)*40;cx=bx+39;
                if((output_x<160 && output_y<160) || (output_x>=375 && output_x<575 && output_y>=120 && output_y<144))
                    gold_rgb=baseline_d2[26:3];
                else if(output_x>=24 && output_x<888 && output_y>=680 && output_y<712) begin
                    char_column=(output_x-24)/16;char_row=(output_y-680)%16;char_bit=15-(output_x-24)%16;
                    gold_char=(output_y<696) ? diag0[char_column] : diag1[char_column];
                    gold_rgb=reference_font[gold_char*16+char_row][char_bit] ? 24'hfff200 : 24'h101010;
                end else if(gold_visible) begin
                    if(output_x>=24 && output_x<248 && output_y>=640 && output_y<674) begin
                        text0=$sformatf("RED X%04d Y219",cx);text1="N003200 TRACK ";
                        char_column=(output_x-24)/16;char_row=(output_y<658 ? output_y-640 : output_y-658)%16;char_bit=15-(output_x-24)%16;
                        gold_char=(output_y<658) ? text0[char_column] : text1[char_column];
                        gold_rgb=reference_font[gold_char*16+char_row][char_bit] ? 24'hffffff : 24'h101010;
                    end else if((output_y==219 && output_x>=cx-12 && output_x<=cx+12) || (output_x==cx && output_y>=207 && output_y<=231))gold_rgb=24'hffff00;
                    else if(((output_y>=200 && output_y<=202) || (output_y>=237 && output_y<=239)) && output_x>=bx && output_x<=bx+79)gold_rgb=24'h00ff00;
                    else if(((output_x>=bx && output_x<=bx+2) || (output_x>=bx+77 && output_x<=bx+79)) && output_y>=200 && output_y<=239)gold_rgb=24'h00ff00;
                end
                if(mixed_rgb!==gold_rgb)$display("FINAL_MISMATCH x=%0d y=%0d source=%0d draw=%b got=%h expected=%h",output_x,output_y,selected_source,gold_visible,mixed_rgb,gold_rgb);
                check(mixed_rgb===gold_rgb,"final HDMI base/Logo/CNT/box/cross/text/diagnostic exact pixel");
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
        #210000000;
        check(commits>=5 && metadata_packets>=3 && output_checks>921600,"multiple complete 720p frames checked");
        check(fifo_counts[15:0]==0 && metadata_faults==0,"no steady FIFO or metadata faults in bounded service model");
        check(visible_scans>=2 && absence_scans>=1 && expired_scans>=1,"appearance movement absence and silent-source expiry all observed");
        $display("PASS TARGET_FINAL_SYSTEM checks=%0d writes=%0d reads=%0d commits=%0d visible=%0d absence=%0d expired=%0d",checks,writes,reads,commits,visible_scans,absence_scans,expired_scans); $finish;
    end
    initial begin #90000000;run_csi=0;#35000000;run_csi=1;end
    initial begin #220000000; $fatal(1,"timeout"); end
endmodule
