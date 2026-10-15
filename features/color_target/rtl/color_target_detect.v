`timescale 1ns / 1ps
// color_target_detect —— TARGET 角色的独立颜色目标检测（T1 + T2）。
//
// 对应协议 docs/TEAM_AI_WORK_PROTOCOL.md：
//   §4.2 规范化像素观察流（输入）
//   §4.3 检测结果及标注   （输出）
//   §2.2 T1 参数化颜色分类（默认红色）、T2 匹配像素数 / 包围框 / 包围框中心 / 帧身份
//
// 边界（务必如实对外说明）：
//   * 本版本**不做**形态学或水平游程滤波，也**不做**多目标分离。整帧所有匹配像素
//     合成**一个**包围框；若场景里有两块同色区域，会被统计进同一个框（协议 §2.2 要求
//     主动报告这条限制）。去噪与防抖属 T4。
//   * 包围框中心是 **(xmin+xmax)/2 向下取整**，**不是像素质心**（协议 §2.2 明确要求
//     区分这两者）。本模块不计算质心。
//   * 坐标始终以原图 1280x720 为准，来自 MAIN 给出的 I_x0/I_y；本模块不使用任何
//     下采样坐标（协议 §4.3 禁止用 640 点 Sobel 坐标代替）。
//   * 本模块不产生 bit、不改变主线接线；仅在模拟输入下自检（协议 §5.2）。
module color_target_detect #(
    parameter integer TARGET_CLASS       = 0,     // 0=红 1=绿 2=蓝，首个演示目标默认红
    parameter integer HUE_HALF_WIDTH_DEG = 30,
    parameter integer C_MIN              = 24,    // 彩度下限，兼滤白灰与暗部噪声
    parameter integer V_MIN              = 32,    // 亮度下限
    parameter integer MIN_COUNT          = 64,    // 低于此像素数判为无目标
    parameter integer XW                 = 11,    // x / 中心 x 位宽（协议 §4.3）
    parameter integer YW                 = 10     // y / 中心 y 位宽（协议 §4.3）
)(
    input               clk,
    input               rst_n,

    // ---- §4.2 规范化像素观察流 ----
    // 4 像素/拍；lane0=[95:72] lane1=[71:48] lane2=[47:24] lane3=[23:0]，
    // 每 lane 24 位为 {R[7:0],G[7:0],B[7:0]}，按显示坐标从左到右。
    // 注意：这是**接口约定**，MAIN 必须验证主线实际映射，必要时由适配器转换。
    input               I_pixel_valid,
    input      [95:0]   I_data,
    input      [XW-1:0] I_x0,          // 本拍 lane0 的 x；lane k 的 x = x0+k
    input      [YW-1:0] I_y,
    input               I_sof,         // 伴随本帧首个有效拍
    input               I_eol,         // 伴随本行最后一个有效拍（本版本不依赖，保留对齐接口）
    input               I_eof,         // 伴随本帧最后一个有效拍
    input      [31:0]   I_session_id,
    input      [31:0]   I_frame_id,
    input               I_frame_abort, // 中断/错误帧：丢弃本帧结果

    // ---- §4.3 检测结果（帧末原子锁存，整帧稳定）----
    output reg [31:0]   O_res_session_id,
    output reg [31:0]   O_res_frame_id,
    output reg          O_result_valid, // 中断帧为 0
    output reg          O_target_present,
    output reg [1:0]    O_color_class,
    output reg [19:0]   O_pixel_count,
    output reg [XW-1:0] O_xmin, O_xmax, O_center_x,
    output reg [YW-1:0] O_ymin, O_ymax, O_center_y,
    output reg          O_result_ready  // 一拍脉冲：新结果已锁存
);
    // ---------------- 逐像素分类：4 路并行 ----------------
    wire h0, h1, h2, h3;
    color_classify #(.TARGET_CLASS(TARGET_CLASS), .HUE_HALF_WIDTH_DEG(HUE_HALF_WIDTH_DEG),
                     .C_MIN(C_MIN), .V_MIN(V_MIN)) u_cls0 (
        .I_r(I_data[95:88]), .I_g(I_data[87:80]), .I_b(I_data[79:72]), .O_hit(h0));
    color_classify #(.TARGET_CLASS(TARGET_CLASS), .HUE_HALF_WIDTH_DEG(HUE_HALF_WIDTH_DEG),
                     .C_MIN(C_MIN), .V_MIN(V_MIN)) u_cls1 (
        .I_r(I_data[71:64]), .I_g(I_data[63:56]), .I_b(I_data[55:48]), .O_hit(h1));
    color_classify #(.TARGET_CLASS(TARGET_CLASS), .HUE_HALF_WIDTH_DEG(HUE_HALF_WIDTH_DEG),
                     .C_MIN(C_MIN), .V_MIN(V_MIN)) u_cls2 (
        .I_r(I_data[47:40]), .I_g(I_data[39:32]), .I_b(I_data[31:24]), .O_hit(h2));
    color_classify #(.TARGET_CLASS(TARGET_CLASS), .HUE_HALF_WIDTH_DEG(HUE_HALF_WIDTH_DEG),
                     .C_MIN(C_MIN), .V_MIN(V_MIN)) u_cls3 (
        .I_r(I_data[23:16]), .I_g(I_data[15:8]),  .I_b(I_data[7:0]),   .O_hit(h3));

    // 本拍命中数与命中像素的 x 候选（未命中给中性元，便于树形归约）
    wire [2:0]  hits    = {2'b0,h0} + {2'b0,h1} + {2'b0,h2} + {2'b0,h3};
    wire        any_hit = |hits;

    wire [XW-1:0] x0 = I_x0;
    wire [XW-1:0] x1 = I_x0 + {{(XW-3){1'b0}}, 2'd1};
    wire [XW-1:0] x2 = I_x0 + {{(XW-3){1'b0}}, 2'd2};
    wire [XW-1:0] x3 = I_x0 + {{(XW-3){1'b0}}, 2'd3};

    localparam [XW-1:0] X_MAX = {XW{1'b1}};
    localparam [YW-1:0] Y_MAX = {YW{1'b1}};

    wire [XW-1:0] cx0 = h0 ? x0 : X_MAX;
    wire [XW-1:0] cx1 = h1 ? x1 : X_MAX;
    wire [XW-1:0] cx2 = h2 ? x2 : X_MAX;
    wire [XW-1:0] cx3 = h3 ? x3 : X_MAX;
    wire [XW-1:0] cxa = (cx0 < cx1) ? cx0 : cx1;
    wire [XW-1:0] cxb = (cx2 < cx3) ? cx2 : cx3;
    wire [XW-1:0] hit_xmin = (cxa < cxb) ? cxa : cxb;

    wire [XW-1:0] dx0 = h0 ? x0 : {XW{1'b0}};
    wire [XW-1:0] dx1 = h1 ? x1 : {XW{1'b0}};
    wire [XW-1:0] dx2 = h2 ? x2 : {XW{1'b0}};
    wire [XW-1:0] dx3 = h3 ? x3 : {XW{1'b0}};
    wire [XW-1:0] dxa = (dx0 > dx1) ? dx0 : dx1;
    wire [XW-1:0] dxb = (dx2 > dx3) ? dx2 : dx3;
    wire [XW-1:0] hit_xmax = (dxa > dxb) ? dxa : dxb;

    wire [YW-1:0] hit_ymin = any_hit ? I_y : Y_MAX;
    wire [YW-1:0] hit_ymax = any_hit ? I_y : {YW{1'b0}};

    // ---------------- 帧内累加 ----------------
    reg        open_f;                       // 本帧已由 sof 打开
    reg        aborted_f;
    reg [31:0] cur_session, cur_frame;
    reg [19:0] acc_cnt;
    reg [XW-1:0] acc_xmin, acc_xmax;
    reg [YW-1:0] acc_ymin, acc_ymax;

    wire start_f = I_pixel_valid && I_sof;

    wire [19:0] nxt_cnt = start_f ? {20'h0} + hits
                                  : acc_cnt + hits;
    wire [XW-1:0] base_xmin = start_f ? X_MAX : acc_xmin;
    wire [XW-1:0] base_xmax = start_f ? {XW{1'b0}} : acc_xmax;
    wire [YW-1:0] base_ymin = start_f ? Y_MAX : acc_ymin;
    wire [YW-1:0] base_ymax = start_f ? {YW{1'b0}} : acc_ymax;
    wire [XW-1:0] nxt_xmin = (hit_xmin < base_xmin) ? hit_xmin : base_xmin;
    wire [XW-1:0] nxt_xmax = (hit_xmax > base_xmax) ? hit_xmax : base_xmax;
    wire [YW-1:0] nxt_ymin = (hit_ymin < base_ymin) ? hit_ymin : base_ymin;
    wire [YW-1:0] nxt_ymax = (hit_ymax > base_ymax) ? hit_ymax : base_ymax;

    // 本拍是帧末有效拍：下一拍再锁存结果，保证 eof 那一拍的 4 个像素已计入
    wire pend_pub = I_pixel_valid && I_eof;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            open_f <= 1'b0; aborted_f <= 1'b0;
            cur_session <= 32'd0; cur_frame <= 32'd0;
            acc_cnt <= 20'd0;
            acc_xmin <= X_MAX; acc_xmax <= {XW{1'b0}};
            acc_ymin <= Y_MAX; acc_ymax <= {YW{1'b0}};
        end else begin
            if (start_f) begin
                open_f    <= 1'b1;
                aborted_f <= I_frame_abort;      // sof 与 abort 同拍时也算中断
                cur_session <= I_session_id;
                cur_frame   <= I_frame_id;
            end else if (I_frame_abort) begin
                aborted_f <= 1'b1;
            end

            if (I_pixel_valid) begin
                acc_cnt  <= nxt_cnt;
                acc_xmin <= nxt_xmin; acc_xmax <= nxt_xmax;
                acc_ymin <= nxt_ymin; acc_ymax <= nxt_ymax;
            end
        end
    end

    // ---------------- 帧末原子锁存结果 ----------------
    // 必须在同一拍用 nxt_* 而不是 acc_*：acc_* 与本次锁存是同一时钟沿的非阻塞赋值，
    // 读 acc_* 会丢掉 eof 那一拍的 4 个像素，而协议 §4.3 明确要求把它们计入。
    // eff_open / eff_abort 覆盖 sof 与 eof（或 abort）同拍的单拍帧情形。
    wire         eff_open  = open_f | start_f;
    wire         eff_abort = aborted_f | I_frame_abort;
    wire         eff_ok    = eff_open & ~eff_abort;
    // 单拍帧（sof 与 eof 同拍）时 cur_* 尚未更新，必须取本拍的 I_*_id，否则会报上一帧身份
    wire [31:0]  eff_session = start_f ? I_session_id : cur_session;
    wire [31:0]  eff_frame   = start_f ? I_frame_id   : cur_frame;
    // 只有"帧有效 且 命中数达门限"才填字段；否则按 §4.3 全部清零（含中止帧）。
    // MIN_COUNT 在编译期夹到 >=1：取 0 会让"零命中"的帧也判为存在，而那时包围框还是
    // 中性元（xmin=全 1、xmax=0），会输出 2047/1023 这类垃圾坐标。夹取不产生运行时逻辑。
    localparam [19:0] MIN_COUNT_EFF = (MIN_COUNT < 1) ? 20'd1 : MIN_COUNT[19:0];
    wire         res_ok  = eff_ok & (nxt_cnt >= MIN_COUNT_EFF);
    // 中心：先把加法拓宽一位再右移。xmin+xmax 最大 2555、ymin+ymax 最大 1438，
    // 直接用 XW/YW 位相加会截断（Verilog 按操作数最大位宽求值）。
    wire [XW:0]   cx_sum = {1'b0, nxt_xmin} + {1'b0, nxt_xmax};
    wire [YW:0]   cy_sum = {1'b0, nxt_ymin} + {1'b0, nxt_ymax};
    wire [XW-1:0] res_cx = cx_sum[XW:1];   // 包围框中心（非质心，向下取整）
    wire [YW-1:0] res_cy = cy_sum[YW:1];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            O_res_session_id <= 32'd0; O_res_frame_id <= 32'd0;
            O_result_valid   <= 1'b0;
            O_target_present <= 1'b0;
            O_color_class    <= 2'd0;
            O_pixel_count    <= 20'd0;
            O_xmin <= {XW{1'b0}}; O_xmax <= {XW{1'b0}}; O_center_x <= {XW{1'b0}};
            O_ymin <= {YW{1'b0}}; O_ymax <= {YW{1'b0}}; O_center_y <= {YW{1'b0}};
            O_result_ready   <= 1'b0;
        end else begin
            O_result_ready <= pend_pub;                  // 单拍脉冲
            if (pend_pub) begin
                // 结果恒为整帧锁存，下一帧期间保持不变
                O_res_session_id <= eff_session;
                O_res_frame_id   <= eff_frame;
                O_result_valid   <= eff_ok;
                O_target_present <= res_ok;
                O_color_class    <= res_ok ? TARGET_CLASS[1:0] : 2'd0;
                O_pixel_count    <= res_ok ? nxt_cnt    : 20'd0;
                O_xmin           <= res_ok ? nxt_xmin   : {XW{1'b0}};
                O_xmax           <= res_ok ? nxt_xmax   : {XW{1'b0}};
                O_ymin           <= res_ok ? nxt_ymin   : {YW{1'b0}};
                O_ymax           <= res_ok ? nxt_ymax   : {YW{1'b0}};
                O_center_x       <= res_ok ? res_cx     : {XW{1'b0}};
                O_center_y       <= res_ok ? res_cy     : {YW{1'b0}};
            end
        end
    end
endmodule
