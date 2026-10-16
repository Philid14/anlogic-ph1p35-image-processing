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
// 为什么能无除法：设 C = max-min，d = 另两个通道之差，在目标通道为最大的扇区内
//     |hue 偏移| = 60度 * |d| / C
//   因此 "|hue 偏移| <= W 度" 等价于下面的**交叉乘积**判据，两侧都左移了 C：
//     60 * |d|  <=  W * C
//   全式只有常数乘法（TD 会做 CSD 移位加法分解）、减法与比较，无除法、无 DSP 乘法器。
//   （早期版本把 60/W 预合并成一个 Q8 斜率常数来省一次乘法，那个形式在小 W 下
//     斜率会撑爆固定位宽；交叉乘积两侧上界恒为 60*255，位宽与 W 无关，故弃用。）
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
    // 参数合法范围：W 的语义是"hue 半宽（度）"，而 R 为最大通道的扇区本身只有 60 度宽，
    // 因此把 W 夹到 0..60。夹取是编译期常量折叠，不产生运行时逻辑，也顺带杜绝
    // 越界参数造成的乘积溢出。其余参数：C_MIN 取 0..511（内部按 9 位比较）、V_MIN 取 0..255。
    localparam integer W_DEG = (HUE_HALF_WIDTH_DEG < 0) ? 0
                             : ((HUE_HALF_WIDTH_DEG > 60) ? 60 : HUE_HALF_WIDTH_DEG);

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

    // 判据直接用交叉乘积： 60 * |d| <= W * C   （等价于 |d|/C <= W/60，即 hue 偏移 <= W 度）
    // 两侧上界都是 60*255 = 15300，14 位足够，**位宽与 W 无关**。
    // 原实现把 60/W 预先合并成 Q8 斜率，斜率随 W 变小而变大（W=10 时 255*1536 = 391680
    // 需要 19 位），却固定用 18 位承载，于是小半宽下乘积被截断、判据失效 ——
    // 例如 W=10、RGB=(255,200,0) 实际色相 47 度，却被误判为红色。
    wire [13:0] hue_lhs = diff_abs * 60;
    wire [13:0] hue_rhs = chroma * W_DEG[7:0];

    assign O_hit = sel_max
                && (hue_lhs <= hue_rhs)
                && (chroma  >= C_MIN[8:0])
                && (lmax    >= V_MIN[7:0]);
endmodule
