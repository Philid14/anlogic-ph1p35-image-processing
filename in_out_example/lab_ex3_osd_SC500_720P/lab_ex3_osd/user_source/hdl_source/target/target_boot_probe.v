// Diagnostic-only telemetry. Independent of frame admission and metadata reset.
// Neither mailbox drives capture, DDR arbitration, leases, or FrameRef commit.
module target_boot_probe(
    input rst_n,csi_clk,ddr_clk,hdmi_clk,
    input [15:0] csi_events,ddr_events,live_status,
    input [15:0] drops,cancels,faults,
    output reg [95:0] diagnostics
);
    reg [15:0] csi_seen,ddr_seen,csi_sample;
    wire csi_ready,csi_receive,display_ready,display_receive;
    wire [15:0] csi_payload;
    wire [95:0] display_payload;
    always @(posedge csi_clk or negedge rst_n)
        if(!rst_n)csi_seen<=0;else csi_seen<=csi_seen|csi_events;
    always @(posedge ddr_clk or negedge rst_n) begin
        if(!rst_n)begin ddr_seen<=0;csi_sample<=0;end
        else begin
            ddr_seen<=ddr_seen|ddr_events;
            if(csi_receive)csi_sample<=csi_payload;
        end
    end
    frame_bundle_cdc #(.WIDTH(16),.PULSE_PAYLOAD(1)) u_boot_csi(
        .src_clk(csi_clk),.src_rst_n(rst_n),.dst_clk(ddr_clk),.dst_rst_n(rst_n),
        .send(csi_ready),.payload(csi_seen),.ready(csi_ready),.overflow(),.overflow_count(),
        .receive(csi_receive),.received_payload(csi_payload),.src_online(),.dst_online());
    frame_bundle_cdc #(.WIDTH(96),.PULSE_PAYLOAD(1)) u_boot_display(
        .src_clk(ddr_clk),.src_rst_n(rst_n),.dst_clk(hdmi_clk),.dst_rst_n(rst_n),
        .send(display_ready),.payload({csi_sample,ddr_seen,live_status,drops,cancels,faults}),
        .ready(display_ready),.overflow(),.overflow_count(),.receive(display_receive),
        .received_payload(display_payload),.src_online(),.dst_online());
    always @(posedge hdmi_clk or negedge rst_n)
        if(!rst_n)diagnostics<=0;else if(display_receive)diagnostics<=display_payload;
endmodule
