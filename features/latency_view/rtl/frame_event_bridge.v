//======================================================================
// frame_event_bridge.v - capture event edge detection + CDC of
//                        {queued, kind, session_id, frame_id}
//
// Contract (docs/INTERFACE.md, TEAM_PROTOCOL_V1 4.1/4.4):
//   cap_event is a LEVEL or a PULSE in the capture domain. Only its RISING EDGE
//   is an event: holding it high for N cycles produces exactly one event.
//   Kinds: 0 = frame captured, 1 = aborted/overwritten, 2 = frame complete.
//
// Loss accounting (TARGET review 2026-10-21, P1)
//   Every dropped event - too close (MIN_GAP_SRC) OR FIFO full - increments an
//   8 bit gray coded counter in the capture domain. The counter is synchronized
//   to the destination and compared with the last value seen there, so a full
//   queue can never be silent and two errors inside one sampling interval can
//   never cancel each other (the old toggle scheme could). lost_count reports
//   the exact number of lost source events. Nothing is back-pressured.
//
// Queueing / timing validity
//   At the supported event rate (one frame start per frame, reader pops every
//   cycle) the FIFO never backs up, so the crossing delay stays inside the
//   documented CROSS_CYCLES estimate. Any event loss or too-close destination
//   pop is reported (lost_count / evt_gap_alarm) and latency_meter latches a
//   fatal fault that requires an explicit resync before statistics resume.
//
// Flush / epoch
//   flush_req discards all pending entries without delivering them. The read
//   side also flushes automatically after its own reset, so a single-side
//   destination reset cannot replay retired entries. The source is never
//   stalled.
//======================================================================
`timescale 1ns/1ps

module frame_event_bridge #(
    parameter integer SID_W       = 32,
    parameter integer FID_W       = 32,
    parameter integer DEPTH_LOG2  = 4,
    parameter integer MIN_GAP_SRC = 2,
    parameter integer MIN_GAP_DST = 3
) (
    // capture side
    input  wire              clk_cap,
    input  wire              rst_cap_n,
    input  wire              cap_event,
    input  wire [1:0]        cap_kind,
    input  wire [SID_W-1:0]  cap_sid,
    input  wire [FID_W-1:0]  cap_fid,
    // destination side
    input  wire              clk,
    input  wire              rst_n,
    input  wire              evt_ready,
    input  wire              flush_req,
    output wire [SID_W+FID_W+1:0] evt_data,   // {kind, sid, fid}
    output wire              evt_valid,
    output reg               evt_gap_alarm,   // 1 cycle pulse: pops too close
    output reg               lost_event,     // 1 cycle pulse: new source losses
    output reg  [7:0]        lost_count      // total lost source events
);
    localparam integer W = SID_W + FID_W + 2;
    localparam integer DEP = (1 << DEPTH_LOG2);

    function [DEPTH_LOG2:0] gray2bin;
        input [DEPTH_LOG2:0] g;
        integer k;
        begin
            gray2bin[DEPTH_LOG2] = g[DEPTH_LOG2];
            for (k = DEPTH_LOG2 - 1; k >= 0; k = k - 1)
                gray2bin[k] = gray2bin[k + 1] ^ g[k];
        end
    endfunction

    function [7:0] gray2bin8;
        input [7:0] g;
        integer k;
        begin
            gray2bin8[7] = g[7];
            for (k = 6; k >= 0; k = k - 1)
                gray2bin8[k] = gray2bin8[k + 1] ^ g[k];
        end
    endfunction

    // ---------------- declarations ----------------
    reg        cap_d;
    reg [15:0] gap_cnt;
    reg [7:0]  err_bin, err_gray;

    reg [W-1:0] mem [0:DEP-1];
    reg [DEPTH_LOG2:0] wbin, rbin, wgray, rgray;
    reg [DEPTH_LOG2:0] wq1_rgray, wq2_rgray;
    reg [DEPTH_LOG2:0] rq1_wgray, rq2_wgray;

    reg        flush_active;
    reg [15:0] dsp_gap;

    reg [7:0]  eq1_err, eq2_err;
    reg [7:0]  seen_err;

    wire       cap_rise = cap_event & ~cap_d;
    wire       gap_ok   = (gap_cnt >= MIN_GAP_SRC[15:0]) || (gap_cnt == 16'hFFFF);

    wire full  = (wgray == {~wq2_rgray[DEPTH_LOG2:DEPTH_LOG2-1], wq2_rgray[DEPTH_LOG2-2:0]});
    wire empty = (rgray == rq2_wgray);

    wire       drop_gap  = cap_rise & ~gap_ok;
    wire       drop_full = cap_rise & gap_ok & full;
    wire       drop_any  = drop_gap | drop_full;

    wire       pop = ~empty & (evt_ready | flush_active);

    wire [DEPTH_LOG2:0] wbin_nxt  = wbin + {{DEPTH_LOG2{1'b0}}, (cap_rise & gap_ok & ~full)};
    wire [DEPTH_LOG2:0] rbin_nxt  = rbin + {{DEPTH_LOG2{1'b0}}, pop};
    wire [DEPTH_LOG2:0] wgray_nxt = (wbin_nxt >> 1) ^ wbin_nxt;
    wire [DEPTH_LOG2:0] rgray_nxt = (rbin_nxt >> 1) ^ rbin_nxt;

    wire [7:0] err_bin_sync = gray2bin8(eq2_err);

    assign evt_valid = ~empty & ~flush_active;
    assign evt_data  = mem[rbin[DEPTH_LOG2-1:0]];

    // ---------------- capture side ----------------
    always @(posedge clk_cap or negedge rst_cap_n) begin
        if (!rst_cap_n) begin
            cap_d    <= 1'b0;
            gap_cnt  <= 16'hFFFF;
            err_bin  <= 8'd0;
            err_gray <= 8'd0;
        end else begin
            cap_d <= cap_event;
            if (cap_rise) gap_cnt <= 16'd0;
            else if (gap_cnt != 16'hFFFF) gap_cnt <= gap_cnt + 16'd1;
            if (drop_any) begin
                err_bin  <= err_bin + 8'd1;
                err_gray <= ((err_bin + 8'd1) >> 1) ^ (err_bin + 8'd1);
            end
        end
    end

    always @(posedge clk_cap or negedge rst_cap_n) begin
        if (!rst_cap_n) begin
            wbin  <= {(DEPTH_LOG2+1){1'b0}};
            wgray <= {(DEPTH_LOG2+1){1'b0}};
        end else begin
            wbin  <= wbin_nxt;
            wgray <= wgray_nxt;
            if (cap_rise & gap_ok & ~full)
                mem[wbin[DEPTH_LOG2-1:0]] <= {cap_kind, cap_sid, cap_fid};
        end
    end

    always @(posedge clk_cap or negedge rst_cap_n) begin
        if (!rst_cap_n) begin
            wq1_rgray <= {(DEPTH_LOG2+1){1'b0}};
            wq2_rgray <= {(DEPTH_LOG2+1){1'b0}};
        end else begin
            wq1_rgray <= rgray;
            wq2_rgray <= wq1_rgray;
        end
    end

    // ---------------- destination side ----------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rbin  <= {(DEPTH_LOG2+1){1'b0}};
            rgray <= {(DEPTH_LOG2+1){1'b0}};
        end else begin
            rbin  <= rbin_nxt;
            rgray <= rgray_nxt;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rq1_wgray <= {(DEPTH_LOG2+1){1'b0}};
            rq2_wgray <= {(DEPTH_LOG2+1){1'b0}};
        end else begin
            rq1_wgray <= wgray;
            rq2_wgray <= rq1_wgray;
        end
    end

    // error counter crossing: gray -> binary, compare, report the delta
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            eq1_err    <= 8'd0;
            eq2_err    <= 8'd0;
            seen_err   <= 8'd0;
            lost_event <= 1'b0;
            lost_count <= 8'd0;
        end else begin
            eq1_err    <= err_gray;
            eq2_err    <= eq1_err;
            lost_event <= 1'b0;
            if (err_bin_sync != seen_err) begin
                lost_event <= 1'b1;
                lost_count <= lost_count + (err_bin_sync - seen_err);
                seen_err   <= err_bin_sync;
            end
        end
    end

    // flush / epoch + pop spacing
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dsp_gap       <= 16'hFFFF;
            evt_gap_alarm <= 1'b0;
            flush_active  <= 1'b1;              // drain stale entries after reset
        end else begin
            evt_gap_alarm <= 1'b0;
            if (flush_req) flush_active <= 1'b1;
            else if (flush_active && empty) flush_active <= 1'b0;

            if (pop && !flush_active) begin
                if (dsp_gap < MIN_GAP_DST[15:0]) evt_gap_alarm <= 1'b1;
                dsp_gap <= 16'd0;
            end else if (dsp_gap != 16'hFFFF) begin
                dsp_gap <= dsp_gap + 16'd1;
            end
        end
    end

endmodule
