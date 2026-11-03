`timescale 1ns / 1ps
// Independent observation-domain wrapper. No CDC, DDR or display-frame matching.
// MAIN supplies authoritative session control, retired identities and timestamps.
// Both age limits MUST be configured; zero leaves admission safely disabled.
module color_target_track_guard #(
    parameter integer XW=11, YW=10, TIME_W=64, COUNTER_W=16,
    parameter integer ACQ_FRAMES=3, LOST_FRAMES=15,
    parameter signed [TIME_W:0] MAX_TARGET_AGE_TICKS=0,
    parameter signed [TIME_W:0] MAX_RELIABLE_AGE_TICKS=0
)(
    input clk, input rst_n,
    input I_session_start, input [31:0] I_control_session_id,
    input I_time_valid, input [TIME_W-1:0] I_now_tick,
    input I_result_strobe, input I_identity_valid,
    input [31:0] I_session_id, I_frame_id,
    input I_result_valid, input I_cancelled, input I_target_present,
    input [TIME_W-1:0] I_capture_tick,
    input [1:0] I_color_class, input [19:0] I_pixel_count,
    input [XW-1:0] I_xmin, I_xmax, I_center_x,
    input [YW-1:0] I_ymin, I_ymax, I_center_y,
    output O_session_ready, output reg [31:0] O_current_session_id,
    output reg O_event_strobe, O_retired_strobe, O_admitted_strobe,
    output reg [7:0] O_reason,
    output reg O_timeout_strobe,
    output [1:0] O_track_state,
    output O_observation_usable,
    output O_reliable_valid, O_positive_valid,
    output [31:0] O_observation_session_id, O_observation_frame_id,
    output [31:0] O_box_session_id, O_box_frame_id,
    output [TIME_W-1:0] O_reliable_age, O_positive_age,
    output [TIME_W-1:0] O_reliable_tick, O_positive_tick,
    output [1:0] O_color_class, output [19:0] O_pixel_count,
    output [XW-1:0] O_xmin, O_xmax, O_center_x,
    output [YW-1:0] O_ymin, O_ymax, O_center_y,
    output reg [COUNTER_W-1:0] O_duplicate_count, O_reorder_count,
    output reg [COUNTER_W-1:0] O_wrong_session_count, O_identity_error_count,
    output reg [COUNTER_W-1:0] O_invalid_count, O_cancelled_count,
    output reg [COUNTER_W-1:0] O_stale_result_count, O_time_error_count,
    output reg [COUNTER_W-1:0] O_timeout_count
);
    localparam [7:0] R_NONE=0, R_POSITIVE=1, R_NO_TARGET=2, R_INVALID=3,
        R_CANCELLED=4, R_DUPLICATE=5, R_REORDER=6, R_WRONG_SESSION=7,
        R_NO_IDENTITY=8, R_STALE=9, R_FUTURE=10, R_NO_TIME=11,
        R_BARRIER=12, R_DISABLED=13, R_SESSION_REUSE=14, R_NOT_READY=15;
    wire config_good=(TIME_W>=2) && (COUNTER_W>=1) &&
        (MAX_TARGET_AGE_TICKS>0) && !MAX_TARGET_AGE_TICKS[TIME_W] &&
        (MAX_RELIABLE_AGE_TICKS>0) && !MAX_RELIABLE_AGE_TICKS[TIME_W];
    reg session_seen, active, have_clock, have_high_water;
    reg [TIME_W-1:0] last_now;
    reg [31:0] high_water;
    reg have_reliable, have_positive;
    reg [TIME_W-1:0] reliable_tick, positive_tick;
    reg [31:0] observation_frame, box_frame;
    reg [1:0] box_class;
    wire clock_backwards=have_clock && I_now_tick<last_now;
    wire clock_good=I_time_valid && !clock_backwards;
    assign O_session_ready=active && config_good && clock_good && !I_session_start;
    wire [TIME_W-1:0] reliable_age=I_now_tick-reliable_tick;
    wire [TIME_W-1:0] positive_age=I_now_tick-positive_tick;
    wire reliable_expired=have_reliable && reliable_age>MAX_RELIABLE_AGE_TICKS[TIME_W-1:0];
    wire positive_expired=have_positive && positive_age>MAX_TARGET_AGE_TICKS[TIME_W-1:0];
    wire expired=reliable_expired || positive_expired;
    wire [TIME_W-1:0] incoming_age=I_now_tick-I_capture_tick;
    wire future_capture=I_capture_tick>I_now_tick;
    wire incoming_stale=incoming_age>MAX_RELIABLE_AGE_TICKS[TIME_W-1:0] ||
        (I_target_present && incoming_age>MAX_TARGET_AGE_TICKS[TIME_W-1:0]);
    wire new_identity=!have_high_water || I_frame_id>high_water;
    wire retire=O_session_ready && I_result_strobe && I_identity_valid &&
        I_session_id==O_current_session_id && new_identity;
    wire admit=retire && !I_cancelled && I_result_valid && !future_capture && !incoming_stale;

    // The unchanged legacy core resets acquisition on a different session token.
    // A private token changes only on first admitted data after a flush. It is
    // the complement of the LAST CONSUMED token, not an increment per flush:
    // even many control/timeout events without data cannot alias the old run.
    // No generated reset/clock, reset bubble or hidden result queue is needed.
    reg core_fresh;
    reg [31:0] last_core_token;
    wire [31:0] core_token=(!core_fresh || expired) ? ~last_core_token : last_core_token;
    wire [1:0] core_state;
    wire core_show;
    wire [19:0] core_count;
    wire [XW-1:0] core_xmin, core_xmax, core_cx;
    wire [YW-1:0] core_ymin, core_ymax, core_cy;
    color_target_track #(.XW(XW),.YW(YW),.ACQ_FRAMES(ACQ_FRAMES),
        .LOST_FRAMES(LOST_FRAMES),.MAX_JUMP(0)) u_track (
        .clk(clk),.rst_n(rst_n),.I_result_strobe(admit),.I_result_valid(1'b1),
        .I_target_present(I_target_present),.I_pixel_count(I_pixel_count),
        .I_xmin(I_xmin),.I_xmax(I_xmax),.I_center_x(I_center_x),
        .I_ymin(I_ymin),.I_ymax(I_ymax),.I_center_y(I_center_y),
        .I_session_id(core_token),.I_frame_id(I_frame_id),
        .O_track_state(core_state),.O_show(core_show),.O_out_count(core_count),
        .O_out_xmin(core_xmin),.O_out_xmax(core_xmax),.O_out_center_x(core_cx),
        .O_out_ymin(core_ymin),.O_out_ymax(core_ymax),.O_out_center_y(core_cy),
        .O_out_session_id(),.O_out_frame_id(),.O_state_change());

    // A target-age expiry must not erase a still-recent reliable NO_TARGET.
    // Reliable link activity and usable positive tracking are distinct facts.
    assign O_reliable_valid=O_session_ready && have_reliable && !reliable_expired;
    assign O_positive_valid=O_reliable_valid && core_fresh && have_positive && !positive_expired;
    assign O_observation_usable=O_positive_valid && core_show;
    assign O_track_state=(O_session_ready && core_fresh && !expired) ? core_state : 2'd0;
    assign O_reliable_age=O_reliable_valid ? reliable_age : {TIME_W{1'b1}};
    assign O_positive_age=O_positive_valid ? positive_age : {TIME_W{1'b1}};
    assign O_reliable_tick=reliable_tick;
    assign O_positive_tick=positive_tick;
    assign O_observation_session_id=O_reliable_valid ? O_current_session_id : 0;
    assign O_observation_frame_id=O_reliable_valid ? observation_frame : 0;
    assign O_box_session_id=O_positive_valid ? O_current_session_id : 0;
    assign O_box_frame_id=O_positive_valid ? box_frame : 0;
    assign O_color_class=O_observation_usable ? box_class : 0;
    assign O_pixel_count=O_observation_usable ? core_count : 0;
    assign O_xmin=O_observation_usable ? core_xmin : 0;
    assign O_xmax=O_observation_usable ? core_xmax : 0;
    assign O_center_x=O_observation_usable ? core_cx : 0;
    assign O_ymin=O_observation_usable ? core_ymin : 0;
    assign O_ymax=O_observation_usable ? core_ymax : 0;
    assign O_center_y=O_observation_usable ? core_cy : 0;

    function [COUNTER_W-1:0] increment;
        input [COUNTER_W-1:0] value;
        begin increment=(&value) ? value : value+1'b1; end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active<=0; session_seen<=0; have_clock<=0; have_high_water<=0;
            O_current_session_id<=0; last_now<=0; high_water<=0;
            have_reliable<=0; have_positive<=0; reliable_tick<=0; positive_tick<=0;
            observation_frame<=0; box_frame<=0; box_class<=0;
            core_fresh<=0; last_core_token<=0;
            O_event_strobe<=0; O_retired_strobe<=0; O_admitted_strobe<=0;
            O_reason<=R_NONE; O_timeout_strobe<=0;
            O_duplicate_count<=0; O_reorder_count<=0; O_wrong_session_count<=0;
            O_identity_error_count<=0; O_invalid_count<=0; O_cancelled_count<=0;
            O_stale_result_count<=0; O_time_error_count<=0; O_timeout_count<=0;
        end else begin
            O_event_strobe<=I_result_strobe;
            O_retired_strobe<=0; O_admitted_strobe<=0;
            O_reason<=R_NONE; O_timeout_strobe<=0;
            if (I_session_start) begin
                // A trusted epoch barrier cancels same-cycle result delivery.
                active<=0; have_high_water<=0; core_fresh<=0;
                have_reliable<=0; have_positive<=0;
                if (!config_good) O_reason<=R_DISABLED;
                else if (!I_time_valid) O_reason<=R_NO_TIME;
                else if (session_seen && I_control_session_id==O_current_session_id)
                    O_reason<=R_SESSION_REUSE;
                else begin
                    active<=1; session_seen<=1; have_clock<=1;
                    last_now<=I_now_tick; O_current_session_id<=I_control_session_id;
                    O_reason<=R_BARRIER;
                end
            end else if (active && !clock_good) begin
                // Time loss/rollback retires this run until an explicit NEW SID.
                active<=0; core_fresh<=0; have_reliable<=0; have_positive<=0;
                O_reason<=R_NO_TIME;
                O_time_error_count<=increment(O_time_error_count);
            end else begin
                if (active) last_now<=I_now_tick;
                if (active && reliable_expired) have_reliable<=0;
                if (active && core_fresh && expired) begin
                    core_fresh<=0; have_positive<=0;
                    O_timeout_strobe<=1;
                    O_timeout_count<=increment(O_timeout_count);
                end
                if (I_result_strobe) begin
                    if (!config_good) O_reason<=R_DISABLED;
                    else if (!O_session_ready) O_reason<=R_NOT_READY;
                    else if (!I_identity_valid) begin
                        O_reason<=R_NO_IDENTITY;
                        O_identity_error_count<=increment(O_identity_error_count);
                    end else if (I_session_id!=O_current_session_id) begin
                        O_reason<=R_WRONG_SESSION;
                        O_wrong_session_count<=increment(O_wrong_session_count);
                    end else if (have_high_water && I_frame_id==high_water) begin
                        O_reason<=R_DUPLICATE;
                        O_duplicate_count<=increment(O_duplicate_count);
                    end else if (!new_identity) begin
                        O_reason<=R_REORDER;
                        O_reorder_count<=increment(O_reorder_count);
                    end else begin
                        // Identity retires even when its disposition is invalid.
                        high_water<=I_frame_id; have_high_water<=1; O_retired_strobe<=1;
                        if (I_cancelled) begin
                            O_reason<=R_CANCELLED;
                            O_cancelled_count<=increment(O_cancelled_count);
                        end else if (!I_result_valid) begin
                            O_reason<=R_INVALID;
                            O_invalid_count<=increment(O_invalid_count);
                        end else if (future_capture) begin
                            O_reason<=R_FUTURE;
                            O_time_error_count<=increment(O_time_error_count);
                        end else if (incoming_stale) begin
                            O_reason<=R_STALE;
                            O_stale_result_count<=increment(O_stale_result_count);
                        end else begin
                            O_admitted_strobe<=1;
                            O_reason<=I_target_present ? R_POSITIVE : R_NO_TARGET;
                            core_fresh<=1; last_core_token<=core_token;
                            have_reliable<=1; reliable_tick<=I_now_tick;
                            observation_frame<=I_frame_id;
                            if (I_target_present) begin
                                have_positive<=1; positive_tick<=I_now_tick;
                                box_frame<=I_frame_id; box_class<=I_color_class;
                            end
                        end
                    end
                end
            end
        end
    end
endmodule
