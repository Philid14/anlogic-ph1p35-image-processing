// MAIN normalized early-SOF adapter. Immutable TARGET classifier/stats/guard
// are observed without video backpressure. Complete coordinates are LAST;
// current-pixel highlight and block-end motion masks carry pixel timing.
module vision_source_observer #(parameter WIDTH=1280,HEIGHT=720,MAX_AGE_CYCLES=6000000)(
    input clk,rst_n,input [95:0] rgb,input [31:0] gray,
    input valid,user,last,
    output reg [3:0] target_mark,output [3:0] motion_mark,
    output [1:0] track_state,output target_valid,
    output reg [10:0] target_x,output reg [9:0] target_y,
    output reg [43:0] target_box,output reg [19:0] target_count,output reg [31:0] target_frame,
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
        wire raw_hit;
        wire [7:0] r=rgb[95-lane*24-:8],g=rgb[87-lane*24-:8],b=rgb[79-lane*24-:8];
        wire [7:0] red_limit=r-(r>>2);
        color_classify #(.TARGET_CLASS(0),.HUE_HALF_WIDTH_DEG(30),.C_MIN(24),.V_MIN(32)) u_class(
            .I_r(r),.I_g(g),.I_b(b),.O_hit(raw_hit));
        // Relative channel dominance rejects warm near-neutral highlights.
        assign mask[3-lane]=raw_hit && g<=red_limit && b<=red_limit;
    end endgenerate
    wire det_ready,det_valid,det_present;wire [31:0] det_sid,det_fid;
    wire [19:0] det_count;wire [10:0] dx0,dx1,dcx;wire [9:0] dy0,dy1,dcy;
    wire [1:0] det_class=0;wire det_error=0;
    // MAIN spatial admission after the unchanged TARGET color classifier.
    // The authoritative raster/abort validation above also qualifies EOF.
    // Select a coherent region rather than extrema of all red pixels.
    vision_red_run_stats u_stats(
        .clk(clk),.rst_n(rst_n),.valid(valid && active && (!finished || user)),.mask(mask),
        .x(px),.y(py),.eol(last),.eof(pixel_eof),.good(frame_good && !abort),
        .sid(pixel_sid),.fid(pixel_fid),
        .res_sid(det_sid),.res_fid(det_fid),.result_valid(det_valid),
        .present(det_present),.count(det_count),
        .xmin(dx0),.xmax(dx1),.cx(dcx),.ymin(dy0),.ymax(dy1),.cy(dcy),.ready(det_ready));
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
            last_target_valid<=0;target_box<=0;target_x<=0;target_y<=0;target_count<=0;target_frame<=0;
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
                    last_target_valid<=0;target_box<=0;target_x<=0;target_y<=0;target_count<=0;
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
                last_target_valid<=0;target_box<=0;target_x<=0;target_y<=0;target_count<=0;
            end
            if(pixel_eof)begin
                retire_tick<=capture_tick;
                if(frame_good)complete_toggle<=!complete_toggle;
            end
            if(det_ready)begin
                last_target_valid<=det_valid && det_present;target_frame<=det_fid;
                target_box<=det_valid && det_present?{dx0,dx1,1'b0,dy0,1'b0,dy1}:44'd0;
                target_x<=det_valid && det_present?dcx:0;target_y<=det_valid && det_present?dcy:0;
                target_count<=det_valid?det_count:0;
            end
        end
    end
endmodule

