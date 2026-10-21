`timescale 1ns / 1ps
// Read both text lines through public glyph ports after every input clock.
// All 28 character probes fit before the next edge; no internal registers
// are observed, so this test does not depend on the converter implementation.
module tb_color_target_text_updates;
    parameter integer XW = 11;
    parameter integer YW = 10;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg upd = 0, shw = 0;
    reg [1:0] st = 0;
    reg [19:0] cnt = 0;
    reg [XW-1:0] cx = 0, x = 0;
    reg [YW-1:0] cy = 0, y = 0;
    wire ov;
    wire [23:0] rgb;
    wire [7:0] ch;
    wire [3:0] row;
    color_target_text_overlay #(.XW(XW), .YW(YW), .X0(16), .Y0(16)) dut (
        .clk(clk), .rst_n(rst_n), .I_pixel_valid(1'b1), .I_x(x), .I_y(y),
        .I_update(upd), .I_show(shw), .I_state(st), .I_count(cnt),
        .I_center_x(cx), .I_center_y(cy), .O_glyph_char(ch), .O_glyph_row(row),
        .I_glyph_bits(16'hffff), .O_overlay_valid(ov), .O_overlay_rgb(rgb)
    );
    integer fin, fout, rc, n = 0, k;
    reg [2047:0] spath, opath;
    reg r_in, u_in, sh_in;
    reg [1:0] st_in;
    reg [31:0] c_in, cx_in, cy_in;
    reg [111:0] line0, line1;
    reg [23:0] tone;
    initial begin
        if (!$value$plusargs("STIM=%s", spath)) begin $display("FAIL missing STIM"); $finish; end
        if (!$value$plusargs("OUT=%s", opath)) begin $display("FAIL missing OUT"); $finish; end
        fin = $fopen(spath, "r"); fout = $fopen(opath, "w");
        if (fin == 0 || fout == 0) begin $display("FAIL open files"); $finish; end
        repeat (4) @(negedge clk);
        while (!$feof(fin)) begin
            rc = $fscanf(fin, "%d %d %d %d %d %d %d\n",
                         r_in, u_in, sh_in, st_in, c_in, cx_in, cy_in);
            if (rc == 7) begin
                @(negedge clk);
                rst_n = r_in; upd = u_in; shw = sh_in; st = st_in;
                cnt = c_in[19:0]; cx = cx_in[XW-1:0]; cy = cy_in[YW-1:0];
                @(posedge clk); #1;
                line0 = 0; line1 = 0;
                for (k = 0; k < 28; k = k + 1) begin
                    x = 16 + (k % 14) * 16;
                    y = (k < 14) ? 16 : 34;
                    #0.01;
                    if (!ov || row != 0) begin $display("FAIL glyph probe"); $finish; end
                    if (k == 0) tone = rgb;
                    if (rgb !== tone) begin $display("FAIL tone changed within clock"); $finish; end
                    if (k < 14) line0 = {line0[103:0], ch};
                    else line1 = {line1[103:0], ch};
                end
                $fwrite(fout, "%0d %028h %028h %06h\n", n, line0, line1, tone);
                n = n + 1;
            end else if (!$feof(fin)) begin
                $display("FAIL malformed stimulus"); $finish;
            end
        end
        $fclose(fin); $fclose(fout);
        if (n == 0) begin $display("FAIL no samples"); $finish; end
        $display("PASS color_target_text_updates samples=%0d", n);
        $finish;
    end
endmodule
