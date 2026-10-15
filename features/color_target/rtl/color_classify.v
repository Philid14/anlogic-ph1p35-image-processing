`timescale 1ns / 1ps
// color_classify —— 单像素颜色分类，HSV 扇区法，**不含除法器**。
//
// 为什么不用 RGB 阈值：协议 §2.2 要求"不修改主线 AWB/曝光来迁就检测"，而 RGB 阈值
// 随增益/白平衡漂移。HSV 的 hue 与亮度无关，阈值法抗光照变化，是公开资料的通行做法
// （见本目录 GITHUB_RESEARCH.md 的调研表）。
//
// 判据（以 TARGET_CLASS=红为例）：
//     R 为最大通道  且   hue 偏离 0 度不超过 HUE_HALF_WIDTH_DEG
//                  且   彩度 C = max-min >= C_MIN
//                  且   亮度 max       >= V_MIN
//
// 为什么能无除法：设 C = max-min，在 R 为最大的扇区内
//     |hue 偏移| = 60度 * |G-B| / C
//   因此 "|hue 偏移| <= W" 等价于 "60*|G-B| <= W*C"，
//   再把 60/W 合并成一个 Q8 常数斜率 HUE_SLOPE_Q8 = 60*256/W：
//     |G-B| * HUE_SLOPE_Q8  <=  C * 256
//   全式只有常数乘法（TD 会做 CSD 移位加法分解）、减法与比较，无除法、无 DSP 乘法器。
//
// C_MIN 同时承担两件事：滤掉白/灰（彩度低）与滤掉暗部噪声（暗处色度也低）。
module color_classify #(
    parameter integer TARGET_CLASS        = 0,    // 0=红 1=绿 2=蓝
    parameter integer HUE_HALF_WIDTH_DEG  = 30,   // hue 半宽 W，单位度
    parameter integer C_MIN               = 24,   // 彩度下限
    parameter integer V_MIN               = 32    // 亮度下限
)(
    input      [7:0] I_r,
    input      [7:0] I_g,
    input      [7:0] I_b,
    output           O_hit
);
    // 60*256/W 的整数四舍五入；W 为标准参数量，编译期常量
    localparam integer HUE_SLOPE_Q8 = (60*256 + HUE_HALF_WIDTH_DEG/2) / HUE_HALF_WIDTH_DEG;

    wire [7:0] lmax = (I_r >= I_g) ? ((I_r >= I_b) ? I_r : I_b)
                                   : ((I_g >= I_b) ? I_g : I_b);
    wire [7:0] lmin = (I_r <= I_g) ? ((I_r <= I_b) ? I_r : I_b)
                                   : ((I_g <= I_b) ? I_g : I_b);
    wire [8:0] chroma = lmax - lmin;              // C，0..255

    // 目标类是否为本像素的最大通道（并列时给低序号通道优先，保证分类互斥）
    wire sel_max_r = (I_r >= I_g) && (I_r >= I_b);
    wire sel_max_g = (I_g >  I_r) && (I_g >= I_b);
    wire sel_max_b = (I_b >  I_r) && (I_b >  I_g);

    // 另外两个通道之差的绝对值 |d|
    wire [7:0] d_r = (I_g >= I_b) ? (I_g - I_b) : (I_b - I_g);
    wire [7:0] d_g = (I_r >= I_b) ? (I_r - I_b) : (I_b - I_r);
    wire [7:0] d_b = (I_r >= I_g) ? (I_r - I_g) : (I_g - I_r);

    // 只保留目标类所需的比较链，其余被常量条件剪掉，省 LUT
    wire       sel_max;
    wire [7:0] diff_abs;
    generate
        if (TARGET_CLASS == 1) begin : g_green
            assign sel_max  = sel_max_g;
            assign diff_abs = d_g;
        end else if (TARGET_CLASS == 2) begin : g_blue
            assign sel_max  = sel_max_b;
            assign diff_abs = d_b;
        end else begin : g_red
            assign sel_max  = sel_max_r;
            assign diff_abs = d_r;
        end
    endgenerate

    wire [17:0] hue_lhs = diff_abs * HUE_SLOPE_Q8;   // <= 255*1024 = 261120，18 位足够
    wire [17:0] hue_rhs = {chroma, 8'b0};            // C * 256

    assign O_hit = sel_max
                && (hue_lhs <= hue_rhs)
                && (chroma  >= C_MIN[8:0])
                && (lmax    >= V_MIN[7:0]);
endmodule
