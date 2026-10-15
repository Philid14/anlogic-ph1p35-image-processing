`timescale 1ns / 1ps
// tb_color_target_chain —— 三级链路端到端自检：detect -> track -> overlay。
//
// 目的：在 MAIN 介入之前，先证明我自己这三个模块**按协议规定的时序**接在一起是对的，
// 并给 MAIN 一份可照抄的接线参考。
//
// 关键时序（协议 §4.3 特意警告过的一点）：
//   detect 的结果在 **eof 那一拍之后 1 拍** 才发布（O_result_ready 单拍脉冲）。
//   track 在该脉冲那一拍消费结果，因此 **track 的输出在 eof 之后 1 拍才更新**。
//   overlay 是纯组合的，直接把 track 的输出接进去 —— 于是"框"在 eof 之后 1 拍才变，
//   而那一拍仍属于本帧的最后像素。
//   所以本台**逐拍**记录 overlay 的判定，把这个"末拍才切换"的现象如实测出来，
//   而不是假设它不存在。实测结论写在 README 里。
//
// 激励每行 12 字段（与 tb_color_target 相同）：
//   valid sof eol eof abort x0 y d_hi d_mid d_lo session frame
// 每拍输出 4 字段：track_state track_show overlay_valid overlay_rgb(hex)
module tb_color_target_chain;
    parameter integer TARGET_CLASS       = 0;
    parameter integer HUE_HALF_WIDTH_DEG = 30;
    parameter integer C_MIN              = 24;
    parameter integer V_MIN              = 32;
    parameter integer MIN_COUNT          = 4;
    parameter integer XW                 = 11;
    parameter integer YW                 = 10;
    parameter integer ACQ_FRAMES         = 3;
    parameter integer LOST_FRAMES        = 15;
    parameter integer MAX_JUMP           = 0;
    parameter integer BOX_THICK          = 3;
    parameter integer CROSS_ARM          = 12;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;

    reg              valid = 0, sof = 0, eol = 0, eof = 0, abort = 0;
    reg [XW-1:0]     x0 = 0;
    reg [YW-1:0]     y  = 0;
    reg [95:0]       data = 0;
    reg [31:0]       sess = 0, fid = 0;

    // ---- detect ----
    wire [31:0] d_rs, d_rf;
    wire        d_rv, d_rp, d_rr;
    wire [1:0]  d_cls;
    wire [19:0] d_cnt;
    wire [XW-1:0] d_xmin, d_xmax, d_cx;
    wire [YW-1:0] d_ymin, d_ymax, d_cy;

    color_target_detect #(
        .TARGET_CLASS(TARGET_CLASS), .HUE_HALF_WIDTH_DEG(HUE_HALF_WIDTH_DEG),
        .C_MIN(C_MIN), .V_MIN(V_MIN), .MIN_COUNT(MIN_COUNT), .XW(XW), .YW(YW)
    ) u_detect (
        .clk(clk), .rst_n(rst_n),
        .I_pixel_valid(valid), .I_data(data), .I_x0(x0), .I_y(y),
        .I_sof(sof), .I_eol(eol), .I_eof(eof),
        .I_session_id(sess), .I_frame_id(fid), .I_frame_abort(abort),
        .O_res_session_id(d_rs), .O_res_frame_id(d_rf),
        .O_result_valid(d_rv), .O_target_present(d_rp), .O_color_class(d_cls),
        .O_pixel_count(d_cnt),
        .O_xmin(d_xmin), .O_xmax(d_xmax), .O_center_x(d_cx),
        .O_ymin(d_ymin), .O_ymax(d_ymax), .O_center_y(d_cy),
        .O_result_ready(d_rr)
    );

    // ---- track ----
    wire [1:0]  t_state;
    wire        t_show, t_chg;
    wire [19:0] t_cnt;
    wire [XW-1:0] t_xmin, t_xmax, t_cx;
    wire [YW-1:0] t_ymin, t_ymax, t_cy;
    wire [31:0] t_sess, t_fid;

    color_target_track #(
        .XW(XW), .YW(YW), .ACQ_FRAMES(ACQ_FRAMES),
        .LOST_FRAMES(LOST_FRAMES), .MAX_JUMP(MAX_JUMP)
    ) u_track (
        .clk(clk), .rst_n(rst_n),
        .I_result_strobe(d_rr), .I_result_valid(d_rv), .I_target_present(d_rp),
        .I_pixel_count(d_cnt),
        .I_xmin(d_xmin), .I_xmax(d_xmax), .I_center_x(d_cx),
        .I_ymin(d_ymin), .I_ymax(d_ymax), .I_center_y(d_cy),
        .I_session_id(d_rs), .I_frame_id(d_rf),
        .O_track_state(t_state), .O_show(t_show), .O_state_change(t_chg),
        .O_out_count(t_cnt),
        .O_out_xmin(t_xmin), .O_out_xmax(t_xmax), .O_out_center_x(t_cx),
        .O_out_ymin(t_ymin), .O_out_ymax(t_ymax), .O_out_center_y(t_cy),
        .O_out_session_id(t_sess), .O_out_frame_id(t_fid)
    );

    // ---- overlay（按 §4.2 说明的两行接线接 track）----
    wire ov, _unused_ready;
    wire [23:0] orgb;

    color_target_overlay #(
        .XW(XW), .YW(YW), .BOX_THICK(BOX_THICK), .CROSS_ARM(CROSS_ARM)
    ) u_overlay (
        .I_pixel_valid(valid), .I_x(x0), .I_y(y),
        .I_result_valid(t_show), .I_target_present(t_show),
        .I_xmin(t_xmin), .I_xmax(t_xmax), .I_ymin(t_ymin), .I_ymax(t_ymax),
        .I_center_x(t_cx), .I_center_y(t_cy),
        .O_overlay_valid(ov), .O_overlay_rgb(orgb)
    );

    integer fin, fout, rc, n = 0;
    reg [2047:0] spath, opath;
    reg          s_in, rv_in, pr_in;
    reg          sof_hold, eol_hold, eof_hold, abort_hold;   // 暂存读入的字段
    reg [XW-1:0] x0_in, xmin_in, xmax_in, cx_in;
    reg [YW-1:0] y_in, ymin_in, ymax_in, cy_in;
    reg [31:0]   d_hi, d_mid, d_lo, sess_in, fid_in;

    initial begin
        if (!$value$plusargs("STIM=%s", spath)) begin $display("FAIL missing STIM"); $finish; end
        if (!$value$plusargs("OUT=%s",  opath)) begin $display("FAIL missing OUT");  $finish; end
        fin  = $fopen(spath, "r");
        fout = $fopen(opath, "w");
        if (fin == 0 || fout == 0) begin $display("FAIL open files"); $finish; end

        repeat (4) @(negedge clk);
        rst_n = 1;

        while (!$feof(fin)) begin
            // 链路激励 12 字段；后 6 个（rvalid/present/...）在本台不用，读进来丢弃
            rc = $fscanf(fin, "%d %d %d %d %d %d %d %h %h %h %d %d\n",
                         s_in, sof_hold, eol_hold, eof_hold, abort_hold, x0_in, y_in,
                         d_hi, d_mid, d_lo, sess_in, fid_in);
            if (rc == 12) begin
                @(negedge clk);
                valid = s_in;
                sof = sof_hold; eol = eol_hold; eof = eof_hold; abort = abort_hold;
                x0 = x0_in; y = y_in;
                data = {d_hi, d_mid, d_lo};
                sess = sess_in; fid = fid_in;
                @(posedge clk); #1;
                $fwrite(fout, "%0d %0d %0d %08x\n", t_state, t_show, ov, orgb);
                n = n + 1;
            end else if (!$feof(fin)) begin
                $display("FAIL malformed stimulus (rc=%0d)", rc); $finish;
            end
        end
        $fclose(fin);
        $fclose(fout);
        if (n == 0) begin $display("FAIL no beats checked"); $finish; end
        $display("PASS color_target_chain beats=%0d", n);
        $finish;
    end
endmodule
