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
    parameter integer PROBE_ENABLE = 0
)(
    input clk, input rst_n,
    input [8:0] requested_config,
    input I_probe_pack_valid,I_probe_pack_user,
    input [1:0] I_probe_fifo_sticky,
    input [1:0] I_probe_fifo_armed,
    input [95:0] I_data, input I_valid, input I_user, input I_last,
    output [95:0] O_data, output O_valid, output O_user, output O_last,
    output I_ready, input O_ready
);
    localparam EDGE_STAGES = (DENOISE_ENABLE ? 9 : 5) + (NMS_ENABLE ? 4 : 0)
        + ((QUALITY_ENABLE && NMS_ENABLE) ? 3*QUALITY_HOPS : 0);
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
    wire [95:0] edge_data;
    wire [95:0] edge_input;
    wire probe_ev,probe_eu;
    wire [319:0] probe_panel;
    generate if(PROBE_ENABLE)begin:g_probe
        probe_fixed_rgb #(.IMG_WIDTH(IMG_WIDTH),.IMG_HEIGHT(IMG_HEIGHT)) u_pattern(
            .clk(clk),.rst_n(rst_n),.v(I_valid),.u(I_user),.rgb(edge_input));
        probe_stream_monitor #(.IMG_WIDTH(IMG_WIDTH),.IMG_HEIGHT(IMG_HEIGHT)) u_monitor(
            .clk(clk),.rst_n(rst_n),.iv(I_valid),.iu(I_user),.il(I_last),
            .ev(probe_ev),.eu(probe_eu),.edge_rgb(edge_data),.edge_threshold(config_p[EDGE_STAGES-1][7:0]),
            .pv(I_probe_pack_valid),.pu(I_probe_pack_user),.fifo_sticky(I_probe_fifo_sticky),.fifo_armed(I_probe_fifo_armed),.panel(probe_panel));
    end else begin:g_no_probe
        assign edge_input=I_data;assign probe_panel=0;
    end endgenerate
    edge_detect_96 #(.IMG_WIDTH(IMG_WIDTH), .IMG_HEIGHT(IMG_HEIGHT),
                     .RUNTIME_THRESHOLD(1), .DENOISE_ENABLE(DENOISE_ENABLE), .NMS_ENABLE(NMS_ENABLE), .QUALITY_ENABLE(QUALITY_ENABLE), .QUALITY_HOPS(QUALITY_HOPS)) u_edge (
        .I_clk(clk), .I_rst_n(rst_n), .I_tdata(edge_input), .I_tvalid(I_valid),
        .I_tuser(I_user), .I_tlast(I_last), .I_threshold(beat_config[7:0]),
        .I_tready(I_ready), .O_tready(O_ready), .O_tdata(edge_data),
        .O_tvalid(probe_ev), .O_tuser(probe_eu), .O_tlast()
    );
    wire [95:0] selected_data = config_p[EDGE_STAGES-1][8] ? edge_data : original_p[EDGE_STAGES-1];
    edge_status_osd #(.IMG_WIDTH(IMG_WIDTH), .IMG_HEIGHT(IMG_HEIGHT),
                     .ENABLE(OSD_ENABLE),.PROBE_ENABLE(PROBE_ENABLE && OSD_ENABLE)) u_status (
        .clk(clk), .rst_n(rst_n), .I_data(selected_data),
        .I_valid(valid_p[EDGE_STAGES-1]), .I_user(user_p[EDGE_STAGES-1]), .I_last(last_p[EDGE_STAGES-1]),
        .I_config(config_p[EDGE_STAGES-1]),.I_probe_panel(probe_panel), .O_data(O_data), .O_valid(O_valid),
        .O_user(O_user), .O_last(O_last)
    );
endmodule
