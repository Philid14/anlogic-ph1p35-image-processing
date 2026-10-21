//======================================================================
// tb_latency_meter.v - scenario driven testbench for latency_meter.v
//
// The vector file drives events by ABSOLUTE TIME, so the stimulus is
// independent of the DUT's internal timing assumptions. The testbench prints
// every driven event time and every measurement; the Python runner
// (tests/run_latency_sim.py) computes the true latency from those printed
// times and compares it with what the DUT reported.
//
// Vector record: <kind> <time_ns> <a> <b> <c> <d>
//   1  capture pulse : a=sid b=fid c=cap_kind
//   2  display pulse : a=sid b=fid
//   3  alarm_clr pulse
//   4  resync_req pulse
//   5  capture LEVEL : a=sid b=fid c=cap_kind d=hold_ns   (multi cycle test)
//   0  end
//
// Behavioural evidence only: no synthesis, no board claim.
//======================================================================
`timescale 1ns/1ps

module tb_latency_meter;
    parameter integer TB_SAME_CLOCK     = 1;
    parameter real    TB_DEST_HALF      = 5.0;
    parameter real    TB_CAP_HALF       = 5.0;
    parameter integer TB_TICK_BASE      = 2;
    parameter integer TB_TICK_REMAINDER = 50000;
    parameter integer TB_TICK_MOD       = 100000;
    parameter integer TB_CROSS          = 3;
    parameter integer TB_TICK_CROSS     = 1;
    parameter integer TB_FPS_WINDOW     = 100000;
    parameter integer TB_MIN_GAP_SRC    = 2;
    parameter integer TB_MAX_EVENTS     = 64;

    reg clk     = 1'b0;
    reg cap_clk = 1'b0;
    always #(TB_DEST_HALF) clk     = ~clk;
    always #(TB_CAP_HALF)  cap_clk = ~cap_clk;

    wire clk_cap = TB_SAME_CLOCK ? clk : cap_clk;

    reg rst_n = 1'b0, rst_cap_n = 1'b0;

    reg        cap_event = 1'b0;
    reg [1:0]  cap_kind = 2'd0;
    reg [7:0]  cap_sid = 8'd0;
    reg [15:0] cap_fid = 16'd0;
    reg        dsp_event = 1'b0;
    reg [7:0]  dsp_sid = 8'd0;
    reg [15:0] dsp_fid = 16'd0;
    reg        alarm_clr = 1'b0, resync_req = 1'b0;

    wire        cap_too_fast, evt_gap_alarm, lat_valid, lat_seen, age_valid, age_seen;
    wire        stats_valid;
    wire [31:0] lat_cycles, age_cycles, stat_count, unmatched_count, repeat_count, entry_count;
    wire [31:0] cap_count, cap_done_count, cap_abort_count, dsp_count, lost_done_count, lost_abort_count;
    wire [31:0] cap_fps, dsp_fps;
    wire [31:0] queued_count;
    wire        fps_valid;
    wire [31:0] lat_ticks;
    wire [3:0]  alarm;
    wire [63:0] stat_sum_cycles;

    latency_meter #(
        .SID_W          (8),
        .FID_W          (16),
        .ENTRY_LOG2     (3),
        .CNT_W          (32),
        .TICK_W         (32),
        .TICK_BASE      (TB_TICK_BASE),
        .TICK_REMAINDER (TB_TICK_REMAINDER),
        .TICK_MOD       (TB_TICK_MOD),
        .CROSS_CYCLES   (TB_CROSS),
        .TICK_CROSS     (TB_TICK_CROSS),
        .FPS_WINDOW_TICKS (TB_FPS_WINDOW),
        .MIN_GAP_SRC    (TB_MIN_GAP_SRC),
        .MIN_GAP_DST    (3)
    ) dut (
        .clk_cap       (clk_cap),
        .rst_cap_n     (rst_cap_n),
        .cap_event     (cap_event),
        .cap_kind      (cap_kind),
        .cap_sid       (cap_sid),
        .cap_fid       (cap_fid),
        .cap_too_fast  (cap_too_fast),
        .clk           (clk),
        .rst_n         (rst_n),
        .dsp_event     (dsp_event),
        .dsp_sid       (dsp_sid),
        .dsp_fid       (dsp_fid),
        .alarm_clr     (alarm_clr),
        .resync_req    (resync_req),
        .lat_valid     (lat_valid),
        .lat_cycles    (lat_cycles),
        .lat_ticks     (lat_ticks),
        .lat_seen      (lat_seen),
        .age_valid     (age_valid),
        .age_cycles    (age_cycles),
        .age_seen      (age_seen),
        .stats_valid   (stats_valid),
        .alarm         (alarm),
        .stat_count    (stat_count),
        .stat_sum_cycles (stat_sum_cycles),
        .unmatched_count (unmatched_count),
        .repeat_count  (repeat_count),
        .entry_count   (entry_count),
        .lost_done_count (lost_done_count),
        .lost_abort_count (lost_abort_count),
        .cap_count     (cap_count),
        .cap_done_count (cap_done_count),
        .cap_abort_count (cap_abort_count),
        .dsp_count     (dsp_count),
        .cap_fps       (cap_fps),
        .dsp_fps       (dsp_fps),
        .fps_valid     (fps_valid),
        .queued_count  (queued_count),
        .evt_gap_alarm (evt_gap_alarm)
    );

    // ---------------- vector storage ----------------
    integer ev_kind [0:TB_MAX_EVENTS-1];
    real    ev_t    [0:TB_MAX_EVENTS-1];
    integer ev_a    [0:TB_MAX_EVENTS-1];
    integer ev_b    [0:TB_MAX_EVENTS-1];
    integer ev_c    [0:TB_MAX_EVENTS-1];
    integer ev_d    [0:TB_MAX_EVENTS-1];
    integer ev_n = 0;
    integer fd, rc, i;
    reg [8*260-1:0] vec_path;
    real    wait_ns;

    // ---------------- result monitor ----------------
    always @(posedge clk) begin
        #1;
        if (lat_valid) $display("LAT %0d %0d %0.1f", lat_cycles, lat_ticks, $realtime);
        if (age_valid) $display("AGE %0d %0.1f", age_cycles, $realtime);
    end

    initial begin
        if (!$value$plusargs("VECTORS=%s", vec_path)) begin
            $display("TB_ERRORS=1 (missing +VECTORS)"); $finish;
        end
        fd = $fopen(vec_path, "r");
        if (fd == 0) begin
            $display("TB_ERRORS=1 (cannot open vectors)"); $finish;
        end
        begin : read_loop
            while (1) begin
                rc = $fscanf(fd, "%d %f %d %d %d %d\n",
                             ev_kind[ev_n], ev_t[ev_n], ev_a[ev_n], ev_b[ev_n], ev_c[ev_n], ev_d[ev_n]);
                if (rc != 6) disable read_loop;
                if (ev_kind[ev_n] == 0) disable read_loop;
                ev_n = ev_n + 1;
                if (ev_n >= TB_MAX_EVENTS) disable read_loop;
            end
        end
        $fclose(fd);

        rst_n = 1'b0; rst_cap_n = 1'b0;
        repeat (3) @(negedge clk);
        rst_n = 1'b1; rst_cap_n = 1'b1;

        for (i = 0; i < ev_n; i = i + 1) begin
            wait_ns = ev_t[i] - $realtime;
            if (wait_ns > 0.0) #(wait_ns);
            case (ev_kind[i])
                1: begin  // capture, one capture clock cycle
                    @(posedge clk_cap); #1;
                    cap_sid = ev_a[i][7:0]; cap_fid = ev_b[i][15:0]; cap_kind = ev_c[i][1:0];
                    cap_event = 1'b1;
                    // the next capture edge is the instant the design samples the
                    // event, so that edge is the physical event time of record
                    @(posedge clk_cap);
                    $display("EVT CAP %0.1f %0d %0d %0d", $realtime, ev_a[i], ev_b[i], ev_c[i]);
                    #1; cap_event = 1'b0;
                end
                2: begin  // display, one video clock cycle
                    @(posedge clk); #1;
                    dsp_sid = ev_a[i][7:0]; dsp_fid = ev_b[i][15:0]; dsp_event = 1'b1;
                    @(posedge clk);
                    $display("EVT DSP %0.1f %0d %0d", $realtime, ev_a[i], ev_b[i]);
                    #1; dsp_event = 1'b0;
                end
                3: begin  // alarm clear, one cycle
                    @(posedge clk); #1; alarm_clr = 1'b1;
                    @(posedge clk); #1; alarm_clr = 1'b0;
                end
                4: begin  // resync request, one cycle
                    @(posedge clk); #1; resync_req = 1'b1;
                    @(posedge clk); #1; resync_req = 1'b0;
                end
                5: begin  // multi cycle LEVEL, exactly one event expected
                    @(posedge clk_cap); #1;
                    cap_sid = ev_a[i][7:0]; cap_fid = ev_b[i][15:0]; cap_kind = ev_c[i][1:0];
                    cap_event = 1'b1;
                    @(posedge clk_cap);
                    $display("EVT CAP %0.1f %0d %0d %0d LEVEL %0d", $realtime, ev_a[i], ev_b[i], ev_c[i], ev_d[i]);
                    #(ev_d[i]);
                    cap_event = 1'b0;
                end
                default: ;
            endcase
        end

        #200;
        $display("ALARM %0d", alarm);
        $display("STATS %0d %0d %0d", stats_valid, stat_count, stat_sum_cycles);
        $display("CNT %0d %0d %0d %0d", entry_count, unmatched_count, repeat_count, lat_seen);
        // sticky alarm bit2 covers both the dropped-event toggle and the pop spacing
        $display("FLAGS %0d %0d %0d", dut.alarm[2], dut.alarm[2], age_seen);
        $display("LAST %0d %0d", lat_cycles, lat_ticks);
        $display("COUNTS %0d %0d %0d %0d", cap_count, cap_done_count, cap_abort_count, dsp_count);
        $display("FPS %0d %0d %0d", cap_fps, dsp_fps, fps_valid);
        $display("LOST %0d %0d", lost_done_count, lost_abort_count);
        $display("QUEUED %0d", queued_count);
        $display("TB_ERRORS=0");
        $finish;
    end

    initial begin
        #2000000;
        $display("TB_ERRORS=1 (timeout)");
        $finish;
    end

endmodule
