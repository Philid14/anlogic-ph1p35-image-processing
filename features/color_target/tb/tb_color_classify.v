`timescale 1ns / 1ps
// tb_color_classify —— color_classify 的逐像素自检台（纯组合，无需时钟）。
//
// 激励每行 3 字段：r g b
// 每行输出 1 字段：O_hit
// 期望值由 run_color_classify.py **按数学判据独立计算**（不调用 model/ 里的分类器），
// 因此模型与 RTL 若一起错，这里仍能暴露。
//
// 参数（TARGET_CLASS / HUE_HALF_WIDTH_DEG / C_MIN / V_MIN）由 runner 逐个组合注入，
// 同一个 testbench 会被编译多次以覆盖不同参数——这正是原来缺失的"多色相半宽"回归。
module tb_color_classify;
    parameter integer TARGET_CLASS       = 0;
    parameter integer HUE_HALF_WIDTH_DEG = 30;
    parameter integer C_MIN              = 24;
    parameter integer V_MIN              = 32;

    reg  [7:0] r = 0;
    reg  [7:0] g = 0;
    reg  [7:0] b = 0;
    wire       hit;

    color_classify #(
        .TARGET_CLASS(TARGET_CLASS), .HUE_HALF_WIDTH_DEG(HUE_HALF_WIDTH_DEG),
        .C_MIN(C_MIN), .V_MIN(V_MIN)
    ) dut (
        .I_r(r), .I_g(g), .I_b(b), .O_hit(hit)
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
            rc = $fscanf(fin, "%d %d %d\n", r, g, b);
            if (rc == 3) begin
                #1;                                  // 组合路径稳定
                $fwrite(fout, "%d\n", hit);
                n = n + 1;
            end else if (!$feof(fin)) begin
                $display("FAIL malformed stimulus (rc=%0d)", rc); $finish;
            end
        end
        $fclose(fin);
        $fclose(fout);
        if (n == 0) begin $display("FAIL no pixels checked"); $finish; end
        $display("PASS color_classify pixels=%0d", n);
        $finish;
    end
endmodule
