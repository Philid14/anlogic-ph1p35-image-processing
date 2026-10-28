// MAIN integration owner: two existing pixel FIFOs, bounded DDR transactions,
// authoritative capture keys, TARGET guard, and one atomic display snapshot.
// Experimental until the multi-clock/top-level validation gates have passed.
module target_frame_system #(parameter integer BOOT_DIAG_ENABLE=0)(
    input rst_n, csi_clk, ddr_clk, hdmi_clk, input calib_ready,
    input raw_valid, raw_sof, raw_eol, native_frame_end, input packet_error,
    input awb_user, awb_valid, awb_last, input [95:0] awb_rgb,
    input packed_user, packed_valid, input [127:0] packed_rgb,
    input user_ready, user_read_valid, input [127:0] user_read_data,
    input mc_write_accept, input [24:0] mc_write_address,
    output user_write_enable,user_read_enable,
    output [24:0] user_address, output [127:0] user_write_data,
    input display_vsync,display_read_enable,
    output [23:0] display_rgb,
    output [31:0] fifo_counts,
    output [63:0] display_tick,
    output display_metadata_receive, output [505:0] display_metadata,
    output display_metadata_online, output display_scan_fault,
    input diag_packet_error,diag_lane_error,
    output [95:0] boot_diagnostics,
    output [15:0] dropped_frames,cancelled_frames,metadata_faults
);
    localparam [63:0] MAX_AGE=64'd100000;
    wire [63:0] csi_tick,ddr_tick;
    wire csi_time_valid,ddr_time_valid;
    frame_timebase u_time(.rst_n(rst_n),.hdmi_clk(hdmi_clk),.csi_clk(csi_clk),.ddr_clk(ddr_clk),
        .master_tick(display_tick),.csi_tick(csi_tick),.ddr_tick(ddr_tick),
        .csi_valid(csi_time_valid),.ddr_valid(ddr_time_valid));

    reg [31:0] next_session;
    wire ledger_ready; wire [31:0] ledger_session;
    reg [2:0] recovery;
    reg [5:0] flush_count;
    reg barrier_pulse;
    wire flushing=recovery==3;
    wire metadata_rst_n=rst_n && !flushing;
    wire [32:0] camera_control;
    wire camera_control_receive,camera_control_ready;
    reg [31:0] camera_session; reg camera_ready;
    frame_bundle_cdc #(.WIDTH(33),.PULSE_PAYLOAD(1)) u_control(
        .src_clk(ddr_clk),.src_rst_n(metadata_rst_n),.dst_clk(csi_clk),.dst_rst_n(metadata_rst_n),
        .send(camera_control_ready),.payload({ledger_ready && recovery==0,ledger_session}),
        .ready(camera_control_ready),.overflow(),.overflow_count(),.receive(camera_control_receive),
        .received_payload(camera_control),.src_online(),.dst_online());
    always @(posedge csi_clk or negedge metadata_rst_n) begin
        if(!metadata_rst_n) begin camera_session<=0; camera_ready<=0; end
        else if(camera_control_receive) begin camera_session<=camera_control[31:0]; camera_ready<=camera_control[32]; end
    end

    wire capture_start,observer_valid,observer_sof,observer_eol,observer_eof,observer_abort;
    wire [95:0] observer_rgb;
    wire [10:0] observer_x;
    wire [9:0] observer_y;
    wire [31:0] capture_session,capture_frame,observation_session,observation_frame;
    wire [63:0] capture_time,observation_time;
    wire raw_complete,raw_good,observer_done,observer_good,capture_fault;
    target_observer_adapter u_observer(
        .clk(csi_clk),.rst_n(metadata_rst_n),.control_session(camera_session),.session_ready(camera_ready),
        .now_tick(csi_tick),.time_valid(csi_time_valid),.raw_valid(raw_valid),.raw_sof(raw_sof),
        .raw_eol(raw_eol),.native_frame_end(native_frame_end),.external_error(packet_error),
        .awb_user(awb_user),.awb_valid(awb_valid),.awb_last(awb_last),.awb_rgb(awb_rgb),
        .capture_start(capture_start),.capture_session(capture_session),.capture_frame(capture_frame),
        .capture_time(capture_time),.pixel_valid(observer_valid),.pixel_rgb(observer_rgb),
        .sof(observer_sof),.eol(observer_eol),.eof(observer_eof),.x0(observer_x),.y(observer_y),
        .observation_session(observation_session),.observation_frame(observation_frame),
        .observation_time(observation_time),.frame_abort(observer_abort),
        .raw_complete(raw_complete),.raw_good(raw_good),.observer_done(observer_done),
        .observer_good(observer_good),.epoch_fault(capture_fault),.raw_error_count(),.observer_error_count());
    wire detector_strobe,detector_valid,detector_present,detector_error;
    wire [31:0] detector_session,detector_frame;
    wire [1:0] detector_class; wire [19:0] detector_count;
    wire [10:0] detector_xmin,detector_xmax,detector_cx;
    wire [9:0] detector_ymin,detector_ymax,detector_cy;
    color_target_detect_stream #(.FILTER_ENABLE(0),.TARGET_CLASS(0)) u_detector(
        .clk(csi_clk),.rst_n(metadata_rst_n),.I_pixel_valid(observer_valid),.I_data(observer_rgb),
        .I_x0(observer_x),.I_y(observer_y),.I_sof(observer_sof),.I_eol(observer_eol),.I_eof(observer_eof),
        .I_session_id(observation_session),.I_frame_id(observation_frame),.I_frame_abort(observer_abort),
        .O_res_session_id(detector_session),.O_res_frame_id(detector_frame),
        .O_result_valid(detector_valid),.O_target_present(detector_present),.O_color_class(detector_class),
        .O_pixel_count(detector_count),.O_xmin(detector_xmin),.O_xmax(detector_xmax),.O_center_x(detector_cx),
        .O_ymin(detector_ymin),.O_ymax(detector_ymax),.O_center_y(detector_cy),
        .O_result_ready(detector_strobe),.O_protocol_error(detector_error));

    wire begin_receive,begin_ready,begin_overflow;
    wire [127:0] begin_payload;
    frame_bundle_cdc #(.WIDTH(128),.PULSE_PAYLOAD(1)) u_begin(
        .src_clk(csi_clk),.src_rst_n(metadata_rst_n),.dst_clk(ddr_clk),.dst_rst_n(metadata_rst_n),
        .send(capture_start),.payload({capture_session,capture_frame,capture_time}),
        .ready(begin_ready),.overflow(begin_overflow),.overflow_count(),.receive(begin_receive),
        .received_payload(begin_payload),.src_online(),.dst_online());
    wire allocated,dropped,write_active,committed,cancelled;
    wire [1:0] write_slot; wire [31:0] write_generation;
    reg [31:0] current_frame,current_session;
    reg [63:0] current_capture_time;
    reg [127:0] requested_capture;
    reg reply_pending;
    wire grant_receive,grant_ready,grant_overflow;
    wire [98:0] grant;
    frame_bundle_cdc #(.WIDTH(99),.PULSE_PAYLOAD(1)) u_grant(
        .src_clk(ddr_clk),.src_rst_n(metadata_rst_n),.dst_clk(csi_clk),.dst_rst_n(metadata_rst_n),
        .send(reply_pending),.payload({allocated,requested_capture[127:64],write_slot,write_generation}),
        .ready(grant_ready),.overflow(grant_overflow),.overflow_count(),.receive(grant_receive),
        .received_payload(grant),.src_online(),.dst_online());
    always @(posedge ddr_clk or negedge rst_n) begin
        if(!rst_n) begin current_session<=0; current_frame<=0; current_capture_time<=0; requested_capture<=0; reply_pending<=0; end
        else begin
            reply_pending<=begin_receive;
            if(begin_receive) requested_capture<=begin_payload;
            if(allocated) begin current_session<=requested_capture[127:96];
                current_frame<=requested_capture[95:64]; current_capture_time<=requested_capture[63:0]; end
        end
    end
    reg grant_matches,pack_open,pack_decided,pack_allow,pack_bad,pack_finished;
    reg [1:0] granted_slot; reg [31:0] granted_generation;
    reg [17:0] packed_words;
    reg raw_seen,raw_ok,detector_seen;
    reg [86:0] detected;
    reg [31:0] detected_session,detected_frame;
    wire camera_full;
    wire camera_we=pack_open && packed_valid && (pack_decided ? pack_allow : grant_matches) && camera_ready;
    always @(posedge csi_clk or negedge metadata_rst_n) begin
        if(!metadata_rst_n) begin
            grant_matches<=0; granted_slot<=0; granted_generation<=0;
            pack_open<=0; pack_decided<=0; pack_allow<=0; pack_bad<=0; pack_finished<=0;
            packed_words<=0; raw_seen<=0; raw_ok<=0; detector_seen<=0; detected<=0;
            detected_session<=0; detected_frame<=0;
        end else begin
            if(capture_start) begin
                grant_matches<=0; pack_open<=1; pack_decided<=0; pack_allow<=0;
                pack_bad<=0; pack_finished<=0; packed_words<=0; raw_seen<=0; detector_seen<=0;
            end
            if(grant_receive && grant[97:66]==capture_session && grant[65:34]==capture_frame) begin
                grant_matches<=grant[98]; granted_slot<=grant[33:32]; granted_generation<=grant[31:0];
            end
            if(raw_complete) begin raw_seen<=1; raw_ok<=raw_good; end
            if(detector_strobe) begin
                detector_seen<=1; detected_session<=detector_session; detected_frame<=detector_frame;
                detected<={detector_valid,detector_present,detector_class,detector_count,
                    detector_xmin,detector_xmax,detector_cx,detector_ymin,detector_ymax,detector_cy};
            end
            if(packed_valid && pack_open) begin
                if(!pack_decided) begin pack_decided<=1; pack_allow<=grant_matches; end
                if(camera_we && camera_full) pack_bad<=1;
                if(packed_words<172800) packed_words<=packed_words+1'b1;
                else pack_bad<=1;
                if(packed_words==172799) begin pack_finished<=1; pack_open<=0; end
            end
            if(packet_error) pack_bad<=1;
        end
    end
    reg terminal_sent;
    wire terminal_send=!terminal_sent && pack_finished && raw_seen && detector_seen;
    wire terminal_good=raw_ok && !pack_bad && pack_allow &&
        detected_session==capture_session && detected_frame==capture_frame && detected[86];
    wire terminal_ready,terminal_receive,terminal_overflow;
    wire [185:0] terminal;
    always @(posedge csi_clk or negedge metadata_rst_n) begin
        if(!metadata_rst_n) terminal_sent<=0;
        else if(capture_start) terminal_sent<=0;
        else if(terminal_send) terminal_sent<=1;
    end
    frame_bundle_cdc #(.WIDTH(186),.PULSE_PAYLOAD(1)) u_terminal(
        .src_clk(csi_clk),.src_rst_n(metadata_rst_n),.dst_clk(ddr_clk),.dst_rst_n(metadata_rst_n),
        .send(terminal_send),.payload({terminal_good,capture_session,capture_frame,granted_slot,granted_generation,detected}),
        .ready(terminal_ready),.overflow(terminal_overflow),.overflow_count(),.receive(terminal_receive),
        .received_payload(terminal),.src_online(),.dst_online());

    wire [24:0] write_address,read_address;
    wire write_busy,read_busy,write_idle,read_idle;
    wire [17:0] issued_words,requested_words;
    wire [18:0] outstanding_reads;
    wire scan_request,scan_underflow;
    reg [18:0] pending_writes;
    reg [4:0] cancel_flush;
    wire write_flush=flushing || cancel_flush!=0;
    video_in #(.TRANSACTIONAL(1)) u_writer(
        .I_rst_n(rst_n),.I_camera_clk(csi_clk),.I_camera_frame_start(packed_user),
        .I_camera_valid(packed_valid),.I_camera_data(packed_rgb),.I_mipi_rx_error(1'b0),
        .I_ddr_clk(ddr_clk),.I_display_pause(1'b0),.I_video_out_rd_busy(read_busy),
        .O_video_in_wr_busy(write_busy),.O_video_out_rp(),.O_ddr_user_wr_en(user_write_enable),
        .O_ddr_user_addr(write_address),.O_ddr_user_wr_data(user_write_data),.I_ddr_user_ready(user_ready),
        .O_fifo_event_counts(fifo_counts),.I_transaction_start(allocated),.I_transaction_slot(write_slot),
        .I_camera_write_enable(camera_we),.I_transaction_flush(write_flush),
        .O_write_pipeline_idle(write_idle),.O_camera_full(camera_full),.O_issued_words(issued_words));
    wire scan_selected,scan_valid; wire [1:0] scan_slot;
    wire [31:0] scan_generation,scan_session,scan_frame;
    wire [63:0] scan_capture_time;
    wire scan_annotation_valid; wire [151:0] scan_annotation;
    video_out #(.TRANSACTIONAL(1)) u_reader(
        .I_rst_n(rst_n),.I_ddr_clk(ddr_clk),.O_video_out_rd_busy(read_busy),
        .I_video_in_wr_busy(write_busy),.I_video_out_rp(scan_slot),.O_ddr_user_rd_en(user_read_enable),
        .O_ddr_user_addr(read_address),.I_ddr_user_ready(user_ready),.I_ddr_user_rd_valid(user_read_valid),
        .I_ddr_user_rd_data(user_read_data),.I_dsi_clk(hdmi_clk),.I_video_vsync(display_vsync),
        .I_video_rd_en(display_read_enable),.O_vdieo_data(display_rgb),
        .I_scan_commit(scan_selected),.I_allow_read(scan_valid && recovery==0),.I_transaction_flush(flushing),
        .O_scan_request(scan_request),.O_read_pipeline_idle(read_idle),.O_requested_words(requested_words),
        .O_outstanding_reads(outstanding_reads),.O_scan_underflow(scan_underflow));
    assign user_address=user_write_enable ? write_address : (user_read_enable ? read_address : 25'd0);
    assign display_scan_fault=scan_underflow;
    function [24:0] base;
        input [1:0] slot;
        begin case(slot) 0:base=0; 1:base=7000000; 2:base=14000000; 3:base=21000000; endcase end
    endfunction
    wire [24:0] accepted_delta=mc_write_address-base(write_slot);
    wire accepted_address_good=accepted_delta[2:0]==0 && accepted_delta<25'd1382400;
    always @(posedge ddr_clk or negedge rst_n) begin
        if(!rst_n) begin pending_writes<=0; cancel_flush<=16; end
        else begin
            case({user_write_enable,mc_write_accept})
                2'b10: pending_writes<=pending_writes+1'b1;
                2'b01: if(pending_writes!=0) pending_writes<=pending_writes-1'b1;
                default: pending_writes<=pending_writes;
            endcase
            if(cancelled) cancel_flush<=16;
            else if(cancel_flush!=0) cancel_flush<=cancel_flush-1'b1;
        end
    end

    reg terminal_cached,terminal_ok;
    reg [86:0] cached_detection;
    reg result_pending,guard_fire;
    reg [63:0] result_wait_start;
    reg result_cancelled;
    reg transaction_owned;
    wire guard_retired;
    wire terminal_match=terminal[184:153]==current_session && terminal[152:121]==current_frame &&
        terminal[120:119]==write_slot && terminal[118:87]==write_generation;
    wire capture_timeout=write_active && ddr_tick>=current_capture_time &&
        ddr_tick-current_capture_time>64'd55000;
    wire ledger_cancel=capture_timeout || (terminal_receive && terminal_match && !terminal[185]);
    always @(posedge ddr_clk or negedge metadata_rst_n) begin
        if(!metadata_rst_n) begin
            terminal_cached<=0; terminal_ok<=0; cached_detection<=0;
            result_pending<=0; guard_fire<=0; result_wait_start<=0; result_cancelled<=0; transaction_owned<=0;
        end else begin
            guard_fire<=0;
            if(allocated) begin terminal_cached<=0; terminal_ok<=0; transaction_owned<=1; end
            if(guard_retired) transaction_owned<=0;
            if(terminal_receive && terminal_match && !terminal_cached) begin
                terminal_cached<=1; terminal_ok<=terminal[185]; cached_detection<=terminal[86:0];
            end
            if(committed || cancelled) begin
                result_pending<=1; result_wait_start<=ddr_tick; result_cancelled<=cancelled;
            end
            if(result_pending && (terminal_cached || result_cancelled || ddr_tick-result_wait_start>=5000)) begin
                guard_fire<=1; result_pending<=0;
            end
        end
    end
    wire guard_ready,guard_admitted,guard_usable;
    wire [1:0] guard_state,guard_class;
    wire [31:0] box_session,box_frame,guard_obs_session,guard_obs_frame;
    wire [63:0] box_time;
    wire [19:0] guard_count;
    wire [10:0] gxmin,gxmax,gcx; wire [9:0] gymin,gymax,gcy;
    wire [7:0] guard_reason;
    wire [15:0] gd,gr,gw,gi,gv,gc,gs,gt,go;
    reg session_start;
    reg [31:0] previous_session;
    always @(posedge ddr_clk or negedge rst_n) begin
        if(!rst_n) begin session_start<=0; previous_session<=0; end
        else begin session_start<=ledger_ready && previous_session!=ledger_session;
            if(ledger_ready) previous_session<=ledger_session; end
    end
    color_target_track_guard #(.TIME_W(64),.COUNTER_W(16),.ACQ_FRAMES(3),.LOST_FRAMES(15),
        .MAX_TARGET_AGE_TICKS(65'd100000),.MAX_RELIABLE_AGE_TICKS(65'd100000)) u_guard(
        .clk(ddr_clk),.rst_n(rst_n),.I_session_start(session_start),.I_control_session_id(ledger_session),
        .I_time_valid(ddr_time_valid && ledger_ready),.I_now_tick(ddr_tick),
        .I_result_strobe(guard_fire),.I_identity_valid(1'b1),.I_session_id(current_session),.I_frame_id(current_frame),
        .I_result_valid(terminal_cached && terminal_ok),.I_cancelled(result_cancelled),
        .I_target_present(cached_detection[85]),.I_capture_tick(current_capture_time),
        .I_color_class(cached_detection[84:83]),.I_pixel_count(cached_detection[82:63]),
        .I_xmin(cached_detection[62:52]),.I_xmax(cached_detection[51:41]),.I_center_x(cached_detection[40:30]),
        .I_ymin(cached_detection[29:20]),.I_ymax(cached_detection[19:10]),.I_center_y(cached_detection[9:0]),
        .O_session_ready(guard_ready),.O_current_session_id(),.O_event_strobe(),.O_retired_strobe(guard_retired),
        .O_admitted_strobe(guard_admitted),.O_reason(guard_reason),.O_timeout_strobe(),
        .O_track_state(guard_state),.O_observation_usable(guard_usable),.O_reliable_valid(),.O_positive_valid(),
        .O_observation_session_id(guard_obs_session),.O_observation_frame_id(guard_obs_frame),
        .O_box_session_id(box_session),.O_box_frame_id(box_frame),.O_reliable_age(),.O_positive_age(),
        .O_reliable_tick(),.O_positive_tick(box_time),.O_color_class(guard_class),.O_pixel_count(guard_count),
        .O_xmin(gxmin),.O_xmax(gxmax),.O_center_x(gcx),.O_ymin(gymin),.O_ymax(gymax),.O_center_y(gcy),
        .O_duplicate_count(gd),.O_reorder_count(gr),.O_wrong_session_count(gw),.O_identity_error_count(gi),
        .O_invalid_count(gv),.O_cancelled_count(gc),.O_stale_result_count(gs),.O_time_error_count(gt),.O_timeout_count(go));
    wire [151:0] annotation={box_session,box_frame,guard_usable,guard_state,guard_class,guard_count,
        gxmin,gxmax,gcx,gymin,gymax,gcy};
    wire ledger_drained=recovery!=0 ? (recovery==4) :
        (write_idle && pending_writes==0 && (terminal_cached || capture_timeout));
    frame_transaction_ledger #(.ANNOT_W(152)) u_ledger(
        .clk(ddr_clk),.rst_n(rst_n),.barrier(barrier_pulse),.io_drained(ledger_drained),
        .next_session(next_session),.ready(ledger_ready),.session_id(ledger_session),
        .start(begin_receive && recovery==0),.allocation_permitted(!transaction_owned),
        .start_session(begin_payload[127:96]),.start_frame(begin_payload[95:64]),.capture_tick(begin_payload[63:0]),
        .allocated(allocated),.dropped(dropped),.write_slot(write_slot),.write_generation(write_generation),
        .write_accept(mc_write_accept),.accepted_slot(write_slot),.accepted_generation(write_generation),
        .accepted_offset(accepted_address_good ? accepted_delta[20:3] : 18'h3ffff),
        .raster_done(terminal_receive && terminal_match),.raster_good(terminal[185]),.cancel(ledger_cancel),
        .committed(committed),.cancelled(cancelled),.terminal_frame(),
        .result_strobe(guard_admitted),.result_session(guard_obs_session),.result_frame(guard_obs_frame),
        .result_slot(write_slot),.result_generation(write_generation),.result_annotation(annotation),
        .result_accepted(),.result_rejected(),.select_scan(scan_request && read_idle && recovery==0),
        .release_scan(scan_request && read_idle),.scan_selected(scan_selected),.scan_valid(scan_valid),
        .scan_slot(scan_slot),.scan_generation(scan_generation),.scan_session(scan_session),.scan_frame(scan_frame),
        .scan_capture_tick(scan_capture_time),.scan_annotation_valid(scan_annotation_valid),.scan_annotation(scan_annotation),
        .drop_count(dropped_frames),.cancel_count(cancelled_frames),.result_reject_count(),
        .complete_slots(),.leased_slots(),.write_active(write_active),.barrier_pending());

    wire display_send_ready,display_overflow;
    wire [151:0] masked_annotation=scan_annotation_valid ? scan_annotation : 152'd0;
    wire metadata_transport_online;
    (* async_reg="true" *) reg [2:0] display_recovery_sync;
    always @(posedge hdmi_clk or negedge rst_n) begin
        if(!rst_n) display_recovery_sync<=7;
        else display_recovery_sync<={display_recovery_sync[1:0],recovery!=0};
    end
    assign display_metadata_online=metadata_transport_online && !display_recovery_sync[2];
    frame_bundle_cdc #(.WIDTH(506),.PULSE_PAYLOAD(1)) u_display(
        .src_clk(ddr_clk),.src_rst_n(metadata_rst_n),.dst_clk(hdmi_clk),.dst_rst_n(metadata_rst_n),
        .send(scan_selected),.payload({gd,gr,gw,gi,gv,gc,gs,gt,go,dropped_frames,cancelled_frames,metadata_faults,
            scan_slot,scan_generation,scan_session,scan_frame,scan_capture_time,masked_annotation}),
        .ready(display_send_ready),.overflow(display_overflow),.overflow_count(),
        .receive(display_metadata_receive),.received_payload(display_metadata),.src_online(),.dst_online(metadata_transport_online));

    (* async_reg="true" *) reg [2:0] camera_fault_sync;
    reg [15:0] fault_count;
    reg fault_seen;
    wire camera_fault=capture_fault || begin_overflow || terminal_overflow;
    wire fault=camera_fault_sync[2] || grant_overflow || display_overflow || !calib_ready || !ddr_time_valid;
    assign metadata_faults=fault_count;
    always @(posedge ddr_clk or negedge rst_n) begin
        if(!rst_n) begin
            recovery<=1; next_session<=1; barrier_pulse<=0; flush_count<=0;
            camera_fault_sync<=0; fault_count<=0; fault_seen<=0;
        end else begin
            camera_fault_sync<={camera_fault_sync[1:0],camera_fault};
            barrier_pulse<=0;
            case(recovery)
                0: if(fault) begin
                    recovery<=1; barrier_pulse<=1; next_session<=ledger_session+1'b1;
                    if(!(&fault_count)) fault_count<=fault_count+1'b1;
                end
                1: if(scan_request && write_idle && read_idle && pending_writes==0) begin
                    recovery<=3; flush_count<=0;
                end
                3: if(flush_count==31) begin recovery<=4; flush_count<=0; end
                   else flush_count<=flush_count+1'b1;
                4: if(ledger_ready && calib_ready && ddr_time_valid) recovery<=0;
                default: recovery<=1;
            endcase
        end
    end
