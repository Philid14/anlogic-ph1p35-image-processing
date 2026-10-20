//======================================================================
// tb_latency_osd.v - panel content test for latency_osd.v
//
// Drives a 320x64 raster and, in every frame, one capture start, one frame
// complete and one display event near the end of the frame (inside the short
// fps window). After the last frame the 80 character panel is dumped.
// The runner compares it with model/latency_model.py built from the DBG values
// printed here, so this test checks formatting + layout, while the association
// logic is covered by tb_latency_meter.v.
//======================================================================
`timescale 1ns/1ps

module tb_latency_osd;
    parameter integer H  = 320;
    parameter integer V  = 64;
    parameter integer HT = 340;
    parameter integer VT = 74;
    parameter integer FRAMES = 3;
    parameter integer TB_TICK_BASE = 10;
    parameter integer TB_TICK_REMAINDER = 50000;
    parameter integer TB_TICK_MOD = 100000;
    parameter integer TB_FPS_WINDOW = 200;
    parameter integer TB_X0 = 8;
    parameter integer TB_Y0 = 4;
    parameter integer TB_REPEAT = 1;   // drive a repeat display -> AGE digits
    parameter integer TB_FAULT  = 0;   // drive an unmatched display -> stats invalid

    localparam integer FC = HT * VT;

    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst_n = 1'b0;

    reg        de = 1'b0, hs = 1'b0, vs = 1'b0;
    reg [23:0] rgb_in = 24'd0;
    reg        cap_event = 1'b0;
    reg [1:0]  cap_kind = 2'd0;
    reg [31:0] cap_sid = 32'd0, cap_fid = 32'd0;
    reg        dsp_event = 1'b0;
    reg [31:0] dsp_sid = 32'd0, dsp_fid = 32'd0;

    wire [23:0] rgb_out;
    wire de_out, hs_out, vs_out;
    wire [7:0]  dbg_rdata;
    wire [31:0] dbg_lat_cycles, dbg_lat_ticks, dbg_age_cycles, dbg_age_ticks;
    wire [31:0] dbg_cap_fps, dbg_dsp_fps, dbg_cap_count, dbg_dsp_count;
    wire [3:0]  dbg_alarm;
    wire        dbg_stats_valid, dbg_lat_seen, dbg_age_seen, dbg_fps_valid;

    reg [6:0] dbg_raddr = 7'd0;

    latency_osd #(
        .TICK_BASE(TB_TICK_BASE), .TICK_REMAINDER(TB_TICK_REMAINDER), .TICK_MOD(TB_TICK_MOD),
        .FPS_WINDOW_TICKS(TB_FPS_WINDOW),
        .H_ACTIVE(H), .V_ACTIVE(V), .X0(TB_X0), .Y0(TB_Y0), .SCALE_LOG2(1),
        .PANEL_EN(1), .BG_DIM(1), .FG_RGB(24'hFFFFFF), .BG_RGB(24'h000000)
    ) dut (
        .clk_cap(clk), .rst_cap_n(rst_n), .cap_event(cap_event), .cap_kind(cap_kind),
        .cap_sid(cap_sid), .cap_fid(cap_fid),
        .clk(clk), .rst_n(rst_n), .de(de), .hs(hs), .vs(vs), .rgb_in(rgb_in),
        .dsp_event(dsp_event), .dsp_sid(dsp_sid), .dsp_fid(dsp_fid),
        .alarm_clr(1'b0), .resync_req(1'b0),
        .rgb_out(rgb_out), .de_out(de_out), .hs_out(hs_out), .vs_out(vs_out),
        .dbg_raddr(dbg_raddr), .dbg_rdata(dbg_rdata),
        .dbg_lat_cycles(dbg_lat_cycles), .dbg_lat_ticks(dbg_lat_ticks),
        .dbg_age_cycles(dbg_age_cycles), .dbg_age_ticks(dbg_age_ticks),
        .dbg_cap_fps(dbg_cap_fps), .dbg_dsp_fps(dbg_dsp_fps),
        .dbg_cap_count(dbg_cap_count), .dbg_dsp_count(dbg_dsp_count),
        .dbg_alarm(dbg_alarm), .dbg_stats_valid(dbg_stats_valid),
        .dbg_lat_seen(dbg_lat_seen), .dbg_age_seen(dbg_age_seen), .dbg_fps_valid(dbg_fps_valid)
    );

    integer cyc = 0, line = 0, col = 0, i, f;
    integer start_off = 1500, done_off = 1400, dsp_off = 1300;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cyc <= 0; de <= 1'b0; hs <= 1'b0; vs <= 1'b0;
            cap_event <= 1'b0; dsp_event <= 1'b0;
        end else begin
            cyc <= cyc + 1;
            line = (cyc % FC) / HT;
            col  = (cyc % FC) % HT;
            vs <= (line < 2);
            hs <= (col >= H) && (col < H + 4);
            de <= (line < V) && (col < H);

            cap_event <= 1'b0;
            dsp_event <= 1'b0;
            for (f = 0; f < FRAMES; f = f + 1) begin
                if (cyc == (f + 1) * FC - start_off) begin
                    cap_event <= 1'b1; cap_kind <= 2'd0;
                    cap_sid <= 32'd1; cap_fid <= f[31:0];
                end
                if (cyc == (f + 1) * FC - done_off) begin
                    cap_event <= 1'b1; cap_kind <= 2'd2;
                    cap_sid <= 32'd1; cap_fid <= f[31:0];
                end
                if (cyc == (f + 1) * FC - dsp_off) begin
                    dsp_event <= 1'b1; dsp_sid <= 32'd1; dsp_fid <= f[31:0];
                end
            end
            // repeat display of frame 0 -> image age
            if (TB_REPEAT != 0 && (cyc == 3 * FC - dsp_off + 50)) begin
                dsp_event <= 1'b1; dsp_sid <= 32'd1; dsp_fid <= 32'd0;
            end
            // unmatched display -> association invalid, LAT must show "---.--"
            if (TB_FAULT != 0 && (cyc == FRAMES * FC - dsp_off + 25)) begin
                dsp_event <= 1'b1; dsp_sid <= 32'd1; dsp_fid <= 32'd9;
            end
        end
    end

    // Latch the meter values at every vs falling edge: these are exactly the
    // values the formatter uses for the panel that follows, so the DBG output
    // and the dumped characters describe the same frame.
    reg     vs_tb_d = 1'b0;
    integer falls = 0;
    integer lat_at = 0, age_at = 0, cap_at = 0, dsp_at = 0, frame_at = 0;
    integer alarm_at = 0, ls_at = 0, as_at = 0, fv_at = 0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            vs_tb_d <= 1'b0;
        end else begin
            vs_tb_d <= vs;
            #1;
            if (vs_tb_d && !vs) begin
                falls   = falls + 1;
                lat_at   = dbg_lat_ticks;
                age_at   = dbg_age_ticks;
                cap_at   = dbg_cap_fps;
                dsp_at   = dbg_dsp_fps;
                frame_at = dut.frame_bcd;
                alarm_at = dbg_alarm;
                ls_at    = dbg_lat_seen;
                as_at    = dbg_age_seen;
                fv_at    = dbg_fps_valid;
            end
        end
    end

    initial begin
        rst_n = 1'b0;
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        // wait until the formatter is idle again after the last intended frame
        while ((falls < FRAMES + 2) || (dut.state !== 4'd1)) @(posedge clk);
        #20;
        $display("DBG lat_ticks=%0d age_ticks=%0d cap=%0d dsp=%0d alarm=%0d stats=%0d lat_seen=%0d age_seen=%0d fps_valid=%0d",
                 lat_at, age_at, cap_at, dsp_at, alarm_at, dbg_stats_valid, ls_at, as_at, fv_at);
        $display("FRAME_BCD %08x", frame_at);
        for (i = 0; i < 80; i = i + 1) begin
            dbg_raddr = i[6:0];
            #1;
            $display("CHAR %0d %0d", i, dbg_rdata);
        end
        $display("TB_ERRORS=0");
        $finish;
    end

    initial begin
        #5000000;
        $display("TB_ERRORS=1 timeout");
        $finish;
    end
endmodule
