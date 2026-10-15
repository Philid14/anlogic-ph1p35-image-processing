`timescale 1ns / 1ps
// color_target_overlay —— TARGET 的独立标注模块（T3）。
//
// 对应协议：
//   §2.2 T3   输出框线、中心十字和坐标的覆盖请求；由 MAIN 合成至对应显示帧
//   §4.3      接受 MAIN 提供的显示坐标、有效像素和整帧锁存的结果，输出 overlay_valid
//             与 RGB888 覆盖颜色，**帧/行内不改变基础像素数量**
//   §4.5      MAIN 分配显示区域、统一字体与合成顺序；不能遮挡 Logo、不改写字库
//
// 设计取舍：
//   * **纯组合**，无流水级。MAIN 用它逐像素判断，不引入对齐负担。
//   * **只产生几何请求**，不参与合成、不决定优先级。Logo/主线状态高于目标框的优先级由
//     MAIN 的 mixer 按 §4.5 执行；本模块不做遮挡规避，也不绑定按键/引脚。
//   * **不做文字**。坐标文字需要字库，而 §4.5 规定字库与字体由 MAIN 统一。本模块只输出
//     框线与十字；文字由 MAIN 用它自己的字库、按本模块输出的框坐标呈现。这是 T3 第一版
//     的明确边界，已在 README 与 INTERFACE 中声明。
module color_target_overlay #(
    parameter integer XW          = 11,
    parameter integer YW          = 10,
    parameter integer BOX_THICK   = 3,          // 框线粗细（像素）
    parameter [23:0]  BOX_RGB     = 24'h00FF00, // 框线颜色，默认绿
    parameter integer CROSS_ARM   = 12,         // 十字半臂长（像素）
    parameter integer CROSS_THICK = 1,          // 十字线粗细（像素）
    parameter [23:0]  CROSS_RGB   = 24'hFFFF00  // 十字颜色，默认黄
)(
    input               I_pixel_valid,     // 当前显示坐标有效
    input      [XW-1:0] I_x,
    input      [YW-1:0] I_y,
    input               I_result_valid,    // 来自 color_target_detect 的整帧锁存结果
    input               I_target_present,
    input      [XW-1:0] I_xmin,
    input      [XW-1:0] I_xmax,
    input      [YW-1:0] I_ymin,
    input      [YW-1:0] I_ymax,
    input      [XW-1:0] I_center_x,
    input      [YW-1:0] I_center_y,
    output              O_overlay_valid,
    output reg [23:0]   O_overlay_rgb
);
    // 比较域加宽一位，避免 in+THICK-1 溢出；减法一侧饱和到 0，避免 max-THICK+1 下溢。
    localparam integer X1 = XW + 1;
    localparam integer Y1 = YW + 1;

    wire [X1-1:0] px = {1'b0, I_x};
    wire [Y1-1:0] py = {1'b0, I_y};
    wire [X1-1:0] xmin_w = {1'b0, I_xmin};
    wire [X1-1:0] xmax_w = {1'b0, I_xmax};
    wire [Y1-1:0] ymin_w = {1'b0, I_ymin};
    wire [Y1-1:0] ymax_w = {1'b0, I_ymax};

    // ---- 框线：四条带，合起来就是矩形描边 ----
    wire [X1-1:0] xl_hi = xmin_w + (BOX_THICK-1);
    wire [X1-1:0] xr_lo = (xmax_w >= (BOX_THICK-1)) ? (xmax_w - (BOX_THICK-1)) : {X1{1'b0}};
    wire [Y1-1:0] yt_hi = ymin_w + (BOX_THICK-1);
    wire [Y1-1:0] yb_lo = (ymax_w >= (BOX_THICK-1)) ? (ymax_w - (BOX_THICK-1)) : {Y1{1'b0}};

    wire x_in_span = (px >= xmin_w) && (px <= xmax_w);
    wire y_in_span = (py >= ymin_w) && (py <= ymax_w);
    wire x_in_band = ((px >= xmin_w) && (px <= xl_hi)) || ((px >= xr_lo) && (px <= xmax_w));
    wire y_in_band = ((py >= ymin_w) && (py <= yt_hi)) || ((py >= yb_lo) && (py <= ymax_w));
    wire box_hit   = (y_in_band && x_in_span) || (x_in_band && y_in_span);

    // ---- 中心十字 ----
    // 臂长向两侧展开；线宽**居中**：横臂行范围 [cy - T/2, cy + (T-1)/2]，
    // 竖臂列范围同理。否则 CROSS_THICK>1 时十字会整体偏向一侧，视觉中心偏离
    // 模块对外报告的 center_*。默认 T=1 时退化为单像素线，行为不变。
    wire [X1-1:0] cxw = {1'b0, I_center_x};
    wire [Y1-1:0] cyw = {1'b0, I_center_y};
    wire [X1-1:0] arm_x_lo = (cxw >= CROSS_ARM) ? (cxw - CROSS_ARM) : {X1{1'b0}};
    wire [X1-1:0] arm_x_hi = cxw + CROSS_ARM;
    wire [Y1-1:0] arm_y_lo = (cyw >= CROSS_ARM) ? (cyw - CROSS_ARM) : {Y1{1'b0}};
    wire [Y1-1:0] arm_y_hi = cyw + CROSS_ARM;

    localparam integer CT_LO = CROSS_THICK / 2;          // 向负方向扩张
    localparam integer CT_HI = (CROSS_THICK - 1) / 2;    // 向正方向扩张
    wire [Y1-1:0] hbar_lo = (cyw >= CT_LO) ? (cyw - CT_LO) : {Y1{1'b0}};
    wire [Y1-1:0] hbar_hi = cyw + CT_HI;
    wire [X1-1:0] vbar_lo = (cxw >= CT_LO) ? (cxw - CT_LO) : {X1{1'b0}};
    wire [X1-1:0] vbar_hi = cxw + CT_HI;

    wire x_in_arm  = (px >= arm_x_lo) && (px <= arm_x_hi);
    wire y_in_arm  = (py >= arm_y_lo) && (py <= arm_y_hi);
    wire y_hbar    = (py >= hbar_lo) && (py <= hbar_hi);
    wire x_vbar    = (px >= vbar_lo) && (px <= vbar_hi);
    wire cross_hit = (x_in_arm && y_hbar) || (x_vbar && y_in_arm);

    wire active = I_pixel_valid && I_result_valid && I_target_present;

    assign O_overlay_valid = active && (cross_hit || box_hit);

    // 十字压在框线之上（同一像素两者都命中时给十字色）
    always @* begin
        if (cross_hit) O_overlay_rgb = CROSS_RGB;
        else           O_overlay_rgb = BOX_RGB;
    end
endmodule
