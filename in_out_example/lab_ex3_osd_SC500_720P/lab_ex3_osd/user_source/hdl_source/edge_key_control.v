`timescale 1ns / 1ps
// Active-low board keys. All counters run on the existing 24 MHz clock.
module edge_key_event #(
    parameter integer DEBOUNCE_CYCLES = 480000,
    parameter integer LONG_CYCLES = 16800000
)(
    input clk, input rst_n, input key_n,
    output reg press, output reg short_release, output reg long_press
);
    localparam DB_BITS = (DEBOUNCE_CYCLES > 1) ? $clog2(DEBOUNCE_CYCLES) : 1;
    localparam LP_BITS = (LONG_CYCLES > 1) ? $clog2(LONG_CYCLES) : 1;
    (* async_reg = "true" *) reg key_meta, key_sync;
    reg stable_n, long_fired;
    reg [DB_BITS-1:0] db_count;
    reg [LP_BITS-1:0] held_count;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            key_meta <= 1; key_sync <= 1; stable_n <= 1;
            db_count <= 0; held_count <= 0; long_fired <= 0;
            press <= 0; short_release <= 0; long_press <= 0;
        end else begin
            key_meta <= key_n; key_sync <= key_meta;
            press <= 0; short_release <= 0; long_press <= 0;
            if (key_sync == stable_n) db_count <= 0;
            else if (db_count == DEBOUNCE_CYCLES-1) begin
                db_count <= 0; stable_n <= key_sync;
                held_count <= 0;
                if (!key_sync) begin
                    press <= 1; long_fired <= 0;
                end else begin
                    short_release <= !long_fired;
                    long_fired <= 0;
                end
            end else db_count <= db_count + 1'b1;

            // A debounced release has priority over the long-press timer.
            if (!stable_n && !(key_sync && db_count == DEBOUNCE_CYCLES-1)) begin
                if (!long_fired) begin
                    if (held_count == LONG_CYCLES-1) begin
                        long_press <= 1; long_fired <= 1;
                    end else held_count <= held_count + 1'b1;
                end
            end else held_count <= 0;
        end
    end
endmodule

module edge_key_control #(
    parameter integer DEBOUNCE_CYCLES = 480000,
    parameter integer LONG_CYCLES = 16800000
)(
    input clk, input rst_n, input [1:0] keys_n,
    output reg [17:0] requested_config
);
    localparam [1:0] MODE_ORIGIN = 2'b00;
    localparam [1:0] MODE_GRAY   = 2'b01;
    localparam [1:0] MODE_BINARY = 2'b10;
    localparam [1:0] MODE_EDGE   = 2'b11;
    wire mode_press, threshold_short, threshold_long;
    edge_key_event #(.DEBOUNCE_CYCLES(DEBOUNCE_CYCLES), .LONG_CYCLES(LONG_CYCLES)) u_mode (
        .clk(clk), .rst_n(rst_n), .key_n(keys_n[0]),
        .press(mode_press), .short_release(), .long_press()
    );
    edge_key_event #(.DEBOUNCE_CYCLES(DEBOUNCE_CYCLES), .LONG_CYCLES(LONG_CYCLES)) u_threshold (
        .clk(clk), .rst_n(rst_n), .key_n(keys_n[1]),
        .press(), .short_release(threshold_short), .long_press(threshold_long)
    );
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) requested_config <= {MODE_EDGE,8'd80,8'd130};
        else begin
            // K3 advances EDGE(11) -> ORIGIN(00) -> GRAY(01) -> BINARY(10).
            // A two-bit increment wraps naturally and cannot enter an illegal mode.
            if (mode_press) requested_config[17:16] <= requested_config[17:16] + 2'b01;
            // K4 edits only the threshold belonging to the current mode.
            // ORIGIN and GRAY ignore both short and long events.
            if (threshold_short) begin
                case (requested_config[17:16])
                    MODE_BINARY:
                        requested_config[7:0] <= (requested_config[7:0] > 8'd20)
                            ? requested_config[7:0]-8'd10 : 8'd10;
                    MODE_EDGE:
                        requested_config[15:8] <= (requested_config[15:8] > 8'd20)
                            ? requested_config[15:8]-8'd10 : 8'd10;
                    default: ;
                endcase
            end else if (threshold_long) begin
                case (requested_config[17:16])
                    MODE_BINARY:
                        requested_config[7:0] <= (requested_config[7:0] < 8'd240)
                            ? requested_config[7:0]+8'd10 : 8'd250;
                    MODE_EDGE:
                        requested_config[15:8] <= (requested_config[15:8] < 8'd240)
                            ? requested_config[15:8]+8'd10 : 8'd250;
                    default: ;
                endcase
            end
        end
    end
endmodule
