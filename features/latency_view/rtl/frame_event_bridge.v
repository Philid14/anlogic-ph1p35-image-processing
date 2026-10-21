//======================================================================
// frame_event_bridge.v - capture event edge detection + CDC of
//                        {kind, session_id, frame_id}
//
// Contract (see docs/interface-contract.md):
//   cap_event is a LEVEL or a PULSE in the capture clock domain. Only its
//   RISING EDGE is an event: holding it high for N cycles produces exactly one
//   event (the b43284c defect counted N events for an N cycle level).
//
//   Errors are explicit:
//     cap_too_fast  two rising edges closer than MIN_GAP_SRC capture cycles.
//                   It is a TOGGLE: each dropped event flips it, and the
//                   destination detects the change, so a slower destination
//                   clock can never miss it (a one cycle pulse could).
//                   The second event is DROPPED (never counted), because a
//                   toggle synchroniser cannot represent events that close.
//     evt_gap_alarm two events reach the destination closer than MIN_GAP_DST
//                   destination cycles; the pair cannot be resolved reliably.
//
//   Minimum spacing requirement for the CDC: an accepted event must be at
//   least MIN_GAP_SRC (default 2) capture cycles after the previous one, and
//   the destination must see at least MIN_GAP_DST (default 3) cycles between
//   pops. Frame starts are thousands of cycles apart in every supported video
//   mode, so the defaults only reject malformed stimulus.
//
//   Data crosses through a classic gray pointer asynchronous FIFO (depth
//   2**DEPTH_LOG2). Only the payload that the destination actually pops is
//   forwarded, so no event can be invented or duplicated by the crossing.
//
//   Queueing: the payload carries ``queued`` = "the FIFO was not empty when
//   this event was written". A queued event has an unknown extra delay, which a
//   fixed CROSS_CYCLES cannot remove; latency_meter excludes such samples from
//   the statistic and flags alarm[2] instead (MAIN interface reply 2026-10-21).
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
    input  wire              cap_event,     // level or pulse; rising edge = 1 event
    input  wire [1:0]        cap_kind,      // 0 = captured, 1 = aborted, 2 = complete
    input  wire [SID_W-1:0]  cap_sid,
    input  wire [FID_W-1:0]  cap_fid,
    output reg               cap_too_fast,  // toggle: an event was dropped
    // destination side
    input  wire              clk,
    input  wire              rst_n,
    input  wire              evt_ready,     // consumer accepts a pop this cycle
    output wire [SID_W+FID_W+2:0] evt_data,   // {queued, kind, sid, fid}
    output wire              evt_valid,     // FIFO not empty
    output reg               evt_gap_alarm  // sticky: pops too close together
);
    localparam integer W   = SID_W + FID_W + 3;
    localparam integer DEP = (1 << DEPTH_LOG2);

    //------------------------------------------------------------------
    // capture side: rising edge detect + minimum spacing
    //------------------------------------------------------------------
    reg  cap_d;
    reg [15:0] gap_cnt;
    wire       cap_rise = cap_event & ~cap_d;
    wire       gap_ok   = (gap_cnt >= MIN_GAP_SRC[15:0]) || (gap_cnt == 16'hFFFF);

    always @(posedge clk_cap or negedge rst_cap_n) begin
        if (!rst_cap_n) begin
            cap_d        <= 1'b0;
            gap_cnt      <= 16'hFFFF;
            cap_too_fast <= 1'b0;
        end else begin
            cap_d <= cap_event;
            if (cap_rise && !gap_ok) begin
                cap_too_fast <= ~cap_too_fast;  // dropped: toggle, latched by the meter
                gap_cnt      <= 16'd0;
            end else if (cap_rise) begin
                gap_cnt <= 16'd0;
            end else if (gap_cnt != 16'hFFFF) begin
                gap_cnt <= gap_cnt + 16'd1;
            end
        end
    end

    //------------------------------------------------------------------
    // asynchronous FIFO: gray pointers
    //------------------------------------------------------------------
    reg [W-1:0] mem [0:DEP-1];
    reg [DEPTH_LOG2:0] wbin, rbin;
    reg [DEPTH_LOG2:0] wgray, rgray;
    reg [DEPTH_LOG2:0] wq1_rgray, wq2_rgray;
    reg [DEPTH_LOG2:0] rq1_wgray, rq2_wgray;

    wire full  = (wgray == {~wq2_rgray[DEPTH_LOG2:DEPTH_LOG2-1],
                            wq2_rgray[DEPTH_LOG2-2:0]});
    wire empty = (rgray == rq2_wgray);

    // gray -> binary (the synchronised pointer is gray coded; comparing it to
    // the binary write pointer directly was the bug found in self-review)
    function [DEPTH_LOG2:0] gray2bin;
        input [DEPTH_LOG2:0] g;
        integer k;
        begin
            gray2bin[DEPTH_LOG2] = g[DEPTH_LOG2];
            for (k = DEPTH_LOG2 - 1; k >= 0; k = k - 1)
                gray2bin[k] = gray2bin[k + 1] ^ g[k];
        end
    endfunction

    wire [DEPTH_LOG2:0] rbin_sync = gray2bin(wq2_rgray);
    wire [DEPTH_LOG2:0] occ_w     = wbin - rbin_sync;
    // One entry is normally in flight (the reader needs 2-3 cycles to see the
    // write pointer). Only an occupancy of two or more means an event had to
    // wait behind another one, which is the queueing we must invalidate.
    wire                wr_queued = (occ_w > {{DEPTH_LOG2{1'b0}}, 1'b1});
    wire [DEPTH_LOG2:0] wbin_nxt = wbin + {{DEPTH_LOG2{1'b0}}, (cap_rise & gap_ok & ~full)};
    wire [DEPTH_LOG2:0] rbin_nxt = rbin + {{DEPTH_LOG2{1'b0}}, (evt_valid & evt_ready)};
    wire [DEPTH_LOG2:0] wgray_nxt = (wbin_nxt >> 1) ^ wbin_nxt;
    wire [DEPTH_LOG2:0] rgray_nxt = (rbin_nxt >> 1) ^ rbin_nxt;

    assign evt_valid = ~empty;
    assign evt_data  = mem[rbin[DEPTH_LOG2-1:0]];

    always @(posedge clk_cap or negedge rst_cap_n) begin
        if (!rst_cap_n) begin
            wbin  <= {(DEPTH_LOG2+1){1'b0}};
            wgray <= {(DEPTH_LOG2+1){1'b0}};
        end else begin
            wbin  <= wbin_nxt;
            wgray <= wgray_nxt;
            if (cap_rise & gap_ok & ~full)
                mem[wbin[DEPTH_LOG2-1:0]] <= {wr_queued, cap_kind, cap_sid, cap_fid};
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rbin  <= {(DEPTH_LOG2+1){1'b0}};
            rgray <= {(DEPTH_LOG2+1){1'b0}};
        end else begin
            rbin  <= rbin_nxt;
            rgray <= rgray_nxt;
        end
    end

    // pointer synchronisers
    always @(posedge clk_cap or negedge rst_cap_n) begin
        if (!rst_cap_n) begin
            wq1_rgray <= {(DEPTH_LOG2+1){1'b0}};
            wq2_rgray <= {(DEPTH_LOG2+1){1'b0}};
        end else begin
            wq1_rgray <= rgray;
            wq2_rgray <= wq1_rgray;
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

    //------------------------------------------------------------------
    // destination side: pop spacing monitor
    //------------------------------------------------------------------
    reg [15:0] dsp_gap;
    wire       pop = evt_valid & evt_ready;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dsp_gap       <= 16'hFFFF;
            evt_gap_alarm <= 1'b0;
        end else begin
            evt_gap_alarm <= 1'b0;             // one cycle pulse
            if (pop) begin
                if (dsp_gap < MIN_GAP_DST[15:0]) evt_gap_alarm <= 1'b1;
                dsp_gap <= 16'd0;
            end else if (dsp_gap != 16'hFFFF) begin
                dsp_gap <= dsp_gap + 16'd1;
            end
        end
    end

endmodule
