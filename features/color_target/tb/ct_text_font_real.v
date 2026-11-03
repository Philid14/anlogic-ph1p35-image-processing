`timescale 1ns / 1ps
// ct_text_font_real —— 把**主线的共享字库**包装成本自检台统一的字形端口。
//
// 用途：接入前就用**真字库**跑一遍，逐位验证 color_target_text_overlay 与字库之间的
// 唯一隐式契约——字形位索引（`[15]` 最左、每行 16 位、16 行）。这条约定用桩测不出来：
// 桩用什么约定，模块就跟着用什么约定，两边一起错也发现不了。
//
// ⚠️ 本文件**只读**引用主线文件，不修改它（协议 §3：共享 OSD 由 MAIN 维护）。
// `osd_char_lib.v` 的路径由 runner 传入（默认取主线示例目录下的那一份）；
// 那个文件不在时，runner 会自动退回 ct_text_font_stub.v 并打印说明。
//
// 本包装**不新增字库实例以外的东西**：它就是一个透传。MAIN 真正接入时不必用这个文件——
// 直接把已有 osd_char_lib 实例（或它的第二份）接到 color_target_text_overlay 的
// `O_glyph_char`/`O_glyph_row`/`I_glyph_bits` 三个端口上即可。
module ct_text_font (
    input      [7:0]  I_char,
    input      [3:0]  I_row,
    output     [15:0] O_row_bits
);
    osd_char_lib u_font (
        .I_char(I_char),
        .I_row(I_row),
        .O_row_bits(O_row_bits)
    );
endmodule
