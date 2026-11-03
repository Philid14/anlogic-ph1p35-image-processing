`timescale 1ns / 1ps
// tb_color_target —— color_target_detect 的独立自检台。
//
// 结构：
//   激励文件每行 12 个字段：valid sof eol eof abort x0 y d_hi d_mid d_lo session frame
//   命中 O_result_ready 时把整组结果写一行到输出文件：
//     session frame valid present cls count xmin xmax ymin ymax cx cy
//   期望值由 Python 参考模型 model/ref_color_target.py 算出后逐行比对。
//
// 本台还自带两条结构断言（不依赖期望值）：
//   1. O_result_ready 只允许出现在"上一拍 valid&&eof"之后；
//   2. 未发布期间结果寄存器必须保持不变（协议 §4.3 要求原子发布并稳定保持）。
module tb_color_target;
    parameter integer TARGET_CLASS       = 0;
    parameter integer HUE_HALF_WIDTH_DEG = 30;
    parameter integer C_MIN              = 24;
    parameter integer V_MIN              = 32;
    parameter integer MIN_COUNT          = 64;
    parameter integer XW                 = 11;
    parameter integer YW                 = 10;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;

    reg              valid = 0, sof = 0, eol = 0, eof = 0, abort = 0;
    reg [XW-1:0]     x0 = 0;
    reg [YW-1:0]     y  = 0;
    reg [95:0]       data = 0;
    reg [31:0]       sess = 0, fid = 0;

    wire [31:0] O_res_session_id, O_res_frame_id;
    wire        O_result_valid, O_target_present, O_result_ready;
    wire [1:0]  O_color_class;
    wire [19:0] O_pixel_count;
    wire [XW-1:0] O_xmin, O_xmax, O_center_x;
    wire [YW-1:0] O_ymin, O_ymax, O_center_y;

    color_target_detect #(
        .TARGET_CLASS(TARGET_CLASS), .HUE_HALF_WIDTH_DEG(HUE_HALF_WIDTH_DEG),
        .C_MIN(C_MIN), .V_MIN(V_MIN), .MIN_COUNT(MIN_COUNT),
        .XW(XW), .YW(YW)
    ) dut (
        .clk(clk), .rst_n(rst_n),
        .I_pixel_valid(valid), .I_data(data), .I_x0(x0), .I_y(y),
        .I_sof(sof), .I_eol(eol), .I_eof(eof),
        .I_session_id(sess), .I_frame_id(fid), .I_frame_abort(abort),
        .O_res_session_id(O_res_session_id), .O_res_frame_id(O_res_frame_id),
        .O_result_valid(O_result_valid), .O_target_present(O_target_present),
        .O_color_class(O_color_class), .O_pixel_count(O_pixel_count),
        .O_xmin(O_xmin), .O_xmax(O_xmax), .O_center_x(O_center_x),
        .O_ymin(O_ymin), .O_ymax(O_ymax), .O_center_y(O_center_y),
        .O_result_ready(O_result_ready)
    );

    integer fin, fout, rc, cycles = 0, published = 0;
    reg [2047:0] spath, opath;
    reg [31:0] d_hi, d_mid, d_lo;
    reg [31:0] l_session = 0, l_frame = 0;
    reg [19:0] l_count = 0;
    reg [XW-1:0] l_xmin = 0, l_xmax = 0, l_cx = 0;
    reg [YW-1:0] l_ymin = 0, l_ymax = 0, l_cy = 0;
    reg l_valid = 0, l_present = 0;
    reg [1:0] l_cls = 0;
    reg have_pub = 0;

    initial begin
        if (!$value$plusargs("STIM=%s", spath)) begin $display("FAIL missing STIM"); $finish; end
        if (!$value$plusargs("OUT=%s",  opath)) begin $display("FAIL missing OUT");  $finish; end
        fin  = $fopen(spath, "r");
        fout = $fopen(opath, "w");
        if (fin == 0 || fout == 0) begin $display("FAIL open files"); $finish; end

        repeat (4) @(negedge clk);
        rst_n = 1;

        while (!$feof(fin)) begin
            rc = $fscanf(fin, "%d %d %d %d %d %d %d %h %h %h %d %d\n",
                         valid, sof, eol, eof, abort, x0, y,
                         d_hi, d_mid, d_lo, sess, fid);
            if (rc == 12) begin
                data = {d_hi, d_mid, d_lo};
                @(negedge clk);
                @(posedge clk); #1;

                // 断言 1：ready 当拍必须恰好对应"本拍的 valid&&eof"。
                // 采样点在 posedge 之后，而 O_result_ready 是 pend_pub(=本拍 valid&&eof)
                // 经非阻塞赋值传出来的，所以应与**本拍**比较，不是上一拍。
                if (O_result_ready !== (valid && eof)) begin
                    $display("FAIL ready-vs-eof cycle=%0d ready=%b pend=%b",
                             cycles, O_result_ready, (valid && eof));
                    $finish;
                end
                // 断言 2：未发布时结果必须保持不变
                if (have_pub && !O_result_ready) begin
                    if (O_res_session_id !== l_session || O_res_frame_id !== l_frame ||
                        O_result_valid !== l_valid || O_target_present !== l_present ||
                        O_color_class !== l_cls || O_pixel_count !== l_count ||
                        O_xmin !== l_xmin || O_xmax !== l_xmax ||
                        O_ymin !== l_ymin || O_ymax !== l_ymax ||
                        O_center_x !== l_cx || O_center_y !== l_cy) begin
                        $display("FAIL result changed outside publish cycle=%0d", cycles);
                        $finish;
                    end
                end
                if (O_result_ready) begin
                    $fwrite(fout, "%0d %0d %d %d %d %0d %0d %0d %0d %0d %0d %0d\n",
                            O_res_session_id, O_res_frame_id, O_result_valid,
                            O_target_present, O_color_class, O_pixel_count,
                            O_xmin, O_xmax, O_ymin, O_ymax, O_center_x, O_center_y);
                    l_session = O_res_session_id; l_frame = O_res_frame_id;
                    l_valid   = O_result_valid;   l_present = O_target_present;
                    l_cls     = O_color_class;    l_count   = O_pixel_count;
                    l_xmin    = O_xmin; l_xmax = O_xmax; l_cx = O_center_x;
                    l_ymin    = O_ymin; l_ymax = O_ymax; l_cy = O_center_y;
                    have_pub  = 1;
                    published = published + 1;
                end
                cycles = cycles + 1;
            end else if (!$feof(fin)) begin
                $display("FAIL malformed stimulus line (rc=%0d)", rc); $finish;
            end
        end
        $fclose(fin);
        $fclose(fout);
        if (published == 0) begin $display("FAIL no result published"); $finish; end
        $display("PASS color_target cycles=%0d published=%0d", cycles, published);
        $finish;
    end
endmodule
