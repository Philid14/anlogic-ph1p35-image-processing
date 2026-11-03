`timescale 1ns/1ps
// Production guard + overlay + text in a TEST-ONLY display scheduling prototype.
// Independent observation/display clocks. stage_annotation is an explicit
// abstract atomic transfer, NOT a physical CDC circuit or MAIN implementation.
module tb_display_transactions;
  parameter integer MUTATION=0;
  localparam [63:0] AGE=10000;
  reg clk=0,dclk=0,rst_n=0,clock_running=1;
  always #5 if(clock_running) clk=~clk;
  always #7 dclk=~dclk;
  reg [63:0] counter=0,bias=0;
  always @(posedge clk) counter<=counter+1;
  wire [63:0] now_tick=counter+bias;
  reg session_start=0,time_valid=1,strobe=0,identity_valid=1;
  reg [31:0] control_sid=0,sid=0,fid=0;
  reg valid=1,cancelled=0,present=1;
  reg [63:0] captured=0;
  reg [19:0] count=0;
  reg [10:0] xmin=0,xmax=0,cx=0;
  reg [9:0] ymin=0,ymax=0,cy=0;
  wire ready,usable;
  wire [31:0] current_sid,box_sid,box_fid;
  wire [7:0] reason;
  wire [1:0] state;
  wire [19:0] gc;
  wire [10:0] gxmin,gxmax,gcx;
  wire [9:0] gymin,gymax,gcy;
  wire [63:0] positive_tick;
  color_target_track_guard #(.MAX_TARGET_AGE_TICKS(10000),.MAX_RELIABLE_AGE_TICKS(10000)) guard(
    .clk(clk),.rst_n(rst_n),.I_session_start(session_start),.I_control_session_id(control_sid),
    .I_time_valid(time_valid),.I_now_tick(now_tick),.I_result_strobe(strobe),.I_identity_valid(identity_valid),
    .I_session_id(sid),.I_frame_id(fid),.I_result_valid(valid),.I_cancelled(cancelled),.I_target_present(present),
    .I_capture_tick(captured),.I_color_class(2'd0),.I_pixel_count(count),
    .I_xmin(xmin),.I_xmax(xmax),.I_center_x(cx),.I_ymin(ymin),.I_ymax(ymax),.I_center_y(cy),
    .O_session_ready(ready),.O_current_session_id(current_sid),.O_reason(reason),.O_track_state(state),
    .O_observation_usable(usable),.O_box_session_id(box_sid),.O_box_frame_id(box_fid),
    .O_positive_tick(positive_tick),.O_pixel_count(gc),.O_xmin(gxmin),.O_xmax(gxmax),.O_center_x(gcx),
    .O_ymin(gymin),.O_ymax(gymax),.O_center_y(gcy));

  reg prepared=0,prepared_show=0;
  reg [31:0] psid=0,pfid=0;
  reg [31:0] pslot=0,pgen=0;
  reg [63:0] pcapture=0;
  reg [1:0] pstate=0;
  reg [19:0] pc=0;
  reg [10:0] pxmin=0,pxmax=0,pcx=0;
  reg [9:0] pymin=0,pymax=0,pcy=0;
  reg scan_active=0,scan_show=0;
  reg [31:0] dsid=0,dfid=0,dslot=0,dgen=0;
  reg [63:0] display_ticks=0,scan_start_display_tick=0,scan_start_age=0;
  reg display_fault=0;
  always @(posedge dclk) display_ticks<=display_ticks+1;
  // Test-only independent reference conversion: source tick 10ns, display
  // tick 14ns. This is not a proposed synthesizable frequency converter.
  wire [63:0] scan_age=scan_start_age+(display_ticks-scan_start_display_tick)*14/10;
  always @(posedge dclk) begin
    if(!rst_n) display_fault<=0;
    else if(scan_active && scan_age>AGE && MUTATION!=5) display_fault<=1;
  end
  reg [10:0] x=0;
  reg [9:0] y=0;
  wire scan_enable=scan_active && scan_show && rst_n && time_valid && ready &&
      !session_start && dsid==current_sid && !display_fault &&
      ((MUTATION==5)||scan_age<=AGE);
  wire [10:0] draw_xmin=(MUTATION==2 && scan_active)?gxmin:pxmin;
  wire [10:0] draw_xmax=(MUTATION==2 && scan_active)?gxmax:pxmax;
  wire [9:0] draw_ymin=(MUTATION==2 && scan_active)?gymin:pymin;
  wire [9:0] draw_ymax=(MUTATION==2 && scan_active)?gymax:pymax;
  wire [10:0] draw_cx=(MUTATION==2 && scan_active)?gcx:pcx;
  wire [9:0] draw_cy=(MUTATION==2 && scan_active)?gcy:pcy;
  wire box_valid,text_valid;
  wire [23:0] box_rgb,text_rgb;
  wire [7:0] glyph;
  wire [3:0] glyph_row;
  color_target_overlay #(.BOX_THICK(1),.CROSS_ARM(2)) box(
    .I_pixel_valid(scan_enable),.I_x(x),.I_y(y),.I_result_valid(scan_enable),.I_target_present(scan_enable),
    .I_xmin(draw_xmin),.I_xmax(draw_xmax),.I_ymin(draw_ymin),.I_ymax(draw_ymax),
    .I_center_x(draw_cx),.I_center_y(draw_cy),.O_overlay_valid(box_valid),.O_overlay_rgb(box_rgb));
  color_target_text_overlay #(.X0(16),.Y0(16)) text(
    .clk(dclk),.rst_n(rst_n),.I_pixel_valid(scan_enable),.I_x(x),.I_y(y),.I_update(1'b0),
    .I_show(prepared_show),.I_state(pstate),.I_count(pc),.I_center_x(pcx),.I_center_y(pcy),
    .O_glyph_char(glyph),.O_glyph_row(glyph_row),.I_glyph_bits(16'hffff),
    .O_overlay_valid(text_valid),.O_overlay_rgb(text_rgb));

  integer checks=0,failures=0;
  task check_condition;
    input condition;input [511:0] label;
    begin checks=checks+1;if(condition!==1'b1)begin failures=failures+1;$display("FAIL %0s",label);end end
  endtask
  task begin_session;
    input [31:0] value;
    begin
      @(negedge clk);control_sid=value;session_start=1;
      @(posedge clk);#1;check_condition(reason==12,"session barrier reason");
      @(negedge clk);session_start=0;
      @(negedge dclk);prepared=0;display_fault=0;
    end
  endtask
  task deliver;
    input [31:0] s,f;
    input v,c,p;
    input [19:0] n;
    input [10:0] center_x;
    input [9:0] center_y;
    input integer time_offset;
    input [7:0] wanted;
    begin
      @(negedge clk);sid=s;fid=f;valid=v;cancelled=c;present=p;count=n;
      cx=center_x;cy=center_y;xmin=p?center_x-10:0;xmax=p?center_x+10:0;
      ymin=p?center_y-10:0;ymax=p?center_y+10:0;captured=now_tick+time_offset;strobe=1;
      @(posedge clk);#1;check_condition(reason==wanted,"guard result disposition");
      @(negedge clk);strobe=0;
    end
  endtask
  task stage_annotation;
    input [31:0] slot,generation;
    begin
      @(negedge dclk);
      if(scan_active)begin
        check_condition(1,"prepare while scanning is deferred");
      end else begin
        // This testbench transfer is deliberately atomic. A real implementation
        // still needs a proven mailbox/FIFO, capacity and reset transaction.
        psid=box_sid;pfid=box_fid;pslot=slot;pgen=generation;pcapture=positive_tick;
        prepared_show=usable;pstate=state;pc=gc;pxmin=gxmin;pxmax=gxmax;
        pymin=gymin;pymax=gymax;pcx=gcx;pcy=gcy;
        prepared=(MUTATION==4);
      end
    end
  endtask
  // Deliberately use the documented 140-clock stable-input bound plus one
  // handoff clock. This is a harness schedule, not a new completion RTL port.
  task wait_text;
    begin repeat(141)@(posedge dclk);@(negedge dclk);prepared=1;end
  endtask
  task select_frame;
    input [31:0] s,f,slot,generation;
    input [63:0] duration_bound;
    input wanted;
    begin
      @(negedge dclk);scan_active=1;dsid=s;dfid=f;dslot=slot;dgen=generation;
      scan_start_display_tick=display_ticks;scan_start_age=now_tick-pcapture;
      scan_show=prepared && prepared_show && ((MUTATION==3)||(psid==s && pfid==f)) &&
        pslot==slot && ((MUTATION==1)||pgen==generation) &&
        now_tick>=pcapture && now_tick+duration_bound-pcapture<=AGE;
      #0.01;check_condition(scan_enable==wanted,"strict same-frame bundle selection");
    end
  endtask
  task end_scan;
    begin @(negedge dclk);scan_active=0;end
  endtask
  task geometry;
    input [10:0] xx;input [9:0] yy;input hit;input [23:0] rgb;
    begin x=xx;y=yy;#0.01;check_condition(box_valid==hit,"public geometry hit");
      if(hit)check_condition(box_rgb==rgb,"public geometry RGB");end
  endtask
  task hidden;
    begin x=16;y=16;#0.01;check_condition(!box_valid && !text_valid,"all annotation hidden together");end
  endtask
  task text_lines;
    input [111:0] expected0,expected1;
    reg [111:0] line0,line1;integer k;
    begin
      line0=0;line1=0;
      for(k=0;k<28;k=k+1)begin
        x=16+(k%14)*16;y=(k<14)?16:34;#0.01;
        check_condition(text_valid && glyph_row==0,"public glyph request valid");
        if(k<14)line0={line0[103:0],glyph};else line1={line1[103:0],glyph};
      end
      check_condition(line0===expected0,"public text coordinates equal frozen bundle");
      check_condition(line1===expected1,"public text count/state equal frozen bundle");
    end
  endtask
  task inspect_a;
    begin
      geometry(100,90,1,24'h00ff00);geometry(110,100,1,24'hffff00);geometry(10,10,0,0);
      text_lines("RED X0110 Y100","N012345 TRACK ");
    end
  endtask
  initial begin
    repeat(4)@(negedge clk);rst_n=1;begin_session(1);
    $display("CASE startup_missing");
    select_frame(1,1,0,1,20,0);hidden();end_scan();
    deliver(1,1,1,0,1,12345,110,100,0,1);
    deliver(1,2,1,0,1,12345,110,100,0,1);
    deliver(1,3,1,0,1,12345,110,100,0,1);
    check_condition(usable && state==2 && box_fid==3,"three independent results confirm A");
    $display("CASE text_preparation_barrier");
    stage_annotation(0,3);select_frame(1,3,0,3,20,0);hidden();end_scan();wait_text();
    $display("CASE same_frame_public_outputs");
    select_frame(1,3,0,3,20,1);inspect_a();
    $display("CASE newer_result_during_scan");
    deliver(1,4,1,0,1,54,210,200,0,1);
    check_condition(box_fid==4 && gcx==210,"guard updated independently to B");
    stage_annotation(1,1);inspect_a();end_scan();
    $display("CASE late_result_boundary");
    select_frame(1,4,1,1,20,0);hidden();stage_annotation(1,1);hidden();end_scan();
    stage_annotation(1,1);wait_text();select_frame(1,4,1,1,20,1);
    geometry(200,190,1,24'h00ff00);text_lines("RED X0210 Y200","N000054 TRACK ");end_scan();
    $display("CASE slot_generation_mismatch");
    select_frame(1,4,1,2,20,0);hidden();end_scan();
    $display("CASE hold_keeps_true_box_identity");
    deliver(1,5,1,0,0,0,0,0,0,2);
    check_condition(state==3 && box_fid==4,"absence HOLD keeps B source frame");
    stage_annotation(1,1);wait_text();select_frame(1,5,1,1,20,0);hidden();end_scan();
    $display("CASE identity_and_disposition");
    deliver(1,5,1,0,1,999,310,300,0,5);
    deliver(1,4,1,0,1,999,310,300,0,6);
    deliver(1,6,0,0,1,999,310,300,0,3);
    deliver(1,7,1,1,1,999,310,300,0,4);
    deliver(1,8,1,0,1,999,310,300,10,10);
    deliver(1,8,1,0,1,999,310,300,0,5);
    $display("CASE frame_wrap_requires_session");
    deliver(1,32'hffffffff,1,0,1,54,210,200,0,1);
    deliver(1,0,1,0,1,54,210,200,0,6);
    $display("CASE session_barrier_masks_inflight");
    select_frame(1,4,1,1,20,1);begin_session(2);hidden();end_scan();
    deliver(1,99,1,0,1,999,110,100,0,7);
    deliver(2,0,1,0,1,7,310,300,0,1);
    deliver(2,1,1,0,1,7,310,300,0,1);
    deliver(2,2,1,0,1,7,310,300,0,1);
    stage_annotation(2,1);wait_text();select_frame(2,2,2,1,20,1);
    geometry(300,290,1,24'h00ff00);text_lines("RED X0310 Y300","N000007 TRACK ");end_scan();
    $display("CASE whole_scan_age_budget");
    @(negedge clk);bias=pcapture+AGE-100-counter;
    @(posedge clk);#1;check_condition(usable,"guard still young at display-start budget test");
    select_frame(2,2,2,1,200,0);hidden();end_scan();
    $display("CASE observation_clock_stop_display_watchdog");
    select_frame(2,2,2,1,20,1);
    @(negedge clk);clock_running=0;
    repeat(90)@(negedge dclk);
    check_condition(usable,"stopped observation guard cannot age itself");hidden();end_scan();
    clock_running=1;time_valid=0;repeat(3)@(negedge clk);time_valid=1;begin_session(3);
    deliver(3,0,1,0,1,7,310,300,0,1);
    deliver(3,1,1,0,1,7,310,300,0,1);
    deliver(3,2,1,0,1,7,310,300,0,1);
    stage_annotation(2,2);wait_text();
    $display("CASE independent_time_loss_masks_all");
    select_frame(3,2,2,2,20,1);
    @(negedge clk);time_valid=0;#0.01;hidden();end_scan();
    $display("CASE global_reset_masks_all");
    rst_n=0;prepared=0;#0.01;hidden();
    $display("DISPLAY_TX_COMPLETE checks=%0d failures=%0d",checks,failures);
    $finish;
  end
endmodule
