// Independent integration requirements, not a replacement LATENCY regression.
// Only public ports form the oracle. Clock periods are fixtures, not board data.
`timescale 1ns/1ps
module tb_latency_handoff_review;
    parameter integer CASE_ID = 0;
    reg src = 0, dst = 0, dst_run = 1;
    always #5 src = ~src;
    always #7 if (dst_run) dst = ~dst;
    reg srst = 0, drst = 0;
    reg be = 0, br = 0;
    reg [1:0] bk = 0;
    reg [31:0] bs = 1, bf = 0;
    wire bt, bv, bg;
    wire [65:0] bd;
    frame_event_bridge #(.SID_W(32), .FID_W(32), .DEPTH_LOG2(4)) bridge(.clk_cap(src), .rst_cap_n(srst),
        .cap_event(be), .cap_kind(bk), .cap_sid(bs), .cap_fid(bf),
        .cap_too_fast(bt), .clk(dst), .rst_n(drst), .evt_ready(br),
        .evt_data(bd), .evt_valid(bv), .evt_gap_alarm(bg));

    reg me = 0, de = 0, clr = 0, resync = 0;
    reg [1:0] mk = 0;
    reg [31:0] ms = 1, mf = 0, ds = 1, df = 0;
    wire mt, lv, av, stats;
    wire [3:0] alarm;
    wire [31:0] count, caps, dones, repeats;
    wire [63:0] sum;
    latency_meter #(.TICK_BASE(2), .TICK_REMAINDER(0),
        .TICK_MOD(100000), .CROSS_CYCLES(3)) meter(
        .clk_cap(src), .rst_cap_n(srst), .cap_event(me), .cap_kind(mk),
        .cap_sid(ms), .cap_fid(mf), .cap_too_fast(mt),
        .clk(dst), .rst_n(drst), .dsp_event(de), .dsp_sid(ds), .dsp_fid(df),
        .alarm_clr(clr), .resync_req(resync), .lat_valid(lv),
        .age_valid(av), .stats_valid(stats), .alarm(alarm), .stat_count(count),
        .stat_sum_cycles(sum), .cap_count(caps), .cap_done_count(dones),
        .repeat_count(repeats), .lat_cycles(), .lat_ticks(), .lat_seen(),
        .age_cycles(), .age_ticks(), .age_seen(), .cap_abort_count(),
        .dsp_count(), .unmatched_count(), .stat_sum_ticks(), .cap_fps(),
        .dsp_fps(), .fps_valid(), .entry_count(), .evt_gap_alarm(),
        .lost_done_count(), .lost_abort_count());

    integer checks = 0, setup_failures = 0, requirement_failures = 0;
    integer delivered = 0, bridge_alarm_seen = 0, sequence_errors = 0;
    integer lat_pulses = 0, age_pulses = 0, meter_alarm_seen = 0;
    integer next_fid = 1, offered = 0, i, saved;
    integer source_drop_toggles = 0;
    reg previous_mt = 0;
    integer bridge_drop_toggles = 0, source_cycle = 0;
    integer previous_offer_cycle = -1, minimum_offer_gap = 65535;
    reg previous_bt = 0, previous_be = 0;
    reg check_sequence = 0;
    always @(posedge src) if (srst) begin
        source_cycle = source_cycle + 1;
        if (be && !previous_be) begin
            if (previous_offer_cycle >= 0 &&
                source_cycle-previous_offer_cycle < minimum_offer_gap)
                minimum_offer_gap = source_cycle-previous_offer_cycle;
            previous_offer_cycle = source_cycle;
        end
        previous_be = be;
    end
    always @(negedge src) if (srst) begin
        if (mt !== previous_mt) begin
            source_drop_toggles = source_drop_toggles + 1;
            $display("SOURCE_DROP_TOGGLE value=%0d",mt);
        end
        previous_mt = mt;
        if (bt !== previous_bt) bridge_drop_toggles = bridge_drop_toggles + 1;
        previous_bt = bt;
    end
    always @(posedge dst) if (drst) begin
        if (bg) bridge_alarm_seen = 1;
        if (alarm[2]) meter_alarm_seen = 1;
        if (br && bv) begin
            delivered = delivered + 1;
            $display("DELIVER fid=%0d sid=%0d kind=%0d", bd[31:0], bd[63:32], bd[65:64]);
            if (check_sequence && bd !== {2'd0,32'd1,next_fid[31:0]})
                sequence_errors = sequence_errors + 1;
            next_fid = next_fid + 1;
        end
        // NBA outputs from the preceding edge are still a whole-cycle pulse.
        if (lv) lat_pulses = lat_pulses + 1;
        if (av) age_pulses = age_pulses + 1;
    end

    task check;
        input integer is_setup;
        input [8*90-1:0] label;
        input [63:0] actual, expected;
        begin
            checks = checks + 1;
            $display("CHECK setup=%0d name=%0s expected=%0d actual=%0d pass=%0d",
                is_setup,label,expected,actual,(actual === expected));
            if (actual !== expected) begin
                if (is_setup) setup_failures = setup_failures + 1;
                else requirement_failures = requirement_failures + 1;
            end
        end
    endtask
    task wait_dst; input integer n; begin repeat(n) @(negedge dst); end endtask
    task bsend;
        input integer fid;
        begin
            @(negedge src); be=1; bf=fid; offered=offered+1;
            @(negedge src); be=0;
            // Next invocation adds its own leading edge: 1 high + 3 low +
            // that leading edge gives exactly five cycles between rises.
            repeat(3) @(negedge src);
        end
    endtask
    task msend;
        input integer kind, sid, fid;
        begin
            @(negedge src); me=1; mk=kind; ms=sid; mf=fid;
            @(negedge src); me=0;
            repeat(4) @(negedge src);
        end
    endtask
    task msettled;
        input integer kind, sid, fid;
        begin msend(kind,sid,fid); wait_dst(12); end
    endtask
    task display_frame;
        input integer sid, fid;
        begin
            @(negedge dst); de=1; ds=sid; df=fid;
            @(negedge dst); de=0;
            wait_dst(4);
        end
    endtask
    task pair;
        input integer sid, fid;
        begin msettled(0,sid,fid); msettled(2,sid,fid); display_frame(sid,fid); end
    endtask
    task sparse_drain;
        input integer n;
        begin
            repeat(n) begin
                @(negedge dst); br=1;
                @(negedge dst); br=0;
                wait_dst(5);
            end
        end
    endtask

    initial begin
        $display("CASE id=%0d",CASE_ID);
        repeat(4) @(negedge src);
        srst=1; drst=1;
        wait_dst(8);
        case(CASE_ID)
        0: begin
            pair(1,1);
            check(1,"normal_complete_first_display",count,1);
            check(0,"normal_stats_valid",stats,1);
            display_frame(1,1);
            check(0,"repeat_not_new_observation",count,1);
            check(0,"repeat_reports_age",repeats,1);
            check(0,"normal_no_alarm",alarm,0);
        end
        1: begin
            pair(1,1);
            check(1,"prior_window_exists",count,1);
            @(negedge dst); resync=1;
            @(negedge dst); resync=0;
            wait_dst(4);
            check(0,"resync_count_zero",count,0);
            check(0,"resync_sum_zero",sum,0);
            check(0,"resync_invalid_until_clean_pair",stats,0);
            pair(1,2);
            check(0,"new_window_one_pair",count,1);
            check(0,"new_window_valid",stats,1);
        end
        2: begin
            check_sequence=1;
            for(i=1;i<=20;i=i+1) bsend(i);
            check(1,"offered_twenty_legal_gap_events",offered,20);
            check(1,"source_input_gap_is_five_cycles",minimum_offer_gap,5);
            wait_dst(8);
            sparse_drain(24);
            check(1,"delivered_payloads_arrive_in_order",sequence_errors,0);
            $display("OBS offered=%0d delivered=%0d source_loss_transitions=%0d destination_alarm=%0d",
                offered,delivered,bridge_drop_toggles,bridge_alarm_seen);
            check(0,"all_events_delivered_or_loss_visible",
                ((delivered==offered) || (bridge_drop_toggles>0) || bridge_alarm_seen),1);
        end
        3: begin
            // Stop safely on the low phase: two rejected rises happen entirely
            // between destination samples. One accepted payload cannot cause
            // a destination inter-pop alarm when the clock resumes.
            @(negedge dst); dst_run=0;
            @(negedge src); me=1; mk=0; ms=1; mf=1;
            @(negedge src); me=0;
            @(negedge src); me=1; mf=2;
            @(negedge src); me=0;
            @(negedge src); me=1; mf=3;
            @(negedge src); me=0;
            repeat(4) @(negedge src);
            check(1,"exactly_two_source_drop_toggles",source_drop_toggles,2);
            check(1,"two_drops_restore_toggle_to_initial_value",mt,0);
            dst_run=1; wait_dst(20);
            check(1,"one_accepted_event_survives",caps,1);
            check(0,"two_dropped_events_are_visible",meter_alarm_seen,1);
        end
        4: begin
            // Fill all eight association records with unfinished captures.
            // The ninth evicts a pending record, then that same new record
            // completes/displays without resync or a new trusted epoch.
            for(i=1;i<=9;i=i+1) msettled(0,1,i);
            check(1,"pending_table_overflow_alarm",alarm[1],1);
            check(1,"overflow_makes_stats_invalid",stats,0);
            @(negedge dst); clr=1;
            @(negedge dst); clr=0;
            wait_dst(4);
            check(1,"clear_alarm_does_not_itself_restore_stats",stats,0);
            msettled(2,1,9); display_frame(1,9);
            check(0,"overflow_cannot_recover_without_resync",stats,0);
            check(0,"overflow_window_rejects_new_statistic",count,0);
        end
        5: begin
            pair(1,1); pair(2,1);
            check(1,"new_session_pair_accepted",lat_pulses,2);
            saved=lat_pulses;
            // Old source traffic is data, not authority to switch back.
            pair(1,2);
            check(0,"retired_session_cannot_reopen_from_data",lat_pulses-saved,0);
        end
        6: begin
            bsend(11); wait_dst(8); sparse_drain(2);
            check(1,"one_event_delivered_before_destination_reset",delivered,1);
            @(negedge dst); drst=0;
            wait_dst(4); drst=1;
            wait_dst(8); sparse_drain(3);
            check(0,"one_sided_reset_must_not_replay_retired_payload",delivered,1);
        end
        7: begin
            // Resync clears the meter table, not its bridge FIFO. The queued
            // pre-barrier traffic must be drained/cancelled by MAIN explicitly.
            @(negedge dst); dst_run=0;
            msend(0,1,7); msend(2,1,7);
            resync=1; dst_run=1;
            @(negedge dst); resync=0;
            wait_dst(20);
            check(1,"queued_old_events_have_arrived",caps,1);
            display_frame(1,7);
            check(0,"table_resync_alone_cannot_certify_epoch_barrier",count,0);
        end
        8: begin
            // Positive control: the existing toggle path does convey a single
            // pending error. Two-error failure is not just a dead monitor.
            @(negedge dst); dst_run=0;
            @(negedge src); me=1; mk=0; ms=1; mf=1;
            @(negedge src); me=0;
            @(negedge src); me=1; mf=2;
            @(negedge src); me=0;
            repeat(4) @(negedge src);
            check(1,"exactly_one_source_drop_toggle",source_drop_toggles,1);
            dst_run=1; wait_dst(20);
            check(1,"single_error_control_keeps_accepted_event",caps,1);
            check(0,"single_pending_error_is_visible",meter_alarm_seen,1);
        end
        default: begin check(1,"known_case",CASE_ID,0); end
        endcase
        $display("LATENCY_REVIEW_COMPLETE id=%0d checks=%0d setup_failures=%0d requirement_failures=%0d",
            CASE_ID,checks,setup_failures,requirement_failures);
        $finish;
    end
    initial begin #200000; $display("** Error: watchdog expired"); $finish; end
endmodule
