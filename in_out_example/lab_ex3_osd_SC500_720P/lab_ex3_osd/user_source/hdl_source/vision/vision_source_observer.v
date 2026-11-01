// MAIN normalized early-SOF adapter. Immutable TARGET classifier/stats/guard
// are observed without video backpressure. Complete coordinates are LAST;
// current-pixel highlight and block-end motion masks carry pixel timing.
module vision_source_observer #(parameter WIDTH=1280,HEIGHT=720,MAX_AGE_CYCLES=6000000)(
    input clk,rst_n,input [95:0] rgb,input [31:0] gray,
    input valid,user,last,
    output reg [3:0] target_mark,output [3:0] motion_mark,
    output [1:0] track_state,output target_valid,
    output reg [10:0] target_x,output reg [9:0] target_y,
    output reg [19:0] target_count,output reg [31:0] target_frame,
    output motion_ready,motion_valid,output [11:0] motion_count,
    output [2:0] motion_state,output [31:0] motion_frame,
    output reg complete_toggle,output reg protocol_error
);
    reg [10:0] x;reg [9:0] y;reg armed,first,finished,bad;
    reg [17:0] beats;reg [31:0] fid,sid;reg [63:0] now_tick,capture_tick,retire_tick;
    reg session_start,cancel_pending,last_target_valid,gap_expired;reg [31:0] cancel_fid,cancel_sid;
    reg [63:0] cancel_tick;
    wire [10:0] px=user?0:x;wire [9:0] py=user?0:y;
    wire at_last=px==WIDTH-4;wire at_end=at_last && py==HEIGHT-1;
    wire geometry=last!=at_last;
    wire active=armed || user;
    wire stream_error=(valid && (!active || (!user && finished) || geometry)) || (!valid && last);
    wire abort=((bad || gap_expired) && !user) || stream_error || (user && armed && !finished && beats!=0);
    wire pixel_sof=valid && (user || first);
    wire pixel_eof=valid && active && (!finished || user) && at_end;
    wire frame_good=pixel_eof && !bad && !stream_error && beats==(WIDTH/4)*HEIGHT-1;
    wire [31:0] pixel_fid=user?fid+1'b1:fid;
    wire restart=user && ((fid==32'hffffffff) || (armed && !finished && beats!=0));
    wire [31:0] pixel_sid=restart ? sid+1'b1 : sid;
    wire usable,positive;
    assign target_valid=last_target_valid && usable;
    wire [3:0] mask;
    genvar lane;
    generate for(lane=0;lane<4;lane=lane+1)begin:g_class
        color_classify #(.TARGET_CLASS(0),.HUE_HALF_WIDTH_DEG(30),.C_MIN(24),.V_MIN(32)) u_class(
            .I_r(rgb[95-lane*24-:8]),.I_g(rgb[87-lane*24-:8]),.I_b(rgb[79-lane*24-:8]),.O_hit(mask[3-lane]));
    end endgenerate
    wire det_ready,det_valid,det_present;wire [31:0] det_sid,det_fid;
    wire [19:0] det_count;wire [10:0] dx0,dx1,dcx;wire [9:0] dy0,dy1,dcy;
    wire [1:0] det_class;wire det_error;
    color_target_mask_stats #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.MIN_COUNT(64),.TARGET_CLASS(0)) u_stats(
        .clk(clk),.rst_n(rst_n),.I_pixel_valid(valid && active && (!finished || user)),.I_mask(mask),
        .I_x0(px),.I_y(py),.I_sof(pixel_sof),.I_eol(last),.I_eof(pixel_eof),
        .I_session_id(pixel_sid),.I_frame_id(pixel_fid),.I_frame_abort(abort),
        .O_res_session_id(det_sid),.O_res_frame_id(det_fid),.O_result_valid(det_valid),
        .O_target_present(det_present),.O_color_class(det_class),.O_pixel_count(det_count),
        .O_xmin(dx0),.O_xmax(dx1),.O_center_x(dcx),.O_ymin(dy0),.O_ymax(dy1),.O_center_y(dcy),
        .O_result_ready(det_ready),.O_protocol_error(det_error));
    color_target_track_guard #(.TIME_W(64),.COUNTER_W(16),.ACQ_FRAMES(3),.LOST_FRAMES(15),
        .MAX_TARGET_AGE_TICKS(MAX_AGE_CYCLES),.MAX_RELIABLE_AGE_TICKS(MAX_AGE_CYCLES)) u_guard(
        .clk(clk),.rst_n(rst_n),.I_session_start(session_start),.I_control_session_id(sid),
        .I_time_valid(1'b1),.I_now_tick(now_tick),.I_result_strobe(det_ready || cancel_pending),
        .I_identity_valid(1'b1),.I_session_id(cancel_pending?cancel_sid:det_sid),
        .I_frame_id(cancel_pending?cancel_fid:det_fid),.I_result_valid(det_valid && !cancel_pending),
        .I_cancelled(cancel_pending),.I_target_present(det_present && !cancel_pending),
        .I_capture_tick(cancel_pending?cancel_tick:retire_tick),.I_color_class(det_class),.I_pixel_count(det_count),
        .I_xmin(dx0),.I_xmax(dx1),.I_center_x(dcx),.I_ymin(dy0),.I_ymax(dy1),.I_center_y(dcy),
        .O_track_state(track_state),.O_observation_usable(usable),.O_positive_valid(positive));
    vision_motion_grid #(.WIDTH(WIDTH),.HEIGHT(HEIGHT)) u_motion(
        .clk(clk),.rst_n(rst_n),.gray(gray),.valid(valid && active && (!finished || user)),
        .sof(pixel_sof),.eof(pixel_eof),.abort(abort),.frame_good(frame_good),.x(px),.y(py),.frame_id(pixel_fid),
        .mark(motion_mark),.result_ready(motion_ready),.result_valid(motion_valid),
        .result_frame(motion_frame),.changed_cells(motion_count),.result_state(motion_state));
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            x<=0;y<=0;armed<=0;first<=0;finished<=0;bad<=0;beats<=0;fid<=0;sid<=1;
            now_tick<=0;capture_tick<=0;retire_tick<=0;session_start<=1;cancel_pending<=0;
            cancel_fid<=0;cancel_sid<=0;cancel_tick<=0;target_mark<=0;
            last_target_valid<=0;target_x<=0;target_y<=0;target_count<=0;target_frame<=0;
            complete_toggle<=0;protocol_error<=0;gap_expired<=0;
        end else begin
            now_tick<=now_tick+1'b1;session_start<=0;cancel_pending<=0;
            if(armed && now_tick-capture_tick>MAX_AGE_CYCLES)gap_expired<=1;
            target_mark<=valid && !abort && usable && positive && track_state[1]?mask:4'd0;
            if(stream_error || det_error)protocol_error<=1;
            if(user)begin
                gap_expired<=0;
                x<=valid?4:0;y<=0;armed<=1;first<=!valid;finished<=0;
                beats<=valid?1:0;bad<=valid && geometry;fid<=fid+1'b1;capture_tick<=now_tick;
                if(restart)begin sid<=sid+1'b1;session_start<=1;end
                if(armed && !finished && beats!=0)begin
                    cancel_pending<=1;cancel_fid<=fid;cancel_sid<=sid;cancel_tick<=capture_tick;
                    last_target_valid<=0;target_x<=0;target_y<=0;target_count<=0;
                end
            end else if(valid)begin
                first<=0;if(stream_error)bad<=1;
                if(beats<(WIDTH/4)*HEIGHT+1)beats<=beats+1'b1;
                x<=at_last?0:px+4;
                if(at_last)begin y<=py+1'b1;if(at_end)finished<=1;end
            end else if(last)bad<=1;
            if(stream_error && !bad && armed && !finished && !user)begin
                sid<=sid+1'b1;session_start<=1;
                cancel_pending<=1;cancel_fid<=fid;cancel_sid<=sid;cancel_tick<=capture_tick;
                last_target_valid<=0;target_x<=0;target_y<=0;target_count<=0;
            end
            if(pixel_eof)begin
                retire_tick<=capture_tick;
                if(frame_good)complete_toggle<=!complete_toggle;
            end
            if(det_ready)begin
                last_target_valid<=det_valid && det_present;target_frame<=det_fid;
                target_x<=det_valid && det_present?dcx:0;target_y<=det_valid && det_present?dcy:0;
                target_count<=det_valid?det_count:0;
            end
        end
    end
endmodule
