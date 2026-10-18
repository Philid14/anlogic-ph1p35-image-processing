`timescale 1ns / 1ps
// Runtime ORIGIN/EDGE, with matched Original delay and frame configuration.
// SOF is the existing AWB early notification; it need not coincide with valid.
module edge_control_stream #(
    parameter integer IMG_WIDTH = 1280,
    parameter integer IMG_HEIGHT = 720,
    parameter integer OSD_ENABLE = 1,
    parameter integer DENOISE_ENABLE = 0,
    parameter integer NMS_ENABLE = 0,
    parameter integer QUALITY_ENABLE = 0,
    parameter integer QUALITY_HOPS = 4,
    parameter integer TEMPORAL_ENABLE = 0,
    parameter integer RELIABILITY_ENABLE = 0
)(
    input clk, input rst_n,
    input [8:0] requested_config,
    input [31:0] I_fifo_event_counts,
    input [95:0] I_data, input I_valid, input I_user, input I_last,
    output [95:0] O_data, output O_valid, output O_user, output O_last,
    output I_ready, input O_ready
);
    localparam SPATIAL_STAGES = (DENOISE_ENABLE ? 9 : 5) + (NMS_ENABLE ? 4 : 0)
        + ((QUALITY_ENABLE && NMS_ENABLE) ? 3*QUALITY_HOPS : 0);
    localparam HOLD_ENABLE=TEMPORAL_ENABLE && QUALITY_ENABLE && NMS_ENABLE;
    localparam EDGE_STAGES=SPATIAL_STAGES+(HOLD_ENABLE?2:0);
    reg [8:0] active_config;
    wire [8:0] beat_config = I_user ? requested_config : active_config;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) active_config <= {1'b1,8'd80};
        else if (I_user) active_config <= requested_config;
    end
    reg [95:0] original_p [0:EDGE_STAGES-1];
    reg [8:0] config_p [0:EDGE_STAGES-1];
    reg [EDGE_STAGES-1:0] valid_p, user_p, last_p;
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_p <= 0; user_p <= 0; last_p <= 0;
            for (i=0; i<EDGE_STAGES; i=i+1) begin
                original_p[i] <= 0; config_p[i] <= {1'b1,8'd80};
            end
        end else begin
            original_p[0] <= I_data; config_p[0] <= beat_config;
            for (i=1; i<EDGE_STAGES; i=i+1) begin
                original_p[i] <= original_p[i-1]; config_p[i] <= config_p[i-1];
            end
            valid_p <= {valid_p[EDGE_STAGES-2:0],I_valid};
            user_p <= {user_p[EDGE_STAGES-2:0],I_user};
            last_p <= {last_p[EDGE_STAGES-2:0],I_last};
        end
    end
    wire [95:0] edge_data,stable_edge_data;
    wire [1:0] edge_support;
    edge_detect_96 #(.IMG_WIDTH(IMG_WIDTH), .IMG_HEIGHT(IMG_HEIGHT),
                     .RUNTIME_THRESHOLD(1), .DENOISE_ENABLE(DENOISE_ENABLE), .NMS_ENABLE(NMS_ENABLE), .QUALITY_ENABLE(QUALITY_ENABLE), .QUALITY_HOPS(QUALITY_HOPS),.TEMPORAL_ENABLE(HOLD_ENABLE)) u_edge (
        .I_clk(clk), .I_rst_n(rst_n), .I_tdata(I_data), .I_tvalid(I_valid),
        .I_tuser(I_user), .I_tlast(I_last), .I_threshold(beat_config[7:0]),
        .I_tready(I_ready), .O_tready(O_ready), .O_tdata(edge_data),
        .O_tvalid(), .O_tuser(), .O_tlast(),.O_temporal_support(edge_support)
    );
    generate if(HOLD_ENABLE)begin:g_temporal
        wire[1:0] bits_out;
        edge_temporal_hold #(.IMG_WIDTH(IMG_WIDTH),.IMG_HEIGHT(IMG_HEIGHT)) u_hold(
            .clk(clk),.rst_n(rst_n),.I_edge({edge_data[95],edge_data[47]}),.I_support(edge_support),
            .I_valid(valid_p[SPATIAL_STAGES-1]),.I_user(user_p[SPATIAL_STAGES-1]),.I_last(last_p[SPATIAL_STAGES-1]),
            .I_threshold(config_p[SPATIAL_STAGES-1][7:0]),.O_edge(bits_out),.O_valid(),.O_user(),.O_last());
        assign stable_edge_data={{48{bits_out[1]}},{48{bits_out[0]}}};
    end else begin:g_spatial assign stable_edge_data=edge_data;end endgenerate
    wire [95:0] selected_data = config_p[EDGE_STAGES-1][8] ? stable_edge_data : original_p[EDGE_STAGES-1];
    edge_status_osd #(.IMG_WIDTH(IMG_WIDTH), .IMG_HEIGHT(IMG_HEIGHT),
                     .ENABLE(OSD_ENABLE),.RELIABILITY_ENABLE(RELIABILITY_ENABLE)) u_status (
        .clk(clk), .rst_n(rst_n), .I_data(selected_data),
        .I_valid(valid_p[EDGE_STAGES-1]), .I_user(user_p[EDGE_STAGES-1]), .I_last(last_p[EDGE_STAGES-1]),
        .I_config(config_p[EDGE_STAGES-1]), .I_fifo_event_counts(I_fifo_event_counts), .O_data(O_data), .O_valid(O_valid),
        .O_user(O_user), .O_last(O_last)
    );
endmodule
