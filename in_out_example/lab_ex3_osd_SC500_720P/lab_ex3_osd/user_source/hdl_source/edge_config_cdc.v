`timescale 1ns / 1ps
// Bundled-data mailbox. Data is held from request launch until returned ACK.
// Three destination request flops allow the bus to settle before capture.
// Requests during a transfer are coalesced to the latest complete config.
module edge_config_cdc (
    input src_clk, input dst_clk, input rst_n,
    input [18:0] requested_config,
    output reg [18:0] received_config
);
    localparam [18:0] RESET_CONFIG = {3'd3,8'd80,8'd130};
    reg [18:0] held_config;
    reg req_toggle, ack_toggle;
    (* async_reg = "true" *) reg ack_meta, ack_sync;
    (* async_reg = "true" *) reg req_meta, req_sync, req_guard;
    always @(posedge src_clk or negedge rst_n) begin
        if (!rst_n) begin
            held_config <= RESET_CONFIG; req_toggle <= 0;
            ack_meta <= 0; ack_sync <= 0;
        end else begin
            ack_meta <= ack_toggle; ack_sync <= ack_meta;
            if (req_toggle == ack_sync && requested_config != held_config) begin
                held_config <= requested_config;
                req_toggle <= !req_toggle;
            end
        end
    end
    always @(posedge dst_clk or negedge rst_n) begin
        if (!rst_n) begin
            req_meta <= 0; req_sync <= 0; req_guard <= 0;
            ack_toggle <= 0; received_config <= RESET_CONFIG;
        end else begin
            req_meta <= req_toggle; req_sync <= req_meta; req_guard <= req_sync;
            if (req_guard != ack_toggle) begin
                received_config <= held_config;
                ack_toggle <= req_guard;
            end
        end
    end
endmodule
