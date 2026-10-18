`timescale 1ns / 1ps
// Four RGB888 pixels per beat -> display gray and thresholded binary.
// AWB lane format is {R[23:16], G[15:8], B[7:0]} in every 24-bit lane.
// Y = (77R + 150G + 29B + 128) >> 8, implemented with shift/add terms.
module rgb_effects_96 (
    input [95:0] I_rgb,
    input [7:0] I_binary_threshold,
    output [95:0] O_gray,
    output [95:0] O_binary
);
    function [15:0] luma16;
        input [7:0] r, g, b;
        reg [15:0] r_term, g_term, b_term;
        begin
            r_term = {8'd0,r} + ({8'd0,r} << 2)
                   + ({8'd0,r} << 3) + ({8'd0,r} << 6);
            g_term = ({8'd0,g} << 1) + ({8'd0,g} << 2)
                   + ({8'd0,g} << 4) + ({8'd0,g} << 7);
            b_term = {8'd0,b} + ({8'd0,b} << 2)
                   + ({8'd0,b} << 3) + ({8'd0,b} << 4);
            luma16 = r_term + g_term + b_term + 16'd128;
        end
    endfunction

    wire [15:0] luma[0:3];
    wire [7:0] y[0:3];
    genvar lane;
    generate for (lane = 0; lane < 4; lane = lane + 1) begin : g_lane
        assign luma[lane] = luma16(
            I_rgb[lane*24+23 -: 8],
            I_rgb[lane*24+15 -: 8],
            I_rgb[lane*24+7  -: 8]);
        assign y[lane] = luma[lane][15:8];
        assign O_gray[lane*24 +: 24] = {y[lane],y[lane],y[lane]};
        assign O_binary[lane*24 +: 24] =
            (y[lane] >= I_binary_threshold) ? 24'hffffff : 24'h000000;
    end endgenerate
endmodule
