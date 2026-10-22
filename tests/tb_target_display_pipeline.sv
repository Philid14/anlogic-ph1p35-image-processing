`timescale 1ns/1ps
module tb_target_display_pipeline;
    reg clk=0;always #6.6665 clk=~clk;
    reg rst_n=0;reg[63:0] now_tick=110;
    reg metadata_receive=0,metadata_online=1,scan_fault=0;
    reg[505:0] metadata=0;
    reg[23:0] video_rgb=0;reg video_de=0,video_hs=0,video_vs=0,blanking_start=0;
    wire[23:0] out_rgb,old_rgb,off_rgb;
    wire out_de,out_hs,out_vs,old_de,old_hs,old_vs,off_de,off_hs,off_vs;
    wire[7:0] glyph_char,old_char;wire[3:0] glyph_row,old_row;
    wire[15:0] glyph_bits,old_bits;
    wire glyph_request,display_enable,first_pixel;
    wire[31:0] pixel_session,pixel_frame,pixel_generation;
    wire[1:0] pixel_slot;wire[15:0] hidden_count,late_count;
    target_display_commit #(.PIPELINE_GLYPH(1)) dut(.*);
    target_display_commit_reference old_dut(
        .clk(clk),.rst_n(rst_n),.now_tick(now_tick),.metadata_receive(metadata_receive),.metadata(metadata),
        .metadata_online(metadata_online),.scan_fault(scan_fault),.video_rgb(video_rgb),
        .video_de(video_de),.video_hs(video_hs),.video_vs(video_vs),.blanking_start(blanking_start),
        .out_rgb(old_rgb),.out_de(old_de),.out_hs(old_hs),.out_vs(old_vs),
        .glyph_char(old_char),.glyph_row(old_row),.glyph_bits(old_bits));
    target_display_commit #(.PIPELINE_GLYPH(1),.ENABLE(0)) off_dut(
        .clk(clk),.rst_n(rst_n),.now_tick(now_tick),.metadata_receive(metadata_receive),.metadata(metadata),
        .metadata_online(metadata_online),.scan_fault(scan_fault),.video_rgb(video_rgb),
        .video_de(video_de),.video_hs(video_hs),.video_vs(video_vs),.blanking_start(blanking_start),
        .out_rgb(off_rgb),.out_de(off_de),.out_hs(off_hs),.out_vs(off_vs),.glyph_bits(16'd0));
    osd_char_lib font(.I_char(glyph_char),.I_row(glyph_row),.O_row_bits(glyph_bits));
    osd_char_lib old_font(.I_char(old_char),.I_row(old_row),.O_row_bits(old_bits));
    reg[26:0] expected=0,off_expected=0;
    reg compare_pixels=0;
    integer checks=0,x=0,y=0;
    task check(input bit good,input string label);
        begin checks=checks+1;if(!good)$fatal(1,"%s x=%0d y=%0d got=%h expected=%h",label,x,y,out_rgb,expected[26:3]);end
    endtask
    task step;
        begin
            @(posedge clk);#0.1;
            if(rst_n && compare_pixels) begin
                check({out_rgb,out_de,out_hs,out_vs}===expected,"font/request pipeline preserves exact pixel and controls");
                check({off_rgb,off_de,off_hs,off_vs}===off_expected,"disabled TARGET uniform two-cycle video");
            end
            expected={old_rgb,old_de,old_hs,old_vs};off_expected={video_rgb,video_de,video_hs,video_vs};
            @(negedge clk);
        end
    endtask
    task prepare;
        begin
            video_de=0;blanking_start=1;step;blanking_start=0;step;
            metadata={192'd0,2'd2,32'd9,32'd1,32'd7,64'd100,
                32'd1,32'd7,1'b1,2'd2,2'd0,20'd12345,
                11'd400,11'd500,11'd450,10'd300,10'd400,10'd350};
            metadata_receive=1;step;metadata_receive=0;repeat(145)step;
        end
    endtask
    initial begin
        repeat(4)step;rst_n=1;repeat(4)step;compare_pixels=1;prepare;
        for(y=0;y<750;y=y+1) begin
            for(x=0;x<1650;x=x+1) begin
                video_de=(x<1280 && y<720);video_hs=(x>=1390 && x<1430);video_vs=(y>=725 && y<730);
                video_rgb={y[7:0],x[7:0],8'h35};step;
            end
        end
        video_de=0;repeat(4)step;
        // The last pipeline clock is part of the real first-pixel age check.
        compare_pixels=0;prepare;now_tick=83599;video_de=1;step;
        check(!first_pixel,"request edge is not final HDMI first-pixel event");
        now_tick=83600;step;
        check(first_pixel && out_de && !display_enable,"expired on actual output edge hides whole group");
        video_de=0;prepare;now_tick=83599;video_de=1;step;step;
        check(first_pixel && display_enable,"inclusive actual first-pixel age boundary");
        check(pixel_session==1 && pixel_frame==7 && pixel_generation==9 && pixel_slot==2,"committed FrameRef at actual output");
        scan_fault=1;step;check(!display_enable,"current output fault closes group immediately");
        $display("PASS DISPLAY_PIPELINE checks=%0d full_raster_cycles=1237500",checks);$finish;
    end
endmodule
