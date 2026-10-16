`timescale 1ns / 1ps
// color_target_text_overlay —— TARGET 的**文字标注**（T3 的文字部分）。
//
// 对应赛题（docs/赛题/…选题指南.pdf，选题二）：
//   扩展要求(2) "…并在输出画面中叠加检测结果与**文字说明**"
//   高阶挑战项(2) "动态目标跟踪与**坐标叠加**"
// 本模块补的是这半句：把 track 的结果以文字形式叠加到画面上
// （框线与中心十字在 color_target_overlay.v 里，两者是并列的两个覆盖请求）。
//
// ---------------------------------------------------------------------------
// 三个刻意的设计决定
//
// 1) **不实例化任何字库**（协议 §3：共享 OSD 由 MAIN 维护）。
//    字形通过端口借：本模块输出 `O_glyph_char` / `O_glyph_row` 请求，
//    由 MAIN 把**它已有的那一个** `osd_char_lib`（或它决定再放一份）接上，
//    组合返回 `I_glyph_bits`（16 位字形行点阵，高位在左——与主线一致）。
//    这样既不多占一份字库资源，也不改写共享件。
//    参考量：主线 EDGE_CONTROL_V1 的综合报告里，`edge_status_osd`（**含字库**）
//    占 248 LUT / 234 reg（整机 18307/38189 LUT）——即整份状态 OSD 约 0.65% 器件。
//
// 2) **必须接在显示侧合成，不能放在 ISP→DDR 之前**。
//    主线现有的 `edge_status_osd` 在 ISP 流里（DDR 之前），因为它显示的是"配置值"，
//    帧开始时就知道。而**目标检测结果要帧末才有**，塞不进本帧的像素流。
//    好在显示侧有一整帧的余量，比框线那 1~2 像素的对齐宽松得多。
//
// 3) **十进制转换不用除法器、也不用上百 LUT 的组合转换器**。
//    值每帧才变一次，所以逐位双-dabble（double dabble）移位折算，每帧 3 轮、
//    约 66 个周期就够了：一个 24 位 BCD 移位寄存器 + 6 个 4 位加法器。
//    触发条件是"输入变化 **或** I_update 脉冲"，所以 MAIN 即使不接 I_update 也能工作。
//
// 画面内容（两行；SCALE=1 时字符格 16x16）：
//     RED Xnnnn Ynnn            ← 中心坐标（不是质心）
//     Nnnnnnn SEARCH|ACQ|TRACK|HOLD
// 数字若超出显示位数则**饱和**显示（如 999999），不截断——截断会显示错误的数。
// 具体上限见 §"饱和"。实际取值范围内永远不会饱和：count ≤ 921600、x ≤ 1279、y ≤ 719。
// ---------------------------------------------------------------------------
module color_target_text_overlay #(
    parameter integer XW         = 11,        // 显示坐标位宽（与 detect/track 一致）
    parameter integer YW         = 10,
    parameter integer ENABLE     = 1,         // 0 = 恒不覆盖（MAIN 可以先接上看资源再决定开不开）
    parameter integer X0         = 16,        // 区域左上角（显示坐标）——**由 MAIN 决定**
    parameter integer Y0         = 600,       // 默认放左下角，避开主线右上角的状态框(800,16,448x72)
    parameter integer SCALE      = 1,         // 字形放大倍数，只支持 1 -> 16x16，2 -> 32x32
    parameter integer LINE_CHARS = 14,        // 每行字符数（决定区域宽度 = LINE_CHARS*16*SCALE）
    parameter [23:0]  TEXT_RGB   = 24'hFFFFFF,// 字形颜色，默认白
    parameter [23:0]  DIM_RGB    = 24'h808080,// I_show=0 时字形的颜色（暗一档，仍可见）
    parameter [23:0]  BG_RGB     = 24'h101010 // 文字块底色，默认深灰（与主线 OSD 一致）
)(
    input               clk,
    input               rst_n,

    // ---- 显示侧逐像素接口（与 color_target_overlay.v 同一约定）----
    input               I_pixel_valid,
    input      [XW-1:0] I_x,
    input      [YW-1:0] I_y,

    // ---- 来自 color_target_track 的稳定结果 ----
    input               I_update,          // 可选：结果更新脉冲（接 detect 的 O_result_ready）
    input               I_show,            // track.O_show
    input      [1:0]    I_state,           // track.O_track_state（0=SEARCH 1=ACQ 2=TRACK 3=HOLD）
    input      [19:0]   I_count,           // track.O_out_count
    input      [XW-1:0] I_center_x,        // track.O_out_center_x
    input      [YW-1:0] I_center_y,        // track.O_out_center_y

    // ---- 字形借出借入：本模块不实例化字库（见文件头 1）----
    output      [7:0]   O_glyph_char,      // 请求的字符（ASCII，与主线 osd_char_lib 一致）
    output      [3:0]   O_glyph_row,       // 请求的字形行（0..15，自上而下）
    input       [15:0]  I_glyph_bits,      // 该行的点阵，[15] 最左

    // ---- 覆盖请求（合成顺序仍由 MAIN 的 mixer 决定，协议 §4.5）----
    output              O_overlay_valid,
    output      [23:0]  O_overlay_rgb
);
    // ------------------------------------------------------------------
    // 几何
    // ------------------------------------------------------------------
    localparam integer S      = (SCALE <= 1) ? 1 : 2;      // 只支持 1 或 2
    localparam integer LOG2S  = (S == 1) ? 0 : 1;
    localparam integer CELL   = 16 * S;                    // 字符格边长
    localparam integer SHIFT  = 4 + LOG2S;                 // 由 lx 取字符列的移位量（CELL 是 2 的幂）
    localparam integer GAP    = 2 * S;                     // 两行之间的空档
    localparam integer REG_W  = LINE_CHARS * CELL;
    localparam integer REG_H  = 2 * CELL + GAP;
    localparam integer X1     = XW + 1;                    // 比较域加宽一位，避免 X0+REG_W 越界回绕
    localparam integer Y1     = YW + 1;

    wire [X1-1:0] px   = {1'b0, I_x};
    wire [Y1-1:0] py   = {1'b0, I_y};
    wire          in_x = (px >= X0) && (px < X0 + REG_W);
    wire          in_y = (py >= Y0) && (py < Y0 + REG_H);
    wire          in_region = ENABLE && in_x && in_y;

    wire [X1-1:0] lx = px - X0;                            // 仅在 in_region 时使用
    wire [Y1-1:0] ly = py - Y0;
    wire          line1 = (ly >= CELL + GAP);              // 0=第一行 1=第二行
    wire [Y1-1:0] ly_l  = line1 ? (ly - (CELL + GAP)) : ly;
    wire [X1-1:0] char_col = lx >> SHIFT;                  // 第几个字符格
    wire [X1-1:0] in_cell_x = lx & (CELL - 1);
    wire [Y1-1:0] in_cell_y = ly_l & (CELL - 1);
    wire [3:0]    gcol = in_cell_x >> LOG2S;               // 字形列 0..15
    wire [3:0]    grow = in_cell_y >> LOG2S;               // 字形行 0..15
    wire [4:0]    bit_idx = 5'd15 - {1'b0, gcol};          // 高位在左（与主线一致）
    wire          gbit = I_glyph_bits[bit_idx[3:0]];

    // ------------------------------------------------------------------
    // 十进制转换：20 位二进制 -> 6 位 BCD，逐位双-dabble；每帧 3 轮（count/x/y）
    // ------------------------------------------------------------------
    localparam [1:0] C_IDLE = 2'd0, C_LOAD = 2'd1, C_STEP = 2'd2, C_STORE = 2'd3;
    localparam integer STEPS = 20;                          // 20 位输入 -> 20 次移位

    // 饱和（不是截断）：显示位数有限，超范围显示成最大可显示值，避免显示错误的数。
    // 右侧的赋值靠"赋值位宽自动零扩展"，不写显式零扩展——那样在 XW>20 时会是负数重复次数。
    wire [19:0] sat_c = (I_count    > 20'd999999) ? 20'd999999 : I_count;
    wire [19:0] sat_x = (I_center_x > 20'd9999)   ? 20'd9999   : I_center_x;
    wire [19:0] sat_y = (I_center_y > 20'd999)    ? 20'd999    : I_center_y;

    reg [1:0]  cst;            // 转换状态
    reg [1:0]  round;          // 0=count 1=x 2=y
    reg [4:0]  step;
    reg [19:0] bin;            // 待移位的二进制
    reg [23:0] bcd;            // 6 位 BCD（每位 4 bit）
    reg [23:0] dig_c;          // count 的 6 位十进制
    reg [15:0] dig_x;          // x 的 4 位十进制
    reg [11:0] dig_y;          // y 的 3 位十进制
    // 原始输入的影子寄存器：只在 I_update/值变化时才重新换算
    reg [19:0]   raw_c;
    reg [XW-1:0] raw_x;
    reg [YW-1:0] raw_y;

    wire inputs_changed = (I_count    != raw_c) ||
                          (I_center_x != raw_x) ||
                          (I_center_y != raw_y);
    wire start = (cst == C_IDLE) && (I_update || inputs_changed);

    // 本轮要转换的值（从饱和后的输入取）
    wire [19:0] conv_val = (round == 2'd0) ? sat_c :
                           (round == 2'd1) ? {6'b0, sat_x} :
                                             {10'b0, sat_y};

    // 每个 BCD 位：≥5 则加 3（双-dabble 的修正步）
    reg [23:0] bcd_corr;
    integer i;
    always @* begin
        bcd_corr = bcd;
        for (i = 0; i < 6; i = i + 1)
            if (bcd_corr[i*4 +: 4] >= 4'd5)
                bcd_corr[i*4 +: 4] = bcd_corr[i*4 +: 4] + 4'd3;
    end

    wire [43:0] v_shift = {bcd_corr, bin} << 1;             // 修正后整体左移一位

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cst <= C_IDLE; round <= 2'd0; step <= 5'd0;
            bin <= 20'd0; bcd <= 24'd0;
            dig_c <= 24'd0; dig_x <= 16'd0; dig_y <= 12'd0;
            raw_c <= 20'd0; raw_x <= {XW{1'b0}}; raw_y <= {YW{1'b0}};
        end else begin
            case (cst)
                C_IDLE: begin
                    if (start) begin
                        raw_c <= I_count; raw_x <= I_center_x; raw_y <= I_center_y;
                        round <= 2'd0;
                        cst   <= C_LOAD;
                    end
                end
                C_LOAD: begin
                    bin  <= conv_val;
                    bcd  <= 24'd0;
                    step <= 5'd0;
                    cst  <= C_STEP;
                end
                C_STEP: begin
                    if (step == STEPS) begin
                        cst <= C_STORE;
                    end else begin
                        bcd <= v_shift[43:20];
                        bin <= v_shift[19:0];
                        step <= step + 5'd1;
                    end
                end
                default: begin                  // C_STORE
                    case (round)
                        2'd0: dig_c <= bcd;
                        2'd1: dig_x <= bcd[15:0];
                        default: dig_y <= bcd[11:0];
                    endcase
                    if (round == 2'd2) begin
                        round <= 2'd0;
                        cst   <= C_IDLE;
                    end else begin
                        round <= round + 2'd1;
                        cst   <= C_LOAD;
                    end
                end
            endcase
        end
    end

    // 取 BCD 的某一位为 ASCII（0..9 已是合法 BCD，直接 +'0'）
    function [7:0] adec;
        input [3:0] d;
        begin adec = 8'h30 + {4'b0, d}; end
    endfunction

    // 状态名（6 字符，右侧补空格）
    reg [47:0] name6;
    always @* case (I_state)
        2'd0:    name6 = "SEARCH";
        2'd1:    name6 = "ACQ   ";
        2'd2:    name6 = "TRACK ";
        default: name6 = "HOLD  ";
    endcase

    // ------------------------------------------------------------------
    // 字符选择
    // ------------------------------------------------------------------
    reg [7:0] ch;
    always @* begin
        ch = 8'h20;                                        // 空格
        if (!line1) begin
            case (char_col)
                0:  ch = "R";
                1:  ch = "E";
                2:  ch = "D";
                3:  ch = " ";
                4:  ch = "X";
                5:  ch = adec(dig_x[15:12]);
                6:  ch = adec(dig_x[11:8]);
                7:  ch = adec(dig_x[7:4]);
                8:  ch = adec(dig_x[3:0]);
                9:  ch = " ";
                10: ch = "Y";
                11: ch = adec({2'b0, dig_y[11:8]});
                12: ch = adec(dig_y[7:4]);
                13: ch = adec(dig_y[3:0]);
                default: ch = 8'h20;
            endcase
        end else begin
            case (char_col)
                0:  ch = "N";
                1:  ch = adec(dig_c[23:20]);
                2:  ch = adec(dig_c[19:16]);
                3:  ch = adec(dig_c[15:12]);
                4:  ch = adec(dig_c[11:8]);
                5:  ch = adec(dig_c[7:4]);
                6:  ch = adec(dig_c[3:0]);
                7:  ch = " ";
                8:  ch = name6[47:40];
                9:  ch = name6[39:32];
                10: ch = name6[31:24];
                11: ch = name6[23:16];
                12: ch = name6[15:8];
                13: ch = name6[7:0];
                default: ch = 8'h20;
            endcase
        end
    end

    assign O_glyph_char = ch;
    assign O_glyph_row  = grow;

    assign O_overlay_valid = I_pixel_valid && in_region;
    // 文字块始终覆盖（底色），字形颜色按 I_show 分两档：有目标时亮、无目标时暗。
    // 这样现场能看到 SEARCH/ACQ/HOLD 的状态变化，而不是一片空白；
    // 想看"有目标才显示"的话，把整块使能接到 I_show 上即可（MAIN 侧改接线，不用改本模块）。
    assign O_overlay_rgb   = gbit ? (I_show ? TEXT_RGB : DIM_RGB) : BG_RGB;
endmodule
