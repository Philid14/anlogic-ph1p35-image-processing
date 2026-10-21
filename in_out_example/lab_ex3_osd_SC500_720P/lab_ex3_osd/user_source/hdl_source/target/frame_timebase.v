// Common 64-bit reference: configured 75 MHz HDMI /75 = nominal 1 MHz.
// Whole snapshots travel in held-bundle mailboxes; there is no per-bit sampling
// of a running binary counter. Age at actual HDMI output uses master_tick.
// Receivers are conservative timestamp quantizers, not frequency measurements.
module frame_timebase(
    input rst_n, input hdmi_clk, csi_clk, ddr_clk,
    output reg [63:0] master_tick,
    output wire [63:0] csi_tick, ddr_tick,
    output wire csi_valid, ddr_valid
);
    reg [6:0] divide;
    wire csi_ready,ddr_ready,csi_receive,ddr_receive;
    reg csi_seen,ddr_seen;
    reg [10:0] csi_silence,ddr_silence;
    always @(posedge hdmi_clk or negedge rst_n) begin
        if(!rst_n) begin master_tick<=0; divide<=0; end
        else if(divide==74) begin divide<=0; master_tick<=master_tick+1'b1; end
        else divide<=divide+1'b1;
    end
    frame_bundle_cdc #(.WIDTH(64)) u_time_csi(
        .src_clk(hdmi_clk),.src_rst_n(rst_n),.dst_clk(csi_clk),.dst_rst_n(rst_n),
        .send(csi_ready),.payload(master_tick),.ready(csi_ready),.overflow(),.overflow_count(),
        .receive(csi_receive),.received_payload(csi_tick),.src_online(),.dst_online());
    frame_bundle_cdc #(.WIDTH(64)) u_time_ddr(
        .src_clk(hdmi_clk),.src_rst_n(rst_n),.dst_clk(ddr_clk),.dst_rst_n(rst_n),
        .send(ddr_ready),.payload(master_tick),.ready(ddr_ready),.overflow(),.overflow_count(),
        .receive(ddr_receive),.received_payload(ddr_tick),.src_online(),.dst_online());
    always @(posedge csi_clk or negedge rst_n) begin
        if(!rst_n) begin csi_seen<=0; csi_silence<=2047; end
        else if(csi_receive) begin csi_seen<=1; csi_silence<=0; end
        else if(!(&csi_silence)) csi_silence<=csi_silence+1'b1;
    end
    always @(posedge ddr_clk or negedge rst_n) begin
        if(!rst_n) begin ddr_seen<=0; ddr_silence<=2047; end
        else if(ddr_receive) begin ddr_seen<=1; ddr_silence<=0; end
        else if(!(&ddr_silence)) ddr_silence<=ddr_silence+1'b1;
    end
    assign csi_valid=csi_seen && !csi_silence[10];
    assign ddr_valid=ddr_seen && !ddr_silence[10];
endmodule
