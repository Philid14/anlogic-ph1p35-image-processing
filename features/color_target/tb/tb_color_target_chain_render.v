`timescale 1ns / 1ps
// tb_color_target_chain_render —— 把三级链路的**逐像素输出**完整导出，用于渲染帧图。
//
// 与 tb_color_target_chain.v 的区别：那个台每拍只在 lane0 的坐标上采一次 overlay
// （因为它的目的是验证时序与状态机）；这个台把每拍的 4 个 lane **逐个**送进 overlay
// 求覆盖，并把"覆盖后的最终像素"写出来，因此可以还原出 MAIN 合成后的画面。
//
// 两个输出文件：
//   +PIX=<path>   每像素一行： frame y x comp_rgb ov
//   +BEAT=<path>  每拍一行：   track_state track_show
//
// 激励每行 12 字段（与 tb_color_target 相同）：
//   valid sof eol eof abort x0 y d_hi d_mid d_lo session frame
//
// ⚠️ 像素转储**必须带帧号**：多帧画面里 (x,y) 会重复出现，只有坐标无法区分是第几帧，
//    上层按坐标建图时后一帧会覆盖前一帧。（第一版就踩了这个坑，逐像素比对当场报错。）
module tb_color_target_chain_render;
    parameter integer TARGET_CLASS       = 0;
    parameter integer HUE_HALF_WIDTH_DEG = 30;
    parameter integer C_MIN              = 24;
    parameter integer V_MIN              = 32;
    parameter integer MIN_COUNT          = 4;
    parameter integer XW                 = 9;
    parameter integer YW                 = 8;
    parameter integer ACQ_FRAMES         = 3;
    parameter integer LOST_FRAMES        = 15;
    parameter integer MAX_JUMP           = 0;
    parameter integer BOX_THICK          = 3;
    parameter integer CROSS_ARM          = 12;
    parameter integer CROSS_THICK        = 1;

    reg clk = 0;
    // 周期取 30ns，而不是别的台用的 10ns：本台在每拍之后要额外花几纳秒把 4 个 lane
    // 逐个送进 overlay 求覆盖（组合路径，需要 #1 稳定）。若周期只有 10ns，那几次 #1 会
    // 正好把仿真时刻推到下一个 negedge 上，下一拍的 @(negedge clk) 就会错过它、多等一整
    // 个周期——期间同一个 beat 会被 posedge **采两次**（README §2.3 记过这个坑）。
    // 放宽周期后，拍与拍之间严格一个时钟沿，扫描不再影响时序。
    always #15 clk = ~clk;
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

    // ---- overlay：x 由本台逐 lane 驱动（datapath 里它是 per-pixel 组合模块）----
    reg  [XW-1:0] ovl_x = 0;
    wire          ov;
    wire [23:0]   orgb;

    color_target_overlay #(
        .XW(XW), .YW(YW), .BOX_THICK(BOX_THICK), .CROSS_ARM(CROSS_ARM),
        .CROSS_THICK(CROSS_THICK)
    ) u_overlay (
        .I_pixel_valid(valid), .I_x(ovl_x), .I_y(y),
        .I_result_valid(t_show), .I_target_present(t_show),
        .I_xmin(t_xmin), .I_xmax(t_xmax), .I_ymin(t_ymin), .I_ymax(t_ymax),
        .I_center_x(t_cx), .I_center_y(t_cy),
        .O_overlay_valid(ov), .O_overlay_rgb(orgb)
    );

    integer fin, fpix, fbeat, rc, n = 0, k;
    reg [2047:0] spath, ppath, bpath;
    reg          s_in, rv_in, pr_in;
    reg          sof_hold, eol_hold, eof_hold, abort_hold;
    reg [XW-1:0] x0_in, xmin_in, xmax_in, cx_in;
    reg [YW-1:0] y_in, ymin_in, ymax_in, cy_in;
    reg [31:0]   d_hi, d_mid, d_lo, sess_in, fid_in;
    reg [23:0]   base_rgb, comp;
    reg [XW-1:0] px;

    initial begin
        if (!$value$plusargs("STIM=%s", spath)) begin $display("FAIL missing STIM"); $finish; end
        if (!$value$plusargs("PIX=%s",  ppath)) begin $display("FAIL missing PIX");  $finish; end
        if (!$value$plusargs("BEAT=%s", bpath)) begin $display("FAIL missing BEAT"); $finish; end
        fin   = $fopen(spath, "r");
        fpix  = $fopen(ppath, "w");
        fbeat = $fopen(bpath, "w");
        if (fin == 0 || fpix == 0 || fbeat == 0) begin $display("FAIL open files"); $finish; end

        repeat (4) @(negedge clk);
        rst_n = 1;

        while (!$feof(fin)) begin
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
                // 本拍的状态与显示（与 tb_color_target_chain 完全一致，便于与链路模型对拍）
                $fwrite(fbeat, "%0d %0d\n", t_state, t_show);
                // 逐 lane 求覆盖并合成最终像素。lane k 的 x = x0+k，颜色取 data 的对应 24 位
                if (valid) begin
                    for (k = 0; k < 4; k = k + 1) begin
                        ovl_x = x0 + k;
                        #1;
                        base_rgb = data[95 - 24*k -: 24];
                        comp     = ov ? orgb : base_rgb;
                        px       = x0 + k;
                        $fwrite(fpix, "%0d %0d %0d %06x %0d\n", fid, y, px, comp, ov);
                    end
                    ovl_x = x0;
                end
                n = n + 1;
            end else if (!$feof(fin)) begin
                $display("FAIL malformed stimulus (rc=%0d)", rc); $finish;
            end
        end
        $fclose(fin);
        $fclose(fpix);
        $fclose(fbeat);
        if (n == 0) begin $display("FAIL no beats checked"); $finish; end
        $display("PASS color_target_render beats=%0d", n);
        $finish;
    end
endmodule
