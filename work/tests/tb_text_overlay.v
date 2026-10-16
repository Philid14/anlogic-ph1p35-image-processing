//======================================================================
// tb_text_overlay.v - self checking testbench for work/rtl/osd/text_overlay.v
//
// The testbench generates a synthetic raster stream (de/hs/vs plus a
// deterministic RGB pattern), programs the overlay character RAM during
// blanking and checks three things:
//   1. de_out equals de delayed by exactly the documented three cycles;
//   2. a 32-bit running hash of every active output pixel equals the value
//      computed by work/models/latency_osd_model.py;
//   3. every pixel of the first text row is printed as "PIX <x> <rgb>" so the
//      glyph bitmaps themselves are compared, not only an aggregate.
//
// Vector file (five integers per line, terminated by a zero line):
//   1 <c0> <c1> <c2> <c3> <0>          characters written into the panel
//   2 <hash_hi16> <hash_lo16> <0> <0>  expected output hash
//   0 0 0 0 0
//
// Behavioural evidence only: no synthesis, no board claim.
//======================================================================
`timescale 1ns/1ps

module tb_text_overlay;

    parameter integer TB_H          = 64;    // active pixels per line
    parameter integer TB_V          = 32;    // active lines per frame
    parameter integer TB_HT         = 84;    // total pixels per line
    parameter integer TB_VT         = 42;    // total lines per frame
    parameter integer TB_FRAMES     = 2;     // whole frames streamed after programming
    parameter integer TB_COLS       = 4;
    parameter integer TB_ROWS       = 1;
    parameter integer TB_X0         = 8;
    parameter integer TB_Y0         = 8;
    parameter integer TB_SCALE_LOG2 = 1;
    parameter integer TB_ADDR_W     = 3;
    parameter integer TB_PANEL_EN   = 1;
    parameter integer TB_BG_DIM     = 1;
    parameter        TB_FG_RGB      = 24'hFFFFFF;
    parameter        TB_BG_RGB      = 24'h000000;
    parameter real    TB_CLK_HALF   = 5.0;

    localparam integer CELL = (8 << TB_SCALE_LOG2);

    reg clk = 1'b0;
    always #(TB_CLK_HALF) clk = ~clk;

    reg rst_n = 1'b0;

    // ---------------- raster generator ----------------
    integer    gt    = 0;
    integer    bsum  = 0;
    integer    lfrac = 0;
    integer    line  = 0;
    integer    col   = 0;
    reg        vs_gen = 1'b0;
    reg        hs_gen = 1'b0;
    reg        de_gen = 1'b0;
    reg [23:0] rgb_gen = 24'd0;

    task raster_step;
        begin
            gt     = gt + 1;
            line   = (gt - 1) / TB_HT;
            col    = (gt - 1) % TB_HT;
            vs_gen = ((line % TB_VT) < 2);
            hs_gen = (col >= TB_H) && (col < TB_H + 4);
            de_gen = (((line % TB_VT) < TB_V) && (col < TB_H));
            lfrac   = line % TB_VT;          // frame local line index
            bsum    = (col + lfrac) & 255;   // low byte, no width surprise
            rgb_gen = {col[7:0], lfrac[7:0], bsum[7:0]};
        end
    endtask

    // ---------------- DUT ----------------
    reg                  we    = 1'b0;
    reg  [TB_ADDR_W-1:0] waddr = 0;
    reg  [7:0]           wdata = 8'h20;
    reg  [TB_ADDR_W-1:0] dbg_raddr = 0;

    wire [7:0]  dbg_rdata;
    wire [23:0] rgb_out;
    wire        de_out, hs_out, vs_out;

    text_overlay #(
        .H_ACTIVE   (TB_H),
        .V_ACTIVE   (TB_V),
        .COLS       (TB_COLS),
        .ROWS       (TB_ROWS),
        .ADDR_W     (TB_ADDR_W),
        .X0         (TB_X0),
        .Y0         (TB_Y0),
        .SCALE_LOG2 (TB_SCALE_LOG2),
        .PANEL_EN   (TB_PANEL_EN),
        .BG_DIM     (TB_BG_DIM),
        .FG_RGB     (TB_FG_RGB),
        .BG_RGB     (TB_BG_RGB)
    ) dut (
        .clk       (clk),
        .rst_n     (rst_n),
        .de        (de_gen),
        .hs        (hs_gen),
        .vs        (vs_gen),
        .rgb_in    (rgb_gen),
        .we        (we),
        .waddr     (waddr),
        .wdata     (wdata),
        .dbg_raddr (dbg_raddr),
        .dbg_rdata (dbg_rdata),
        .rgb_out   (rgb_out),
        .de_out    (de_out),
        .hs_out    (hs_out),
        .vs_out    (vs_out)
    );

    // ---------------- output checks ----------------
    reg        de_s1 = 1'b0, de_s2 = 1'b0, de_s3 = 1'b0;
    reg [31:0] hash  = 32'd0;
    reg        hash_enable = 1'b0;
    integer    delay_errors   = 0;
    integer    checked_pixels = 0;
    integer    row0_pixels    = 0;
    integer    out_x = 0, out_y = 0;
    integer    row0_done = 0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            de_s1 <= 1'b0; de_s2 <= 1'b0; de_s3 <= 1'b0;
            hash  <= 32'd0;
        end else begin
            de_s1 <= de_gen;
            de_s2 <= de_s1;
            de_s3 <= de_s2;
            if (gt > 4) begin
                if (de_out !== de_s3) delay_errors = delay_errors + 1;
            end
            if (de_out && hash_enable) begin
                hash <= (hash * 33) + rgb_out;
                checked_pixels = checked_pixels + 1;
                if ((row0_done == 0) && (out_y == TB_Y0) &&
                    (out_x >= TB_X0) && (out_x < TB_X0 + TB_COLS * CELL)) begin
                    $display("PIX %0d %0d", out_x - TB_X0, rgb_out);
                    row0_pixels = row0_pixels + 1;
                    if (out_x == TB_X0 + TB_COLS * CELL - 1) row0_done = 1;
                end
            end
            if (de_out && hash_enable) begin
                if (out_x == TB_H - 1) begin
                    out_x <= 0;
                    out_y <= (out_y == TB_V - 1) ? 0 : (out_y + 1);
                end else begin
                    out_x <= out_x + 1;
                end
            end
        end
    end

    // ---------------- stimulus ----------------
    integer fd, rc, k;
    integer ev_kind [0:15];
    integer ev_a    [0:15];
    integer ev_b    [0:15];
    integer ev_c    [0:15];
    integer ev_d    [0:15];
    integer ev_n = 0;
    integer errors = 0;
    reg [8*260-1:0] vec_path;
    reg [31:0]      exp_hash;
    integer         total_cycles;

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
                if (ev_n >= 16) disable read_loop;
            end
        end
        $fclose(fd);

        exp_hash = {ev_a[1][15:0], ev_b[1][15:0]};

        rst_n = 1'b0;
        @(negedge clk); @(negedge clk);
        rst_n = 1'b1;
        gt = 0;

        // wait for the first vertical blanking region, then program the panel
        while ((line % TB_VT) < TB_V) begin
            @(posedge clk);
            raster_step;
        end
        for (k = 0; k < TB_COLS * TB_ROWS; k = k + 1) begin
            we    = 1'b1;
            waddr = k[TB_ADDR_W-1:0];
            // the four characters sit in the four value fields of record 1
            case (k)
                0:       wdata = ev_a[0];
                1:       wdata = ev_b[0];
                2:       wdata = ev_c[0];
                3:       wdata = ev_d[0];
                default: wdata = 8'h20;
            endcase
            @(posedge clk);
            raster_step;
        end
        we    = 1'b0;
        waddr = 0;
        wdata = 8'h20;
        // wait out the pipeline before counting: only the frames that show the
        // fully programmed panel contribute to the hash
        for (k = 0; k < 8; k = k + 1) begin
            @(posedge clk);
            raster_step;
        end
        hash_enable = 1'b1;

        // stream whole frames with a frozen panel
        total_cycles = TB_HT * TB_VT * (TB_FRAMES + 1);
        while (gt < total_cycles) begin
            @(posedge clk);
            raster_step;
        end
        #2;
        $display("TB_CHECKED_PIXELS=%0d", checked_pixels);
        $display("TB_ROW0_PIXELS=%0d", row0_pixels);
        $display("TB_HASH=%08x EXPECTED=%08x", hash, exp_hash);
        $display("TB_DELAY_ERRORS=%0d", delay_errors);
        if (hash !== exp_hash) errors = errors + 1;
        $display("TB_ERRORS=%0d", errors + delay_errors + ((ev_n < 2) ? 1 : 0));
        $finish;
    end

    initial begin
        #200000000;   // 10 M cycles: enough for one 1280x720 frame
        $display("TB_ERRORS=1 (timeout)");
        $finish;
    end

endmodule
