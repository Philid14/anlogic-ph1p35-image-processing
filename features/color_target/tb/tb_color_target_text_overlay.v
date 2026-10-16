`timescale 1ns / 1ps
// tb_color_target_text_overlay —— 文字标注模块的自检台。
//
// 三件事刻意这样安排：
//
// 1) **字形由 ct_text_font 提供，端口固定**，具体是"桩"还是"主线真字库"由 runner 决定：
//    桩（ct_text_font_stub.v）逐位可复现、不依赖主线路径；真字库（ct_text_font_real.v
//    包装 osd_char_lib.v）用来把**字形位索引约定**也验掉——这条约定用桩测不出来。
//    本台要验证的是"请求了哪个字符、哪一行、落在哪个像素"，不是字体长什么样
//    （字库是 MAIN 维护的共享件，由它自己的自检负责）。
//
// 2) **每个用例先给一段"沉降"激励**（valid=0，约 100 拍），等十进制转换跑完 3 轮
//    （每轮 20 次移位 + 装载/存储，约 66 拍）再开始扫像素。否则扫到的还是上一轮的旧数字。
//
// 3) 激励里的数值在扫描期间**保持不变**，所以变化检测不会重新触发转换——
//    这样"一次转换、多次扫描"的时序才稳定。
//
// 激励每行 9 字段： valid x y update show state count cx cy
//   update=1 只出现在沉降段的第一行（用来覆盖 I_update 触发路径；
//   也让部分用例全程 update=0，覆盖"只靠输入变化触发"的路径）
// 每行输出 6 字段（仅 valid=1 时写）： x y ov rgb char row
module tb_color_target_text_overlay;
    parameter integer XW         = 11;
    parameter integer YW         = 10;
    parameter integer ENABLE     = 1;
    parameter integer X0         = 16;
    parameter integer Y0         = 600;
    parameter integer SCALE      = 1;
    parameter integer LINE_CHARS = 14;
    parameter integer TEXT_RGB   = 24'hFFFFFF;
    parameter integer DIM_RGB    = 24'h808080;
    parameter integer BG_RGB     = 24'h101010;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;

    reg               valid = 0;
    reg  [XW-1:0]     x = 0;
    reg  [YW-1:0]     y = 0;
    reg               upd = 0;
    reg               shw = 0;
    reg  [1:0]        st  = 0;
    reg  [19:0]       cnt = 0;
    reg  [XW-1:0]     cx  = 0;
    reg  [YW-1:0]     cy  = 0;

    wire        ov;
    wire [23:0] orgb;
    wire [7:0]  gch;
    wire [3:0]  grow;

    // 字形源：runner 决定编译哪一个实现（ct_text_font_stub.v 桩，或 ct_text_font_real.v
    // 包装主线 osd_char_lib.v）。两者端口一致，本台不关心是哪个。
    wire [15:0] gbits;
    ct_text_font u_font (.I_char(gch), .I_row(grow), .O_row_bits(gbits));

    color_target_text_overlay #(
        .XW(XW), .YW(YW), .ENABLE(ENABLE), .X0(X0), .Y0(Y0), .SCALE(SCALE),
        .LINE_CHARS(LINE_CHARS), .TEXT_RGB(TEXT_RGB), .DIM_RGB(DIM_RGB),
        .BG_RGB(BG_RGB)
    ) dut (
        .clk(clk), .rst_n(rst_n),
        .I_pixel_valid(valid), .I_x(x), .I_y(y),
        .I_update(upd), .I_show(shw), .I_state(st),
        .I_count(cnt), .I_center_x(cx), .I_center_y(cy),
        .O_glyph_char(gch), .O_glyph_row(grow), .I_glyph_bits(gbits),
        .O_overlay_valid(ov), .O_overlay_rgb(orgb)
    );

    integer fin, fout, rc, n = 0;
    reg [2047:0] spath, opath;
    reg          v_in, u_in, sh_in;
    reg [1:0]    st_in;
    reg [31:0]   x_in, y_in, c_in, cx_in, cy_in;

    initial begin
        if (!$value$plusargs("STIM=%s", spath)) begin $display("FAIL missing STIM"); $finish; end
        if (!$value$plusargs("OUT=%s",  opath)) begin $display("FAIL missing OUT");  $finish; end
        fin  = $fopen(spath, "r");
        fout = $fopen(opath, "w");
        if (fin == 0 || fout == 0) begin $display("FAIL open files"); $finish; end

        repeat (4) @(negedge clk);
        rst_n = 1;

        while (!$feof(fin)) begin
            rc = $fscanf(fin, "%d %d %d %d %d %d %d %d %d\n",
                         v_in, x_in, y_in, u_in, sh_in, st_in, c_in, cx_in, cy_in);
            if (rc == 9) begin
                @(negedge clk);
                valid = v_in;
                x = x_in[XW-1:0]; y = y_in[YW-1:0];
                upd = u_in; shw = sh_in; st = st_in;
                cnt = c_in[19:0]; cx = cx_in[XW-1:0]; cy = cy_in[YW-1:0];
                @(posedge clk); #1;
                if (valid)
                    $fwrite(fout, "%0d %0d %0d %06x %0d %0d\n",
                            x, y, ov, orgb, gch, {2'b0, grow});
                n = n + 1;
            end else if (!$feof(fin)) begin
                $display("FAIL malformed stimulus (rc=%0d)", rc); $finish;
            end
        end
        $fclose(fin);
        $fclose(fout);
        if (n == 0) begin $display("FAIL no lines"); $finish; end
        $display("PASS color_target_text_overlay lines=%0d", n);
        $finish;
    end
endmodule
