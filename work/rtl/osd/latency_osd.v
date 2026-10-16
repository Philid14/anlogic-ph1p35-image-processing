//======================================================================
// latency_osd.v - end-to-end latency measurement with an on-screen readout
//
// Part of the "latency measurement and on-screen display" deliverable.
// Signal contract: docs/architecture/latency-osd-interface.md
//
//     sof_frame_src ----------------+
//                                   |   latency_meter (frame)   --> LAT-F value
//     vs (HDMI frame start) --------+                                |
//                                                                    v
//     sof_pipe_src -----------------+   latency_meter (pipe)    --> LAT-P value
//     vs (HDMI frame start) --------+                                |
//                                                                    v
//     rgb_in -------> text_overlay <---- character RAM <---- formatter FSM
//                        |                                 (frame blanking only)
//                        v
//                     rgb_out  (+3 clk cycles of fixed latency)
//
// Panel content (16 x 3 characters, see work/rtl/osd/osd_layout.vh):
//     LAT-F DDD.DD MS   frame latency  : sof_frame_src -> vs
//     LAT-P DDD.DD MS   pipeline latency: sof_pipe_src -> vs
//     FRM ########  E#  frame counter (BCD) and sticky error nibble
//
// Value format: 0.01 ms units, three integer digits, two decimals, leading
// zeros blanked, saturating at 999.99 ms (which also raises ERR bit 2).
//
// Error nibble (sticky until err_clr or reset)
//     bit 0 : time-stamp queue overflow  -> pairing lost, discard the reading
//     bit 1 : destination event with an empty queue
//     bit 2 : at least one reading saturated at 999.99 ms
//
// Frame boundary rule
//   The formatter writes the character RAM only while de is low, so a displayed
//   frame can never mix two text revisions. Numeric fields are refreshed once
//   per frame from the measurement of the frame that just completed.
//
// Arithmetic
//   No divider and no multiplier anywhere: decimal digits come from a 17-bit
//   double-dabble converter clocked once per bit inside the vertical blanking
//   interval (17 + 17 + 24 cycles per frame), and the frame counter is a BCD
//   ripple counter. See latency_meter.v for the tick generator.
//
// Verification level
//   Behavioural simulation only (work/tests/tb_latency_osd.v). No TD build and
//   no board measurement, so no resource or on-board number may be claimed.
//======================================================================
`timescale 1ns/1ps

`include "osd_layout.vh"

