`timescale 1ns / 1ps
// ct_text_font_stub —— 自检用的**字形桩**（不是真字库）。
//
// 为什么要有桩：本模块（color_target_text_overlay）不拥有字库——协议 §3 规定共享 OSD 由
// MAIN 维护。自检要验的是"请求了哪个字符、哪一行、落在哪个像素"，所以用一个**逐位可复现**
// 的伪字形就够了，而且它不依赖主线路径上的任何文件。
//
// 映射： bits = {I_char, I_row, 4'h0} ^ 16'hABCD
// XOR 让高位与低位都出现 0 和 1，从而覆盖到"字形位=0/1"两条分支。
//
// ⚠️ 桩测不出**字形位的索引约定**（[15] 最左）——桩用什么约定，模块就跟着用什么约定，
// 两边一起错也发现不了。所以渲染工具默认改用主线真实字库跑（见 ct_text_font_real.v），
// 逐位比对之后再交付。
module ct_text_font (
    input      [7:0]  I_char,
    input      [3:0]  I_row,
    output     [15:0] O_row_bits
);
    assign O_row_bits = {I_char, I_row, 4'h0} ^ 16'hABCD;
endmodule
