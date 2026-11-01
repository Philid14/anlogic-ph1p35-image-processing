`timescale 1ns / 1ps
// Runtime ORIGIN/GRAY/BINARY/EDGE/STYLE with frame-latched structured configuration.
// SOF is the existing AWB early notification; it need not coincide with valid.
// The complete Edge history pipeline always runs, including in non-Edge modes.
module edge_control_stream #(
    parameter integer IMG_WIDTH = 1280,
    parameter integer IMG_HEIGHT = 720,
    parameter integer OSD_ENABLE = 1,
    parameter integer DENOISE_ENABLE = 0,
    parameter integer NMS_ENABLE = 0,
    parameter integer QUALITY_ENABLE = 0,
    parameter integer QUALITY_HOPS = 4,
    parameter integer TEMPORAL_ENABLE = 0,
    parameter integer RELIABILITY_ENABLE = 0,
    parameter integer COLOR_COMPARE_ENABLE = 0,
    parameter integer INSPECTION_ENABLE = 0,
    parameter integer AUTO_DIMENSION = 0,
    parameter integer USABILITY_ENABLE = 0,
    parameter integer INSPECTION_V4 = 0,
    parameter integer VISION_ENABLE = 0
)(
    input clk, input rst_n,
    input [18:0] requested_config,
    input [31:0] I_fifo_event_counts,
    input [3:0] I_switch,input I_measure_key_n,
    input [95:0] I_data, input I_valid, input I_user, input I_last,
    output [95:0] O_data, output O_valid, output O_user, output O_last,
    output I_ready, input O_ready,output O_capture_toggle
);
    localparam [2:0] MODE_ORIGIN = 3'd0;
    localparam [2:0] MODE_GRAY   = 3'd1;
    localparam [2:0] MODE_BINARY = 3'd2;
    localparam [2:0] MODE_EDGE   = 3'd3;
    localparam [2:0] MODE_STYLE  = 3'd4;
    localparam [18:0] RESET_CONFIG = {MODE_EDGE,8'd80,8'd130};
    localparam SPATIAL_STAGES = (DENOISE_ENABLE ? 9 : 5) + (NMS_ENABLE ? 4 : 0)
        + ((QUALITY_ENABLE && NMS_ENABLE) ? 3*QUALITY_HOPS : 0);
    localparam HOLD_ENABLE=TEMPORAL_ENABLE && QUALITY_ENABLE && NMS_ENABLE;
    localparam EDGE_STAGES=SPATIAL_STAGES+(HOLD_ENABLE?2:0);
    reg [18:0] active_config;
    wire [18:0] beat_config = I_user ? requested_config : active_config;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) active_config <= RESET_CONFIG;
        else if (I_user) active_config <= requested_config;
    end
    reg [95:0] original_p [0:EDGE_STAGES-1];
    reg [95:0] gray_p [0:EDGE_STAGES-1];
    reg [95:0] binary_p [0:EDGE_STAGES-1];
    reg [18:0] config_p [0:EDGE_STAGES-1];
    reg [EDGE_STAGES-1:0] valid_p, user_p, last_p;
    integer i;
    wire [95:0] gray_now, binary_now;
    rgb_effects_96 u_rgb_effects (
        .I_rgb(I_data), .I_binary_threshold(beat_config[7:0]),
        .O_gray(gray_now), .O_binary(binary_now)
    );
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_p <= 0; user_p <= 0; last_p <= 0;
            for (i=0; i<EDGE_STAGES; i=i+1) begin
                original_p[i] <= 0; gray_p[i] <= 0; binary_p[i] <= 0;
                config_p[i] <= RESET_CONFIG;
            end
        end else begin
            original_p[0] <= I_data;
            gray_p[0] <= gray_now;
            binary_p[0] <= binary_now;
            config_p[0] <= beat_config;
            for (i=1; i<EDGE_STAGES; i=i+1) begin
                original_p[i] <= original_p[i-1];
                gray_p[i] <= gray_p[i-1];
                binary_p[i] <= binary_p[i-1];
                config_p[i] <= config_p[i-1];
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
        .I_tuser(I_user), .I_tlast(I_last), .I_threshold(beat_config[15:8]),
        .I_tready(I_ready), .O_tready(O_ready), .O_tdata(edge_data),
        .O_tvalid(), .O_tuser(), .O_tlast(),.O_temporal_support(edge_support)
    );
    generate if(HOLD_ENABLE)begin:g_temporal
        wire[1:0] bits_out;
        edge_temporal_hold #(.IMG_WIDTH(IMG_WIDTH),.IMG_HEIGHT(IMG_HEIGHT)) u_hold(
            .clk(clk),.rst_n(rst_n),.I_edge({edge_data[95],edge_data[47]}),.I_support(edge_support),
            .I_valid(valid_p[SPATIAL_STAGES-1]),.I_user(user_p[SPATIAL_STAGES-1]),.I_last(last_p[SPATIAL_STAGES-1]),
            .I_threshold(config_p[SPATIAL_STAGES-1][15:8]),.O_edge(bits_out),.O_valid(),.O_user(),.O_last());
        assign stable_edge_data={{48{bits_out[1]}},{48{bits_out[0]}}};
    end else begin:g_spatial assign stable_edge_data=edge_data;end endgenerate
    // Compute STYLE near the end of the existing alignment window, reusing
    // the ORIGIN delay instead of adding another 27x96-bit register chain.
    wire [95:0] style_data;
    generate if(EDGE_STAGES>5)begin:g_style_delayed
        style_fill_96 #(.IMG_WIDTH(IMG_WIDTH),.IMG_HEIGHT(IMG_HEIGHT)) u_style(
            .clk(clk),.rst_n(rst_n),.I_data(original_p[EDGE_STAGES-6]),
            .I_valid(valid_p[EDGE_STAGES-6]),.I_user(user_p[EDGE_STAGES-6]),.O_data(style_data));
    end else begin:g_style_direct
        style_fill_96 #(.IMG_WIDTH(IMG_WIDTH),.IMG_HEIGHT(IMG_HEIGHT)) u_style(
            .clk(clk),.rst_n(rst_n),.I_data(I_data),.I_valid(I_valid),.I_user(I_user),.O_data(style_data));
    end endgenerate
    // Every branch is delayed by the same number of beats. Selection uses the
    // configuration already travelling with this exact pixel beat.
    wire [3:0] target_mark,motion_mark;
    wire [1:0] track_state;wire target_valid;
    wire [10:0] target_x;wire [9:0] target_y;wire [19:0] target_count;
    wire [31:0] target_frame,motion_frame;wire [11:0] motion_count;
    wire [2:0] motion_state;wire motion_valid,observer_error;
    wire [3:0] target_aligned,motion_aligned;
    generate if(VISION_ENABLE && EDGE_STAGES>=4)begin:g_vision
        vision_source_observer #(.WIDTH(IMG_WIDTH),.HEIGHT(IMG_HEIGHT)) u_observer(
            .clk(clk),.rst_n(rst_n),.rgb(original_p[0]),
            .gray({gray_p[0][95:88],gray_p[0][71:64],gray_p[0][47:40],gray_p[0][23:16]}),
            .valid(valid_p[0]),.user(user_p[0]),.last(last_p[0]),
            .target_mark(target_mark),.motion_mark(motion_mark),.track_state(track_state),
            .target_valid(target_valid),.target_x(target_x),.target_y(target_y),
            .target_count(target_count),.target_frame(target_frame),
            .motion_ready(),.motion_valid(motion_valid),.motion_count(motion_count),
            .motion_state(motion_state),.motion_frame(motion_frame),
            .complete_toggle(O_capture_toggle),.protocol_error(observer_error));
        reg [3:0] tp[0:EDGE_STAGES-3],mp[0:EDGE_STAGES-4];integer vi;
        always @(posedge clk or negedge rst_n)begin
            if(!rst_n)begin
                for(vi=0;vi<EDGE_STAGES-2;vi=vi+1)tp[vi]<=0;
                for(vi=0;vi<EDGE_STAGES-3;vi=vi+1)mp[vi]<=0;
            end else begin
                tp[0]<=target_mark;mp[0]<=motion_mark;
                for(vi=1;vi<EDGE_STAGES-2;vi=vi+1)tp[vi]<=tp[vi-1];
                for(vi=1;vi<EDGE_STAGES-3;vi=vi+1)mp[vi]<=mp[vi-1];
            end
        end
        assign target_aligned=tp[EDGE_STAGES-3];assign motion_aligned=mp[EDGE_STAGES-4];
    end else begin:g_no_vision
        assign target_mark=0;assign motion_mark=0;assign target_aligned=0;assign motion_aligned=0;
        assign track_state=0;assign target_valid=0;assign target_x=0;assign target_y=0;
        assign target_count=0;assign target_frame=0;assign motion_frame=0;
        assign motion_count=0;assign motion_state=0;assign motion_valid=0;
        assign observer_error=0;assign O_capture_toggle=0;
    end endgenerate
    reg [95:0] selected_data;integer mark_lane;
    always @(*) begin
        case (config_p[EDGE_STAGES-1][18:16])
            MODE_ORIGIN: selected_data = original_p[EDGE_STAGES-1];
            MODE_GRAY:   selected_data = gray_p[EDGE_STAGES-1];
            MODE_BINARY: selected_data = binary_p[EDGE_STAGES-1];
            MODE_STYLE: selected_data = style_data;
            3'd5,3'd6:begin
                selected_data=VISION_ENABLE?original_p[EDGE_STAGES-1]:stable_edge_data;
                for(mark_lane=0;mark_lane<4;mark_lane=mark_lane+1)begin
                    if(VISION_ENABLE && config_p[EDGE_STAGES-1][18:16]==3'd5 && target_aligned[3-mark_lane])
                        selected_data[95-mark_lane*24-:24]=24'h00ff80;
                    if(VISION_ENABLE && config_p[EDGE_STAGES-1][18:16]==3'd6 && motion_aligned[3-mark_lane])
                        selected_data[95-mark_lane*24-:24]=24'hff00ff;
                end
            end
            default:     selected_data = stable_edge_data;
        endcase
    end
    wire [3:0] ui_switches;
    wire capture_toggle,clear_toggle,repeat_toggle;
    wire [2:0] ui_cal_status;
    wire [10:0] ui_span_x,ui_span_y;wire ui_calibrated;wire [1:0] ui_visited;
    generate if(INSPECTION_ENABLE)begin:g_inspection_controls
        inspection_control u_controls(.clk(clk),.rst_n(rst_n),.switches(I_switch),
            .key_n(I_measure_key_n),.stable_switches(ui_switches),
            .capture_toggle(capture_toggle),.clear_toggle(clear_toggle),.repeat_toggle(repeat_toggle));
        if(AUTO_DIMENSION)begin:g_auto
            wire [10:0] ruler_span;
            ruler_auto_calibration #(.WIDTH(IMG_WIDTH),.HEIGHT(IMG_HEIGHT),.ROBUST_ENABLE(USABILITY_ENABLE),.AREA_ENABLE(INSPECTION_V4)) u_ruler(
                .clk(clk),.rst_n(rst_n),
                .gray({gray_p[0][95:88],gray_p[0][71:64],gray_p[0][47:40],gray_p[0][23:16]}),
                .valid(valid_p[0]),.user(user_p[0]),.last(last_p[0]),
                .enable(ui_switches[1] && ui_switches[3] && beat_config[18:16]==MODE_ORIGIN),
                .request_toggle(capture_toggle),.span(ruler_span),.calibrated(ui_calibrated),.status(ui_cal_status));
            assign ui_span_x=ruler_span;assign ui_span_y=ruler_span;assign ui_visited=0;
        end else begin:g_manual
            inspection_calibration u_calibration(.clk(clk),.rst_n(rst_n),.switches(ui_switches),
                .short_toggle(capture_toggle),.up_toggle(repeat_toggle),.span_x(ui_span_x),.span_y(ui_span_y),
                .calibrated(ui_calibrated),.visited(ui_visited));
            assign ui_cal_status=0;
        end
    end else begin:g_legacy_controls
        assign ui_switches=4'b0001;
        assign capture_toggle=1'b0;assign clear_toggle=1'b0;assign repeat_toggle=1'b0;
        assign ui_cal_status=0;assign ui_span_x=256;assign ui_span_y=256;assign ui_calibrated=0;assign ui_visited=0;
    end endgenerate
    reg [3:0] ui_frame;
    wire [3:0] ui_beat=I_user?ui_switches:ui_frame;
    reg [3:0] ui_pipe[0:EDGE_STAGES-1];
    integer ui_i;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            ui_frame<=0;for(ui_i=0;ui_i<EDGE_STAGES;ui_i=ui_i+1)ui_pipe[ui_i]<=0;
        end else begin
            if(I_user)ui_frame<=ui_switches;
            ui_pipe[0]<=ui_beat;
            for(ui_i=1;ui_i<EDGE_STAGES;ui_i=ui_i+1)ui_pipe[ui_i]<=ui_pipe[ui_i-1];
        end
    end
    wire [95:0] compare_data;
    wire [18:0] compare_config;wire [3:0] compare_switches;wire [2:0] compare_ruler;
    wire compare_valid,compare_user,compare_last;
    generate if(COLOR_COMPARE_ENABLE)begin:g_color_compare
        reg [18:0] config_d1,config_d2;reg [3:0] switches_d1,switches_d2;reg [2:0] ruler_d1,ruler_d2;
        always @(posedge clk or negedge rst_n)begin
            if(!rst_n)begin config_d1<=RESET_CONFIG;config_d2<=RESET_CONFIG;switches_d1<=0;switches_d2<=0;ruler_d1<=0;ruler_d2<=0;end
            else begin config_d1<=config_p[EDGE_STAGES-1];config_d2<=config_d1;switches_d1<=ui_pipe[EDGE_STAGES-1];switches_d2<=switches_d1;ruler_d1<=ui_cal_status;ruler_d2<=ruler_d1;end
        end
        assign compare_config=config_d2;assign compare_switches=switches_d2;assign compare_ruler=ruler_d2;
        wire [47:0] measured_means;
        wire measurement_valid;
        wire [15:0] measurement_id;
        color_compare_stats #(.WIDTH(IMG_WIDTH),.HEIGHT(IMG_HEIGHT),
            .REF_X(USABILITY_ENABLE?304:256),.TEST_X(USABILITY_ENABLE?944:896),.ROI_Y(USABILITY_ENABLE?304:256),
            .W_LOG(USABILITY_ENABLE?5:7),.H_LOG(USABILITY_ENABLE?5:7)) u_stats(
            .clk(clk),.rst_n(rst_n),.rgb(I_data),.valid(I_valid),.user(I_user),.last(I_last),
            .means(measured_means),.result_valid(measurement_valid),.sample_id(measurement_id));
        wire [43:0] dim_sizes,dim_box,dim_gap_coords;wire dim_valid,dim_present;
        wire [1:0] dim_gap;wire [7:0] dim_cut;wire dim_bright;wire [15:0] dim_id;
        if(INSPECTION_ENABLE)begin:g_measure_stats
            planar_measure_stats #(.WIDTH(IMG_WIDTH),.HEIGHT(IMG_HEIGHT)) u_dimension(
                .clk(clk),.rst_n(rst_n),.binary_pixels({binary_p[0][95],binary_p[0][71],binary_p[0][47],binary_p[0][23]}),
                .valid(valid_p[0]),.user(user_p[0]),.last(last_p[0]),.bright(ui_pipe[0][2]),
                .threshold(config_p[0][7:0]),.result_valid(dim_valid),.present(dim_present),
                .gap_valid(dim_gap),.gap_coords(dim_gap_coords),.sizes(dim_sizes),.box_coords(dim_box),.sample_id(dim_id),
                .result_threshold(dim_cut),.result_bright(dim_bright));
        end else begin:g_no_measure_stats
            assign dim_gap_coords=0;assign dim_sizes=0;assign dim_box=0;assign dim_valid=0;assign dim_present=0;
            assign dim_gap=0;assign dim_cut=0;assign dim_bright=0;assign dim_id=0;
        end
        color_compare_osd #(.WIDTH(IMG_WIDTH),.HEIGHT(IMG_HEIGHT),.UI_ENABLE(INSPECTION_ENABLE),.AUTO_DIMENSION(AUTO_DIMENSION),.USABILITY_ENABLE(USABILITY_ENABLE),.INSPECTION_V4(INSPECTION_V4),
            .REF_X(USABILITY_ENABLE?304:256),.TEST_X(USABILITY_ENABLE?944:896),.ROI_Y(USABILITY_ENABLE?304:256),
            .ROI_W(USABILITY_ENABLE?32:128),.ROI_H(USABILITY_ENABLE?32:128)) u_compare(
            .clk(clk),.rst_n(rst_n),.rgb(selected_data),.valid(valid_p[EDGE_STAGES-1]),
            .user(user_p[EDGE_STAGES-1]),.last(last_p[EDGE_STAGES-1]),
            .means(measured_means),.result_valid(measurement_valid),.sample_id(measurement_id),
             .display_enable(ui_pipe[EDGE_STAGES-1][0]),.dimension_enable(ui_pipe[EDGE_STAGES-1][1]),
            .cal_mode(ui_pipe[EDGE_STAGES-1][3]),.axis_y(ui_pipe[EDGE_STAGES-1][2]),
            .calibrated(ui_calibrated),.span_x(ui_span_x),.span_y(ui_span_y),.cal_visited(ui_visited),
            .dim_sizes(dim_sizes),.dim_box(dim_box),.dim_gap_coords(dim_gap_coords),.cal_status(ui_cal_status),
            .dim_valid(dim_valid && dim_cut==config_p[EDGE_STAGES-1][7:0] && dim_bright==ui_pipe[EDGE_STAGES-1][2]),
            .dim_present(dim_present),.dim_gap_valid(dim_gap),.dim_threshold(config_p[EDGE_STAGES-1][7:0]),.dim_id(dim_id),
            .out_rgb(compare_data),.out_valid(compare_valid),.out_user(compare_user),.out_last(compare_last));
    end else begin:g_no_color_compare
        assign compare_config=config_p[EDGE_STAGES-1];assign compare_switches=ui_pipe[EDGE_STAGES-1];assign compare_ruler=ui_cal_status;
        assign compare_data=selected_data;
        assign compare_valid=valid_p[EDGE_STAGES-1];
        assign compare_user=user_p[EDGE_STAGES-1];
        assign compare_last=last_p[EDGE_STAGES-1];
    end endgenerate
    edge_status_osd #(.IMG_WIDTH(IMG_WIDTH), .IMG_HEIGHT(IMG_HEIGHT),
                     .ENABLE(OSD_ENABLE),.RELIABILITY_ENABLE(RELIABILITY_ENABLE),.SWITCH_DIAG_ENABLE(USABILITY_ENABLE),.VISION_ENABLE(VISION_ENABLE)) u_status (
        .clk(clk), .rst_n(rst_n), .I_data(compare_data),
        .I_valid(compare_valid), .I_user(compare_user), .I_last(compare_last),
        .I_config(compare_config),.I_switches(compare_switches),.I_ruler_status(compare_ruler), .I_fifo_event_counts(I_fifo_event_counts), .O_data(O_data), .O_valid(O_valid),
        .I_track_state(track_state),.I_target_valid(target_valid),.I_target_x(target_x),.I_target_y(target_y),
        .I_target_count(target_count),.I_target_frame(target_frame),.I_motion_valid(motion_valid),
        .I_motion_count(motion_count),.I_motion_state(motion_state),.I_motion_frame(motion_frame),.I_observer_error(observer_error),
        .O_user(O_user), .O_last(O_last)
    );
endmodule
