//======================================================================
// latency_meter.v - same frame latency measurement keyed by
//                   {session_id, frame_id}   (protocol TEAM_PROTOCOL_V1)
//
// Protocol mapping (docs/TEAM_AI_WORK_PROTOCOL.md sections 4.1, 4.4 and 2.3)
//   session_id / frame_id : both 32 bit; a reset or a frame-id wrap without a
//                           new session invalidates the old association.
//   cap_event kind 0      : first valid pixel of a frame after MIPI decode.
//   cap_event kind 2      : last valid pixel of the same frame (frame complete).
//   cap_event kind 1      : frame aborted / overwritten upstream.
//   dsp_event             : first valid pixel of a frame actually sent to HDMI;
//                           the identity is the one MAIN latched at readout
//                           time and carried along the pixel path (4.4).
//
// Statistics (2.3 L1/L2)
//   Only the FIRST display of a COMPLETE frame enters the latency statistic.
//   Repeat display -> age_* (image age), never re-enters the statistic.
//   cap_count / cap_done_count / cap_abort_count / dsp_count are frame event
//   counters; cap_fps and dsp_fps are counts inside a one second window, so the
//   HDMI refresh rate (dsp_fps) and the independent captured frame rate
//   (cap_fps) are reported separately as the protocol demands.
//
// Error recovery (review item 3.1)
//   alarm_clr  only clears the sticky alarm bits.
//   resync_req flushes the association table and forces stats_valid = 0; the
//   statistic becomes valid again only after a fresh complete capture that is
//   then displayed for the first time.
//
// Accuracy (review item 3.3)
//   The capture time stamp is taken when the crossed event is popped in the
//   display domain, i.e. CROSS_CYCLES after the physical trigger; the reported
//   value is compensated by +CROSS_CYCLES. The residual error is bounded and
//   SIGNED (+/-1 display clock; exactly 0 when clk_cap == clk). There is no
//   "reading is never smaller than the physical latency" claim; the test report
//   measures the error against independently recorded event times.
//
// Alarm bits (sticky until alarm_clr or reset)
//   [0] display without a matching record, or a frame displayed before done
//   [1] pending record evicted (table full) / done for an unknown frame
//   [2] capture events too close: dropped before or unresolvable after the CDC
//   [3] session switch, frame-id wrap, or abort of an unknown frame
//======================================================================
`timescale 1ns/1ps

module latency_meter #(
    parameter integer SID_W         = 32,
    parameter integer FID_W         = 32,
    parameter integer ENTRY_LOG2    = 3,      // 8 association records
    parameter integer CNT_W         = 32,
    parameter integer TICK_W        = 32,
    parameter integer TICK_BASE     = 742,    // cycles per 10 us tick (integer part)
    parameter integer TICK_REMAINDER= 50000,  // fraction out of TICK_MOD
    parameter integer TICK_MOD      = 100000,
    parameter integer CROSS_CYCLES  = 3,      // CDC + pop latency compensation, cycles
    parameter integer TICK_CROSS    = 0,      // same compensation expressed in ticks
    parameter integer MIN_GAP_SRC   = 2,
    parameter integer MIN_GAP_DST   = 3,
    parameter integer FPS_WINDOW_TICKS = 100000   // 1 s at 0.01 ms per tick
) (
    // ---- capture side (MIPI decode domain) ----
    input  wire              clk_cap,
    input  wire              rst_cap_n,
    input  wire              cap_event,    // level or pulse: rising edge = one event
    input  wire [1:0]        cap_kind,     // 0 start, 1 abort, 2 complete
    input  wire [SID_W-1:0]  cap_sid,
    input  wire [FID_W-1:0]  cap_fid,
    output wire              cap_too_fast,
    // ---- display side (HDMI pixel domain) ----
    input  wire              clk,
    input  wire              rst_n,
    input  wire              dsp_event,    // first valid pixel of a displayed frame
    input  wire [SID_W-1:0]  dsp_sid,
    input  wire [FID_W-1:0]  dsp_fid,
    input  wire              alarm_clr,
    input  wire              resync_req,
    // ---- measurement results ----
    output reg               lat_valid,    // 1 cycle pulse
    output reg  [CNT_W-1:0]  lat_cycles,   // held last first-display latency
    output reg  [TICK_W-1:0] lat_ticks,    // held, 0.01 ms units
    output reg               lat_seen,
    output reg               age_valid,    // 1 cycle pulse on repeat display
    output reg  [CNT_W-1:0]  age_cycles,
    output reg  [TICK_W-1:0] age_ticks,    // image age in 0.01 ms units
    output reg               age_seen,
    output reg               stats_valid,
    output reg  [3:0]        alarm,
    // ---- frame and rate statistics (L1) ----
    output reg  [CNT_W-1:0]  cap_count,        // frame starts
    output reg  [CNT_W-1:0]  cap_done_count,   // complete frames
    output reg  [CNT_W-1:0]  cap_abort_count,  // aborted frames
    output reg  [CNT_W-1:0]  dsp_count,        // display frame events
    output reg  [CNT_W-1:0]  stat_count,       // first displays counted
    output reg  [CNT_W-1:0]  unmatched_count,
    output reg  [CNT_W-1:0]  repeat_count,
    output reg  [63:0]       stat_sum_cycles,
    output reg  [CNT_W-1:0]  cap_fps,          // captures in the last window
    output reg  [CNT_W-1:0]  dsp_fps,          // display events in the last window
    output reg               fps_valid,        // first window completed
    // ---- debug ----
    output wire [CNT_W-1:0]  entry_count,
    output wire              evt_gap_alarm,
    output reg  [CNT_W-1:0]  lost_done_count,
    output reg  [CNT_W-1:0]  lost_abort_count
);
    localparam integer ENT = (1 << ENTRY_LOG2);

    //------------------------------------------------------------------
    // 1. capture event crossing
    //------------------------------------------------------------------
    wire [SID_W+FID_W+1:0] evt_data;
    wire                   evt_valid;
    wire                   pop = evt_valid;
    wire [1:0]             evt_kind = evt_data[SID_W+FID_W+1:SID_W+FID_W];
    wire [SID_W-1:0]       evt_sid  = evt_data[FID_W +: SID_W];
    wire [FID_W-1:0]       evt_fid  = evt_data[FID_W-1:0];

    frame_event_bridge #(
        .SID_W       (SID_W),
        .FID_W       (FID_W),
        .DEPTH_LOG2  (4),
        .MIN_GAP_SRC (MIN_GAP_SRC),
        .MIN_GAP_DST (MIN_GAP_DST)
    ) u_bridge (
        .clk_cap       (clk_cap),
        .rst_cap_n     (rst_cap_n),
        .cap_event     (cap_event),
        .cap_kind      (cap_kind),
        .cap_sid       (cap_sid),
        .cap_fid       (cap_fid),
        .cap_too_fast  (cap_too_fast),
        .clk           (clk),
        .rst_n         (rst_n),
        .evt_ready     (1'b1),
        .evt_data      (evt_data),
        .evt_valid     (evt_valid),
        .evt_gap_alarm (evt_gap_alarm)
    );

    //------------------------------------------------------------------
    // 2. display domain time base: cycles and 0.01 ms ticks
    //------------------------------------------------------------------
    reg [CNT_W-1:0]  cyc_cnt;
    reg [TICK_W-1:0] tick_cnt;
    reg [16:0]       tick_run, tick_interval, tick_acc;

    wire [17:0] acc_sum  = {1'b0, tick_acc} + TICK_REMAINDER[17:0];
    wire        acc_over = (acc_sum >= TICK_MOD[17:0]);
    wire [16:0] acc_keep = acc_over ? (acc_sum[16:0] - TICK_MOD[16:0]) : acc_sum[16:0];
    wire        tick_end = (tick_run >= (tick_interval - 17'd1));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cyc_cnt       <= {CNT_W{1'b0}};
            tick_cnt      <= {TICK_W{1'b0}};
            tick_run      <= 17'd0;
            tick_interval <= TICK_BASE[16:0];
            tick_acc      <= 17'd0;
        end else begin
            cyc_cnt <= cyc_cnt + 1'b1;
            if (tick_end) begin
                tick_run      <= 17'd0;
                tick_cnt      <= tick_cnt + 1'b1;
                tick_acc      <= acc_keep;
                tick_interval <= acc_over ? (TICK_BASE[16:0] + 17'd1) : TICK_BASE[16:0];
            end else begin
                tick_run <= tick_run + 17'd1;
            end
        end
    end

    //------------------------------------------------------------------
    // 3. association records
    //------------------------------------------------------------------
    reg                vld  [0:ENT-1];
    reg                done [0:ENT-1];   // frame completed (kind 2 seen)
    reg                used [0:ENT-1];   // displayed at least once
    reg [SID_W-1:0]    esid [0:ENT-1];
    reg [FID_W-1:0]    efid [0:ENT-1];
    reg [CNT_W-1:0]    ecyc [0:ENT-1];
    reg [TICK_W-1:0]   etick[0:ENT-1];

    reg [SID_W-1:0] cur_sid;
    reg             cur_sid_vld;
    reg [FID_W-1:0] last_fid;
    reg [ENTRY_LOG2-1:0] victim_ptr;

    assign entry_count = vld[0] + vld[1] + vld[2] + vld[3]
                       + vld[4] + vld[5] + vld[6] + vld[7];

    reg dsp_d;
    wire dsp_rise = dsp_event & ~dsp_d;

    // display key lookup
    reg                  hit;
    reg [ENTRY_LOG2-1:0] hit_idx;
    reg                  hit_used;
    reg                  hit_done;
    integer              i;
    always @(*) begin
        hit      = 1'b0;
        hit_idx  = {ENTRY_LOG2{1'b0}};
        hit_used = 1'b0;
        hit_done = 1'b0;
        for (i = 0; i < ENT; i = i + 1) begin
            if (vld[i] && (esid[i] == dsp_sid) && (efid[i] == dsp_fid) && !hit) begin
                hit      = 1'b1;
                hit_idx  = i[ENTRY_LOG2-1:0];
                hit_used = used[i];
                hit_done = done[i];
            end
        end
    end

    // capture key lookup (for kind 2 / kind 1)
    reg                  key_hit;
    reg [ENTRY_LOG2-1:0] key_idx;
    always @(*) begin
        key_hit = 1'b0;
        key_idx = {ENTRY_LOG2{1'b0}};
        for (i = 0; i < ENT; i = i + 1) begin
            if (vld[i] && (esid[i] == evt_sid) && (efid[i] == evt_fid) && !key_hit) begin
                key_hit = 1'b1;
                key_idx = i[ENTRY_LOG2-1:0];
            end
        end
    end

    // insertion slot
    reg                  ins_free;
    reg [ENTRY_LOG2-1:0] ins_idx;
    reg                  ins_overwrite;
    integer              j;
    always @(*) begin
        ins_free      = 1'b0;
        ins_idx       = {ENTRY_LOG2{1'b0}};
        ins_overwrite = 1'b0;
        for (j = 0; j < ENT; j = j + 1) begin
            if (!vld[j] && !ins_free) begin
                ins_free = 1'b1;
                ins_idx  = j[ENTRY_LOG2-1:0];
            end
        end
        if (!ins_free) begin
            for (j = 0; j < ENT; j = j + 1) begin
                if (vld[j] && used[j] && !ins_free) begin
                    ins_free = 1'b1;
                    ins_idx  = j[ENTRY_LOG2-1:0];
                end
            end
        end
        if (!ins_free) begin
            ins_idx       = victim_ptr;
            ins_overwrite = 1'b1;
        end
    end

    //------------------------------------------------------------------
    // 4. events
    //------------------------------------------------------------------
    wire cap_start = pop && (evt_kind == 2'd0);
    wire cap_abort = pop && (evt_kind == 2'd1);
    wire cap_done  = pop && (evt_kind == 2'd2);

    // re-capture of the same key replaces that record instead of adding a new one
    wire [ENTRY_LOG2-1:0] wr_idx = key_hit ? key_idx : ins_idx;

    wire [CNT_W-1:0]  lat_cyc_nxt  = (cyc_cnt  - ecyc[hit_idx])  + CROSS_CYCLES[CNT_W-1:0];
    wire [TICK_W-1:0] lat_tick_nxt = (tick_cnt - etick[hit_idx]) + TICK_CROSS[TICK_W-1:0];
    wire [CNT_W-1:0]  age_cyc_nxt  = (cyc_cnt  - ecyc[hit_idx])  + CROSS_CYCLES[CNT_W-1:0];
    wire [TICK_W-1:0] age_tick_nxt = (tick_cnt - etick[hit_idx]) + TICK_CROSS[TICK_W-1:0];

    wire commit_lat  = dsp_rise & hit & hit_done & ~hit_used;
    wire commit_age  = dsp_rise & hit & hit_used;
    wire bad_display = dsp_rise & hit & ~hit_done & ~hit_used;
    wire miss_dsp    = dsp_rise & ~hit;

    // session / frame id wrap detection on a capture start
    wire sid_change  = cap_start && cur_sid_vld && (evt_sid != cur_sid);
    wire fid_wrap    = cap_start && cur_sid_vld && (evt_sid == cur_sid) && (evt_fid < last_fid);

    // cap_too_fast is a pulse in the capture domain: synchronise it before use
    reg ct_ff1, ct_ff2, ct_ff3;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) {ct_ff1, ct_ff2, ct_ff3} <= 3'b000;
        else        {ct_ff1, ct_ff2, ct_ff3} <= {cap_too_fast, ct_ff1, ct_ff2};
    end
    wire cap_too_fast_evt = ct_ff2 & ~ct_ff3;
    wire event_too_fast    = cap_too_fast_evt | evt_gap_alarm;

    // one second window counters
    reg  [TICK_W-1:0] fps_base;
    reg  [CNT_W-1:0]  cap_win, dsp_win;
    wire              fps_win_end = (tick_cnt - fps_base) >= FPS_WINDOW_TICKS[TICK_W-1:0];

    //------------------------------------------------------------------
    // 5. sequential logic
    //------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dsp_d            <= 1'b0;
            cur_sid          <= {SID_W{1'b0}};
            cur_sid_vld      <= 1'b0;
            last_fid         <= {FID_W{1'b0}};
            victim_ptr       <= {ENTRY_LOG2{1'b0}};
            lat_valid        <= 1'b0;
            lat_cycles       <= {CNT_W{1'b0}};
            lat_ticks        <= {TICK_W{1'b0}};
            lat_seen         <= 1'b0;
            age_valid        <= 1'b0;
            age_cycles       <= {CNT_W{1'b0}};
            age_ticks        <= {TICK_W{1'b0}};
            age_seen         <= 1'b0;
            stats_valid      <= 1'b0;
            alarm            <= 4'b0000;
            cap_count        <= {CNT_W{1'b0}};
            cap_done_count   <= {CNT_W{1'b0}};
            cap_abort_count  <= {CNT_W{1'b0}};
            dsp_count        <= {CNT_W{1'b0}};
            stat_count       <= {CNT_W{1'b0}};
            stat_sum_cycles  <= 64'd0;
            unmatched_count  <= {CNT_W{1'b0}};
            repeat_count     <= {CNT_W{1'b0}};
            lost_done_count  <= {CNT_W{1'b0}};
            lost_abort_count <= {CNT_W{1'b0}};
            cap_fps          <= {CNT_W{1'b0}};
            dsp_fps          <= {CNT_W{1'b0}};
            fps_valid        <= 1'b0;
            fps_base         <= {TICK_W{1'b0}};
            cap_win          <= {CNT_W{1'b0}};
            dsp_win          <= {CNT_W{1'b0}};
            for (i = 0; i < ENT; i = i + 1) begin
                vld[i]  <= 1'b0;
                done[i] <= 1'b0;
                used[i] <= 1'b0;
            end
        end else begin
            dsp_d     <= dsp_event;
            lat_valid <= 1'b0;
            age_valid <= 1'b0;

            if (alarm_clr) alarm <= 4'b0000;

            if (resync_req) begin
                for (i = 0; i < ENT; i = i + 1) begin
                    vld[i] <= 1'b0; done[i] <= 1'b0; used[i] <= 1'b0;
                end
                stats_valid <= 1'b0;
                lat_seen    <= 1'b0;
                age_seen    <= 1'b0;
                cur_sid_vld <= 1'b0;
                victim_ptr  <= {ENTRY_LOG2{1'b0}};
            end else begin
                // ---- session / frame id wrap ----
                if (cap_start && (sid_change || fid_wrap)) begin
                    for (i = 0; i < ENT; i = i + 1) begin
                        vld[i] <= 1'b0; done[i] <= 1'b0; used[i] <= 1'b0;
                    end
                    stats_valid <= 1'b0;
                    alarm[3]    <= 1'b1;
                end else if (dsp_rise && cur_sid_vld && (dsp_sid != cur_sid)) begin
                    for (i = 0; i < ENT; i = i + 1) begin
                        vld[i] <= 1'b0; done[i] <= 1'b0; used[i] <= 1'b0;
                    end
                    stats_valid <= 1'b0;
                    alarm[3]    <= 1'b1;
                end
                if (cap_start) begin
                    cur_sid     <= evt_sid;
                    cur_sid_vld <= 1'b1;
                    last_fid    <= evt_fid;
                end else if (cap_done && key_hit) begin
                    last_fid <= evt_fid;
                end

                // ---- capture start: insert record (replace same key) ----
                if (cap_start) begin
                    vld[wr_idx]   <= 1'b1;
                    done[wr_idx]  <= 1'b0;
                    used[wr_idx]  <= 1'b0;
                    esid[wr_idx]  <= evt_sid;
                    efid[wr_idx]  <= evt_fid;
                    ecyc[wr_idx]  <= cyc_cnt;
                    etick[wr_idx] <= tick_cnt;
                    victim_ptr    <= wr_idx + 1'b1;
                    if (ins_overwrite || key_hit) begin
                        alarm[1]    <= 1'b1;
                        stats_valid <= 1'b0;
                    end
                end else if (cap_abort) begin
                    if (key_hit) begin
                        vld[key_idx]  <= 1'b0;
                        done[key_idx] <= 1'b0;
                        used[key_idx] <= 1'b0;
                    end else begin
                        alarm[3] <= 1'b1;
                        lost_abort_count <= lost_abort_count + 1'b1;
                    end
                end else if (cap_done) begin
                    if (key_hit) begin
                        done[key_idx] <= 1'b1;
                    end else begin
                        alarm[1] <= 1'b1;
                        lost_done_count <= lost_done_count + 1'b1;
                    end
                end

                // ---- display event ----
                if (commit_lat) begin
                    lat_valid      <= 1'b1;
                    lat_cycles     <= lat_cyc_nxt;
                    lat_ticks      <= lat_tick_nxt;
                    lat_seen       <= 1'b1;
                    used[hit_idx]  <= 1'b1;
                    stat_sum_cycles<= stat_sum_cycles + lat_cyc_nxt;
                    stat_count     <= stat_count + 1'b1;
                    stats_valid    <= 1'b1;
                end else if (commit_age) begin
                    age_valid    <= 1'b1;
                    age_cycles   <= age_cyc_nxt;
                    age_ticks    <= age_tick_nxt;
                    age_seen     <= 1'b1;
                    repeat_count <= repeat_count + 1'b1;
                end else if (bad_display) begin
                    unmatched_count <= unmatched_count + 1'b1;
                    alarm[0]        <= 1'b1;
                    stats_valid     <= 1'b0;
                end else if (miss_dsp) begin
                    unmatched_count <= unmatched_count + 1'b1;
                    alarm[0]        <= 1'b1;
                    stats_valid     <= 1'b0;
                end

                // ---- counters ----
                if (cap_start)   cap_count  <= cap_count + 1'b1;
                if (cap_done)    cap_done_count <= cap_done_count + 1'b1;
                if (cap_abort)   cap_abort_count <= cap_abort_count + 1'b1;
                if (dsp_rise)    dsp_count  <= dsp_count + 1'b1;

                // ---- one second window (counts, no divider) ----
                if (fps_win_end) begin
                    cap_fps   <= cap_win + (cap_start ? 1'b1 : 1'b0);
                    dsp_fps   <= dsp_win + (dsp_rise  ? 1'b1 : 1'b0);
                    fps_valid <= 1'b1;
                    cap_win   <= {CNT_W{1'b0}};
                    dsp_win   <= {CNT_W{1'b0}};
                    fps_base  <= tick_cnt;
                end else begin
                    if (cap_start) cap_win <= cap_win + 1'b1;
                    if (dsp_rise)  dsp_win <= dsp_win + 1'b1;
                end

                if (event_too_fast) alarm[2] <= 1'b1;
            end
        end
    end

endmodule
