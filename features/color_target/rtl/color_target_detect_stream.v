`timescale 1ns / 1ps
// Independent RGB -> optional support3 -> mask statistics experiment.
// Original color_target_detect is unchanged. FILTER_ENABLE defaults to 0.
// Complete fixed raster only. Truncation requires an explicit stream reset;
// reset cancels ALL unpublished data, including a preceding frame's tail.
module color_target_detect_stream #(
    parameter integer FILTER_ENABLE=0, WIDTH=1280, HEIGHT=720, XW=11, YW=10,
    parameter integer TARGET_CLASS=0, HUE_HALF_WIDTH_DEG=30,
    parameter integer C_MIN=24, V_MIN=32, MIN_COUNT=64
)(
    input clk, input rst_n,
    input I_pixel_valid, input [95:0] I_data,
    input [XW-1:0] I_x0, input [YW-1:0] I_y,
    input I_sof, input I_eol, input I_eof,
    input [31:0] I_session_id, input [31:0] I_frame_id,
    input I_frame_abort,
    output [31:0] O_res_session_id, output [31:0] O_res_frame_id,
    output O_result_valid, output O_target_present,
    output [1:0] O_color_class, output [19:0] O_pixel_count,
    output [XW-1:0] O_xmin, O_xmax, O_center_x,
    output [YW-1:0] O_ymin, O_ymax, O_center_y,
    output O_result_ready, output O_protocol_error
);
    wire [3:0] mask;
    genvar lane;
    generate for(lane=0;lane<4;lane=lane+1) begin : g_classify
        color_classify #(.TARGET_CLASS(TARGET_CLASS),.HUE_HALF_WIDTH_DEG(HUE_HALF_WIDTH_DEG),
            .C_MIN(C_MIN),.V_MIN(V_MIN)) u_classify (
            .I_r(I_data[95-24*lane -: 8]),.I_g(I_data[87-24*lane -: 8]),
            .I_b(I_data[79-24*lane -: 8]),.O_hit(mask[3-lane]));
    end endgenerate
    // Capture idle-cycle aborts before the filter: support3 samples its abort
    // field only with valid. An abort after completed input EOF does not poison
    // that frame's autonomous tail (there is no longer an open input frame).
    reg input_open, input_bad;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin input_open<=0; input_bad<=0; end
        else if (I_pixel_valid && I_sof) begin
            input_open<=!I_eof; input_bad<=I_frame_abort;
        end else begin
            if (I_frame_abort && input_open) input_bad<=1;
            if (I_pixel_valid && I_eof) input_open<=0;
        end
    end
    wire bad=I_pixel_valid && (I_sof ? I_frame_abort : (input_bad || I_frame_abort));
    wire fv, fs, fl, fe, fa, filter_error, stats_error;
    wire [3:0] fm;
    wire [XW-1:0] fx;
    wire [YW-1:0] fy;
    wire [31:0] fsession, fframe;
    color_target_support3 #(.ENABLE(FILTER_ENABLE),.WIDTH(WIDTH),.HEIGHT(HEIGHT),
        .XW(XW),.YW(YW)) u_filter (
        .clk(clk),.rst_n(rst_n),.I_pixel_valid(I_pixel_valid),.I_mask(mask),
        .I_x0(I_x0),.I_y(I_y),.I_sof(I_sof),.I_eol(I_eol),.I_eof(I_eof),
        .I_session_id(I_session_id),.I_frame_id(I_frame_id),.I_frame_abort(bad),
        .O_pixel_valid(fv),.O_mask(fm),.O_x0(fx),.O_y(fy),.O_sof(fs),.O_eol(fl),.O_eof(fe),
        .O_session_id(fsession),.O_frame_id(fframe),.O_frame_abort(fa),.O_protocol_error(filter_error));
    color_target_mask_stats #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.XW(XW),.YW(YW),
        .MIN_COUNT(MIN_COUNT),.TARGET_CLASS(TARGET_CLASS)) u_stats (
        .clk(clk),.rst_n(rst_n),.I_pixel_valid(fv),.I_mask(fm),.I_x0(fx),.I_y(fy),
        .I_sof(fs),.I_eol(fl),.I_eof(fe),.I_session_id(fsession),.I_frame_id(fframe),
        .I_frame_abort(fa),.O_res_session_id(O_res_session_id),.O_res_frame_id(O_res_frame_id),
        .O_result_valid(O_result_valid),.O_target_present(O_target_present),.O_color_class(O_color_class),
        .O_pixel_count(O_pixel_count),.O_xmin(O_xmin),.O_xmax(O_xmax),.O_center_x(O_center_x),
        .O_ymin(O_ymin),.O_ymax(O_ymax),.O_center_y(O_center_y),
        .O_result_ready(O_result_ready),.O_protocol_error(stats_error));
    assign O_protocol_error=filter_error || stats_error;
endmodule
