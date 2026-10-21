`timescale 1ns/1ps
module tb_video_read_controls #(parameter integer ALIGN_ENABLE=1);
    reg clk=0,ddr_clk=0,rst_n=0;
    always #6.6665 clk=~clk;
    always #7.5 ddr_clk=~ddr_clk;
    reg de=0,hs=0,vs=0,user=0,last=0;
    wire read_enable,av,ah,ad,au,al;
    generate if(ALIGN_ENABLE) begin
        video_read_controls align(.*,.aligned_vs(av),.aligned_hs(ah),.aligned_de(ad),.aligned_user(au),.aligned_last(al));
    end else begin
        assign {av,ah,ad,au,al}={vs,hs,de,user,last};
        assign read_enable=de;
    end endgenerate
    reg inject_valid=0,flush=1; reg [127:0] inject_data=0;
    wire [23:0] reader_rgb;
    video_out #(.TRANSACTIONAL(1)) reader(
        .I_rst_n(rst_n),.I_ddr_clk(ddr_clk),.I_video_in_wr_busy(1'b0),
        .I_video_out_rp(2'd0),.I_ddr_user_ready(1'b0),
        .I_ddr_user_rd_valid(inject_valid),.I_ddr_user_rd_data(inject_data),
        .I_dsi_clk(clk),.I_video_vsync(vs),.I_video_rd_en(read_enable),.O_vdieo_data(reader_rgb),
        .I_scan_commit(1'b0),.I_allow_read(1'b0),.I_transaction_flush(flush));
    wire [23:0] mixed_rgb; wire mixed_de,mixed_hs,mixed_vs;
    hdmi_mixer mixer(.I_clk(clk),.I_rst_n(rst_n),.I_video_vsync(av),.I_video_hsync(ah),.I_video_de(ad),
        .I_video_user(au),.I_video_last(al),.I_debug_status(4'd0),.I_video_rd_data(reader_rgb),
        .O_hdmi_vsync(mixed_vs),.O_hdmi_hsync(mixed_hs),.O_hdmi_de(mixed_de),.O_hdmi_data(mixed_rgb),
        .I_target_glyph_request(1'b0),.I_target_glyph_char(8'd0),.I_target_glyph_row(4'd0));
    function [23:0] pixel(input integer x);
        pixel={x[7:0],x[10:3],(x[7:0]^8'h96)};
    endfunction
    function [127:0] word_data(input integer index);
        integer b,p,c;reg[23:0] rgb;
        begin
            for(b=0;b<16;b=b+1) begin
                p=(16*index+b)/3;c=(16*index+b)%3;rgb=pixel(p);
                word_data[127-8*b-:8]=(rgb>>(8*(2-c)))&255;
            end
        end
    endfunction
    integer n,x=0,checked=0,received=0;
    reg [4:0] delayed_de=0;
    always @(posedge clk) begin
        if(rst_n) begin
            delayed_de<={delayed_de[3:0],de};
            #1;
            if(mixed_de!==(ALIGN_ENABLE ? delayed_de[4] : delayed_de[2])) $fatal(1,"DE latency mismatch");
            if(mixed_de) begin
                if(x>=160) begin
                    if(mixed_rgb!==pixel(x)) $fatal(1,"pixel x=%0d got=%h expected=%h",x,mixed_rgb,pixel(x));
                    checked=checked+1;
                end
                x=x+1;received=received+1;
            end
        end
    end
    initial begin
        #40;rst_n=1;
        repeat(20) @(negedge ddr_clk);flush=0;
        repeat(100) @(negedge ddr_clk);
        for(n=0;n<240;n=n+1) begin inject_valid=1;inject_data=word_data(n);@(negedge ddr_clk);end
        inject_valid=0;repeat(12) @(negedge clk);
        user=1;@(negedge clk);user=0;
        for(n=0;n<1280;n=n+1) begin de=1;last=(n==1279);@(negedge clk);end
        de=0;last=0;repeat(12) @(negedge clk);
        if(received!=1280 || checked!=1120) $fatal(1,"incomplete line received=%0d checked=%0d",received,checked);
        $display("PASS VIDEO_READ_CONTROLS pixels=%0d checked=%0d",received,checked);$finish;
    end
endmodule