// Passive boot evidence survives recovery's metadata-only flush.
    generate if(BOOT_DIAG_ENABLE) begin:g_boot_probe
        target_boot_probe u_probe(.rst_n(rst_n),.csi_clk(csi_clk),.ddr_clk(ddr_clk),.hdmi_clk(hdmi_clk),
            .csi_events({terminal_send && !terminal_good,observer_done && !observer_good,
                raw_complete && !raw_good,camera_we,grant_matches,packed_valid,
                diag_lane_error,diag_packet_error,detector_strobe && detector_valid,
                observer_done && observer_good,awb_valid,awb_user,raw_complete && raw_good,
                native_frame_end,capture_start,raw_valid}),
            .ddr_events({pending_writes!=0,terminal_receive && !terminal[185],
                terminal_receive && terminal_match && terminal[185],terminal_receive,
                cancelled,display_overflow,grant_overflow,camera_fault_sync[2],
                scan_selected,scan_request,committed,mc_write_accept,allocated,
                ledger_ready,ddr_time_valid,calib_ready}),
            .live_status({5'd0,pending_writes==0,read_idle,write_idle,write_active,
                ledger_ready,ddr_time_valid,calib_ready,recovery,metadata_transport_online}),
            .drops(dropped_frames),.cancels(cancelled_frames),.faults(metadata_faults),
            .diagnostics(boot_diagnostics));
    end else begin:g_no_boot_probe
        assign boot_diagnostics=96'd0;
    end endgenerate
endmodule