module latency_osd #(
    // --- timing ---
    parameter integer TICK_BASE      = 742,      // 74.25 MHz -> 742.5 cycles/tick
    parameter integer TICK_REMAINDER = 50000,
    parameter integer TICK_MOD       = 100000,
    parameter integer CNT_W          = 32,
    parameter integer TICK_W         = 32,
    parameter integer DEPTH_LOG2     = 3,
    // --- panel ---
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
    // source side: camera / ISP clock domain
    input  wire        clk_src,
    input  wire        rst_src_n,
    input  wire        sof_frame_src,
    input  wire        sof_pipe_src,
    // video side: HDMI pixel clock domain
    input  wire        clk,
    input  wire        rst_n,
    input  wire        de,
    input  wire        hs,
    input  wire        vs,
    input  wire [23:0] rgb_in,
    input  wire        err_clr,
    // video out, delayed by exactly 3 clk cycles
    output wire [23:0] rgb_out,
    output wire        de_out,
    output wire        hs_out,
    output wire        vs_out,
    // observability (testbenches and lab debug)
    input  wire [5:0]  dbg_raddr,
    output wire [7:0]  dbg_rdata,
    output wire [31:0] dbg_lat_frame_ticks,
    output wire [31:0] dbg_lat_frame_cycles,
    output wire [31:0] dbg_lat_pipe_ticks,
    output wire [31:0] dbg_lat_pipe_cycles,
    output wire [3:0]  dbg_err
);
    localparam integer OSD_ADDR_W = 6;               // 1<<6 = 64 >= COLS*ROWS = 48
    localparam [31:0]  MAX_TICKS  = 32'd99999;       // 999.99 ms

    localparam [16:0]  CLAMP_TICKS = 17'd99999;

    //------------------------------------------------------------------
    // vertical sync edges and the frame BCD counter
    //------------------------------------------------------------------
    reg vs_d;
    reg frame_inc;                                   // set on the vs falling edge

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) vs_d <= 1'b0;
        else        vs_d <= vs;
    end

    wire vs_rise = vs & ~vs_d;                       // frame start at the output
    wire vs_fall = vs_d & ~vs;                       // start of the blanking budget

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) frame_inc <= 1'b0;
        else        frame_inc <= vs_fall;
    end

    reg  [31:0] frame_bcd;
    reg         carry;
    integer     nib;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            frame_bcd <= 32'd0;
        end else if (frame_inc) begin
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
    // the two latency meters
    //------------------------------------------------------------------
    wire [TICK_W-1:0] lat_f_ticks, lat_p_ticks;
    wire [CNT_W-1:0]  lat_f_cycles, lat_p_cycles;
    wire              lat_f_valid, lat_p_valid;
    wire              err_f_ovf, err_f_unf, err_p_ovf, err_p_unf;

    latency_meter #(
        .TICK_BASE      (TICK_BASE),
        .TICK_REMAINDER (TICK_REMAINDER),
        .TICK_MOD       (TICK_MOD),
        .CNT_W          (CNT_W),
        .TICK_W         (TICK_W),
        .DEPTH_LOG2     (DEPTH_LOG2)
    ) u_meter_frame (
        .clk_src       (clk_src),
        .rst_src_n     (rst_src_n),
        .src_token     (sof_frame_src),
        .clk           (clk),
        .rst_n         (rst_n),
        .out_token     (vs_rise),
        .err_clr       (err_clr),
        .lat_ticks     (lat_f_ticks),
        .lat_cycles    (lat_f_cycles),
        .lat_valid     (lat_f_valid),
        .err_overflow  (err_f_ovf),
        .err_underflow (err_f_unf)
    );

    latency_meter #(
        .TICK_BASE      (TICK_BASE),
        .TICK_REMAINDER (TICK_REMAINDER),
        .TICK_MOD       (TICK_MOD),
        .CNT_W          (CNT_W),
        .TICK_W         (TICK_W),
        .DEPTH_LOG2     (DEPTH_LOG2)
    ) u_meter_pipe (
        .clk_src       (clk_src),
        .rst_src_n     (rst_src_n),
        .src_token     (sof_pipe_src),
        .clk           (clk),
        .rst_n         (rst_n),
        .out_token     (vs_rise),
        .err_clr       (err_clr),
        .lat_ticks     (lat_p_ticks),
        .lat_cycles    (lat_p_cycles),
        .lat_valid     (lat_p_valid),
        .err_overflow  (err_p_ovf),
        .err_underflow (err_p_unf)
    );

    assign dbg_lat_frame_ticks  = lat_f_ticks;
    assign dbg_lat_frame_cycles = lat_f_cycles;
    assign dbg_lat_pipe_ticks   = lat_p_ticks;
    assign dbg_lat_pipe_cycles  = lat_p_cycles;

    //------------------------------------------------------------------
    // formatter state machine
    //------------------------------------------------------------------
    localparam [2:0] S_INIT = 3'd0,
                     S_IDLE = 3'd1,
                     S_CONV = 3'd2,
                     S_WR_A = 3'd3,
                     S_WR_B = 3'd4,
                     S_WR_C = 3'd5,
                     S_WR_D = 3'd6;

    reg  [2:0]  state;
    reg  [5:0]  idx;                 // write index inside the current field
    reg  [5:0]  tpl_idx;             // template write index during S_INIT

    reg  [31:0] raw_a, raw_b;        // sampled meter readings (tick units)
    reg         valid_a, valid_b;
    reg         clamp_a, clamp_b;

    reg  [16:0] cv_bin;
    reg  [19:0] cv_bcd;
    reg  [4:0]  cv_cnt;
    reg         cv_sel_b;            // 0: converting field A, 1: field B
    reg  [19:0] bcd_a, bcd_b;

    wire        wr_sel_b = cv_sel_b;
    wire        wr_valid = wr_sel_b ? valid_b : valid_a;
    wire [19:0] bcd_sel  = wr_sel_b ? bcd_b  : bcd_a;

    // double-dabble iteration (+3 to every nibble above 4, then shift left)
    wire [3:0]  a0 = (cv_bcd[3:0]   > 4'd4) ? (cv_bcd[3:0]   + 4'd3) : cv_bcd[3:0];
    wire [3:0]  a1 = (cv_bcd[7:4]   > 4'd4) ? (cv_bcd[7:4]   + 4'd3) : cv_bcd[7:4];
    wire [3:0]  a2 = (cv_bcd[11:8]  > 4'd4) ? (cv_bcd[11:8]  + 4'd3) : cv_bcd[11:8];
    wire [3:0]  a3 = (cv_bcd[15:12] > 4'd4) ? (cv_bcd[15:12] + 4'd3) : cv_bcd[15:12];
    wire [3:0]  a4 = (cv_bcd[19:16] > 4'd4) ? (cv_bcd[19:16] + 4'd3) : cv_bcd[19:16];
    wire [36:0] cv_sh    = {a4, a3, a2, a1, a0, cv_bin} << 1;
    wire [19:0] cv_bcd_n = cv_sh[36:17];
    wire [16:0] cv_bin_n = cv_sh[16:0];

    // latency field characters: DDD.DD with blanked leading zeros
    wire [3:0]  lb0 = bcd_sel[19:16];
    wire [3:0]  lb1 = bcd_sel[15:12];
    wire [3:0]  lb2 = bcd_sel[11:8];
    wire [3:0]  lb3 = bcd_sel[7:4];
    wire [3:0]  lb4 = bcd_sel[3:0];

    reg  [7:0]  wr_char;
    reg  [3:0]  wr_nib;

    always @(*) begin
        wr_nib  = 4'd0;
        wr_char = 8'h20;
        case (state)
            S_WR_A, S_WR_B: begin
                if (idx == 6'd3) begin
                    wr_char = 8'h2E;                             // '.'
                end else if (!wr_valid) begin
                    wr_char = 8'h2D;                             // '-'
                end else begin
                    case (idx)
                        6'd0: wr_nib = lb0;
                        6'd1: wr_nib = lb1;
                        6'd2: wr_nib = lb2;
                        6'd4: wr_nib = lb3;
                        default: wr_nib = lb4;
                    endcase
                    // blank the hundreds and tens digit while they are zero
                    if ((idx == 6'd0) && (lb0 == 4'd0))                       wr_char = 8'h20;
                    else if ((idx == 6'd1) && (lb0 == 4'd0) && (lb1 == 4'd0)) wr_char = 8'h20;
                    else                                                      wr_char = 8'h30 + {4'd0, wr_nib};
                end
            end
            S_WR_C: begin
                wr_nib  = frame_bcd[(4'd7 - idx) * 4 +: 4];
                wr_char = 8'h30 + {4'd0, wr_nib};
            end
            S_WR_D: begin
                wr_nib  = {1'b0, (clamp_a | clamp_b),
                           (err_f_unf | err_p_unf), (err_f_ovf | err_p_ovf)};
                wr_char = 8'h30 + {4'd0, wr_nib};
            end
            default: begin
                wr_char = 8'h20;
            end
        endcase
    end

    // write address and write strobe
    reg  [5:0] osd_waddr;
    reg  [7:0] osd_wdata;
    reg        osd_we;

    reg  [8:0] tpl_base;

    always @(*) begin
        osd_waddr = 6'd0;
        osd_wdata = 8'h20;
        osd_we    = 1'b0;
        tpl_base  = (6'd47 - tpl_idx) * 8;
        case (state)
            S_INIT: begin
                osd_waddr = tpl_idx;
                osd_wdata = OSD_TEMPLATE[tpl_base +: 8];
                osd_we    = ~de;
            end
            S_WR_A: begin
                osd_waddr = OSD_FLD_LAT_FRAME + idx;
                osd_wdata = wr_char;
                osd_we    = ~de;
            end
            S_WR_B: begin
                osd_waddr = OSD_FLD_LAT_PIPE + idx;
                osd_wdata = wr_char;
                osd_we    = ~de;
            end
            S_WR_C: begin
                osd_waddr = OSD_FLD_FRAME + idx;
                osd_wdata = wr_char;
                osd_we    = ~de;
            end
            S_WR_D: begin
                osd_waddr = OSD_FLD_ERR + idx;
                osd_wdata = wr_char;
                osd_we    = ~de;
            end
            default: begin
                osd_waddr = 6'd0;
                osd_wdata = 8'h20;
                osd_we    = 1'b0;
            end
        endcase
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= S_INIT;
            idx       <= 6'd0;
            tpl_idx   <= 6'd0;
            raw_a     <= 32'd0;
            raw_b     <= 32'd0;
            valid_a   <= 1'b0;
            valid_b   <= 1'b0;
            clamp_a   <= 1'b0;
            clamp_b   <= 1'b0;
            cv_bin    <= 17'd0;
            cv_bcd    <= 20'd0;
            cv_cnt    <= 5'd0;
            cv_sel_b  <= 1'b0;
            bcd_a     <= 20'd0;
            bcd_b     <= 20'd0;
        end else begin
            case (state)
                S_INIT: begin
                    if (!de) begin
                        if (tpl_idx == 6'd47) begin
                            tpl_idx <= 6'd0;
                            state   <= S_IDLE;
                        end else begin
                            tpl_idx <= tpl_idx + 6'd1;
                        end
                    end
                end

                S_IDLE: begin
                    if (vs_fall) begin
                        raw_a    <= lat_f_ticks;
                        raw_b    <= lat_p_ticks;
                        valid_a  <= lat_f_valid;
                        valid_b  <= lat_p_valid;
                        clamp_a  <= (lat_f_ticks > MAX_TICKS);
                        clamp_b  <= (lat_p_ticks > MAX_TICKS);
                        // start with field A
                        cv_sel_b <= 1'b0;
                        cv_bin   <= (lat_f_ticks > MAX_TICKS) ? CLAMP_TICKS
                                                             : lat_f_ticks[16:0];
                        cv_bcd   <= 20'd0;
                        cv_cnt   <= 5'd0;
                        idx      <= 6'd0;
                        state    <= S_CONV;
                    end
                end

                S_CONV: begin
                    if (cv_cnt == 5'd16) begin
                        if (cv_sel_b) bcd_b <= cv_bcd_n;
                        else          bcd_a <= cv_bcd_n;
                        cv_cnt <= 5'd0;
                        idx    <= 6'd0;
                        state  <= cv_sel_b ? S_WR_B : S_WR_A;
                    end else begin
                        cv_bcd <= cv_bcd_n;
                        cv_bin <= cv_bin_n;
                        cv_cnt <= cv_cnt + 5'd1;
                    end
                end

                S_WR_A: begin
                    if (osd_we) begin
                        if (idx == (OSD_FLD_LAT_LEN - 6'd1)) begin
                            // second conversion: pipeline field
                            cv_sel_b <= 1'b1;
                            cv_bin   <= (raw_b > MAX_TICKS) ? CLAMP_TICKS : raw_b[16:0];
                            cv_bcd   <= 20'd0;
                            cv_cnt   <= 5'd0;
                            idx      <= 6'd0;
                            state    <= S_CONV;
                        end else begin
                            idx <= idx + 6'd1;
                        end
                    end
                end

                S_WR_B: begin
                    if (osd_we) begin
                        if (idx == (OSD_FLD_LAT_LEN - 6'd1)) begin
                            idx   <= 6'd0;
                            state <= S_WR_C;
                        end else begin
                            idx <= idx + 6'd1;
                        end
                    end
                end

                S_WR_C: begin
                    if (osd_we) begin
                        if (idx == (OSD_FLD_FRAME_LEN - 6'd1)) begin
                            idx   <= 6'd0;
                            state <= S_WR_D;
                        end else begin
                            idx <= idx + 6'd1;
                        end
                    end
                end

                S_WR_D: begin
                    if (osd_we) begin
                        idx   <= 6'd0;
                        state <= S_IDLE;
                    end
                end

                default: state <= S_INIT;
            endcase
        end
    end

    //------------------------------------------------------------------
    // streaming text overlay
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

    assign dbg_err = {1'b0, (clamp_a | clamp_b),
                      (err_f_unf | err_p_unf), (err_f_ovf | err_p_ovf)};

endmodule
