`timescale 1ns/1ps
module tb_target_logo_equivalence;
    reg clk=0; always #5 clk=~clk;
    reg [14:0] address=15'h7fff;
    wire [24:0] original,optimized;
    anlogic_logo_rom reference_rom(.I_addr(address),.O_pixel(original));
    target_logo_palette dut_rom(.clk(clk),.address(address),.pixel(optimized));
    reg [24:0] expected0,expected1;
    integer n,x,y,checks=0;
    reg rst_n=0,vs=0,hs=0,de=0,user=0,last=0;
    reg [23:0] rgb=0;
    wire [23:0] old_rgb,new_rgb;
    wire old_de,old_hs,old_vs,new_de,new_hs,new_vs;
    hdmi_mixer_reference old_mixer(.I_clk(clk),.I_rst_n(rst_n),
        .I_video_vsync(vs),.I_video_hsync(hs),.I_video_de(de),
        .I_video_user(user),.I_video_last(last),.I_debug_status(4'd0),
        .I_video_rd_data(rgb),.O_hdmi_vsync(old_vs),.O_hdmi_hsync(old_hs),
        .O_hdmi_de(old_de),.O_hdmi_data(old_rgb),
        .I_target_glyph_request(1'b0),.I_target_glyph_char(8'd0),.I_target_glyph_row(4'd0));
    hdmi_mixer new_mixer(.I_clk(clk),.I_rst_n(rst_n),
        .I_video_vsync(vs),.I_video_hsync(hs),.I_video_de(de),
        .I_video_user(user),.I_video_last(last),.I_debug_status(4'd0),
        .I_video_rd_data(rgb),.O_hdmi_vsync(new_vs),.O_hdmi_hsync(new_hs),
        .O_hdmi_de(new_de),.O_hdmi_data(new_rgb),
        .I_target_glyph_request(1'b0),.I_target_glyph_char(8'd0),.I_target_glyph_row(4'd0));
    task step;
        begin
            @(posedge clk); #1;
            if(rst_n) begin
                checks=checks+1;
                if({new_rgb,new_de,new_hs,new_vs} !== {old_rgb,old_de,old_hs,old_vs})
                    $fatal(1,"mixer mismatch x=%0d y=%0d new=%h old=%h",x,y,new_rgb,old_rgb);
            end
            @(negedge clk);
        end
    endtask
    initial begin
        repeat(4) step;
        // Every address of the original interface, including transparent tail.
        for(n=0;n<32770;n=n+1) begin
            address=n[14:0]; #1;
            expected0=original;
            @(posedge clk); #1;
            if(n>0 && optimized !== expected1) $fatal(1,"ROM mismatch address=%0d",n-1);
            expected1=expected0;
            @(negedge clk);
        end
        rst_n=1; user=1; step; user=0;
        for(y=0;y<750;y=y+1) begin
            for(x=0;x<1650;x=x+1) begin
                de=(x<1280 && y<720); last=de && x==1279;
                vs=(y>=725 && y<730); hs=(x>=1390 && x<1430);
                rgb={x[7:0],y[7:0],(x[7:0]^y[7:0])};
                step;
            end
        end
        // Reset and a second frame start also preserve CNT and pipelines.
        rst_n=0; repeat(4) step; rst_n=1; user=1; step; user=0;
        repeat(10) step;
        $display("PASS LOGO_EQUIVALENCE rom_addresses=32768 mixer_cycles=%0d",checks);
        $finish;
    end
endmodule
