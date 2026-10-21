`timescale 1ns / 1ps
// tb_color_target_track —— 跟踪状态机的独立自检台。
//
// 激励每行 12 字段：strobe rvalid present count xmin xmax ymin ymax cx cy session frame
// 每拍（posedge 之后）回写一行 12 字段：
//   state show count xmin xmax ymin ymax cx cy session frame change
// 期望值由 model/ref_color_target_track.py 计算后逐行比对。
//
// strobe 每行只脉动一个时钟周期：驱动后立即在采样点收回，避免相邻两行连成高电平被
// 当成两次评估。
module tb_color_target_track;
    parameter integer XW          = 11;
    parameter integer YW          = 10;
    parameter integer ACQ_FRAMES  = 3;
    parameter integer LOST_FRAMES = 15;
    parameter integer MAX_JUMP    = 0;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;

    reg          strobe = 0, rvalid = 0, present = 0;
    reg [19:0]   cnt = 0;
    reg [XW-1:0] xmin = 0, xmax = 0, cx = 0;
    reg [YW-1:0] ymin = 0, ymax = 0, cy = 0;
    reg [31:0]   sess = 0, fid = 0;

    wire [1:0]    O_track_state;
    wire          O_show, O_state_change;
    wire [19:0]   O_out_count;
    wire [XW-1:0] O_out_xmin, O_out_xmax, O_out_center_x;
    wire [YW-1:0] O_out_ymin, O_out_ymax, O_out_center_y;
    wire [31:0]   O_out_session_id, O_out_frame_id;

    color_target_track #(
        .XW(XW), .YW(YW), .ACQ_FRAMES(ACQ_FRAMES),
        .LOST_FRAMES(LOST_FRAMES), .MAX_JUMP(MAX_JUMP)
    ) dut (
        .clk(clk), .rst_n(rst_n),
        .I_result_strobe(strobe), .I_result_valid(rvalid), .I_target_present(present),
        .I_pixel_count(cnt),
        .I_xmin(xmin), .I_xmax(xmax), .I_center_x(cx),
        .I_ymin(ymin), .I_ymax(ymax), .I_center_y(cy),
        .I_session_id(sess), .I_frame_id(fid),
        .O_track_state(O_track_state), .O_show(O_show), .O_state_change(O_state_change),
        .O_out_count(O_out_count),
        .O_out_xmin(O_out_xmin), .O_out_xmax(O_out_xmax), .O_out_center_x(O_out_center_x),
        .O_out_ymin(O_out_ymin), .O_out_ymax(O_out_ymax), .O_out_center_y(O_out_center_y),
        .O_out_session_id(O_out_session_id), .O_out_frame_id(O_out_frame_id)
    );

    integer fin, fout, rc, n = 0;
    reg [2047:0] spath, opath;

    // 先读进临时寄存器，再在 negedge 统一驱动。这样每一行的激励恰好占用一个时钟周期，
    // 不会因为 fscanf 的赋值时刻与复位释放时刻重合而让某一行跨过两个 posedge、被评估两次。
    reg          s_in, rv_in, pr_in;
    reg [19:0]   cnt_in;
    reg [XW-1:0] xmin_in, xmax_in, cx_in;
    reg [YW-1:0] ymin_in, ymax_in, cy_in;
    reg [31:0]   sess_in, fid_in;

    initial begin
        if (!$value$plusargs("STIM=%s", spath)) begin $display("FAIL missing STIM"); $finish; end
        if (!$value$plusargs("OUT=%s",  opath)) begin $display("FAIL missing OUT");  $finish; end
        fin  = $fopen(spath, "r");
        fout = $fopen(opath, "w");
        if (fin == 0 || fout == 0) begin $display("FAIL open files"); $finish; end

        strobe = 0; rvalid = 0; present = 0;
        repeat (4) @(negedge clk);
        rst_n = 1;

        while (!$feof(fin)) begin
            rc = $fscanf(fin, "%d %d %d %d %d %d %d %d %d %d %d %d\n",
                         s_in, rv_in, pr_in, cnt_in,
                         xmin_in, xmax_in, ymin_in, ymax_in, cx_in, cy_in,
                         sess_in, fid_in);
            if (rc == 12) begin
                @(negedge clk);
                strobe = s_in; rvalid = rv_in; present = pr_in;
                cnt = cnt_in;
                xmin = xmin_in; xmax = xmax_in;
                ymin = ymin_in; ymax = ymax_in;
                cx = cx_in; cy = cy_in;
                sess = sess_in; fid = fid_in;
                @(posedge clk); #1;
                $fwrite(fout, "%0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d\n",
                        O_track_state, O_show, O_out_count,
                        O_out_xmin, O_out_xmax, O_out_ymin, O_out_ymax,
                        O_out_center_x, O_out_center_y,
                        O_out_session_id, O_out_frame_id, O_state_change);
                n = n + 1;
            end else if (!$feof(fin)) begin
                $display("FAIL malformed stimulus (rc=%0d)", rc); $finish;
            end
        end
        $fclose(fin);
        $fclose(fout);
        if (n == 0) begin $display("FAIL no frames checked"); $finish; end
        $display("PASS color_target_track frames=%0d", n);
        $finish;
    end
endmodule
