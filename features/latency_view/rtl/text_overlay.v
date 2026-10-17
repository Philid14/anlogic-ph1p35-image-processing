//======================================================================
// text_overlay.v - streaming character OSD panel (no frame buffer)
//
// Part of the "latency measurement and on-screen display" deliverable.
// Signal contract: docs/architecture/latency-osd-interface.md
//
// Function
//   Draws a COLS x ROWS character panel at (X0, Y0) on top of the incoming
//   pixel stream. Characters come from an internal single-clock character RAM
//   that the formatter writes through the (we, waddr, wdata) port; glyph
//   bitmaps come from the generated char_rom. Panel background is either a
//   solid colour (BG_DIM = 0) or the incoming video at half brightness
//   (BG_DIM = 1) so the text stays readable without hiding the image.
//
// Geometry
//   pixel coordinate counters are derived from de/hs/vs inside this module, so
//   the overlay does not depend on the upstream pipeline exporting x/y. Cells
//   are 8x8 pixels scaled by 2**SCALE_LOG2 (integer scale, shift only).
//   Pixel (x, y) is inside the panel when
//       X0 <= x < X0 + COLS*8*2**SCALE_LOG2  and  Y0 <= y < Y0 + ROWS*8*2**SCALE_LOG2
//
// Latency and alignment
//   The panel costs exactly THREE clk cycles of fixed latency: rgb/de/hs/vs
//   are delayed by three registers and the glyph decision is aligned with the
//   third one. Every pixel, valid flag and sync signal of the whole stream is
//   delayed by the same three cycles, so no downstream consumer sees skew.
//   This is a pure line-rate pipeline: no BRAM frame buffer, no DDR, and the
//   three cycles must be added to the end-to-end latency budget.
//
// Frame boundary rule
//   The character RAM must only be written while de is low. latency_osd.v
//   enforces that by stalling its formatter during active video; doing so
//   guarantees that a displayed frame can never mix two text revisions.
//
// Verification level
//   Behavioural simulation only (work/tests/tb_text_overlay.v). No TD build,
//   no board measurement.
//======================================================================
`timescale 1ns/1ps

module text_overlay #(
    parameter integer H_ACTIVE   = 1280,
    parameter integer V_ACTIVE   = 720,
    parameter integer COLS       = 16,          // characters per row
    parameter integer ROWS       = 3,           // text rows
    parameter integer ADDR_W     = 6,           // character RAM address width
    parameter integer X0         = 24,
    parameter integer Y0         = 24,
    parameter integer SCALE_LOG2 = 1,           // 0 -> 1x, 1 -> 2x, 2 -> 4x
    parameter integer PANEL_EN   = 1,           // 1 -> draw the background panel
    parameter integer BG_DIM     = 1,           // 1 -> dim video, 0 -> solid BG_RGB
    parameter [23:0]  FG_RGB     = 24'hFFFFFF,  // glyph colour
    parameter [23:0]  BG_RGB     = 24'h000000   // solid panel colour
) (
    input  wire              clk,
    input  wire              rst_n,
    // video stream in
    input  wire              de,
    input  wire              hs,
    input  wire              vs,
    input  wire [23:0]       rgb_in,
    // character RAM write port (only while de is low)
    input  wire              we,
    input  wire [ADDR_W-1:0] waddr,
    input  wire [7:0]        wdata,
    // asynchronous read port, for testbench observability only
    input  wire [ADDR_W-1:0] dbg_raddr,
    output wire [7:0]        dbg_rdata,
    // video stream out, delayed by exactly 3 clk cycles
    output reg  [23:0]       rgb_out,
    output reg               de_out,
    output reg               hs_out,
    output reg               vs_out
);
    localparam integer CELL   = (8 << SCALE_LOG2);          // cell size in pixels
    localparam integer MEM    = (1 << ADDR_W);              // character RAM depth
    localparam integer SHIFT  = (3 + SCALE_LOG2);           // cell index shift
    localparam [11:0]  X0_Q   = X0[11:0];
    localparam [11:0]  Y0_Q   = Y0[11:0];
    localparam [11:0]  X1_Q   = (X0 + COLS * CELL);
    localparam [11:0]  Y1_Q   = (Y0 + ROWS * CELL);

    //------------------------------------------------------------------
    // character RAM
    //------------------------------------------------------------------
    reg [7:0] char_mem [0:MEM-1];

    always @(posedge clk) begin
        if (we) char_mem[waddr] <= wdata;
    end

    assign dbg_rdata = char_mem[dbg_raddr];

    //------------------------------------------------------------------
    // pixel coordinate counters, derived from de only
    //------------------------------------------------------------------
    reg [11:0] x, y;

    // Coordinates are realigned by the frame/line sync, not only accumulated
    // from de (review item 3.4): a lost or delayed de burst can no longer
    // shift the panel for the rest of the frame.
    reg hs_d, vs_d;
    wire hs_rise = hs & ~hs_d;
    wire vs_rise = vs & ~vs_d;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            x <= 12'd0;
            y <= 12'd0;
            hs_d <= 1'b0;
            vs_d <= 1'b0;
        end else begin
            hs_d <= hs;
            vs_d <= vs;
            if (vs_rise) begin              // frame start: origin
                x <= 12'd0;
                y <= 12'd0;
            end else if (hs_rise) begin     // line start: column origin
                x <= 12'd0;
            end else if (de) begin
                if (x == (H_ACTIVE[11:0] - 12'd1)) begin
                    x <= 12'd0;
                    y <= (y == (V_ACTIVE[11:0] - 12'd1)) ? 12'd0 : (y + 12'd1);
                end else begin
                    x <= x + 12'd1;
                end
            end
        end
    end

    //------------------------------------------------------------------
    // stage 0: region test and character cell decode
    //------------------------------------------------------------------
    wire              in_region = (x >= X0_Q) && (x < X1_Q) && (y >= Y0_Q) && (y < Y1_Q);
    wire [11:0]       bx        = x - X0_Q;
    wire [11:0]       by        = y - Y0_Q;
    wire [11:0]       cx        = bx >> SHIFT;
    wire [11:0]       cy        = by >> SHIFT;
    wire [2:0]        col       = bx[SHIFT-1:SCALE_LOG2];
    wire [2:0]        row       = by[SHIFT-1:SCALE_LOG2];
    wire [ADDR_W-1:0] raddr     = (cy * COLS + cx);

    //------------------------------------------------------------------
    // stage 1: character data (registered read, absorbs the cell decode)
    //------------------------------------------------------------------
    reg        in_region_r;
    reg [2:0]  row_r;
    reg [2:0]  col_r;
    reg [7:0]  cdata;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            in_region_r <= 1'b0;
            row_r       <= 3'd0;
            col_r       <= 3'd0;
            cdata       <= 8'h20;                 // blank
        end else begin
            in_region_r <= in_region;
            row_r       <= row;
            col_r       <= col;
            cdata       <= in_region ? char_mem[raddr] : 8'h20;
        end
    end

    //------------------------------------------------------------------
    // stage 2: glyph bits and the blend decision
    //------------------------------------------------------------------
    wire [7:0] glyph_bits;

    char_rom u_char_rom (
        .char_code (cdata[6:0]),
        .row       (row_r),
        .bits      (glyph_bits)
    );

    reg sel_r;
    reg panel_r;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sel_r   <= 1'b0;
            panel_r <= 1'b0;
        end else begin
            sel_r   <= in_region_r & glyph_bits[col_r];
            panel_r <= in_region_r & PANEL_EN[0];
        end
    end

    //------------------------------------------------------------------
    // stage 3: matching delay line for the video and the sync signals
    //------------------------------------------------------------------
    reg [23:0] rgb_d1, rgb_d2;
    reg        de_d1, de_d2, hs_d1, hs_d2, vs_d1, vs_d2;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rgb_d1 <= 24'd0; rgb_d2 <= 24'd0;
            de_d1  <= 1'b0;  de_d2  <= 1'b0;
            hs_d1  <= 1'b0;  hs_d2  <= 1'b0;
            vs_d1  <= 1'b0;  vs_d2  <= 1'b0;
        end else begin
            rgb_d1 <= rgb_in; rgb_d2 <= rgb_d1;
            de_d1  <= de;     de_d2  <= de_d1;
            hs_d1  <= hs;     hs_d2  <= hs_d1;
            vs_d1  <= vs;     vs_d2  <= vs_d1;
        end
    end

    // half brightness of the delayed video keeps the panel readable without
    // a multiplier: each channel simply loses its least significant bit.
    wire [23:0] dim_rgb = {1'b0, rgb_d2[23:17], 1'b0, rgb_d2[15:9], 1'b0, rgb_d2[7:1]};

    wire [23:0] panel_rgb = BG_DIM[0] ? dim_rgb : BG_RGB;
    wire [23:0] blend_rgb = sel_r ? FG_RGB : (panel_r ? panel_rgb : rgb_d2);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rgb_out <= 24'd0;
            de_out  <= 1'b0;
            hs_out  <= 1'b0;
            vs_out  <= 1'b0;
        end else begin
            rgb_out <= blend_rgb;
            de_out  <= de_d2;
            hs_out  <= hs_d2;
            vs_out  <= vs_d2;
        end
    end

endmodule
