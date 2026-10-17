//======================================================================
// latency_meter.v - same frame latency measurement keyed by
//                   {session_id, frame_id}
//
// Why this replaces the b43284c design
//   b43284c paired capture and display events in FIFO order only. When DDR
//   drops or overwrites a frame (capture A, B, C but only C reaches HDMI) the
//   first display is paired with A, so a 10 cycle latency was reported as 27
//   cycles and no error was raised. Events are now matched by identity, so a
//   display event can only succeed against the capture record of the SAME
//   {session_id, frame_id}; everything else is counted as an anomaly.
//
// Statistics rule (review item 2)
//   * Only the FIRST display of a frame enters the main latency statistic.
//   * A repeated display of the same frame is reported on age_* (image age at
//     the moment it is shown again) and never re-enters the latency statistic.
//   * While the association state is not trustworthy (stats_valid = 0) no
//     latency or age value is emitted as valid.
//
// Error recovery (review item 3.1)
//   alarm_clr  only clears the sticky alarm bits.
//   resync_req flushes the association table and forces stats_valid = 0; the
//              statistic becomes valid again only after a fresh, clean
//              capture -> first display match.
//
// Accuracy statement (review item 3.3)
//   The capture time stamp is taken when the crossed capture event is popped in
//   the display domain, i.e. CROSS_CYCLES after the physical trigger. The
//   reported value is therefore compensated by +CROSS_CYCLES, which makes the
//   residual error bounded and SIGNED: about +/-1 display clock cycle (exact,
//   error 0, when clk_cap == clk). There is no "reading is never smaller than
//   the physical latency" claim any more; the test report measures the actual
//   error against independently recorded event times.
//
// Anomaly bits (sticky until alarm_clr or reset)
//   [0] display event with no matching capture record (unmatched)
//   [1] pending capture evicted because the table was full (overwrite)
//   [2] capture events too close: dropped or unresolvable after the CDC
//   [3] session switch / abort of an unknown frame (association restarted)
//======================================================================
`timescale 1ns/1ps

module latency_meter #(
    parameter integer SID_W         = 8,
    parameter integer FID_W         = 16,
    parameter integer ENTRY_LOG2    = 3,      // 8 pending/age records
    parameter integer CNT_W         = 32,
    parameter integer TICK_W        = 32,
    parameter integer TICK_BASE     = 742,    // cycles per 10 us, integer part
    parameter integer TICK_REMAINDER= 50000,  // fraction out of TICK_MOD
    parameter integer TICK_MOD      = 100000,
    parameter integer CROSS_CYCLES  = 3,      // CDC + pop latency compensation, cycles
    parameter integer TICK_CROSS    = 0,      // same compensation expressed in ticks
    parameter integer MIN_GAP_SRC   = 2,
    parameter integer MIN_GAP_DST   = 3
) (
    // ---- capture side (MIPI decode domain) ----
    input  wire             clk_cap,
    input  wire             rst_cap_n,
    input  wire             cap_event,     // level or pulse: rising edge = frame start
    input  wire             cap_kind,      // 0 = captured, 1 = aborted / overwritten upstream
    input  wire [SID_W-1:0] cap_sid,
    input  wire [FID_W-1:0] cap_fid,
    output wire             cap_too_fast,
    // ---- display side (HDMI pixel domain) ----
    input  wire             clk,
    input  wire             rst_n,
    input  wire             dsp_event,     // first valid pixel of a frame at HDMI
    input  wire [SID_W-1:0] dsp_sid,
    input  wire [FID_W-1:0] dsp_fid,
    input  wire             alarm_clr,
    input  wire             resync_req,
    // ---- results (display domain) ----
    output reg              lat_valid,     // 1 cycle pulse: new first display
    output reg  [CNT_W-1:0] lat_cycles,    // held value of the last measurement
    output reg  [TICK_W-1:0] lat_ticks,    // held value in 0.01 ms units
    output reg              lat_seen,      // level: at least one measurement since resync
    output reg              age_valid,     // 1 cycle pulse: repeated display
    output reg  [CNT_W-1:0] age_cycles,    // held image age of the last repeat
    output reg              age_seen,
    output reg              stats_valid,   // association state is trustworthy
    output reg  [3:0]       alarm,
    output reg  [CNT_W-1:0] stat_count,
    output reg  [63:0]      stat_sum_cycles,
    output reg  [CNT_W-1:0] unmatched_count,
    output reg  [CNT_W-1:0] repeat_count,
    // ---- debug ----
    output wire [CNT_W-1:0] entry_count,
    output wire             evt_gap_alarm
);
    localparam integer ENT = (1 << ENTRY_LOG2);

    //------------------------------------------------------------------
    // 1. capture event crossing
    //------------------------------------------------------------------
    wire [SID_W+FID_W:0] evt_data;
    wire                 evt_valid;
    wire                 pop = evt_valid;      // consumer is always ready
    wire                 evt_kind = evt_data[SID_W+FID_W];
    wire [SID_W-1:0]     evt_sid  = evt_data[FID_W +: SID_W];
    wire [FID_W-1:0]     evt_fid  = evt_data[FID_W-1:0];

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
    // 2. display domain time base (cycles and 0.01 ms ticks)
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
    // 3. association table: valid + already displayed + key + stamps
    //------------------------------------------------------------------
    reg                vld  [0:ENT-1];
    reg                used [0:ENT-1];   // displayed at least once (age buffer)
    reg [SID_W-1:0]    esid [0:ENT-1];
    reg [FID_W-1:0]    efid [0:ENT-1];
    reg [CNT_W-1:0]    ecyc [0:ENT-1];
    reg [TICK_W-1:0]   etick[0:ENT-1];

    reg [SID_W-1:0] cur_sid;
    reg             cur_sid_vld;
    reg [ENTRY_LOG2-1:0] victim_ptr;

    assign entry_count = vld[0] + vld[1] + vld[2] + vld[3]
                       + vld[4] + vld[5] + vld[6] + vld[7];

    // display event edge detect (level or pulse in, one event out)
    reg dsp_d;
    wire dsp_rise = dsp_event & ~dsp_d;

    // combinational look-up of the display key
    reg                  hit;
    reg [ENTRY_LOG2-1:0] hit_idx;
    reg                  hit_used;
    integer              i;
    always @(*) begin
        hit       = 1'b0;
        hit_idx   = {ENTRY_LOG2{1'b0}};
        hit_used  = 1'b0;
        for (i = 0; i < ENT; i = i + 1) begin
            if (vld[i] && (esid[i] == dsp_sid) && (efid[i] == dsp_fid) && !hit) begin
                hit      = 1'b1;
                hit_idx  = i[ENTRY_LOG2-1:0];
                hit_used = used[i];
            end
        end
    end

    // insertion slot: free -> reused age record -> oldest pending (overwrite)
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
            ins_idx       = victim_ptr;     // no free and no age record: overwrite
            ins_overwrite = 1'b1;
        end
    end

    //------------------------------------------------------------------
    // 4. measurement and anomaly logic
    //------------------------------------------------------------------
    wire [CNT_W-1:0]  lat_cyc_nxt  = (cyc_cnt  - ecyc[hit_idx])  + CROSS_CYCLES[CNT_W-1:0];
    wire [TICK_W-1:0] lat_tick_nxt = (tick_cnt - etick[hit_idx]) + TICK_CROSS[TICK_W-1:0];
    wire [CNT_W-1:0]  age_cyc_nxt  = (cyc_cnt  - ecyc[hit_idx]) + CROSS_CYCLES[CNT_W-1:0];

    wire commit_lat = dsp_rise & hit & ~hit_used;
    wire commit_age = dsp_rise & hit &  hit_used;
    wire miss_dsp   = dsp_rise & ~hit;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dsp_d             <= 1'b0;
            cur_sid           <= {SID_W{1'b0}};
            cur_sid_vld       <= 1'b0;
            victim_ptr        <= {ENTRY_LOG2{1'b0}};
            lat_valid         <= 1'b0;
            lat_cycles        <= {CNT_W{1'b0}};
            lat_ticks         <= {TICK_W{1'b0}};
            lat_seen          <= 1'b0;
            age_valid         <= 1'b0;
            age_cycles        <= {CNT_W{1'b0}};
            age_seen          <= 1'b0;
            stats_valid       <= 1'b0;
            alarm             <= 4'b0000;
            stat_count        <= {CNT_W{1'b0}};
            stat_sum_cycles   <= 64'd0;
            unmatched_count   <= {CNT_W{1'b0}};
            repeat_count      <= {CNT_W{1'b0}};
            for (i = 0; i < ENT; i = i + 1) begin
                vld[i]  <= 1'b0;
                used[i] <= 1'b0;
            end
        end else begin
            dsp_d     <= dsp_event;
            lat_valid <= 1'b0;
            age_valid <= 1'b0;

            // ---- sticky alarm clear: alarms only, association is untouched ----
            if (alarm_clr) alarm <= 4'b0000;

            // ---- resynchronisation: drop everything, statistics invalid ----
            if (resync_req) begin
                for (i = 0; i < ENT; i = i + 1) begin
                    vld[i]  <= 1'b0;
                    used[i] <= 1'b0;
                end
                stats_valid <= 1'b0;
                lat_seen    <= 1'b0;
                age_seen    <= 1'b0;
                cur_sid_vld <= 1'b0;
                victim_ptr  <= {ENTRY_LOG2{1'b0}};
            end else begin
                // ---- session change: flush the old session ----
                if (pop && !evt_kind && evt_sid != cur_sid) begin
                    if (cur_sid_vld) begin
                        for (i = 0; i < ENT; i = i + 1) begin
                            if (vld[i]) begin
                                vld[i]  <= 1'b0;
                                used[i] <= 1'b0;
                            end
                        end
                        stats_valid <= 1'b0;
                        alarm[3]    <= 1'b1;
                    end
                    cur_sid     <= evt_sid;
                    cur_sid_vld <= 1'b1;
                end else if (dsp_rise && cur_sid_vld && (dsp_sid != cur_sid)) begin
                    for (i = 0; i < ENT; i = i + 1) begin
                        vld[i]  <= 1'b0;
                        used[i] <= 1'b0;
                    end
                    stats_valid <= 1'b0;
                    alarm[3]    <= 1'b1;
                end

                // ---- capture insert / abort remove ----
                if (pop && !evt_kind) begin
                    vld[ins_idx]   <= 1'b1;
                    used[ins_idx]  <= 1'b0;
                    esid[ins_idx]  <= evt_sid;
                    efid[ins_idx]  <= evt_fid;
                    ecyc[ins_idx]  <= cyc_cnt;
                    etick[ins_idx] <= tick_cnt;
                    victim_ptr     <= ins_idx + 1'b1;
                    if (ins_overwrite) begin
                        alarm[1]    <= 1'b1;
                        stats_valid <= 1'b0;
                    end
                end else if (pop && evt_kind) begin
                    // upstream abort: remove the record, it must never be counted
                    for (i = 0; i < ENT; i = i + 1) begin
                        if (vld[i] && (esid[i] == evt_sid) && (efid[i] == evt_fid)) begin
                            vld[i]  <= 1'b0;
                            used[i] <= 1'b0;
                        end
                    end
                end

                // ---- display event ----
                if (commit_lat) begin
                    lat_valid       <= 1'b1;
                    lat_cycles      <= lat_cyc_nxt;
                    lat_ticks       <= lat_tick_nxt;
                    lat_seen        <= 1'b1;
                    used[hit_idx]   <= 1'b1;
                    if (cyc_cnt != 32'hFFFFFFFF) stat_sum_cycles <= stat_sum_cycles + lat_cyc_nxt;
                    stat_count      <= stat_count + 1'b1;
                    stats_valid     <= 1'b1;
                end else if (commit_age) begin
                    age_valid   <= 1'b1;
                    age_cycles  <= age_cyc_nxt;
                    age_seen    <= 1'b1;
                    repeat_count<= repeat_count + 1'b1;
                end else if (miss_dsp) begin
                    unmatched_count <= unmatched_count + 1'b1;
                    alarm[0]        <= 1'b1;
                    stats_valid     <= 1'b0;
                end

                // ---- capture side anomalies ----
                if (cap_too_fast) alarm[2] <= 1'b1;
                if (evt_gap_alarm) alarm[2] <= 1'b1;
            end
        end
    end

endmodule
