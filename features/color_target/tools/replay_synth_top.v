// Resource harness: serially load all inputs, observe all outputs through mux.
// Input shadow registers and output mux are INCLUDED in the area report.
// This loading interface is for synthesis observability, not the video path.
`ifndef REPLAY_FILTER_ENABLE
`define REPLAY_FILTER_ENABLE 0
`endif
module replay_synth_top (
    input clk, input rst_n,
    input [31:0] load_data, input [2:0] load_slot, input load_en, input fire,
    input [2:0] observe_sel, output reg [31:0] observe
);
    reg [191:0] sample;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) sample<=0;
        else if(load_en) begin
            case(load_slot)
                0: sample[31:0]<=load_data;
                1: sample[63:32]<=load_data;
                2: sample[95:64]<=load_data;
                3: sample[127:96]<=load_data;
                4: sample[159:128]<=load_data;
                5: sample[191:160]<=load_data;
                default: sample<=sample;
            endcase
        end
    end
    wire [31:0] sid,fid;
    wire valid,present,ready,error;
    wire [1:0] cls;
    wire [19:0] count;
    wire [10:0] xmin,xmax,cx;
    wire [9:0] ymin,ymax,cy;
    color_target_detect_stream #(.FILTER_ENABLE(`REPLAY_FILTER_ENABLE)) dut (
        .clk(clk),.rst_n(rst_n),.I_pixel_valid(fire),.I_data(sample[95:0]),
        .I_x0(sample[106:96]),.I_y(sample[116:107]),
        .I_sof(sample[117]),.I_eol(sample[118]),.I_eof(sample[119]),
        .I_session_id(sample[151:120]),.I_frame_id(sample[183:152]),.I_frame_abort(sample[184]),
        .O_res_session_id(sid),.O_res_frame_id(fid),.O_result_valid(valid),.O_target_present(present),
        .O_color_class(cls),.O_pixel_count(count),.O_xmin(xmin),.O_xmax(xmax),.O_center_x(cx),
        .O_ymin(ymin),.O_ymax(ymax),.O_center_y(cy),.O_result_ready(ready),.O_protocol_error(error));
    wire [159:0] all_outputs={7'b0,error,ready,sid,fid,valid,present,cls,count,xmin,xmax,cx,ymin,ymax,cy};
    always @* begin
        case(observe_sel)
            0: observe=all_outputs[31:0];
            1: observe=all_outputs[63:32];
            2: observe=all_outputs[95:64];
            3: observe=all_outputs[127:96];
            default: observe=all_outputs[159:128];
        endcase
    end
endmodule
