//======================================================================
// tb_latency_meter.v - self checking testbench for work/rtl/latency/latency_meter.v
//
// Stimulus model
//   * ``clk``     : destination (video) clock, half period TB_DEST_HALF ns
//   * ``src_clk`` : source (camera/ISP) clock, half period TB_SRC_HALF ns.
//                   TB_SAME_CLOCK = 1 ties the meter's clk_src to clk.
//   * both resets are released 40 ns in (four falling edges of a 10 ns clk),
//     so destination edge 1 is the first rising edge of clk after that instant
//     and destination cycle k is the interval between edge k and edge k+1.
//     These are the conventions of work/models/latency_osd_model.py, whose
//     TB_RESET_RELEASE_NS constant must stay equal to this instant.
//   * the source token is a periodic one-source-cycle pulse (a frame start in
//     a real system): high during source cycles SRC_FIRST + n*SRC_PERIOD.
//   * out_token is pulsed during the destination cycles listed in the vector
//     file, which also carries the expected lat_ticks / lat_cycles / lat_valid
//     values computed by the Python golden model.
//
// Vector file format (whitespace separated, five integers per line):
//     1 <cycle> <exp_ticks> <exp_cycles> <exp_valid>   pulse out_token, check 2 cycles later
//     2 <cycle> <ovf>       <unf>        <unused>      check the sticky error flags, then clear
//     0 0 0 0 0                                        end of file
//
// The testbench is the behavioural evidence for latency_meter.v. It performs
// no synthesis and makes no hardware claim.
//======================================================================
`timescale 1ns/1ps

module tb_latency_meter;

    parameter integer TB_TICK_BASE      = 10;
    parameter integer TB_TICK_REMAINDER = 50000;
    parameter integer TB_TICK_MOD       = 100000;
    parameter integer TB_SAME_CLOCK     = 1;
    parameter real    TB_DEST_HALF      = 5.0;
    parameter real    TB_SRC_HALF       = 5.0;
    parameter integer TB_SRC_FIRST      = 1;     // first source token cycle
    parameter integer TB_SRC_PERIOD     = 7;     // source token period, cycles
    parameter integer TB_MAX_EVENTS     = 256;

    localparam integer CNT_W  = 32;
    localparam integer TICK_W = 32;
    localparam integer DEPTH_LOG2 = 3;

    reg clk     = 1'b0;
    reg src_clk = 1'b0;

    always #(TB_DEST_HALF) clk     = ~clk;
    always #(TB_SRC_HALF)  src_clk = ~src_clk;

    wire meter_clk_src = TB_SAME_CLOCK ? clk : src_clk;

    reg rst_n     = 1'b0;
    reg rst_src_n = 1'b0;

    reg        src_token = 1'b0;
    reg        out_token = 1'b0;
    reg        err_clr   = 1'b0;

    wire [TICK_W-1:0] lat_ticks;
    wire [CNT_W-1:0]  lat_cycles;
    wire              lat_valid;
    wire              err_ovf;
    wire              err_unf;

    latency_meter #(
        .TICK_BASE      (TB_TICK_BASE),
        .TICK_REMAINDER (TB_TICK_REMAINDER),
        .TICK_MOD       (TB_TICK_MOD),
        .CNT_W          (CNT_W),
        .TICK_W         (TICK_W),
        .DEPTH_LOG2     (DEPTH_LOG2)
    ) dut (
        .clk_src       (meter_clk_src),
        .rst_src_n     (rst_src_n),
        .src_token     (src_token),
        .clk           (clk),
        .rst_n         (rst_n),
        .out_token     (out_token),
        .err_clr       (err_clr),
        .lat_ticks     (lat_ticks),
        .lat_cycles    (lat_cycles),
        .lat_valid     (lat_valid),
        .err_overflow  (err_ovf),
        .err_underflow (err_unf)
    );

    //------------------------------------------------------------------
    // periodic source token, synchronous to the source clock
    //------------------------------------------------------------------
    integer src_cycle_cnt = 0;

    always @(posedge meter_clk_src or negedge rst_src_n) begin
        if (!rst_src_n) begin
            src_cycle_cnt <= 0;
            src_token     <= 1'b0;
        end else begin
            src_cycle_cnt <= src_cycle_cnt + 1;
            // +1: the right hand side is evaluated with the pre-edge counter
            // value, so this makes the token high during source cycles
            // TB_SRC_FIRST + n*TB_SRC_PERIOD exactly as the vector file assumes.
            if (TB_SRC_PERIOD > 0)
                src_token <= (((src_cycle_cnt + 1) % TB_SRC_PERIOD) == (TB_SRC_FIRST % TB_SRC_PERIOD));
            else
                src_token <= 1'b0;
        end
    end

    //------------------------------------------------------------------
    // vector storage
    //------------------------------------------------------------------
    integer ev_kind [0:TB_MAX_EVENTS-1];
    integer ev_a    [0:TB_MAX_EVENTS-1];
    integer ev_b    [0:TB_MAX_EVENTS-1];
    integer ev_c    [0:TB_MAX_EVENTS-1];
    integer ev_d    [0:TB_MAX_EVENTS-1];
    integer ev_n = 0;

    integer errors = 0;
    integer checks = 0;
    integer fd, rc, i, j;
    integer cycle;
    reg [8*260-1:0] vec_path;

    task check_int;
        input [8*24-1:0] label;
        input integer    got;
        input integer    exp;
        begin
            checks = checks + 1;
            if (got !== exp) begin
                errors = errors + 1;
                $display("MISMATCH %0s got=%0d expected=%0d (cycle %0d, time %0t)",
                         label, got, exp, cycle, $time);
            end
        end
    endtask

    initial begin
        if (!$value$plusargs("VECTORS=%s", vec_path)) begin
            $display("TB_ERRORS=1 (missing +VECTORS)");
            $finish;
        end
        fd = $fopen(vec_path, "r");
        if (fd == 0) begin
            $display("TB_ERRORS=1 (cannot open vectors)");
            $finish;
        end
        begin : read_loop
            while (1) begin
                rc = $fscanf(fd, "%d %d %d %d %d\n",
                             ev_kind[ev_n], ev_a[ev_n], ev_b[ev_n], ev_c[ev_n], ev_d[ev_n]);
                if (rc != 5) disable read_loop;
                if (ev_kind[ev_n] == 0) disable read_loop;
                ev_n = ev_n + 1;
                if (ev_n >= TB_MAX_EVENTS) disable read_loop;
            end
        end
        $fclose(fd);
        $display("TB_INFO events=%0d same_clock=%0d tick=(%0d + %0d/%0d) src_period=%0d",
                 ev_n, TB_SAME_CLOCK, TB_TICK_BASE, TB_TICK_REMAINDER, TB_TICK_MOD, TB_SRC_PERIOD);

        // ---------------- reset ----------------
        // released 40 ns in (four falling edges of clk); the golden model mirrors
        // this instant through latency_osd_model.TB_RESET_RELEASE_NS
        rst_n = 1'b0; rst_src_n = 1'b0;
        @(negedge clk); @(negedge clk); @(negedge clk);
        @(negedge clk);
        rst_n = 1'b1; rst_src_n = 1'b1;
        cycle = 0;

        // ---------------- run the event list ----------------
        for (i = 0; i < ev_n; i = i + 1) begin
            while (cycle < ev_a[i]) begin
                @(posedge clk);
                cycle = cycle + 1;
            end
            case (ev_kind[i])
                1: begin // out_token pulse + latency check
                    // high across exactly one rising edge: applied 1 ns after the
                    // current edge, cleared 1 ns after the next one. This removes
                    // the driver race and guarantees a single pop.
                    #1 out_token = 1'b1;
                    @(posedge clk); cycle = cycle + 1;
                    #1 out_token = 1'b0;
                    @(posedge clk); cycle = cycle + 1;
                    #1;
                    check_int("lat_ticks ", lat_ticks,  ev_b[i]);
                    check_int("lat_cycles", lat_cycles, ev_c[i]);
                    check_int("lat_valid ", lat_valid,  ev_d[i]);
                end
                2: begin // sticky error flags
                    check_int("err_overflow ", err_ovf, ev_b[i]);
                    check_int("err_underflow", err_unf, ev_c[i]);
                    err_clr = 1'b1;
                    @(posedge clk); cycle = cycle + 1;
                    err_clr = 1'b0;
                    #1;
                end
                default: begin
                end
            endcase
        end

        $display("TB_CHECKS=%0d", checks);
        $display("TB_ERRORS=%0d", errors);
        $finish;
    end

    // safety net: never let a broken stimulus hang the simulation
    initial begin
        #2000000;
        $display("TB_ERRORS=%0d (timeout)", errors + 1);
        $finish;
    end

endmodule