// No image RAM, no video stalls. One 4-pixel block needs >=3 red pixels.
// Keep the longest uninterrupted run (>=8px) in each row. Link consecutive
// rows only when their chosen runs overlap/touch within 4px. Publish the
// largest resulting chain with >=4 rows and >=64 support pixels per frame.
// This is deliberately NOT general connected-component labeling: only one
// run per row is retained. Fine/hollow/multiple red targets are limitations.
// X bounds are quantized to blocks of four; count is accepted block area.
// Two register stages after the last beat; no added common pixel latency.
module vision_red_run_stats(
    input clk,rst_n,valid,input [3:0] mask,
    input [10:0] x,input [9:0] y,input eol,eof,good,
    input [31:0] sid,fid,
    output reg [31:0] res_sid,res_fid,
    output reg result_valid,present,ready,output reg [19:0] count,
    output reg [10:0] xmin,xmax,cx,output reg [9:0] ymin,ymax,cy
);
    wire hit=(mask[3] && mask[2] && (mask[1] || mask[0])) ||
             (mask[1] && mask[0] && (mask[3] || mask[2]));
    wire [8:0] bx=x[10:2];
    reg [8:0] run_left,row_left,row_right;
    reg [9:0] run_len,row_len;
    wire [9:0] base_len=x==0?10'd0:run_len;
    wire [9:0] next_len=hit?base_len+1'b1:10'd0;
    wire [8:0] next_left=(base_len==0)?bx:run_left;
    wire longer=hit && (x==0 || next_len>row_len);
    wire [9:0] win_len=longer?next_len:(x==0?10'd0:row_len);
    wire [8:0] win_left=longer?next_left:row_left;
    wire [8:0] win_right=longer?bx:row_right;
    reg row_pending,row_eof,row_good;
    reg [9:0] ry,rlength;
    reg [8:0] rl,rr,previous_left,previous_right;
    reg [31:0] row_sid,row_fid;
    reg chain_active;
    reg [8:0] chain_left,chain_right,best_left,best_right;
    reg [9:0] chain_top,best_top,best_bottom;
    reg [17:0] chain_area,best_area;
    wire row_ok=rlength>=2;
    wire joins=chain_active && ry!=0 &&
        {1'b0,rl}<={1'b0,previous_right}+10'd1 &&
        {1'b0,rr}+10'd1>={1'b0,previous_left};
    wire [17:0] new_area=(joins?chain_area:18'd0)+rlength;
    wire [8:0] new_left=(joins && chain_left<rl)?chain_left:rl;
    wire [8:0] new_right=(joins && chain_right>rr)?chain_right:rr;
    wire [9:0] new_top=joins?chain_top:ry;
    wire qualified=row_ok && (ry-new_top>=3) && new_area>=16;
    wire wins=qualified && (ry==0 || new_area>best_area);
    wire [17:0] final_area=wins?new_area:best_area;
    wire [8:0] final_left=wins?new_left:best_left;
    wire [8:0] final_right=wins?new_right:best_right;
    wire [9:0] final_top=wins?new_top:best_top;
    wire [9:0] final_bottom=wins?ry:best_bottom;
    wire [11:0] xsum={1'b0,final_left,2'b00}+{1'b0,final_right,2'b11};
    wire [10:0] ysum={1'b0,final_top}+{1'b0,final_bottom};
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            run_left<=0;run_len<=0;row_len<=0;row_left<=0;row_right<=0;
            row_pending<=0;row_eof<=0;row_good<=0;ry<=0;rlength<=0;rl<=0;rr<=0;
            row_sid<=0;row_fid<=0;previous_left<=0;previous_right<=0;
            chain_active<=0;chain_left<=0;chain_right<=0;chain_top<=0;chain_area<=0;
            best_area<=0;best_left<=0;best_right<=0;best_top<=0;best_bottom<=0;
            ready<=0;result_valid<=0;present<=0;count<=0;
            res_sid<=0;res_fid<=0;xmin<=0;xmax<=0;cx<=0;ymin<=0;ymax<=0;cy<=0;
        end else begin
            ready<=row_pending && row_eof;
            row_pending<=valid && eol;
            if(valid)begin
                run_len<=eol?10'd0:next_len;
                if(hit && base_len==0)run_left<=bx;
                row_len<=eol?10'd0:win_len;
                if(longer)begin row_left<=next_left;row_right<=bx;end
                if(eol)begin
                    ry<=y;rlength<=win_len;rl<=win_left;rr<=win_right;
                    row_eof<=eof;row_good<=good;row_sid<=sid;row_fid<=fid;
                end
            end
            if(row_pending)begin
                chain_active<=row_ok;
                previous_left<=rl;previous_right<=rr;
                chain_area<=row_ok?new_area:18'd0;
                chain_left<=new_left;chain_right<=new_right;chain_top<=new_top;
                if(ry==0)best_area<=0;
                else if(wins)begin
                    best_area<=new_area;best_left<=new_left;best_right<=new_right;
                    best_top<=new_top;best_bottom<=ry;
                end
                if(row_eof)begin
                    res_sid<=row_sid;res_fid<=row_fid;result_valid<=row_good;
                    present<=row_good && final_area!=0;
                    count<=row_good?{final_area,2'b00}:20'd0;
                    xmin<=row_good && final_area!=0?{final_left,2'b00}:11'd0;
                    xmax<=row_good && final_area!=0?{final_right,2'b11}:11'd0;
                    cx<=row_good && final_area!=0?xsum[11:1]:11'd0;
                    ymin<=row_good && final_area!=0?final_top:10'd0;
                    ymax<=row_good && final_area!=0?final_bottom:10'd0;
                    cy<=row_good && final_area!=0?ysum[10:1]:10'd0;
                end
            end
        end
    end
endmodule
