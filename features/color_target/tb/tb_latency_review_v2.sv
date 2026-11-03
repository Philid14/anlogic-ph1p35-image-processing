`timescale 1ns/1ps
// Public-port review of LATENCY 87bb9a5. No MAIN adapter or physical CDC proof.
module tb_latency_review_v2;
    reg src=0,dst=0,drun=1,srst=0,drst=0;
    always #5 src=~src;
    always #7 if(drun)dst=~dst;
    reg be=0,br=0,bflush=0;reg [31:0] bf=0;
    wire [65:0] bd;wire bv,bgap,bloss;wire[7:0]blost;
    frame_event_bridge bridge(.clk_cap(src),.rst_cap_n(srst),.cap_event(be),.cap_kind(2'd0),.cap_sid(32'd1),.cap_fid(bf),
        .clk(dst),.rst_n(drst),.evt_ready(br),.flush_req(bflush),.evt_data(bd),.evt_valid(bv),.evt_gap_alarm(bgap),.lost_event(bloss),.lost_count(blost));
    reg me=0,de=0,clr=0,resync=0;reg[1:0]mk=0;reg[31:0]ms=1,mf=0,ds=1,df=0,auth=1;
    wire stats,fatal,lv,av;wire[3:0]alarm;wire[31:0]count,repeats,foreign,entries;wire[63:0]sum;
    latency_meter #(.TICK_BASE(2),.TICK_REMAINDER(0),.TICK_MOD(100000),.CROSS_CYCLES(3)) meter(
        .clk_cap(src),.rst_cap_n(srst),.cap_event(me),.cap_kind(mk),.cap_sid(ms),.cap_fid(mf),
        .clk(dst),.rst_n(drst),.dsp_event(de),.dsp_sid(ds),.dsp_fid(df),.auth_sid(auth),.auth_sid_vld(1'b1),
        .alarm_clr(clr),.resync_req(resync),.lat_valid(lv),.age_valid(av),.stats_valid(stats),.alarm(alarm),
        .stat_count(count),.repeat_count(repeats),.stat_sum_cycles(sum),.foreign_count(foreign),.fatal(fatal),.entry_count(entries));
    integer delivered=0,loss_seen=0,gap_seen=0,lat_pulses=0,age_pulses=0,checks=0,failures=0,i;
    always @(posedge dst)if(drst)begin
        if(br && bv)begin delivered=delivered+1;$display("V2_DELIVER sid=%0d fid=%0d kind=%0d",bd[63:32],bd[31:0],bd[65:64]);end
        if(bloss)loss_seen=loss_seen+1;
        if(bgap)gap_seen=gap_seen+1;
        if(lv)lat_pulses=lat_pulses+1;
        if(av)age_pulses=age_pulses+1;
    end
    task check(input string name,input[63:0]actual,input[63:0]expected);
        begin checks=checks+1;if(actual!==expected)failures=failures+1;
            $display("CHECK %s expected=%0d actual=%0d pass=%0d",name,expected,actual,actual===expected);end
    endtask
    task wd(input integer n);begin repeat(n)@(negedge dst);end endtask
    task reset_all;
        begin srst=0;drst=0;drun=1;be=0;br=0;bflush=0;me=0;de=0;clr=0;resync=0;auth=1;
            #100;@(negedge src);srst=1;@(negedge dst);drst=1;wd(40);
            delivered=0;loss_seen=0;gap_seen=0;lat_pulses=0;age_pulses=0;end
    endtask
    task bsend(input integer fid);
        begin @(negedge src);be=1;bf=fid;@(negedge src);be=0;repeat(3)@(negedge src);end
    endtask
    task msend(input integer kind,input integer sid,input integer fid);
        begin @(negedge src);me=1;mk=kind;ms=sid;mf=fid;@(negedge src);me=0;wd(16);end
    endtask
    task display_frame(input integer sid,input integer fid);
        begin @(negedge dst);de=1;ds=sid;df=fid;@(negedge dst);de=0;wd(5);end
    endtask
    task pair(input integer sid,input integer fid);
        begin msend(0,sid,fid);msend(2,sid,fid);display_frame(sid,fid);end
    endtask
    task sync_meter;
        begin @(negedge dst);resync=1;@(negedge dst);resync=0;wd(40);end
    endtask
    initial begin
        reset_all;pair(1,1);
        check("normal_first_count",count,1);check("normal_valid",stats,1);check("normal_no_fatal",fatal,0);
        display_frame(1,1);check("repeat_not_recounted",count,1);check("repeat_age_event",age_pulses,1);
        sync_meter;check("resync_count_zero",count,0);check("resync_sum_zero",sum,0);check("resync_invalid",stats,0);
        pair(1,2);check("resync_clean_pair",count,1);

        reset_all;@(negedge dst);drun=0;
        @(negedge src);be=1;bf=1;@(negedge src);be=0;
        @(negedge src);be=1;bf=2;@(negedge src);be=0;
        @(negedge src);be=1;bf=3;@(negedge src);be=0;
        repeat(10)@(negedge src);drun=1;wd(20);br=1;wd(30);
        check("two_losses_counted",blost,2);check("two_losses_visible",loss_seen>0,1);check("two_losses_one_delivery",delivered,1);

        reset_all;for(i=1;i<=20;i=i+1)bsend(i);wd(20);
        check("queue_full_lost_four",blost,4);br=1;wd(40);
        check("queue_full_accounted",delivered+blost,20);

        reset_all;auth=2;wd(10);msend(0,1,9);
        check("foreign_counted",foreign,1);check("foreign_not_inserted",entries,0);check("foreign_invalid",stats,0);
        sync_meter;pair(2,1);check("authoritative_pair_recovers",count,1);

        reset_all;for(i=1;i<=9;i=i+1)msend(0,1,i);
        check("overflow_latched_fatal",fatal,1);
        @(negedge dst);clr=1;@(negedge dst);clr=0;wd(5);
        pair(1,50);check("alarm_clear_not_recovery",count,0);check("fatal_survives_alarm_clear",fatal,1);
        sync_meter;pair(1,60);check("fatal_resync_recovers",count,1);

        reset_all;bsend(1);wd(10);drst=0;#100;drst=1;wd(40);br=1;wd(20);
        check("destination_reset_no_old_replay",delivered,0);
        bsend(2);wd(20);check("destination_reset_new_event",delivered,1);

        // Boundary probe: destination clock silent for a full 8-bit loss wrap.
        // Separate from the normal supported-service component controls above.
        reset_all;@(negedge dst);drun=0;
        for(i=1;i<=272;i=i+1)bsend(i);
        drun=1;wd(40);
        $display("WRAP_OBSERVATION offered=272 queued_expected=16 dropped_expected=256 lost_count=%0d lost_pulses=%0d",blost,loss_seen);
        check("loss_wrap_still_visible",loss_seen>0 || gap_seen>0,1);
        br=1;wd(40);check("loss_wrap_deliveries",delivered,16);
        $display("LATENCY_V2_REVIEW_COMPLETE checks=%0d failures=%0d",checks,failures);$finish;
    end
    initial begin #1000000;$fatal(1,"review timeout");end
endmodule
