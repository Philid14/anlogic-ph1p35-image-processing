//======================================================================
// tb_overlay_align.v - text_overlay coordinate realignment (review 3.4)
//
// The panel is placed at (8,0) so the first active line shows glyph row 0.
// Before the frame/line realignment fix the x/y counters were only accumulated
// from de, so a burst of de without sync shifted the panel down by 6 lines and
// the glyph pixel at x=10 was lost. The test intentionally creates such a
// desynchronised burst, then starts a normal frame with vs/hs and requires the
// glyph pixel (16'hFFFF) at ox=10 of the first line.
//======================================================================
`timescale 1ns/1ps
module tb_overlay_align;
    localparam integer H  = 128;
    localparam integer V  = 64;
    localparam integer X0 = 8;
    localparam integer Y0 = 0;

    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst_n = 1'b0;

    reg        de = 1'b0, hs = 1'b0, vs = 1'b0;
    reg [23:0] rgb_in = 24'd0;
    reg        we = 1'b0;
    reg [2:0]  waddr = 3'd0;
    reg [7:0]  wdata = 8'h20;

    wire [23:0] rgb_out;
    wire de_out, hs_out, vs_out;
    wire [7:0]  dbg_rdata;

    text_overlay #(
        .H_ACTIVE(H), .V_ACTIVE(V), .COLS(4), .ROWS(1), .ADDR_W(3),
        .X0(X0), .Y0(Y0), .SCALE_LOG2(1), .PANEL_EN(1), .BG_DIM(1),
        .FG_RGB(24'hFFFFFF), .BG_RGB(24'h000000)
    ) dut (
        .clk(clk), .rst_n(rst_n), .de(de), .hs(hs), .vs(vs), .rgb_in(rgb_in),
        .we(we), .waddr(waddr), .wdata(wdata),
        .dbg_raddr(3'd0), .dbg_rdata(dbg_rdata),
        .rgb_out(rgb_out), .de_out(de_out), .hs_out(hs_out), .vs_out(vs_out)
    );

    // Count white (glyph) pixels per active line of the aligned frame.
    // 'A' row0 = 0x0C -> columns 2,3 -> 2 pixels x scale2 = 4 per row? no:
    // bit0 is leftmost, 0x0C = bits 2,3 -> 2 columns x 2 (scale) = 4 pixels.
    // row1 = 0x1E -> bits 1..4 -> 4 columns x 2 = 8 pixels.
    integer white = 0, lines = 0, i;
    integer white_line0 = -1, white_line1 = -1, white_line2 = -1;
    reg hs_out_d = 1'b0;
    reg de_out_d = 1'b0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            hs_out_d <= 1'b0; de_out_d <= 1'b0;
        end else begin
            hs_out_d <= hs_out;
            de_out_d <= de_out;
            if (hs_out & ~hs_out_d) begin
                if (lines == 0) white_line0 = white;
                if (lines == 1) white_line1 = white;
                if (lines == 2) white_line2 = white;
                lines = lines + 1;
                white = 0;
            end
            if (de_out && (rgb_out === 24'hFFFFFF)) white = white + 1;
        end
    end

    task line_burst(input integer n);   // de WITHOUT any sync, desynchronises
        begin
            for (i = 0; i < n; i = i + 1) begin
                de = 1'b1; @(negedge clk);
            end
            de = 1'b0; @(negedge clk);
        end
    endtask

    initial begin
        rst_n = 1'b0;
        repeat (3) @(negedge clk);
        rst_n = 1'b1;

        // program 'A' into cell 0, blanks elsewhere
        for (i = 0; i < 4; i = i + 1) begin
            we = 1'b1; waddr = i[2:0]; wdata = (i == 0) ? 8'h41 : 8'h20;
            @(negedge clk);
        end
        we = 1'b0;
        #2 $display("RAM0 %02x", dbg_rdata);

        // 1) desynchronised de burst: 6 lines worth of pixels, no vs/hs
        line_burst(H * 6);

        // 2) normal frame: vs then hs, then one active line
        vs = 1'b1; repeat (2) @(negedge clk); vs = 1'b0;
        repeat (2) @(negedge clk);
        hs = 1'b1; repeat (2) @(negedge clk); hs = 1'b0;
        repeat (2) @(negedge clk);
        de = 1'b1; repeat (H) @(negedge clk); de = 1'b0;
        repeat (4) @(negedge clk);
        hs = 1'b1; repeat (2) @(negedge clk); hs = 1'b0;
        repeat (2) @(negedge clk);
        de = 1'b1; repeat (H) @(negedge clk); de = 1'b0;
        repeat (10) @(negedge clk);

        $display("WHITE line0=%0d line1=%0d tail=%0d", white_line0, white_line1, white);
        // 'A' row0 bits 2,3 -> 4 white pixels at scale 2; row1 = 0x1E -> 8.
        if ((white_line1 !== 4) || (white !== 4)) begin   // scale 2: one glyph row spans two lines
            $display("ALIGN_ERRORS 1 (panel not realigned to the frame start)");
        end else begin
            $display("ALIGN_ERRORS 0");
        end
        $finish;
    end
endmodule
