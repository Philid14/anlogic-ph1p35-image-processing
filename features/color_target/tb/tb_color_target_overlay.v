`timescale 1ns / 1ps
// tb_color_target_overlay —— 标注模块的独立自检台（纯组合，无需时钟）。
//
// 激励每行 11 字段：pv x y rv present xmin xmax ymin ymax cx cy
// 输出每行 2 字段：overlay_valid overlay_rgb（十六进制）
// 期望值由 model/ref_color_target_overlay.py 计算后逐行比对。
module tb_color_target_overlay;
    parameter integer XW          = 11;
    parameter integer YW          = 10;
    parameter integer BOX_THICK   = 3;
    parameter [23:0]  BOX_RGB     = 24'h00FF00;
    parameter integer CROSS_ARM   = 12;
    parameter integer CROSS_THICK = 1;
    parameter [23:0]  CROSS_RGB   = 24'hFFFF00;

    reg              pv = 0, rv = 0, present = 0;
    reg [XW-1:0]     x = 0, xmin = 0, xmax = 0, cx = 0;
    reg [YW-1:0]     y = 0, ymin = 0, ymax = 0, cy = 0;
    wire             ov;
    wire [23:0]      orgb;

    color_target_overlay #(
        .XW(XW), .YW(YW), .BOX_THICK(BOX_THICK), .BOX_RGB(BOX_RGB),
        .CROSS_ARM(CROSS_ARM), .CROSS_THICK(CROSS_THICK), .CROSS_RGB(CROSS_RGB)
    ) dut (
        .I_pixel_valid(pv), .I_x(x), .I_y(y),
        .I_result_valid(rv), .I_target_present(present),
        .I_xmin(xmin), .I_xmax(xmax), .I_ymin(ymin), .I_ymax(ymax),
        .I_center_x(cx), .I_center_y(cy),
        .O_overlay_valid(ov), .O_overlay_rgb(orgb)
    );

    integer fin, fout, rc, n = 0;
    reg [2047:0] spath, opath;

    initial begin
        if (!$value$plusargs("STIM=%s", spath)) begin $display("FAIL missing STIM"); $finish; end
        if (!$value$plusargs("OUT=%s",  opath)) begin $display("FAIL missing OUT");  $finish; end
        fin  = $fopen(spath, "r");
        fout = $fopen(opath, "w");
        if (fin == 0 || fout == 0) begin $display("FAIL open files"); $finish; end

        while (!$feof(fin)) begin
            rc = $fscanf(fin, "%d %d %d %d %d %d %d %d %d %d %d\n",
                         pv, x, y, rv, present, xmin, xmax, ymin, ymax, cx, cy);
            if (rc == 11) begin
                #1;                                  // 组合路径稳定
                $fwrite(fout, "%d %08x\n", ov, orgb);
                n = n + 1;
            end else if (!$feof(fin)) begin
                $display("FAIL malformed stimulus (rc=%0d)", rc); $finish;
            end
        end
        $fclose(fin);
        $fclose(fout);
        if (n == 0) begin $display("FAIL no pixels checked"); $finish; end
        $display("PASS color_target_overlay pixels=%0d", n);
        $finish;
    end
endmodule
