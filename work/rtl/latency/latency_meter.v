//======================================================================
// latency_meter.v - end-to-end latency meter (time-stamp queue method)
//
// Part of the "latency measurement and on-screen display" deliverable.
// Signal contract: docs/architecture/latency-osd-interface.md
//
// Function
//   A source event (frame start or line start of the pixel stream entering a
//   segment) is time-stamped with two free-running counters that both live in
//   the *destination* clock domain:
//       cyc_cnt  : one increment per clk cycle           (full resolution)
//       tick_cnt : one increment per 10 us on average    (0.01 ms display unit)
//   A destination event (the same frame/line leaving the segment) pops the
//   oldest time stamp; the difference is the segment latency. Because both
//   samples come from counters in the same domain, the subtraction is exact
//   and no cycle counter value is ever compared across clock domains.
//
//   The source event crosses as a *toggle* (source flop + 2-flop synchroniser
//   + edge detect), so the meter is insensitive to the source pulse width and
//   to the ratio of the two clocks. The crossing adds a bounded, non-negative
//   offset of 0..4 destination cycles to every measurement; the interface
//   document states that budget and the testbench verifies both the exact
//   same-clock case and the bounded cross-clock case.
//
// Arithmetic
//   No division, no multiplier, no vendor primitive. The 10 us tick comes from
//   a compare/subtract fractional accumulator whose average period is exactly
//   CLK_HZ/100000 cycles:
//       mean period = TICK_BASE + TICK_REMAINDER/TICK_MOD   [cycles]
//   with TICK_BASE = CLK_HZ/100000, TICK_REMAINDER = CLK_HZ mod 100000,
//   TICK_MOD = 100000, and the requirement TICK_REMAINDER < TICK_MOD.
//   Example: 74.25 MHz -> TICK_BASE = 742, TICK_REMAINDER = 50000,
//   so alternating intervals of 742 and 743 cycles give 742.5 on average.
//
// Pairing
//   Time stamps are queued in arrival order (DEPTH entries). If a source event
//   arrives while the queue is full the push is dropped and err_overflow
//   latches: every later pairing is shifted, so the reading must be discarded.
//   If a destination event arrives on an empty queue, err_underflow latches.
//   Both sticky flags are cleared by err_clr or reset. A full queue with a
//   simultaneous pop still accepts the push (no tag is lost).
//
// Verification level
//   Behavioural simulation only (work/tests/tb_latency_meter.v). No TD build,
//   no board measurement. Do not claim resource or on-board numbers.
//======================================================================
`timescale 1ns/1ps

module latency_meter #(
    parameter TICK_BASE      = 742,      // cycles per 10 us tick, integer part
    parameter TICK_REMAINDER = 50000,    // fractional part, denominator TICK_MOD
    parameter TICK_MOD       = 100000,   // fractional denominator
    parameter CNT_W          = 32,       // cycle counter width
    parameter TICK_W         = 32,       // tick counter width
    parameter DEPTH_LOG2     = 3         // time-stamp queue depth = 2**DEPTH_LOG2
) (
    // --- source domain: pixel stream entering the measured segment ---
    input  wire              clk_src,
    input  wire              rst_src_n,
    input  wire              src_token,   // any pulse width; one event per pulse
    // --- destination domain: pixel stream leaving the measured segment ---
    input  wire              clk,
    input  wire              rst_n,
    input  wire              out_token,
    input  wire              err_clr,     // clears both sticky flags
    // --- results (valid 2 clk cycles after the out_token edge) ---
    output reg  [TICK_W-1:0] lat_ticks,   // latency in 0.01 ms units
    output reg  [CNT_W-1:0]  lat_cycles,  // latency in clk cycles
    output reg               lat_valid,   // high after the first measurement
    output reg               err_overflow,
    output reg               err_underflow
);
    localparam DEPTH = (1 << DEPTH_LOG2);
    localparam TAG_W = CNT_W + TICK_W;

    localparam [16:0] TICK_BASE_Q = TICK_BASE;
    localparam [17:0] TICK_REM_Q  = TICK_REMAINDER;
    localparam [17:0] TICK_MOD_Q  = TICK_MOD;
    localparam [DEPTH_LOG2:0] DEPTH_Q = DEPTH;

    //------------------------------------------------------------------
    // 1. source-domain event -> toggle
    //------------------------------------------------------------------
    reg tok_tog;
    always @(posedge clk_src or negedge rst_src_n) begin
        if (!rst_src_n)     tok_tog <= 1'b0;
        else if (src_token) tok_tog <= ~tok_tog;
    end

    //------------------------------------------------------------------
    // 2. toggle synchroniser + edge detect (destination domain)
    //------------------------------------------------------------------
    reg tog_s1, tog_s2, tog_s3;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) {tog_s1, tog_s2, tog_s3} <= 3'b000;
        else        {tog_s1, tog_s2, tog_s3} <= {tok_tog, tog_s1, tog_s2};
    end
    wire src_evt = tog_s2 ^ tog_s3;   // exactly one 1-cycle pulse per source event

    //------------------------------------------------------------------
    // 3. free-running time base (destination domain)
    //------------------------------------------------------------------
    reg [CNT_W-1:0]  cyc_cnt;
    reg [TICK_W-1:0] tick_cnt;
    reg [16:0]       tick_run;       // cycles elapsed in the current interval
    reg [16:0]       tick_interval;  // TICK_BASE or TICK_BASE+1
    reg [16:0]       tick_acc;       // fractional accumulator

    wire [17:0] acc_sum  = {1'b0, tick_acc} + TICK_REM_Q;
    wire        acc_over = (acc_sum >= TICK_MOD_Q);
    wire [16:0] acc_keep = acc_over ? (acc_sum[16:0] - TICK_MOD[16:0]) : acc_sum[16:0];

    wire tick_end = (tick_run >= (tick_interval - 17'd1));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cyc_cnt       <= {CNT_W{1'b0}};
            tick_cnt      <= {TICK_W{1'b0}};
            tick_run      <= 17'd0;
            tick_interval <= TICK_BASE_Q;
            tick_acc      <= 17'd0;
        end else begin
            cyc_cnt <= cyc_cnt + 1'b1;
            if (tick_end) begin
                tick_run      <= 17'd0;
                tick_cnt      <= tick_cnt + 1'b1;
                tick_acc      <= acc_keep;
                tick_interval <= acc_over ? (TICK_BASE_Q + 17'd1) : TICK_BASE_Q;
            end else begin
                tick_run <= tick_run + 17'd1;
            end
        end
    end

    //------------------------------------------------------------------
    // 4. time-stamp queue (one clock domain, occupancy counted)
    //------------------------------------------------------------------
    reg  [TAG_W-1:0]      tag_mem [0:DEPTH-1];
    reg  [DEPTH_LOG2:0]   occ;
    reg  [DEPTH_LOG2-1:0] wptr, rptr;
    reg  [TAG_W-1:0]      rd_tag;

    wire full  = (occ == DEPTH_Q);
    wire empty = (occ == {(DEPTH_LOG2+1){1'b0}});
    wire pop   = out_token & ~empty;            // pop is independent of push
    wire wr_ok = ~full | pop;                   // full + simultaneous pop: keep the tag
    wire push  = src_evt & wr_ok;

    wire [TAG_W-1:0] tag_in = {tick_cnt, cyc_cnt};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wptr <= {DEPTH_LOG2{1'b0}};
            rptr <= {DEPTH_LOG2{1'b0}};
        end else begin
            if (push) begin
                tag_mem[wptr] <= tag_in;
                wptr          <= wptr + 1'b1;
            end
            if (pop) begin
                rptr <= rptr + 1'b1;
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)   rd_tag <= {TAG_W{1'b0}};
        else if (pop) rd_tag <= tag_mem[rptr];
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) occ <= {(DEPTH_LOG2+1){1'b0}};
        else        occ <= occ + (push ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
    end

    //------------------------------------------------------------------
    // 5. latency = counter samples taken at the pop edge - popped time stamp
    //    rd_tag is registered on the pop edge and the counter samples are
    //    latched on that same edge, so the subtraction is exact.
    //------------------------------------------------------------------
    reg               pop_d;
    reg [CNT_W-1:0]   cyc_at_pop;
    reg [TICK_W-1:0]  tick_at_pop;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pop_d       <= 1'b0;
            cyc_at_pop  <= {CNT_W{1'b0}};
            tick_at_pop <= {TICK_W{1'b0}};
        end else begin
            pop_d <= pop;
            if (pop) begin
                cyc_at_pop  <= cyc_cnt;
                tick_at_pop <= tick_cnt;
            end
        end
    end

    wire [CNT_W-1:0]  lat_cyc_nxt  = cyc_at_pop  - rd_tag[CNT_W-1:0];
    wire [TICK_W-1:0] lat_tick_nxt = tick_at_pop - rd_tag[TAG_W-1:CNT_W];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            lat_ticks  <= {TICK_W{1'b0}};
            lat_cycles <= {CNT_W{1'b0}};
            lat_valid  <= 1'b0;
        end else if (pop_d) begin
            lat_ticks  <= lat_tick_nxt;
            lat_cycles <= lat_cyc_nxt;
            lat_valid  <= 1'b1;
        end
    end

    //------------------------------------------------------------------
    // 6. sticky pairing errors
    //------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            err_overflow  <= 1'b0;
            err_underflow <= 1'b0;
        end else if (err_clr) begin
            err_overflow  <= 1'b0;
            err_underflow <= 1'b0;
        end else begin
            if (src_evt & ~wr_ok)  err_overflow  <= 1'b1;
            if (out_token & empty) err_underflow <= 1'b1;
        end
    end

endmodule
