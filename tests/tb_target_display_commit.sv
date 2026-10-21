`timescale 1ns/1ps
module tb_target_display_commit;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0; reg [63:0] now_tick=110;
    reg metadata_receive=0; reg [505:0] metadata=0;
    reg metadata_online=1,scan_fault=0;
    reg [23:0] video_rgb=24'h234567;
    reg video_de=0,video_hs=0,video_vs=0,blanking_start=0;
    wire [23:0] out_rgb,off_rgb; wire out_de,out_hs,out_vs;
    wire off_de,off_hs,off_vs;
    wire [7:0] glyph_char; wire [3:0] glyph_row; wire [15:0] glyph_bits;
    wire glyph_request,display_enable,first_pixel;
    wire [31:0] pixel_session,pixel_frame,pixel_generation;
    wire [1:0] pixel_slot; wire [15:0] hidden_count,late_count;
    target_display_commit #(.MAX_AGE_TICKS(1000),.MAX_SCAN_TICKS(20)) dut(.*);
    target_display_commit #(.ENABLE(0),.MAX_AGE_TICKS(1000),.MAX_SCAN_TICKS(20)) off_dut(
        .clk(clk),.rst_n(rst_n),.now_tick(now_tick),.metadata_receive(metadata_receive),.metadata(metadata),
        .metadata_online(metadata_online),.scan_fault(scan_fault),.video_rgb(video_rgb),
        .video_de(video_de),.video_hs(video_hs),.video_vs(video_vs),.blanking_start(blanking_start),
        .glyph_bits(16'hffff),.out_rgb(off_rgb),.out_de(off_de),.out_hs(off_hs),.out_vs(off_vs));
    osd_char_lib font(.I_char(glyph_char),.I_row(glyph_row),.O_row_bits(glyph_bits));
    integer checks=0,px,py,n,scenario;
    string line0="RED X0450 Y350";
    string line1="N012345 TRACK ";
    task check(input bit good,input string message);
        begin checks=checks+1; if(!good) begin $display("FAIL scenario=%0d x=%0d y=%0d %s",scenario,px,py,message); $fatal(1); end end
    endtask
    task step;
        begin @(posedge clk); #1;
            if(rst_n) begin
                check(off_rgb===video_rgb && off_de==video_de && off_hs==video_hs && off_vs==video_vs,"TARGET off exact uniform video pipeline");
                check(out_de==video_de && out_hs==video_hs && out_vs==video_vs,"DE/HS/VS aligned to output pixel");
            end
            @(negedge clk);
        end
    endtask
    task prepare(input bit send_packet,input integer wait_cycles);
        begin
            video_de=0; blanking_start=1; step; blanking_start=0; step;
            if(send_packet) begin metadata_receive=1; step; metadata_receive=0; end
            repeat(wait_cycles) step;
        end
    endtask
    task default_packet;
        begin
            metadata={192'd0,2'd2,32'd9,32'd1,32'd7,64'd100,
                32'd1,32'd7,1'b1,2'd2,2'd0,20'd12345,
                11'd400,11'd500,11'd450,10'd300,10'd400,10'd350};
        end
    endtask
    task start_scan(input bit expected_visible);
        begin
            video_de=1; px=0; py=0; step;
            check(first_pixel && display_enable==expected_visible,"first HDMI pixel rechecks complete annotation");
            if(expected_visible) check(pixel_session==1 && pixel_frame==7 && pixel_generation==9 && pixel_slot==2,"pixel FrameRef immutable snapshot");
        end
    endtask
    initial begin
        #2; step; rst_n=1; step;
        for(scenario=0;scenario<14;scenario=scenario+1) begin
            default_packet; now_tick=110; metadata_online=1; scan_fault=0;
            case(scenario)
                3: metadata[151:120]=2;
                4: metadata[119:88]=6;
                5: metadata[87]=0;
                7: metadata_online=0;
                8: scan_fault=1;
                9: metadata[215:152]=200;
                10:now_tick=1101;
                11:now_tick=1081;
                12:now_tick=2000;
                default:begin end
            endcase
            prepare(scenario!=0 && scenario!=13,scenario==1 ? 3 : 145);
            start_scan(scenario==2 || scenario==6);
            if(scenario==6) begin
                metadata[247:216]=99; metadata[119:88]=99;
                metadata_receive=1; step; metadata_receive=0;
                check(pixel_frame==7,"late result cannot replace scan identity");
                check(late_count==1,"late packet counted");
            end
            video_de=0; step;
        end
        // Real full-width raster reaches text and diagnostic rows without any
        // hierarchical coordinate pokes. The normal glyph string is literal.
        scenario=14; default_packet; now_tick=110; metadata_online=1; scan_fault=0;
        prepare(1,145);
        for(py=0;py<720;py=py+1) begin
            for(px=0;px<1280;px=px+1) begin
                video_de=1; video_rgb={py[7:0],px[7:0],8'h35};
                #1;
                if(px>=24 && px<248 && (py==640 || py==658) && (px-24)%16==0) begin
                    n=(px-24)/16;
                    check(glyph_char==(py==640 ? line0[n] : line1[n]),"literal glyphs share same committed box/count/state");
                end
                step;
                if(px==400 && py==300) check(out_rgb==24'h00ff00,"same-frame box pixel");
                if(px==450 && py==350) check(out_rgb==24'hffff00,"same-frame center cross");
                if(px==20 && py==20) check(out_rgb==video_rgb,"Logo protected region");
            end
            video_de=0; repeat(370) step;
        end
        check(display_enable,"static scan unchanged while time within declared bound");
        // Display clock continues even when the observation side produces no
        // further packets; the actual master age expires the group next scan.
        now_tick=2000; prepare(1,145); start_scan(0);
        scan_fault=1; step; check(!display_enable,"pixel-side fault closes complete group");
        $display("PASS DISPLAY_COMMIT checks=%0d",checks); $finish;
    end
    initial begin #20000000; $fatal(1,"timeout"); end
endmodule
