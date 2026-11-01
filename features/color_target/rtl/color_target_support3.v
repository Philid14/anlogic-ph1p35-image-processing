`timescale 1ns / 1ps
// Independent binary-mask experiment. Not instantiated by the detector/main.
// ENABLE=0: one-clock transparent bypass (default, no row memories).
// ENABLE=1: keep an existing hit iff its zero-padded 3x3 population >= 3.
// Mask bit 3 is the leftmost lane, bit 0 the rightmost. Fixed full raster:
// WIDTH >= 4, WIDTH % 4 == 0, HEIGHT >= 1, coordinates must fit XW/YW.
// Complete frames only, arbitrary valid gaps, no ready, back-to-back allowed.
// Abort poisons a complete frame; truncation requires reset. See SUPPORT3.md.
module color_target_support3 #(
    parameter integer ENABLE = 0,
    parameter integer WIDTH = 1280,
    parameter integer HEIGHT = 720,
    parameter integer XW = 11,
    parameter integer YW = 10
)(
    input clk, input rst_n,
    input I_pixel_valid,
    input [3:0] I_mask,
    input [XW-1:0] I_x0,
    input [YW-1:0] I_y,
    input I_sof, input I_eol, input I_eof,
    input [31:0] I_session_id, input [31:0] I_frame_id,
    input I_frame_abort,
    output reg O_pixel_valid,
    output reg [3:0] O_mask,
    output reg [XW-1:0] O_x0,
    output reg [YW-1:0] O_y,
    output reg O_sof, output reg O_eol, output reg O_eof,
    output reg [31:0] O_session_id, output reg [31:0] O_frame_id,
    output reg O_frame_abort,
    output reg O_protocol_error
);
    function integer clog2;
        input integer n;
        integer v;
        begin v = n - 1; clog2 = 0;
            while (v > 0) begin clog2 = clog2 + 1; v = v >> 1; end
            if (clog2 == 0) clog2 = 1;
        end
    endfunction
    generate if (ENABLE == 0) begin : g_bypass
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                O_pixel_valid <= 0; O_mask <= 0; O_x0 <= 0; O_y <= 0;
                O_sof <= 0; O_eol <= 0; O_eof <= 0;
                O_session_id <= 0; O_frame_id <= 0;
                O_frame_abort <= 0; O_protocol_error <= 0;
            end else begin
                O_pixel_valid <= I_pixel_valid; O_mask <= I_mask;
                O_x0 <= I_x0; O_y <= I_y;
                O_sof <= I_sof; O_eol <= I_eol; O_eof <= I_eof;
                O_session_id <= I_session_id; O_frame_id <= I_frame_id;
                O_frame_abort <= I_frame_abort; O_protocol_error <= 0;
            end
        end
    end else begin : g_support
        localparam integer WORDS = WIDTH / 4;
        localparam integer AW = clog2(WORDS);
        reg [AW-1:0] col;
        reg [YW-1:0] row;
        reg write_bank;
        reg [31:0] session_id, frame_id;
        reg frame_bad;
        wire first = (col == 0 && row == 0);
        wire last_col = (col == WORDS-1);
        wire last_frame = last_col && (row == HEIGHT-1);
        wire [XW-1:0] expected_x = col * 4;
        wire protocol_bad = (I_x0 != expected_x) || (I_y != row) ||
                            (I_sof != first) || (I_eol != last_col) ||
                            (I_eof != last_frame) ||
                            (!first && ((I_session_id != session_id) ||
                                        (I_frame_id != frame_id)));
        wire bad = (first ? 1'b0 : frame_bad) | I_frame_abort | protocol_bad;
        wire [31:0] job_session = first ? I_session_id : session_id;
        wire [31:0] job_frame = first ? I_frame_id : frame_id;

        // Autonomous bottom-row reads begin immediately after the last input.
        // A new first row may write the older bank concurrently. Delay writes
        // by one clock so an old top-row read strictly precedes its overwrite.
        reg flush_active, flush_mid_bank, flush_bad;
        reg [AW-1:0] flush_col;
        reg [31:0] flush_session, flush_frame;
        wire normal_read = I_pixel_valid && (row != 0);
        wire read_en = flush_active || normal_read;
        wire [AW-1:0] read_addr = flush_active ? flush_col : col;

        // Do not depend on mixed-port same-address read-before-write: TD's
        // mapped ERAM model can return NEW data. Read requests stay on the
        // current word; writes lag by one clock. For WORDS=1 the most recent
        // center word is forwarded explicitly, independently of RAM behavior.
        reg wr_pending, wr_bank;
        reg [AW-1:0] wr_addr;
        reg [3:0] wr_mask;
        reg [3:0] bank0 [0:WORDS-1];
        reg [3:0] bank1 [0:WORDS-1];
        reg [3:0] q0, q1;
        always @(posedge clk) begin
            if (rst_n && wr_pending && !wr_bank) bank0[wr_addr] <= wr_mask;
            if (rst_n && wr_pending &&  wr_bank) bank1[wr_addr] <= wr_mask;
            if (read_en) begin q0 <= bank0[read_addr]; q1 <= bank1[read_addr]; end
        end

        reg rd_valid, rd_mid_bank, rd_top_zero, rd_bad;
        reg rd_forward0, rd_forward1;
        reg [3:0] rd_forward_mask;
        reg [3:0] rd_bottom;
        reg [XW-1:0] rd_x;
        reg [YW-1:0] rd_y;
        reg [31:0] rd_session, rd_frame;
        wire [3:0] value0 = rd_forward0 ? rd_forward_mask : q0;
        wire [3:0] value1 = rd_forward1 ? rd_forward_mask : q1;
        wire [3:0] top_word = rd_top_zero ? 4'b0 : (rd_mid_bank ? value0 : value1);
        wire [3:0] mid_word = rd_mid_bank ? value1 : value0;

        // One pending word plus three left-edge bits spans lane/beat boundaries.
        // A pending EOL emits with a zero right neighbor, even during a gap.
        reg pending;
        reg [3:0] p_top, p_mid, p_bottom;
        reg [2:0] p_left;
        reg [XW-1:0] p_x;
        reg [YW-1:0] p_y;
        reg [31:0] p_session, p_frame;
        reg p_bad;
        wire p_last = (p_x == WIDTH-4);
        wire emit_word = pending && (p_last || rd_valid);
        wire [5:0] win_top = {p_left[2], p_top, (p_last ? 1'b0 : top_word[3])};
        wire [5:0] win_mid = {p_left[1], p_mid, (p_last ? 1'b0 : mid_word[3])};
        wire [5:0] win_bottom = {p_left[0], p_bottom, (p_last ? 1'b0 : rd_bottom[3])};
        function keep;
            input [5:0] a, b, c;
            input integer pos;
            reg [3:0] n;
            begin
                n = {3'b0,a[pos+1]} + {3'b0,a[pos]} + {3'b0,a[pos-1]} +
                    {3'b0,b[pos+1]} + {3'b0,b[pos]} + {3'b0,b[pos-1]} +
                    {3'b0,c[pos+1]} + {3'b0,c[pos]} + {3'b0,c[pos-1]};
                keep = b[pos] && (n >= 3);
            end
        endfunction
        integer k;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                col <= 0; row <= 0; write_bank <= 0;
                session_id <= 0; frame_id <= 0; frame_bad <= 0;
                flush_active <= 0; flush_col <= 0; flush_mid_bank <= 0;
                flush_bad <= 0; flush_session <= 0; flush_frame <= 0;
                rd_valid <= 0; rd_mid_bank <= 0; rd_top_zero <= 0; rd_bad <= 0;
                rd_forward0 <= 0; rd_forward1 <= 0; rd_forward_mask <= 0;
                wr_pending <= 0; wr_bank <= 0; wr_addr <= 0; wr_mask <= 0;
                rd_bottom <= 0; rd_x <= 0; rd_y <= 0; rd_session <= 0; rd_frame <= 0;
                pending <= 0; p_top <= 0; p_mid <= 0; p_bottom <= 0; p_left <= 0;
                p_x <= 0; p_y <= 0; p_session <= 0; p_frame <= 0; p_bad <= 0;
                O_pixel_valid <= 0; O_mask <= 0; O_x0 <= 0; O_y <= 0;
                O_sof <= 0; O_eol <= 0; O_eof <= 0;
                O_session_id <= 0; O_frame_id <= 0;
                O_frame_abort <= 0; O_protocol_error <= 0;
            end else begin
                wr_pending <= I_pixel_valid;
                if (I_pixel_valid) begin
                    wr_bank <= write_bank; wr_addr <= col; wr_mask <= I_mask;
                end
                if (flush_active) begin
                    if (flush_col == WORDS-1) flush_active <= 0;
                    else flush_col <= flush_col + 1'b1;
                end
                if (I_pixel_valid) begin
                    if (protocol_bad || (normal_read && flush_active)) O_protocol_error <= 1;
                    if (first) begin session_id <= I_session_id; frame_id <= I_frame_id; end
                    frame_bad <= bad;
                    if (last_col) begin
                        col <= 0; write_bank <= ~write_bank;
                        if (row == HEIGHT-1) row <= 0;
                        else row <= row + 1'b1;
                    end else col <= col + 1'b1;
                    if (last_frame) begin
                        flush_active <= 1; flush_col <= 0; flush_mid_bank <= write_bank;
                        flush_session <= job_session; flush_frame <= job_frame; flush_bad <= bad;
                    end
                end

                rd_valid <= read_en;
                if (read_en) begin
                    rd_forward0 <= wr_pending && !wr_bank && (wr_addr == read_addr);
                    rd_forward1 <= wr_pending &&  wr_bank && (wr_addr == read_addr);
                    rd_forward_mask <= wr_mask;
                    rd_mid_bank <= flush_active ? flush_mid_bank : ~write_bank;
                    rd_top_zero <= flush_active ? (HEIGHT == 1) : (row == 1);
                    rd_bottom <= flush_active ? 4'b0 : I_mask;
                    rd_x <= read_addr * 4;
                    rd_y <= flush_active ? HEIGHT-1 : row - 1'b1;
                    rd_session <= flush_active ? flush_session : job_session;
                    rd_frame <= flush_active ? flush_frame : job_frame;
                    rd_bad <= flush_active ? flush_bad : bad;
                end

                O_pixel_valid <= emit_word;
                O_sof <= 0; O_eol <= 0; O_eof <= 0; O_frame_abort <= 0;
                if (emit_word) begin
                    for (k = 0; k < 4; k = k + 1)
                        O_mask[3-k] <= keep(win_top, win_mid, win_bottom, 4-k);
                    O_x0 <= p_x; O_y <= p_y;
                    O_sof <= (p_x == 0 && p_y == 0);
                    O_eol <= p_last; O_eof <= p_last && (p_y == HEIGHT-1);
                    O_session_id <= p_session; O_frame_id <= p_frame;
                    O_frame_abort <= p_bad;
                    pending <= 0;
                end
                if (rd_valid) begin
                    pending <= 1;
                    p_left <= (rd_x == 0) ? 3'b0 : {p_top[0], p_mid[0], p_bottom[0]};
                    p_top <= top_word; p_mid <= mid_word; p_bottom <= rd_bottom;
                    p_x <= rd_x; p_y <= rd_y; p_bad <= rd_bad;
                    p_session <= rd_session; p_frame <= rd_frame;
                end
            end
        end
    end endgenerate
endmodule
