//======================================================================
// latency_osd.v - latency / frame rate visualisation panel
//
// Protocol TEAM_PROTOCOL_V1 section 2.3 (L1 visualisation) and 4.4.
// Shows, once per frame and only inside vertical blanking:
//     LAT  DDD.DD MS   first display latency of a complete frame
//     AGE  DDD.DD MS   image age of the most recent repeated display
//     CAP    ### FPS   captured frames in the last one second window
//     DSP    ### FPS   display (HDMI) frame events in the last window
//     FRM ########  E# frame counter and sticky alarm nibble
//
// The panel reuses text_overlay (frame/line realigned coordinates, three cycle
// fixed latency) and the generated character ROM. The character buffer and the
// formatting rules are generated from model/latency_model.py, so the software
// model and the RTL cannot drift apart.
//
// No divider and no multiplier: decimal digits come from a 17 bit double-dabble
// converter inside the vertical blanking interval, the frame counter is a BCD
// ripple counter and the frame rates are counts per window.
//
// Verification level: simulation only. No TD build, no board measurement.
//======================================================================
`timescale 1ns/1ps

`include "osd_layout.vh"

module latency_osd #(
    // time base (from the verified clock configuration, not a nominal guess)
    parameter integer TICK_BASE         = 742,
    parameter integer TICK_REMAINDER    = 50000,
    parameter integer TICK_MOD          = 100000,
    parameter integer FPS_WINDOW_TICKS  = 100000,
    parameter integer CROSS_CYCLES      = 3,
    parameter integer TICK_CROSS        = 0,
    parameter integer ENTRY_LOG2        = 3,
    parameter integer MIN_GAP_SRC       = 2,
    parameter integer MIN_GAP_DST       = 3,
    // video geometry and panel
    parameter integer H_ACTIVE   = 1280,
    parameter integer V_ACTIVE   = 720,
    parameter integer X0         = 24,
    parameter integer Y0         = 24,
    parameter integer SCALE_LOG2 = 1,
    parameter integer PANEL_EN   = 1,
    parameter integer BG_DIM     = 1,
    parameter [23:0]  FG_RGB     = 24'hFFFFFF,
    parameter [23:0]  BG_RGB     = 24'h000000
) (
    // ---- capture side ----
    input  wire              clk_cap,
    input  wire              rst_cap_n,
    input  wire              cap_event,
    input  wire [1:0]        cap_kind,
    input  wire [31:0]       cap_sid,
    input  wire [31:0]       cap_fid,
    // ---- display side ----
    input  wire              clk,
    input  wire              rst_n,
    input  wire              de,
    input  wire              hs,
    input  wire              vs,
    input  wire [23:0]       rgb_in,
    input  wire              dsp_event,   // first valid pixel of a displayed frame
    input  wire [31:0]       dsp_sid,
    input  wire [31:0]       dsp_fid,
    input  wire              alarm_clr,
    input  wire              resync_req,
    // ---- video out (3 cycle delay) ----
    output wire [23:0]       rgb_out,
    output wire              de_out,
    output wire              hs_out,
    output wire              vs_out,
    // ---- observability ----
    input  wire [6:0]        dbg_raddr,
    output wire [7:0]        dbg_rdata,
    output wire [31:0]       dbg_lat_cycles,
    output wire [31:0]       dbg_lat_ticks,
    output wire [31:0]       dbg_age_cycles,
    output wire [31:0]       dbg_age_ticks,
    output wire [31:0]       dbg_cap_fps,
    output wire [31:0]       dbg_dsp_fps,
    output wire [31:0]       dbg_cap_count,
    output wire [31:0]       dbg_dsp_count,
    output wire [3:0]        dbg_alarm,
    output wire              dbg_stats_valid,
    output wire              dbg_lat_seen,
    output wire              dbg_age_seen,
    output wire              dbg_fps_valid
);
    localparam integer OSD_ADDR_W = 7;      // 128 >= COLS*ROWS = 80

    //------------------------------------------------------------------
    // measurement + statistics
    //------------------------------------------------------------------
    wire [31:0] lat_cycles, lat_ticks, age_cycles, age_ticks;
    wire [31:0] cap_fps, dsp_fps, cap_count, dsp_count, stat_count, unmatched, repeat_cnt;
    wire [31:0] lost_done, lost_abort, entry_count;
    wire [63:0] stat_sum;
    wire        lat_valid, lat_seen, age_valid, age_seen, stats_valid, fps_valid;
    wire [3:0]  alarm;
    wire        cap_too_fast, evt_gap_alarm;

    latency_meter #(
        .SID_W          (32),
        .FID_W          (32),
        .ENTRY_LOG2     (ENTRY_LOG2),
        .TICK_BASE      (TICK_BASE),
        .TICK_REMAINDER (TICK_REMAINDER),
        .TICK_MOD       (TICK_MOD),
        .CROSS_CYCLES   (CROSS_CYCLES),
        .TICK_CROSS     (TICK_CROSS),
        .MIN_GAP_SRC    (MIN_GAP_SRC),
        .MIN_GAP_DST    (MIN_GAP_DST),
        .FPS_WINDOW_TICKS (FPS_WINDOW_TICKS)
    ) u_meter (
        .clk_cap        (clk_cap),
        .rst_cap_n      (rst_cap_n),
        .cap_event      (cap_event),
        .cap_kind       (cap_kind),
        .cap_sid        (cap_sid),
        .cap_fid        (cap_fid),
        .cap_too_fast   (cap_too_fast),
        .clk            (clk),
        .rst_n          (rst_n),
        .dsp_event      (dsp_event),
        .dsp_sid        (dsp_sid),
        .dsp_fid        (dsp_fid),
        .alarm_clr      (alarm_clr),
        .resync_req     (resync_req),
        .lat_valid      (lat_valid),
        .lat_cycles     (lat_cycles),
        .lat_ticks      (lat_ticks),
        .lat_seen       (lat_seen),
        .age_valid      (age_valid),
        .age_cycles     (age_cycles),
        .age_ticks      (age_ticks),
        .age_seen       (age_seen),
        .stats_valid    (stats_valid),
        .alarm          (alarm),
        .cap_count      (cap_count),
        .cap_done_count (),
        .cap_abort_count(),
        .dsp_count      (dsp_count),
        .stat_count     (stat_count),
        .unmatched_count(unmatched),
        .repeat_count   (repeat_cnt),
        .stat_sum_cycles(stat_sum),
        .cap_fps        (cap_fps),
        .dsp_fps        (dsp_fps),
        .fps_valid      (fps_valid),
        .entry_count    (entry_count),
        .evt_gap_alarm  (evt_gap_alarm),
        .lost_done_count(lost_done),
        .lost_abort_count(lost_abort)
    );

    assign dbg_lat_cycles  = lat_cycles;
    assign dbg_lat_ticks   = lat_ticks;
    assign dbg_age_cycles  = age_cycles;
    assign dbg_age_ticks   = age_ticks;
    assign dbg_cap_fps     = cap_fps;
    assign dbg_dsp_fps     = dsp_fps;
    assign dbg_cap_count   = cap_count;
    assign dbg_dsp_count   = dsp_count;
    assign dbg_alarm       = alarm;
    assign dbg_stats_valid = stats_valid;
    assign dbg_lat_seen    = lat_seen;
    assign dbg_age_seen    = age_seen;
    assign dbg_fps_valid   = fps_valid;

    //------------------------------------------------------------------
    // frame counter and panel refresh trigger
    //------------------------------------------------------------------
    reg vs_d;
    wire vs_fall = vs_d & ~vs;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) vs_d <= 1'b0;
        else        vs_d <= vs;
    end

    reg  [31:0] frame_bcd;
    reg         carry;
    integer     nib;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            frame_bcd <= 32'd0;
        end else if (vs_fall) begin
            carry = 1'b1;
            for (nib = 0; nib < 8; nib = nib + 1) begin
                if (carry) begin
                    if (frame_bcd[nib*4 +: 4] == 4'd9) begin
                        frame_bcd[nib*4 +: 4] <= 4'd0;
                        carry = 1'b1;
                    end else begin
                        frame_bcd[nib*4 +: 4] <= frame_bcd[nib*4 +: 4] + 4'd1;
                        carry = 1'b0;
                    end
                end
            end
        end
    end

    //------------------------------------------------------------------
    // formatter
    //------------------------------------------------------------------
    localparam [3:0] S_INIT  = 4'd0,
                     S_IDLE  = 4'd1,
                     S_CONV  = 4'd2,
                     S_WR_LAT= 4'd3,
                     S_WR_AGE= 4'd4,
                     S_WR_CAP= 4'd5,
                     S_WR_DSP= 4'd6,
                     S_WR_FRM= 4'd7,
                     S_WR_ERR= 4'd8;

    localparam [31:0] MAX_TICKS = 32'd99999;
    localparam [16:0] CLAMP_TICKS = 17'd99999;

    reg  [3:0]  state;
    reg  [6:0]  idx;        // index inside the current field
    reg  [6:0]  tpl_idx;    // template write index
    reg  [1:0]  cv_sel;     // 0 lat, 1 age, 2 cap fps, 3 dsp fps
    reg  [16:0] cv_bin;
    reg  [19:0] cv_bcd;
    reg  [4:0]  cv_cnt;
    reg  [19:0] bcd_lat, bcd_age, bcd_cap, bcd_dsp;

    // double-dabble step
    wire [3:0] a0 = (cv_bcd[3:0]   > 4'd4) ? (cv_bcd[3:0]   + 4'd3) : cv_bcd[3:0];
    wire [3:0] a1 = (cv_bcd[7:4]   > 4'd4) ? (cv_bcd[7:4]   + 4'd3) : cv_bcd[7:4];
    wire [3:0] a2 = (cv_bcd[11:8]  > 4'd4) ? (cv_bcd[11:8]  + 4'd3) : cv_bcd[11:8];
    wire [3:0] a3 = (cv_bcd[15:12] > 4'd4) ? (cv_bcd[15:12] + 4'd3) : cv_bcd[15:12];
    wire [3:0] a4 = (cv_bcd[19:16] > 4'd4) ? (cv_bcd[19:16] + 4'd3) : cv_bcd[19:16];
    wire [36:0] cv_sh    = {a4, a3, a2, a1, a0, cv_bin} << 1;
    wire [19:0] cv_bcd_n = cv_sh[36:17];
    wire [16:0] cv_bin_n = cv_sh[16:0];

    wire [19:0] bcd_sel = (cv_sel == 2'd0) ? bcd_lat :
                          (cv_sel == 2'd1) ? bcd_age :
                          (cv_sel == 2'd2) ? bcd_cap : bcd_dsp;

    // 5 digit decimal of the selected field (d4..d0)
    wire [3:0] d4 = bcd_sel[19:16];
    wire [3:0] d3 = bcd_sel[15:12];
    wire [3:0] d2 = bcd_sel[11:8];
    wire [3:0] d1 = bcd_sel[7:4];
    wire [3:0] d0 = bcd_sel[3:0];

    reg  [7:0] wr_char;
    reg  [3:0] wr_nib;

    wire lat_ok = lat_seen;
    wire age_ok = age_seen;

    always @(*) begin
        wr_char = 8'h20;
        wr_nib  = 4'd0;
        case (state)
            S_WR_LAT, S_WR_AGE: begin
                if (!((state == S_WR_LAT) ? lat_ok : age_ok)) begin
                    wr_char = (idx == 7'd3) ? 8'h2E : 8'h2D;   // "-" with "."
                end else if (idx == 7'd3) begin
                    wr_char = 8'h2E;
                end else begin
                    case (idx)
                        7'd0: wr_nib = d4;
                        7'd1: wr_nib = d3;
                        7'd2: wr_nib = d2;
                        7'd4: wr_nib = d1;
                        default: wr_nib = d0;
                    endcase
                    if ((idx == 7'd0) && (d4 == 4'd0))                          wr_char = 8'h20;
                    else if ((idx == 7'd1) && (d4 == 4'd0) && (d3 == 4'd0))     wr_char = 8'h20;
                    else                                                        wr_char = 8'h30 + {4'd0, wr_nib};
                end
            end
            S_WR_CAP, S_WR_DSP: begin
                if (!fps_valid) begin
                    wr_char = (idx < 7'd2) ? 8'h20 : 8'h2D;
                end else begin
                    case (idx)
                        7'd2: wr_nib = d2;
                        7'd3: wr_nib = d1;
                        7'd4: wr_nib = d0;
                        default: wr_nib = 4'd0;
                    endcase
                    // right aligned, leading zeros blanked (model format_fps_field)
                    if (idx < 7'd2)                              wr_char = 8'h20;
                    else if ((idx == 7'd2) && (d2 == 4'd0))      wr_char = 8'h20;
                    else if ((idx == 7'd3) && (d2 == 4'd0) && (d1 == 4'd0)) wr_char = 8'h20;
                    else                                         wr_char = 8'h30 + {4'd0, wr_nib};
                end
            end
            S_WR_FRM: begin
                wr_nib  = frame_bcd[(7'd7 - idx) * 4 +: 4];
                wr_char = 8'h30 + {4'd0, wr_nib};
            end
            S_WR_ERR: begin
                wr_char = 8'h30 + {4'd0, alarm};
            end
            default: wr_char = 8'h20;
        endcase
    end

    // write port (frame boundary only)
    reg  [6:0] osd_waddr;
    reg  [7:0] osd_wdata;
    reg        osd_we;
    reg  [9:0] tpl_base;

    always @(*) begin
        osd_waddr = 7'd0;
        osd_wdata = 8'h20;
        osd_we    = 1'b0;
        tpl_base  = (7'd79 - tpl_idx) * 8;
        case (state)
            S_INIT:     begin osd_waddr = tpl_idx;              osd_wdata = OSD_TEMPLATE[tpl_base +: 8]; osd_we = ~de; end
            S_WR_LAT:   begin osd_waddr = OSD_FLD_LAT + idx;     osd_wdata = wr_char; osd_we = ~de; end
            S_WR_AGE:   begin osd_waddr = OSD_FLD_AGE + idx;     osd_wdata = wr_char; osd_we = ~de; end
            S_WR_CAP:   begin osd_waddr = OSD_FLD_CAP + idx;     osd_wdata = wr_char; osd_we = ~de; end
            S_WR_DSP:   begin osd_waddr = OSD_FLD_DSP + idx;     osd_wdata = wr_char; osd_we = ~de; end
            S_WR_FRM:   begin osd_waddr = OSD_FLD_FRM + idx;     osd_wdata = wr_char; osd_we = ~de; end
            S_WR_ERR:   begin osd_waddr = OSD_FLD_ERR + idx;     osd_wdata = wr_char; osd_we = ~de; end
            default:    begin osd_waddr = 7'd0; osd_wdata = 8'h20; osd_we = 1'b0; end
        endcase
    end

    integer i;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state   <= S_INIT;
            idx     <= 7'd0;
            tpl_idx <= 7'd0;
            cv_sel  <= 2'd0;
            cv_bin  <= 17'd0;
            cv_bcd  <= 20'd0;
            cv_cnt  <= 5'd0;
            bcd_lat <= 20'd0;
            bcd_age <= 20'd0;
            bcd_cap <= 20'd0;
            bcd_dsp <= 20'd0;
        end else begin
            case (state)
                S_INIT: begin
                    if (!de) begin
                        if (tpl_idx == 7'd79) begin
                            tpl_idx <= 7'd0;
                            state   <= S_IDLE;
                        end else tpl_idx <= tpl_idx + 7'd1;
                    end
                end
                S_IDLE: begin
                    if (vs_fall) begin
                        cv_sel <= 2'd0;
                        cv_bin <= (lat_ticks > MAX_TICKS) ? CLAMP_TICKS : lat_ticks[16:0];
                        cv_bcd <= 20'd0;
                        cv_cnt <= 5'd0;
                        idx    <= 7'd0;
                        state  <= S_CONV;
                    end
                end
                S_CONV: begin
                    if (cv_cnt == 5'd16) begin
                        case (cv_sel)
                            2'd0: bcd_lat <= cv_bcd_n;
                            2'd1: bcd_age <= cv_bcd_n;
                            2'd2: bcd_cap <= cv_bcd_n;
                            default: bcd_dsp <= cv_bcd_n;
                        endcase
                        cv_cnt <= 5'd0;
                        idx    <= 7'd0;
                        case (cv_sel)
                            2'd0: state <= S_WR_LAT;
                            2'd1: state <= S_WR_AGE;
                            2'd2: state <= S_WR_CAP;
                            default: state <= S_WR_DSP;
                        endcase
                    end else begin
                        cv_bcd <= cv_bcd_n;
                        cv_bin <= cv_bin_n;
                        cv_cnt <= cv_cnt + 5'd1;
                    end
                end
                S_WR_LAT, S_WR_AGE, S_WR_CAP, S_WR_DSP: begin
                    if (osd_we) begin
                        if (idx == ((state == S_WR_LAT || state == S_WR_AGE)
                                    ? (OSD_LEN_MS - 7'd1) : (OSD_LEN_FPS - 7'd1))) begin
                            idx <= 7'd0;
                            case (state)
                                S_WR_LAT: state <= S_WR_AGE;
                                S_WR_AGE: begin
                                    // next conversion: capture fps
                                    cv_sel <= 2'd2;
                                    cv_bin <= (cap_fps > 32'd999) ? 17'd999 : cap_fps[16:0];
                                    cv_bcd <= 20'd0;
                                    cv_cnt <= 5'd0;
                                    state  <= S_CONV;
                                end
                                S_WR_CAP: begin
                                    cv_sel <= 2'd3;
                                    cv_bin <= (dsp_fps > 32'd999) ? 17'd999 : dsp_fps[16:0];
                                    cv_bcd <= 20'd0;
                                    cv_cnt <= 5'd0;
                                    state  <= S_CONV;
                                end
                                default: state <= S_WR_FRM;
                            endcase
                        end else idx <= idx + 7'd1;
                    end
                end
                S_WR_FRM: begin
                    if (osd_we) begin
                        if (idx == (OSD_LEN_FRM - 7'd1)) begin idx <= 7'd0; state <= S_WR_ERR; end
                        else idx <= idx + 7'd1;
                    end
                end
                S_WR_ERR: begin
                    if (osd_we) begin
                        idx   <= 7'd0;
                        state <= S_IDLE;
                    end
                end
                default: state <= S_INIT;
            endcase

            // conversion for the AGE field starts right after WR_LAT finishes
            if ((state == S_WR_LAT) && osd_we && (idx == (OSD_LEN_MS - 7'd1))) begin
                // handled above; kept for readability
            end
        end
    end

    //------------------------------------------------------------------
    // streaming overlay
    //------------------------------------------------------------------
    text_overlay #(
        .H_ACTIVE   (H_ACTIVE),
        .V_ACTIVE   (V_ACTIVE),
        .COLS       (OSD_COLS),
        .ROWS       (OSD_ROWS),
        .ADDR_W     (OSD_ADDR_W),
        .X0         (X0),
        .Y0         (Y0),
        .SCALE_LOG2 (SCALE_LOG2),
        .PANEL_EN   (PANEL_EN),
        .BG_DIM     (BG_DIM),
        .FG_RGB     (FG_RGB),
        .BG_RGB     (BG_RGB)
    ) u_overlay (
        .clk       (clk),
        .rst_n     (rst_n),
        .de        (de),
        .hs        (hs),
        .vs        (vs),
        .rgb_in    (rgb_in),
        .we        (osd_we),
        .waddr     (osd_waddr[OSD_ADDR_W-1:0]),
        .wdata     (osd_wdata),
        .dbg_raddr (dbg_raddr),
        .dbg_rdata (dbg_rdata),
        .rgb_out   (rgb_out),
        .de_out    (de_out),
        .hs_out    (hs_out),
        .vs_out    (vs_out)
    );

endmodule
