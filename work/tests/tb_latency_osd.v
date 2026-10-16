//======================================================================
// tb_latency_osd.v - integration testbench for work/rtl/osd/latency_osd.v
//
// One source clock (clk_src is tied to clk so the meter arithmetic is exact
// and reproducible; the two-clock behaviour is covered by tb_latency_meter).
//
// The testbench streams TB_FRAMES complete frames, injects the frame and
// pipeline source tokens a fixed number of cycles before each vs rising edge,
// and then reports:
//   LATF / LATP  measured latency in ticks and cycles plus lat_valid
//   ERR          the 4-bit sticky error nibble shown on screen
//   CHAR         48 characters read back from the overlay RAM
//   HASH         32-bit hash of every active output pixel
//   DELAY_ERRORS de_out versus de delayed by the documented three cycles
//
// The runner (work/tests/run_latency_sim.py) compares these numbers with the
// values produced by work/models/latency_osd_model.py.
//
// Behavioural evidence only: no synthesis, no board claim.
//======================================================================
`timescale 1ns/1ps

module tb_latency_osd;

    parameter integer TB_H          = 320;
    parameter integer TB_V          = 64;
    parameter integer TB_HT         = 340;
    parameter integer TB_VT         = 74;
    parameter integer TB_FRAMES     = 3;
    parameter integer TB_BACK_FRAME = 2000;   // source token lead time, cycles
    parameter integer TB_BACK_PIPE  = 200;
    parameter integer TB_X0         = 8;
    parameter integer TB_Y0         = 4;
    parameter integer TB_SCALE_LOG2 = 1;
    parameter integer TB_TICK_BASE      = 10;
    parameter integer TB_TICK_REMAINDER = 50000;
    parameter integer TB_TICK_MOD       = 100000;
    parameter integer TB_DEST_HALF      = 5;
    parameter real    TB_CLK_HALF       = 5.0;

    localparam integer FRAME_CYCLES   = TB_HT * TB_VT;
    localparam [31:0]  FRAME_CYCLES_U = (TB_HT * TB_VT);
    localparam integer TOTAL_CYCLES   = FRAME_CYCLES * (TB_FRAMES + 1);

    reg clk = 1'b0;
    always #(TB_CLK_HALF) clk = ~clk;

    reg rst_n = 1'b0;

    // ---------------- raster + source token generator ----------------
    integer    gt   = 0;
    integer    bsum  = 0;
    integer    lfrac = 0;
    integer    line = 0;
    integer    col  = 0;
    reg        vs_gen = 1'b0;
    reg        hs_gen = 1'b0;
    reg        de_gen = 1'b0;
    reg [23:0] rgb_gen = 24'd0;

    reg        sof_frame_src = 1'b0;
    reg        sof_pipe_src  = 1'b0;
    reg        err_clr_drv   = 1'b0;

    // The first output frame has no time stamp yet, so the frame meter flags a
    // pairing error. A real integration clears it once, right after the first
    // measured frame; this testbench does the same during frame 1's blanking.
    initial begin
        wait (gt > (FRAME_CYCLES + TB_V * TB_HT));
        err_clr_drv = 1'b1;
        wait (gt > (2 * FRAME_CYCLES));
        err_clr_drv = 1'b0;
    end

    wire [31:0] pos_in_frame = (gt > 0) ? ((gt - 1) % FRAME_CYCLES) : 32'd0;
    wire [31:0] frame_off    = FRAME_CYCLES_U;
    wire [31:0] frame_tok_pos = (frame_off - TB_BACK_FRAME) % frame_off;
    wire [31:0] pipe_tok_pos  = (frame_off - TB_BACK_PIPE) % frame_off;

    task raster_step;
        begin
            // 1 ns after the clock edge so the design's flip flops cannot sample
            // the value that this task is about to drive at the same instant
            #1;
            gt     = gt + 1;
            line   = ((gt - 1) / TB_HT) % TB_VT;
            col    = (gt - 1) % TB_HT;
            vs_gen = (line < 2);
            hs_gen = (col >= TB_H) && (col < TB_H + 4);
            de_gen = (line < TB_V) && (col < TB_H);
            lfrac   = line % TB_VT;          // frame local line index
            bsum    = (col + lfrac) & 255;   // low byte, no width surprise
            rgb_gen = {col[7:0], lfrac[7:0], bsum[7:0]};
            sof_frame_src = (pos_in_frame == frame_tok_pos);
            sof_pipe_src  = (pos_in_frame == pipe_tok_pos);
        end
    endtask

    // ---------------- DUT ----------------
    reg  [5:0] dbg_raddr = 0;
    wire [7:0] dbg_rdata;
    wire [23:0] rgb_out;
    wire        de_out, hs_out, vs_out;
    wire [31:0] dbg_lat_frame_ticks, dbg_lat_frame_cycles;
    wire [31:0] dbg_lat_pipe_ticks,  dbg_lat_pipe_cycles;
    wire [3:0]  dbg_err;

    latency_osd #(
        .TICK_BASE      (TB_TICK_BASE),
        .TICK_REMAINDER (TB_TICK_REMAINDER),
        .TICK_MOD       (TB_TICK_MOD),
        .H_ACTIVE       (TB_H),
        .V_ACTIVE       (TB_V),
        .X0             (TB_X0),
        .Y0             (TB_Y0),
        .SCALE_LOG2     (TB_SCALE_LOG2),
        .PANEL_EN       (1),
        .BG_DIM         (1),
        .FG_RGB         (24'hFFFFFF),
        .BG_RGB         (24'h000000)
    ) dut (
        .clk_src       (clk),
        .rst_src_n     (rst_n),
        .sof_frame_src (sof_frame_src),
        .sof_pipe_src  (sof_pipe_src),
        .clk           (clk),
        .rst_n         (rst_n),
        .de            (de_gen),
        .hs            (hs_gen),
        .vs            (vs_gen),
        .rgb_in        (rgb_gen),
        .err_clr       (err_clr_drv),
        .rgb_out       (rgb_out),
        .de_out        (de_out),
        .hs_out        (hs_out),
        .vs_out        (vs_out),
        .dbg_raddr     (dbg_raddr),
        .dbg_rdata     (dbg_rdata),
        .dbg_lat_frame_ticks  (dbg_lat_frame_ticks),
        .dbg_lat_frame_cycles (dbg_lat_frame_cycles),
        .dbg_lat_pipe_ticks   (dbg_lat_pipe_ticks),
        .dbg_lat_pipe_cycles  (dbg_lat_pipe_cycles),
        .dbg_err              (dbg_err)
    );

    // ---------------- output checks ----------------
    reg        de_s1 = 1'b0, de_s2 = 1'b0, de_s3 = 1'b0;
    reg [31:0] hash  = 32'd0;
    integer    delay_errors   = 0;
    integer    checked_pixels = 0;
    integer    i;

    integer out_frame = -1;
    reg     vs_out_d = 1'b0;
    reg     cap_done = 1'b0;

    // The window opens on the first active output pixel of the last streamed
    // frame; gt is the testbench cycle counter, so the boundary is independent
    // of the output pipeline latency.
    wire cap_window = (gt > (TB_FRAMES * FRAME_CYCLES));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            de_s1 <= 1'b0; de_s2 <= 1'b0; de_s3 <= 1'b0;
            hash  <= 32'd0;
            vs_out_d  <= 1'b0;
            out_frame <= -1;
            cap_done  <= 1'b0;
        end else begin
            de_s1 <= de_gen;
            de_s2 <= de_s1;
            de_s3 <= de_s2;
            vs_out_d <= vs_out;
            if (vs_out & ~vs_out_d) out_frame <= out_frame + 1;
            if (gt > 4) begin
                if (de_out !== de_s3) delay_errors = delay_errors + 1;
            end
            // exactly one complete frame, so the hash is aligned with the model
            if (de_out && cap_window && !cap_done) begin
                hash <= (hash * 33) + rgb_out;
                checked_pixels = checked_pixels + 1;
                if (checked_pixels == (TB_H * TB_V)) cap_done <= 1'b1;
            end
        end
    end

    // ---------------- stimulus ----------------
    integer errors = 0;

    initial begin
        rst_n = 1'b0;
        @(negedge clk); @(negedge clk);
        rst_n = 1'b1;
        gt = 0;
        while (gt < TOTAL_CYCLES) begin
            @(posedge clk);
            raster_step;

        end
        @(posedge clk);
        #2;

        $display("LATF %0d %0d", dbg_lat_frame_ticks, dbg_lat_frame_cycles);
        $display("LATP %0d %0d", dbg_lat_pipe_ticks, dbg_lat_pipe_cycles);
        $display("ERR %0d", dbg_err);
        $display("CHECKED_PIXELS %0d", checked_pixels);
        for (i = 0; i < 48; i = i + 1) begin
            dbg_raddr = i[5:0];
            #1;
            $display("CHAR %0d %0d", i, dbg_rdata);
        end
        $display("HASH %08x", hash);
        $display("DELAY_ERRORS %0d", delay_errors);
        $display("TB_ERRORS %0d", errors + delay_errors);
        $finish;
    end

    initial begin
        #200000000;   // 10 M cycles: enough for one 1280x720 frame
        $display("TB_ERRORS 1");
        $display("HASH 00000000");
        $finish;
    end

endmodule
