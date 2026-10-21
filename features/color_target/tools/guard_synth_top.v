// Standalone measurement fixture. NOT a MAIN adapter or video interface.
// All guard inputs are loadable; every output is registered and observable.
// Shadow/capture registers and the output mux are included in top-level area.
`ifndef GUARD_SYNTH_TIME_W
`define GUARD_SYNTH_TIME_W 64
`endif
`ifndef GUARD_SYNTH_ENABLED
`define GUARD_SYNTH_ENABLED 1
`endif
module guard_synth_top (
    input clk, input rst_n,
    input [31:0] load_data, input [3:0] load_slot, input load_en,
    input fire, input [4:0] observe_sel, output reg [31:0] observe
);
    localparam TW=`GUARD_SYNTH_TIME_W;
    localparam INPUT_W=188+2*TW;
    localparam OUTPUT_W=407+4*TW;
    localparam INPUT_WORDS=(INPUT_W+31)/32;
    localparam OUTPUT_WORDS=(OUTPUT_W+31)/32;
    // Arbitrary synthesis fixtures, NOT production age limits or clock claims.
    localparam signed [TW:0] TARGET_AGE=`GUARD_SYNTH_ENABLED ? 1000003 : 0;
    localparam signed [TW:0] RELIABLE_AGE=`GUARD_SYNTH_ENABLED ? 2000003 : 0;
    reg [INPUT_WORDS*32-1:0] sample;
    reg [OUTPUT_WORDS*32-1:0] output_sample;
    integer k,j;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) sample<=0;
        else if (load_en) begin
            for (k=0;k<INPUT_WORDS;k=k+1)
                if (load_slot==k) sample[k*32+:32]<=load_data;
        end
    end
    wire [31:0] control_sid, sid, fid;
    wire [TW-1:0] now_tick, capture_tick;
    wire [1:0] cls;
    wire [19:0] count;
    wire [10:0] xmin,xmax,cx;
    wire [9:0] ymin,ymax,cy;
    wire session_start,time_valid,result_strobe,identity_valid;
    wire result_valid,cancelled,present;
    assign {control_sid,now_tick,capture_tick,sid,fid,cls,count,
        xmin,xmax,cx,ymin,ymax,cy,session_start,time_valid,result_strobe,
        identity_valid,result_valid,cancelled,present}=sample[INPUT_W-1:0];
    wire ready,event_strobe,retired,admitted,timeout_strobe,usable,rv,pv;
    wire [31:0] current_sid,obs_sid,obs_fid,box_sid,box_fid;
    wire [7:0] reason;
    wire [1:0] state,out_cls;
    wire [TW-1:0] reliable_age,positive_age,reliable_tick,positive_tick;
    wire [19:0] out_count;
    wire [10:0] out_xmin,out_xmax,out_cx;
    wire [9:0] out_ymin,out_ymax,out_cy;
    wire [15:0] dup_count,reorder_count,wrong_sid_count,identity_count;
    wire [15:0] invalid_count,cancel_count,stale_count,time_count,timeout_count;
    color_target_track_guard #(.TIME_W(TW),.COUNTER_W(16),
        .MAX_TARGET_AGE_TICKS(TARGET_AGE),.MAX_RELIABLE_AGE_TICKS(RELIABLE_AGE)) u_guard (
        .clk(clk),.rst_n(rst_n),
        .I_session_start(fire && session_start),.I_control_session_id(control_sid),
        .I_time_valid(time_valid),.I_now_tick(now_tick),
        .I_result_strobe(fire && result_strobe),.I_identity_valid(identity_valid),
        .I_session_id(sid),.I_frame_id(fid),.I_result_valid(result_valid),
        .I_cancelled(cancelled),.I_target_present(present),.I_capture_tick(capture_tick),
        .I_color_class(cls),.I_pixel_count(count),
        .I_xmin(xmin),.I_xmax(xmax),.I_center_x(cx),
        .I_ymin(ymin),.I_ymax(ymax),.I_center_y(cy),
        .O_session_ready(ready),.O_current_session_id(current_sid),
        .O_event_strobe(event_strobe),.O_retired_strobe(retired),.O_admitted_strobe(admitted),
        .O_reason(reason),.O_timeout_strobe(timeout_strobe),.O_track_state(state),
        .O_observation_usable(usable),.O_reliable_valid(rv),.O_positive_valid(pv),
        .O_observation_session_id(obs_sid),.O_observation_frame_id(obs_fid),
        .O_box_session_id(box_sid),.O_box_frame_id(box_fid),
        .O_reliable_age(reliable_age),.O_positive_age(positive_age),
        .O_reliable_tick(reliable_tick),.O_positive_tick(positive_tick),
        .O_color_class(out_cls),.O_pixel_count(out_count),
        .O_xmin(out_xmin),.O_xmax(out_xmax),.O_center_x(out_cx),
        .O_ymin(out_ymin),.O_ymax(out_ymax),.O_center_y(out_cy),
        .O_duplicate_count(dup_count),.O_reorder_count(reorder_count),
        .O_wrong_session_count(wrong_sid_count),.O_identity_error_count(identity_count),
        .O_invalid_count(invalid_count),.O_cancelled_count(cancel_count),
        .O_stale_result_count(stale_count),.O_time_error_count(time_count),
        .O_timeout_count(timeout_count));
    wire [OUTPUT_W-1:0] all_outputs={ready,current_sid,event_strobe,retired,admitted,
        reason,timeout_strobe,state,usable,rv,pv,obs_sid,obs_fid,box_sid,box_fid,
        reliable_age,positive_age,reliable_tick,positive_tick,out_cls,out_count,
        out_xmin,out_xmax,out_cx,out_ymin,out_ymax,out_cy,
        dup_count,reorder_count,wrong_sid_count,identity_count,invalid_count,
        cancel_count,stale_count,time_count,timeout_count};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) output_sample<=0;
        else output_sample<={{(OUTPUT_WORDS*32-OUTPUT_W){1'b0}},all_outputs};
    end
    always @* begin
        observe=0;
        for (j=0;j<OUTPUT_WORDS;j=j+1)
            if (observe_sel==j) observe=output_sample[j*32+:32];
    end
endmodule
