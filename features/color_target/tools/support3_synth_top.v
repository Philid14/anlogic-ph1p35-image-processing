// Standalone gate/resource harness only; not a main-project source list.
`ifndef SUPPORT3_TEST_HEIGHT
`define SUPPORT3_TEST_HEIGHT 720
`endif
module support3_synth_top #(parameter integer ENABLE=1) (
    input clk, input rst_n,
    input I_pixel_valid, input [3:0] I_mask,
    input [10:0] I_x0, input [9:0] I_y,
    input I_sof, input I_eol, input I_eof,
    input [31:0] I_session_id, input [31:0] I_frame_id, input I_frame_abort,
    input [1:0] observe_sel, output [31:0] observe
);
    wire O_pixel_valid, O_sof, O_eol, O_eof, O_frame_abort, O_protocol_error;
    wire [3:0] O_mask;
    wire [10:0] O_x0;
    wire [9:0] O_y;
    wire [31:0] O_session_id, O_frame_id;
    wire [95:0] all_outputs = {1'b0, O_pixel_valid, O_mask, O_x0, O_y,
        O_sof, O_eol, O_eof, O_session_id, O_frame_id, O_frame_abort, O_protocol_error};
    // Observe every output through a 3:1 mux: the full 191-pin internal module
    // exceeds this package's 160 user I/Os. Include mux cost in area reports.
    assign observe = observe_sel == 0 ? all_outputs[31:0] :
                     observe_sel == 1 ? all_outputs[63:32] : all_outputs[95:64];
    color_target_support3 #(.ENABLE(ENABLE), .HEIGHT(`SUPPORT3_TEST_HEIGHT)) u_support (
        .clk(clk), .rst_n(rst_n),
        .I_pixel_valid(I_pixel_valid), .I_mask(I_mask), .I_x0(I_x0), .I_y(I_y),
        .I_sof(I_sof), .I_eol(I_eol), .I_eof(I_eof),
        .I_session_id(I_session_id), .I_frame_id(I_frame_id), .I_frame_abort(I_frame_abort),
        .O_pixel_valid(O_pixel_valid), .O_mask(O_mask), .O_x0(O_x0), .O_y(O_y),
        .O_sof(O_sof), .O_eol(O_eol), .O_eof(O_eof),
        .O_session_id(O_session_id), .O_frame_id(O_frame_id), .O_frame_abort(O_frame_abort),
        .O_protocol_error(O_protocol_error)
    );
endmodule

module support3_bypass_synth_top (
    input clk, input rst_n,
    input I_pixel_valid, input [3:0] I_mask,
    input [10:0] I_x0, input [9:0] I_y,
    input I_sof, input I_eol, input I_eof,
    input [31:0] I_session_id, input [31:0] I_frame_id, input I_frame_abort,
    input [1:0] observe_sel, output [31:0] observe
);
    support3_synth_top #(.ENABLE(0)) u_bypass (
        .clk(clk), .rst_n(rst_n), .I_pixel_valid(I_pixel_valid), .I_mask(I_mask),
        .I_x0(I_x0), .I_y(I_y), .I_sof(I_sof), .I_eol(I_eol), .I_eof(I_eof),
        .I_session_id(I_session_id), .I_frame_id(I_frame_id), .I_frame_abort(I_frame_abort),
        .observe_sel(observe_sel), .observe(observe)
    );
endmodule
