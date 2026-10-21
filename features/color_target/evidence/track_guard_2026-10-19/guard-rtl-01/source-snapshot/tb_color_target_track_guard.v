`timescale 1ns/1ps
// Literal external expectations; no DUT internals or reference-model calls.
module tb_color_target_track_guard;
    parameter integer TIME_W=8;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, start=0, time_valid=1, strobe=0, identity=1;
    reg valid=1, cancelled=0, present=1;
    reg [31:0] control=0, session=0, frame=0;
    reg [TIME_W-1:0] now_tick=0, captured=0;
    wire ready, event_seen, retired, admitted, timeout_event;
    wire [7:0] reason;
    wire [1:0] state;
    wire usable, reliable_valid, positive_valid;
    wire [31:0] current_sid, obs_sid, obs_frame, box_sid, box_frame;
    wire [TIME_W-1:0] reliable_age, positive_age, reliable_tick, positive_tick;
    wire [1:0] color;
    wire [19:0] count;
    wire [10:0] xmin,xmax,cx;
    wire [9:0] ymin,ymax,cy;
    wire [1:0] duplicates,reorders,wrong_sessions,identity_errors,invalids,cancels,stales,time_errors,timeouts;
    color_target_track_guard #(.TIME_W(TIME_W),.COUNTER_W(2),
        .ACQ_FRAMES(2),.LOST_FRAMES(2),.MAX_TARGET_AGE_TICKS(5),.MAX_RELIABLE_AGE_TICKS(5)) dut (
        .clk(clk),.rst_n(rst_n),.I_session_start(start),.I_control_session_id(control),
        .I_time_valid(time_valid),.I_now_tick(now_tick),.I_result_strobe(strobe),.I_identity_valid(identity),
        .I_session_id(session),.I_frame_id(frame),.I_result_valid(valid),.I_cancelled(cancelled),
        .I_target_present(present),.I_capture_tick(captured),.I_color_class(2'd2),.I_pixel_count(20'd22),
        .I_xmin(11'd10),.I_xmax(11'd20),.I_center_x(11'd15),.I_ymin(10'd5),.I_ymax(10'd9),.I_center_y(10'd7),
        .O_session_ready(ready),.O_current_session_id(current_sid),.O_event_strobe(event_seen),
        .O_retired_strobe(retired),.O_admitted_strobe(admitted),.O_reason(reason),.O_timeout_strobe(timeout_event),
        .O_track_state(state),.O_observation_usable(usable),.O_reliable_valid(reliable_valid),.O_positive_valid(positive_valid),
        .O_observation_session_id(obs_sid),.O_observation_frame_id(obs_frame),.O_box_session_id(box_sid),.O_box_frame_id(box_frame),
        .O_reliable_age(reliable_age),.O_positive_age(positive_age),.O_reliable_tick(reliable_tick),.O_positive_tick(positive_tick),
        .O_color_class(color),.O_pixel_count(count),.O_xmin(xmin),.O_xmax(xmax),.O_center_x(cx),
        .O_ymin(ymin),.O_ymax(ymax),.O_center_y(cy),
        .O_duplicate_count(duplicates),.O_reorder_count(reorders),.O_wrong_session_count(wrong_sessions),
        .O_identity_error_count(identity_errors),.O_invalid_count(invalids),.O_cancelled_count(cancels),
        .O_stale_result_count(stales),.O_time_error_count(time_errors),.O_timeout_count(timeouts));

    integer checks=0, failures=0, n;
    task check;
        input [511:0] name; input condition;
        begin checks=checks+1;
            if (condition!==1'b1) begin failures=failures+1;
                $display("FAIL guard %0s reason=%0d retired=%0d admitted=%0d state=%0d usable=%0d box=%0d obs=%0d",name,reason,retired,admitted,state,usable,box_frame,obs_frame);
            end
        end
    endtask
    task expect_event;
        input [511:0] name; input [7:0] want_reason;
        input want_retired,want_admitted; input [1:0] want_state; input want_usable;
        begin check(name,event_seen && reason==want_reason && retired==want_retired &&
            admitted==want_admitted && state==want_state && usable==want_usable);end
    endtask
    task idle;
        input [TIME_W-1:0] at;
        begin @(negedge clk);start=0;strobe=0;now_tick=at;@(posedge clk);#1;end
    endtask
    task begin_session;
        input [31:0] sid; input [TIME_W-1:0] at;
        begin @(negedge clk);start=1;strobe=0;control=sid;now_tick=at;time_valid=1;
            @(posedge clk);#1;check("control barrier",reason==12 && !usable && !retired && !admitted);
            idle(at);check("session ready",ready && current_sid==sid && state==0 && !usable);
        end
    endtask
    task event;
        input [31:0] sid,fid; input [TIME_W-1:0] at,cap;
        input v,c,p,id_ok;
        begin @(negedge clk);start=0;strobe=1;session=sid;frame=fid;now_tick=at;captured=cap;
            valid=v;cancelled=c;present=p;identity=id_ok;@(posedge clk);#1;end
    endtask
    task reset;
        begin @(negedge clk);rst_n=0;start=0;strobe=0;time_valid=1;now_tick=0;
            repeat(2) @(posedge clk);@(negedge clk);rst_n=1;idle(0);
            check("reset masks all metadata",!ready && !usable && state==0 && !reliable_valid && !positive_valid && count==0 && box_frame==0);
        end
    endtask
    task tracked;
        begin reset;begin_session(1,0);
            event(1,1,0,0,1,0,1,1);expect_event("acquire first",1,1,1,1,0);
            event(1,2,0,0,1,0,1,1);expect_event("acquire second",1,1,1,2,1);
        end
    endtask
    initial begin
        reset;
        event(1,1,0,0,1,0,1,1);expect_event("no implicit session",15,0,0,0,0);
        $display("CASE no_implicit_session");
        begin_session(1,0);
        event(1,99,1,1,1,0,1,1);expect_event("first unique",1,1,1,1,0);
        repeat(2) begin event(1,99,1,1,1,0,1,1);expect_event("duplicate cannot acquire",5,0,0,1,0);end
        event(1,98,1,1,1,0,1,1);expect_event("reorder cannot acquire",6,0,0,1,0);
        event(2,1000,1,1,1,0,1,1);expect_event("data cannot change session",7,0,0,1,0);
        event(1,100,2,2,1,0,1,1);expect_event("second unique confirms",1,1,1,2,1);
        check("payload and real SID, not private token",box_sid==1 && box_frame==100 && obs_sid==1 && obs_frame==100 && color==2 && count==22 && xmin==10 && xmax==20 && cx==15 && ymin==5 && ymax==9 && cy==7);
        $display("CASE duplicate_reorder_and_payload");
        event(1,100,7,7,1,0,1,1);expect_event("duplicate boundary no refresh",5,0,0,2,1);
        check("capture age is five",positive_age==5 && positive_tick==2);
        idle(8);check("silent expiry",!usable && state==0 && timeout_event && timeouts==1 && !positive_valid && count==0);
        idle(9);check("timeout is one event",!timeout_event && timeouts==1);
        event(1,100,9,9,1,0,1,1);expect_event("expiry retains high water",5,0,0,0,0);
        event(1,101,9,9,1,0,1,1);expect_event("fresh after expiry re-acquires",1,1,1,1,0);
        event(1,102,9,9,1,0,1,1);expect_event("fresh second after expiry",1,1,1,2,1);
        $display("CASE independent_age_and_high_water");

        reset;begin_session(1,0);
        event(1,1,0,0,1,0,1,1);
        event(1,2,1,200,0,0,1,1);expect_event("invalid does not miss",3,1,0,1,0);
        event(1,2,1,1,1,0,1,1);expect_event("invalid key already retired",5,0,0,1,0);
        event(1,3,2,200,1,1,1,1);expect_event("cancel dominates valid and timestamp",4,1,0,1,0);
        event(1,3,2,2,1,0,1,1);expect_event("cancelled key already retired",5,0,0,1,0);
        event(1,4,3,3,1,0,1,1);expect_event("invalid does not fabricate absence",1,1,1,2,1);
        check("separate dispositions",invalids==1 && cancels==1 && time_errors==0);
        event(1,5,4,4,1,0,0,1);expect_event("first valid absence",2,1,1,3,1);
        check("HOLD preserves positive identity",box_frame==4 && obs_frame==5 && positive_tick==3 && reliable_tick==4);
        event(1,6,4,4,1,0,0,1);expect_event("second valid absence",2,1,1,0,0);
        $display("CASE invalid_cancel_and_absence");

        tracked;
        event(1,3,5,5,1,0,0,1);expect_event("absence is reliable but no target refresh",2,1,1,3,1);
        check("distinct ages",positive_age==5 && reliable_age==0 && positive_tick==0);
        idle(6);check("absence cannot extend positive age",!usable && timeout_event && state==0);
        $display("CASE no_target_never_refreshes_positive_age");
        tracked;
        for(n=1;n<=6;n=n+1) begin
            event(1,n+2,n,0,0,0,0,1);
            if(n<=5)expect_event("invalid stream retains until real timeout",3,1,0,2,1);
            else expect_event("invalid stream expiry",3,1,0,0,0);
        end
        check("invalid saturation and one timeout",invalids==3 && timeouts==1);
        $display("CASE invalid_stream_timeout");

        reset;begin_session(1,10);
        event(1,1,10,4,1,0,1,1);expect_event("late arrival stays old",9,1,0,0,0);
        event(1,1,10,10,1,0,1,1);expect_event("stale key cannot be rewritten",5,0,0,0,0);
        event(1,2,10,11,1,0,1,1);expect_event("future time rejected",10,1,0,0,0);
        event(1,2,10,10,1,0,1,1);expect_event("future key retired",5,0,0,0,0);
        event(1,3,10,10,1,0,1,1);expect_event("first recent result",1,1,1,1,0);
        event(1,1000,10,10,1,0,1,0);expect_event("untrusted identity cannot poison high water",8,0,0,1,0);
        event(1,4,11,11,1,0,1,1);expect_event("real next identity still accepted",1,1,1,2,1);
        check("stale future identity distinct",stales==1 && time_errors==1 && identity_errors==1);
        $display("CASE late_future_and_unavailable_identity");
        event(2,0,11,11,0,0,0,1);expect_event("new SID data is not restart",7,0,0,2,1);
        begin_session(2,11);
        event(2,0,11,11,0,0,0,1);expect_event("new session invalid first result",3,1,0,0,0);
        event(1,9999,11,11,1,0,1,1);expect_event("old session cannot return",7,0,0,0,0);
        event(2,1,11,11,1,0,1,1);expect_event("new session first positive starts fresh",1,1,1,1,0);
        event(2,2,11,11,1,0,1,1);expect_event("new session second confirms",1,1,1,2,1);
        check("external SID survives core restart token",box_sid==2 && obs_sid==2);
        $display("CASE explicit_session_authority");

        tracked;begin_session(2,0);begin_session(3,0);
        event(3,0,0,0,1,0,1,1);expect_event("two empty epochs do not alias core",1,1,1,1,0);
        event(3,1,0,0,1,0,1,1);expect_event("new run second positive",1,1,1,2,1);
        $display("CASE repeated_empty_epoch_barriers");
        @(negedge clk);start=1;strobe=0;control=3;@(posedge clk);#1;
        check("same SID control reuse fails closed",reason==14 && !usable && !ready);
        idle(0);event(3,2,0,0,1,0,1,1);expect_event("needs genuine new SID",15,0,0,0,0);
        $display("CASE session_reuse_rejected");
        begin_session(4,0);
        @(negedge clk);start=1;control=5;strobe=1;session=5;frame=1;@(posedge clk);#1;
        expect_event("control beats same cycle data",12,0,0,0,0);
        event(5,1,0,0,1,0,1,1);expect_event("boundary data can be delivered after barrier",1,1,1,1,0);
        $display("CASE simultaneous_control_and_data");

        tracked;@(negedge clk);time_valid=0;strobe=0;@(posedge clk);#1;
        check("time loss closes run",state==0 && !usable && !ready && time_errors==1);
        @(negedge clk);time_valid=1;@(posedge clk);#1;
        event(1,3,1,1,1,0,1,1);expect_event("time restoration alone cannot reopen",15,0,0,0,0);
        begin_session(2,1);event(2,0,1,1,1,0,1,1);expect_event("new controlled epoch recovers time loss",1,1,1,1,0);
        $display("CASE time_valid_loss_and_recovery");
        reset;begin_session(1,10);event(1,1,10,10,1,0,1,1);
        idle(9);check("backward time closes run",!ready && state==0 && time_errors==1);
        $display("CASE clock_rollback");
        reset;begin_session(1,{TIME_W{1'b1}}-1'b1);
        event(1,1,{TIME_W{1'b1}}-1'b1,{TIME_W{1'b1}}-1'b1,1,0,1,1);
        idle({TIME_W{1'b1}});idle(0);
        check("time wrap requires new epoch",!ready && !usable && time_errors==1);
        $display("CASE clock_wrap");
        reset;begin_session(1,0);
        event(1,32'hffffffff,0,0,1,0,1,1);
        event(1,0,0,0,1,0,1,1);expect_event("frame wrap rejected",6,0,0,1,0);
        begin_session(2,0);event(2,0,0,0,1,0,1,1);expect_event("frame zero valid in new session",1,1,1,1,0);
        $display("CASE frame_id_wrap");

        tracked;
        for(n=0;n<7;n=n+1) begin
            event(1,2,0,0,1,0,1,1);event(1,1,0,0,1,0,1,1);
            event(99,3,0,0,1,0,1,1);event(1,1000,0,0,1,0,1,0);
        end
        check("diagnostics saturate independently",duplicates==3 && reorders==3 && wrong_sessions==3 && identity_errors==3 && usable);
        $display("CASE counter_saturation");
        tracked;
        for(n=3;n<=260;n=n+1) begin
            event(1,n,0,0,1,0,1,1);expect_event("one event each clock without queue or reset bubble",1,1,1,2,1);
        end
        check("latest payload identity at sustained service",box_frame==260 && obs_frame==260);
        $display("CASE one_result_per_clock");
        tracked;
        event(1,3,6,6,1,0,1,1);expect_event("fresh event simultaneous with expiry starts ACQ",1,1,1,1,0);
        check("same cycle expiry counted",timeout_event && timeouts==1 && positive_tick==6);
        event(1,4,6,6,1,0,1,1);expect_event("no reset bubble after expiry",1,1,1,2,1);
        $display("CASE simultaneous_expiry_and_fresh_result");
        $display("GUARD_COMPLETE checks=%0d failures=%0d",checks,failures);
        $finish;
    end
    initial begin #100000; $display("FAIL guard timeout");$finish;end
endmodule

module tb_color_target_track_guard_limits;
    parameter integer TARGET_AGE=3, RELIABLE_AGE=7, MODE=1;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,start=0,strobe=0,present=1;
    reg [7:0] now_tick=0,captured=0;
    reg [31:0] frame=0;
    wire ready,admitted,retired,usable,timeout_event,reliable_valid,positive_valid;
    wire [7:0] reason;
    wire [1:0] state;
    integer checks=0,failures=0;
    color_target_track_guard #(.TIME_W(8),.ACQ_FRAMES(2),.LOST_FRAMES(2),
        .MAX_TARGET_AGE_TICKS(TARGET_AGE),.MAX_RELIABLE_AGE_TICKS(RELIABLE_AGE)) dut (
        .clk(clk),.rst_n(rst_n),.I_session_start(start),.I_control_session_id(32'd1),
        .I_time_valid(1'b1),.I_now_tick(now_tick),.I_result_strobe(strobe),.I_identity_valid(1'b1),
        .I_session_id(32'd1),.I_frame_id(frame),.I_result_valid(1'b1),.I_cancelled(1'b0),
        .I_target_present(present),.I_capture_tick(captured),.I_color_class(2'd0),.I_pixel_count(20'd4),
        .I_xmin(11'd0),.I_xmax(11'd3),.I_center_x(11'd1),.I_ymin(10'd0),.I_ymax(10'd0),.I_center_y(10'd0),
        .O_session_ready(ready),.O_admitted_strobe(admitted),.O_retired_strobe(retired),.O_reason(reason),
        .O_observation_usable(usable),.O_timeout_strobe(timeout_event),.O_track_state(state),
        .O_reliable_valid(reliable_valid),.O_positive_valid(positive_valid));
    task check;
        input condition;
        begin checks=checks+1;if(condition!==1'b1)begin failures=failures+1;
            $display("FAIL limits mode=%0d reason=%0d state=%0d usable=%0d",MODE,reason,state,usable);end end
    endtask
    task tick;
        input [7:0] at;input send;input has_target;
        begin @(negedge clk);start=0;now_tick=at;captured=at;strobe=send;present=has_target;
            frame=frame+1;@(posedge clk);#1;end
    endtask
    initial begin
        repeat(2)@(posedge clk);@(negedge clk);rst_n=1;start=1;
        @(posedge clk);#1;
        if(MODE==0)begin
            check(reason==13 && !ready && !usable);
            tick(0,1,1);check(reason==13 && !admitted && !retired && !usable);
            $display("CASE disabled_or_unrepresentable_limits");
        end else begin
            check(reason==12);
            tick(0,1,1);check(ready && admitted && state==1 && !usable);
            tick(0,1,1);check(admitted && state==2 && usable);
            if(MODE==1)begin
                tick(3,1,0);check(state==3 && usable && reliable_valid && positive_valid);
                tick(4,0,0);check(state==0 && !usable && timeout_event && !positive_valid);
                $display("CASE positive_age_independent_of_reliable_age");
            end else if(MODE==2)begin
                tick(4,1,0);check(reason==2 && admitted && timeout_event && state==0 && !usable && reliable_valid && !positive_valid);
                $display("CASE reliable_watchdog_independent_of_target_limit");
            end else begin
                tick(255,0,0);check(usable && !timeout_event);
                tick(0,0,0);check(!ready && !usable);
                $display("CASE largest_unsigned_age_then_time_wrap");
            end
        end
        $display("GUARD_COMPLETE checks=%0d failures=%0d",checks,failures);$finish;
    end
    initial begin #2000;$display("FAIL limits timeout");$finish;end
endmodule
