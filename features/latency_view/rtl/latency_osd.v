//======================================================================
// latency_osd.v - latency / frame rate visualisation panel
//
// Protocol TEAM_PROTOCOL_V1 section 2.3 (L1 visualisation) and 4.4.
// Eight rows, refreshed once per frame inside vertical blanking from an atomic
// snapshot taken on the vs falling edge:
//     LAT  DDD.DD MS   first display latency of a complete frame
//     AVG  DDD.DD MS   average of all first displays since resync
//     AGE  DDD.DD MS   image age of the most recent repeated display
//     CAP    ### FPS   captured frames in the last fps window
//     DSP    ### FPS   display (HDMI) frame events in the last window
//     FRM ######## E#  frame counter and sticky alarm nibble
//     CNT ########     first displays counted since resync
//     ALM # UNMATCH    alarm nibble and decoded alarm word
//
// No divider operator and no multiplier: the average uses a 64 step serial
// restoring divider during vertical blanking, decimal digits come from a 17 bit
// double-dabble converter, counters are BCD ripple counters and the frame rates
// are counts per window.
//
// Verification level: simulation only. No TD build, no board measurement.
//======================================================================
`timescale 1ns/1ps

`include "osd_layout.vh"

module latency_osd #(
    parameter integer TICK_BASE         = 742,
    parameter integer TICK_REMAINDER    = 50000,
    parameter integer TICK_MOD          = 100000,
    parameter integer FPS_WINDOW_TICKS  = 100000,
    parameter integer CROSS_CYCLES      = 3,
    parameter integer TICK_CROSS        = 0,
    parameter integer ENTRY_LOG2        = 3,
    parameter integer MIN_GAP_SRC       = 2,
    parameter integer MIN_GAP_DST       = 3,
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
    input  wire              clk_cap,
    input  wire              rst_cap_n,
    input  wire              cap_event,
    input  wire [1:0]        cap_kind,
    input  wire [31:0]       cap_sid,
    input  wire [31:0]       cap_fid,
    input  wire              clk,
    input  wire              rst_n,
    input  wire              de,
    input  wire              hs,
    input  wire              vs,
    input  wire [23:0]       rgb_in,
    input  wire              dsp_event,
    input  wire [31:0]       dsp_sid,
    input  wire [31:0]       dsp_fid,
    input  wire              alarm_clr,
    input  wire              resync_req,
    output wire [23:0]       rgb_out,
    output wire              de_out,
    output wire              hs_out,
    output wire              vs_out,
    input  wire [6:0]        dbg_raddr,
    output wire [7:0]        dbg_rdata,
    output wire [31:0]       dbg_lat_cycles,
    output wire [31:0]       dbg_lat_ticks,
    output wire [31:0]       dbg_age_cycles,
    output wire [31:0]       dbg_age_ticks,
    output wire [31:0]       dbg_avg_ticks,
    output wire [31:0]       dbg_cap_fps,
    output wire [31:0]       dbg_dsp_fps,
    output wire [31:0]       dbg_cap_count,
    output wire [31:0]       dbg_dsp_count,
    output wire [31:0]       dbg_stat_count,
    output wire [63:0]       dbg_sum_ticks,
    output wire [3:0]        dbg_alarm,
    output wire              dbg_stats_valid,
    output wire              dbg_lat_seen,
    output wire              dbg_age_seen,
    output wire              dbg_fps_valid
);
    localparam integer OSD_ADDR_W = 7;      // 128 == COLS*ROWS

    //------------------------------------------------------------------
    // measurement
    //------------------------------------------------------------------
    wire [31:0] lat_cycles, lat_ticks, age_cycles, age_ticks;
    wire [31:0] cap_fps, dsp_fps, cap_count, dsp_count, stat_count, unmatched, repeat_cnt;
    wire [63:0] stat_sum, stat_sum_ticks;
    wire [31:0] lost_done, lost_abort, entry_count;
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
        .stat_sum_ticks (stat_sum_ticks),
        .cap_fps        (cap_fps),
        .dsp_fps        (dsp_fps),
        .fps_valid      (fps_valid),
        .entry_count    (entry_count),
        .evt_gap_alarm  (evt_gap_alarm),
        .lost_done_count(lost_done),
        .lost_abort_count(lost_abort)
    );

    //------------------------------------------------------------------
    // per frame snapshot (panel and debug outputs describe the same frame)
    //------------------------------------------------------------------
    reg  [31:0] count_bcd;
    reg         carry_c;
    integer     nib_c;
    reg  [31:0] count_next;

    reg [31:0] shown_lat_ticks, shown_age_ticks, shown_cap, shown_dsp;
    reg [31:0] shown_frame, shown_cnt;
    reg [63:0] shown_sum_ticks;
    reg [31:0] shown_count_bcd;
    reg [3:0]  shown_alarm;
    reg        shown_lat_seen, shown_age_seen, shown_stats, shown_fps;
    reg [31:0] avg_ticks;

    reg vs_d;
    wire vs_fall = vs_d & ~vs;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) vs_d <= 1'b0;
        else        vs_d <= vs;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            shown_lat_ticks <= 32'd0; shown_age_ticks <= 32'd0;
            shown_cap <= 32'd0;       shown_dsp <= 32'd0;
            shown_cnt <= 32'd0;       shown_sum_ticks <= 64'd0;
            shown_count_bcd <= 32'd0;
            shown_alarm <= 4'd0;
            shown_lat_seen <= 1'b0;   shown_age_seen <= 1'b0;
            shown_stats <= 1'b0;      shown_fps <= 1'b0;
            shown_frame <= 32'd0;
        end else if (vs_fall) begin
            shown_lat_ticks <= lat_ticks;
            shown_age_ticks <= age_ticks;
            shown_cap       <= cap_fps;
            shown_dsp       <= dsp_fps;
            shown_cnt       <= stat_count;
            shown_sum_ticks <= stat_sum_ticks;
            shown_count_bcd <= count_bcd;
            shown_alarm     <= alarm;
            shown_lat_seen  <= lat_seen;
            shown_age_seen  <= age_seen;
            shown_stats     <= stats_valid;
            shown_fps       <= fps_valid;
        end
    end

    //------------------------------------------------------------------
    // BCD counters: video frames and counted first displays
    //------------------------------------------------------------------
    reg  [31:0] frame_bcd;
    reg         carry;
    integer     nib;
    reg  [31:0] frame_next;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            frame_bcd   <= 32'd0;
            shown_frame <= 32'd0;
        end else if (vs_fall) begin
            frame_next = frame_bcd;
            carry = 1'b1;
            for (nib = 0; nib < 8; nib = nib + 1) begin
                if (carry) begin
                    if (frame_next[nib*4 +: 4] == 4'd9) begin
                        frame_next[nib*4 +: 4] = 4'd0;
                        carry = 1'b1;
                    end else begin
                        frame_next[nib*4 +: 4] = frame_next[nib*4 +: 4] + 4'd1;
                        carry = 1'b0;
                    end
                end
            end
            frame_bcd   <= frame_next;
            shown_frame <= frame_next;
        end
    end


    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count_bcd <= 32'd0;
        end else if (lat_valid) begin
            count_next = count_bcd;
            carry_c = 1'b1;
            for (nib_c = 0; nib_c < 8; nib_c = nib_c + 1) begin
                if (carry_c) begin
                    if (count_next[nib_c*4 +: 4] == 4'd9) begin
                        count_next[nib_c*4 +: 4] = 4'd0;
                        carry_c = 1'b1;
                    end else begin
                        count_next[nib_c*4 +: 4] = count_next[nib_c*4 +: 4] + 4'd1;
                        carry_c = 1'b0;
                    end
                end
            end
            count_bcd <= count_next;
        end
    end

    //------------------------------------------------------------------
    // serial restoring divider: avg = sum_ticks / count  (64 steps)
    //------------------------------------------------------------------
    reg  [63:0] div_num;
    reg  [32:0] div_rem;
    reg  [31:0] div_quo;
    reg  [6:0]  div_cnt;

    wire [32:0] div_rem_sh = {div_rem[31:0], div_num[63]};
    wire        div_ge     = (div_rem_sh >= {1'b0, shown_cnt});
    wire [32:0] div_rem_n  = div_ge ? (div_rem_sh - {1'b0, shown_cnt}) : div_rem_sh;
    wire [31:0] div_quo_n  = {div_quo[30:0], div_ge};

    //------------------------------------------------------------------
    // formatter
    //------------------------------------------------------------------
    localparam [3:0] S_INIT   = 4'd0,
                     S_IDLE   = 4'd1,
                     S_CONV   = 4'd2,
                     S_WR_LAT = 4'd3,
                     S_DIV    = 4'd4,
                     S_WR_AVG = 4'd5,
                     S_WR_AGE = 4'd6,
                     S_WR_CAP = 4'd7,
                     S_WR_DSP = 4'd8,
                     S_WR_FRM = 4'd9,
                     S_WR_ERR = 4'd10,
                     S_WR_CNT = 4'd11,
                     S_WR_ALM = 4'd12,
                     S_SNAP   = 4'd13;   // one cycle after vs_fall: snapshot visible

    localparam [31:0] MAX_TICKS = 32'd99999;
    localparam [16:0] CLAMP_TICKS = 17'd99999;

    reg  [3:0]  state;
    reg  [6:0]  idx;
    reg  [6:0]  tpl_idx;
    reg  [2:0]  cv_sel;     // 0 lat, 1 avg, 2 age, 3 cap, 4 dsp
    reg  [16:0] cv_bin;
    reg  [19:0] cv_bcd;
    reg  [4:0]  cv_cnt;
    reg  [19:0] bcd_lat, bcd_avg, bcd_age, bcd_cap, bcd_dsp;

    wire [3:0] a0 = (cv_bcd[3:0]   > 4'd4) ? (cv_bcd[3:0]   + 4'd3) : cv_bcd[3:0];
    wire [3:0] a1 = (cv_bcd[7:4]   > 4'd4) ? (cv_bcd[7:4]   + 4'd3) : cv_bcd[7:4];
    wire [3:0] a2 = (cv_bcd[11:8]  > 4'd4) ? (cv_bcd[11:8]  + 4'd3) : cv_bcd[11:8];
    wire [3:0] a3 = (cv_bcd[15:12] > 4'd4) ? (cv_bcd[15:12] + 4'd3) : cv_bcd[15:12];
    wire [3:0] a4 = (cv_bcd[19:16] > 4'd4) ? (cv_bcd[19:16] + 4'd3) : cv_bcd[19:16];
    wire [36:0] cv_sh    = {a4, a3, a2, a1, a0, cv_bin} << 1;
    wire [19:0] cv_bcd_n = cv_sh[36:17];
    wire [16:0] cv_bin_n = cv_sh[16:0];

    wire [19:0] bcd_sel = (cv_sel == 3'd0) ? bcd_lat :
                          (cv_sel == 3'd1) ? bcd_avg :
                          (cv_sel == 3'd2) ? bcd_age :
                          (cv_sel == 3'd3) ? bcd_cap : bcd_dsp;

    wire [3:0] d4 = bcd_sel[19:16];
    wire [3:0] d3 = bcd_sel[15:12];
    wire [3:0] d2 = bcd_sel[11:8];
    wire [3:0] d1 = bcd_sel[7:4];
    wire [3:0] d0 = bcd_sel[3:0];

    // panel validity: LAT/AVG require trustworthy statistics
    wire avg_ok  = shown_stats & (shown_cnt != 32'd0);
    wire lat_ok  = shown_lat_seen & shown_stats;
    wire age_ok  = shown_age_seen;

    // decoded alarm word (8 characters), priority UNMATCH > OVERWR > TOOFAST > SESSION
    reg [63:0] alm_word;
    always @(*) begin
        if (shown_alarm[0])      alm_word = 64'h554E4D4154434820; // "UNMATCH "
        else if (shown_alarm[1]) alm_word = 64'h4F56455257522020; // "OVERWR  "
        else if (shown_alarm[2]) alm_word = 64'h544F4F4641535420; // "TOOFAST "
        else if (shown_alarm[3]) alm_word = 64'h53455353494F4E20; // "SESSION "
        else                     alm_word = 64'h4E4F4E4520202020; // "NONE    "
    end

    reg  [7:0] wr_char;
    reg  [3:0] wr_nib;

    always @(*) begin
        wr_char = 8'h20;
        wr_nib  = 4'd0;
        case (state)
            S_WR_LAT, S_WR_AVG, S_WR_AGE: begin
                if (!((state == S_WR_LAT) ? lat_ok : (state == S_WR_AVG) ? avg_ok : age_ok)) begin
                    wr_char = (idx == 7'd3) ? 8'h2E : 8'h2D;
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
                    if ((idx == 7'd0) && (d4 == 4'd0))                      wr_char = 8'h20;
                    else if ((idx == 7'd1) && (d4 == 4'd0) && (d3 == 4'd0)) wr_char = 8'h20;
                    else                                                   wr_char = 8'h30 + {4'd0, wr_nib};
                end
            end
            S_WR_CAP, S_WR_DSP: begin
                if (!shown_fps) begin
                    wr_char = (idx < 7'd2) ? 8'h20 : 8'h2D;
                end else begin
                    case (idx)
                        7'd2: wr_nib = d2;
                        7'd3: wr_nib = d1;
                        7'd4: wr_nib = d0;
                        default: wr_nib = 4'd0;
                    endcase
                    if (idx < 7'd2)                                        wr_char = 8'h20;
                    else if ((idx == 7'd2) && (d2 == 4'd0))                wr_char = 8'h20;
                    else if ((idx == 7'd3) && (d2 == 4'd0) && (d1 == 4'd0)) wr_char = 8'h20;
                    else                                                   wr_char = 8'h30 + {4'd0, wr_nib};
                end
            end
            S_WR_FRM: begin
                wr_char = 8'h30 + {4'd0, shown_frame[(7'd7 - idx) * 4 +: 4]};
            end
            S_WR_CNT: begin
                wr_char = 8'h30 + {4'd0, shown_count_bcd[(7'd7 - idx) * 4 +: 4]};
            end
            S_WR_ERR: begin
                wr_char = 8'h30 + {4'd0, shown_alarm};
            end
            S_WR_ALM: begin
                if (idx == 7'd0)      wr_char = 8'h30 + {4'd0, shown_alarm};
                else if (idx == 7'd1) wr_char = 8'h20;
                else                  wr_char = alm_word[(7'd7 - (idx - 7'd2)) * 8 +: 8];
            end
            default: wr_char = 8'h20;
        endcase
    end

    reg  [6:0] osd_waddr;
    reg  [7:0] osd_wdata;
    reg        osd_we;
    reg  [9:0] tpl_base;

    always @(*) begin
        osd_waddr = 7'd0;
        osd_wdata = 8'h20;
        osd_we    = 1'b0;
        tpl_base  = (7'd127 - tpl_idx) * 8;
        case (state)
            S_INIT:   begin osd_waddr = tpl_idx;            osd_wdata = OSD_TEMPLATE[tpl_base +: 8]; osd_we = ~de; end
            S_WR_LAT: begin osd_waddr = OSD_FLD_LAT + idx;  osd_wdata = wr_char; osd_we = ~de; end
            S_WR_AVG: begin osd_waddr = OSD_FLD_AVG + idx;  osd_wdata = wr_char; osd_we = ~de; end
            S_WR_AGE: begin osd_waddr = OSD_FLD_AGE + idx;  osd_wdata = wr_char; osd_we = ~de; end
            S_WR_CAP: begin osd_waddr = OSD_FLD_CAP + idx;  osd_wdata = wr_char; osd_we = ~de; end
            S_WR_DSP: begin osd_waddr = OSD_FLD_DSP + idx;  osd_wdata = wr_char; osd_we = ~de; end
            S_WR_FRM: begin osd_waddr = OSD_FLD_FRM + idx;  osd_wdata = wr_char; osd_we = ~de; end
            S_WR_ERR: begin osd_waddr = OSD_FLD_ERR + idx;  osd_wdata = wr_char; osd_we = ~de; end
            S_WR_CNT: begin osd_waddr = OSD_FLD_CNT + idx;  osd_wdata = wr_char; osd_we = ~de; end
            S_WR_ALM: begin osd_waddr = OSD_FLD_ALM_NIB + idx; osd_wdata = wr_char; osd_we = ~de; end
            default:  begin osd_waddr = 7'd0; osd_wdata = 8'h20; osd_we = 1'b0; end
        endcase
    end

    integer i;
    reg [16:0] conv_src;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state   <= S_INIT;
            idx     <= 7'd0;
            tpl_idx <= 7'd0;
            cv_sel  <= 3'd0;
            cv_bin  <= 17'd0;
            cv_bcd  <= 20'd0;
            cv_cnt  <= 5'd0;
            bcd_lat <= 20'd0;
            bcd_avg <= 20'd0;
            bcd_age <= 20'd0;
            bcd_cap <= 20'd0;
            bcd_dsp <= 20'd0;
            div_num <= 64'd0;
            div_rem <= 33'd0;
            div_quo <= 32'd0;
            div_cnt <= 7'd0;
            avg_ticks <= 32'd0;
        end else begin
            case (state)
                S_INIT: begin
                    if (!de) begin
                        if (tpl_idx == 7'd127) begin
                            tpl_idx <= 7'd0;
                            state   <= S_IDLE;
                        end else tpl_idx <= tpl_idx + 7'd1;
                    end
                end
                S_IDLE: begin
                    if (vs_fall) state <= S_SNAP;
                end
                S_SNAP: begin
                    // the snapshot registers are updated on the same edge as
                    // vs_fall, so the first conversion must start one cycle later
                    cv_sel <= 3'd0;
                    cv_bin <= (shown_lat_ticks > MAX_TICKS) ? CLAMP_TICKS : shown_lat_ticks[16:0];
                    cv_bcd <= 20'd0;
                    cv_cnt <= 5'd0;
                    idx    <= 7'd0;
                    state  <= S_CONV;
                end
                S_CONV: begin
                    if (cv_cnt == 5'd16) begin
                        case (cv_sel)
                            3'd0: bcd_lat <= cv_bcd_n;
                            3'd1: bcd_avg <= cv_bcd_n;
                            3'd2: bcd_age <= cv_bcd_n;
                            3'd3: bcd_cap <= cv_bcd_n;
                            default: bcd_dsp <= cv_bcd_n;
                        endcase
                        cv_cnt <= 5'd0;
                        idx    <= 7'd0;
                        case (cv_sel)
                            3'd0: state <= S_WR_LAT;
                            3'd1: state <= S_WR_AVG;
                            3'd2: state <= S_WR_AGE;
                            3'd3: state <= S_WR_CAP;
                            default: state <= S_WR_DSP;
                        endcase
                    end else begin
                        cv_bcd <= cv_bcd_n;
                        cv_bin <= cv_bin_n;
                        cv_cnt <= cv_cnt + 5'd1;
                    end
                end
                S_WR_LAT, S_WR_AVG, S_WR_AGE, S_WR_CAP, S_WR_DSP: begin
                    if (osd_we) begin
                        if (idx == ((state == S_WR_CAP || state == S_WR_DSP)
                                    ? (OSD_LEN_FPS - 7'd1) : (OSD_LEN_MS - 7'd1))) begin
                            idx <= 7'd0;
                            case (state)
                                S_WR_LAT: begin
                                    // start the serial average division
                                    div_num <= shown_sum_ticks;
                                    div_rem <= 33'd0;
                                    div_quo <= 32'd0;
                                    div_cnt <= 7'd0;
                                    avg_ticks <= 32'd0;
                                    state <= S_DIV;
                                end
                                S_WR_AVG: begin
                                    cv_sel <= 3'd2;
                                    cv_bin <= (shown_age_ticks > MAX_TICKS) ? CLAMP_TICKS : shown_age_ticks[16:0];
                                    cv_bcd <= 20'd0;
                                    cv_cnt <= 5'd0;
                                    state  <= S_CONV;
                                end
                                S_WR_AGE: begin
                                    cv_sel <= 3'd3;
                                    cv_bin <= (shown_cap > 32'd999) ? 17'd999 : shown_cap[16:0];
                                    cv_bcd <= 20'd0;
                                    cv_cnt <= 5'd0;
                                    state  <= S_CONV;
                                end
                                S_WR_CAP: begin
                                    cv_sel <= 3'd4;
                                    cv_bin <= (shown_dsp > 32'd999) ? 17'd999 : shown_dsp[16:0];
                                    cv_bcd <= 20'd0;
                                    cv_cnt <= 5'd0;
                                    state  <= S_CONV;
                                end
                                default: state <= S_WR_FRM;
                            endcase
                        end else idx <= idx + 7'd1;
                    end
                end
                S_DIV: begin
                    if (shown_cnt == 32'd0) begin
                        avg_ticks <= 32'd0;
                        cv_sel <= 3'd1;
                        cv_bin <= 17'd0;
                        cv_bcd <= 20'd0;
                        cv_cnt <= 5'd0;
                        state  <= S_CONV;
                    end else if (div_cnt == 7'd63) begin
                        avg_ticks <= div_quo_n;
                        cv_sel <= 3'd1;
                        cv_bin <= (div_quo_n > MAX_TICKS) ? CLAMP_TICKS : div_quo_n[16:0];
                        cv_bcd <= 20'd0;
                        cv_cnt <= 5'd0;
                        state  <= S_CONV;
                    end else begin
                        div_rem <= div_rem_n;
                        div_quo <= div_quo_n;
                        div_num <= {div_num[62:0], 1'b0};
                        div_cnt <= div_cnt + 7'd1;
                    end
                end
                S_WR_FRM: begin
                    if (osd_we) begin
                        if (idx == (OSD_LEN_FRM - 7'd1)) begin idx <= 7'd0; state <= S_WR_ERR; end
                        else idx <= idx + 7'd1;
                    end
                end
                S_WR_ERR: begin
                    if (osd_we) begin idx <= 7'd0; state <= S_WR_CNT; end
                end
                S_WR_CNT: begin
                    if (osd_we) begin
                        if (idx == (OSD_LEN_CNT - 7'd1)) begin idx <= 7'd0; state <= S_WR_ALM; end
                        else idx <= idx + 7'd1;
                    end
                end
                S_WR_ALM: begin
                    if (osd_we) begin
                        if (idx == 7'd9) begin idx <= 7'd0; state <= S_IDLE; end
                        else idx <= idx + 7'd1;
                    end
                end
                default: state <= S_INIT;
            endcase
        end
    end

    //------------------------------------------------------------------
    // debug (snapshot based)
    //------------------------------------------------------------------
    assign dbg_lat_cycles  = lat_cycles;
    assign dbg_lat_ticks   = shown_lat_ticks;
    assign dbg_age_cycles  = age_cycles;
    assign dbg_age_ticks   = shown_age_ticks;
    assign dbg_avg_ticks   = avg_ticks;
    assign dbg_cap_fps     = shown_cap;
    assign dbg_dsp_fps     = shown_dsp;
    assign dbg_cap_count   = cap_count;
    assign dbg_dsp_count   = dsp_count;
    assign dbg_stat_count  = shown_cnt;
    assign dbg_sum_ticks   = shown_sum_ticks;
    assign dbg_alarm       = shown_alarm;
    assign dbg_stats_valid = shown_stats;
    assign dbg_lat_seen    = shown_lat_seen;
    assign dbg_age_seen    = shown_age_seen;
    assign dbg_fps_valid   = shown_fps;

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
