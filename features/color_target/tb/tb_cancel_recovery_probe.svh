// Appended to the pinned MAIN active_epoch harness by the independent runner.
// Read-only hierarchical observations are test instrumentation, not CDC wiring.
    integer issued_total=0,accepted_total=0,accepted_frame=0,recovered_commits=0;
    integer frame_byte_errors=0,total_byte_errors=0,cancel_seen=0,unowned_writes=0;
    integer csi_edges=0,hdmi_edges=0,stop_edges,stop_hdmi,stop_native,stop_cancels;
    integer stop_session=-1,stop_frame=-1,stop_slot=-1,stop_generation=-1;
    integer first_unowned_frame=-1,bad_logged_frame=-1,k,trace_file;
    integer stop_at=6,pause_ns=65000000,resume_ns=35000000;
    integer fault_leases=0,leased_reads_during_stop=0,recovery_display_packets=0;
    reg injected=0,resumed=0,flush_previous=0,error_previous=0;
    reg [63:0] stop_tick;
    string trace_path;
    always @(posedge csi_clk) begin
        csi_edges=csi_edges+1;
        if(dut.capture_start) $fdisplay(trace_file,"BEGIN_CSI t=%0t source=%0d key=%0d/%0d tick=%0d",$time,source_frame,dut.capture_session,dut.capture_frame,dut.capture_time);
        if(dut.terminal_send) $fdisplay(trace_file,"TERMINAL_SEND t=%0t source=%0d key=%0d/%0d detected=%0d/%0d good=%0d pack=%0d raw=%0d/%0d",$time,source_frame,dut.capture_session,dut.capture_frame,dut.detected_session,dut.detected_frame,dut.terminal_good,dut.packed_words,dut.raw_seen,dut.raw_ok);
    end
    always @(posedge hdmi_clk) hdmi_edges=hdmi_edges+1;
    always @(posedge ddr_clk) begin
        dc=dc+1;mc_ready<=dc%29>=3;
        if(rst_n)check(dut.pending_writes==issued_total-accepted_total,"physical issued/accepted accounting");
        if(user_write_enable)issued_total=issued_total+1;
        if(mc_en && mc_cmd==0)accepted_total=accepted_total+1;
        if(dut.allocated) begin
            check(dut.pending_writes==0,"allocation waits for issued MC writes");
            accepted_frame=0;frame_byte_errors=0;
            $fdisplay(trace_file,"ALLOC t=%0t key=%0d/%0d slot=%0d gen=%0d fifo=%0d leases=%h",$time,dut.ledger_session,dut.u_ledger.frames[dut.write_slot],dut.write_slot,dut.write_generation,dut.u_writer.S_fifo_rd_num,dut.u_ledger.leased);
        end
        if(dut.begin_receive)$fdisplay(trace_file,"BEGIN_DDR t=%0t key=%0d/%0d capture=%0d",$time,dut.begin_payload[127:96],dut.begin_payload[95:64],dut.begin_payload[63:0]);
        if(dut.terminal_receive)$fdisplay(trace_file,"TERMINAL_RECEIVE t=%0t key=%0d/%0d slot=%0d gen=%0d good=%0d match=%0d current=%0d/%0d",$time,dut.terminal[184:153],dut.terminal[152:121],dut.terminal[120:119],dut.terminal[118:87],dut.terminal[185],dut.terminal_match,dut.current_session,dut.current_frame);
        if(dut.write_flush!=flush_previous)$fdisplay(trace_file,"FLUSH t=%0t value=%0d source=%0d camera_we=%0d pack_allow=%0d fifo=%0d pending=%0d",$time,dut.write_flush,source_frame,dut.camera_we,dut.pack_allow,dut.u_writer.S_fifo_rd_num,dut.pending_writes);
        flush_previous=dut.write_flush;
        if(dut.write_active && dut.u_ledger.error_now && !error_previous)
            $fdisplay(trace_file,"LEDGER_ERROR t=%0t key=%0d/%0d timeout=%0d terminal_bad=%0d mc=%0d accepted_match=%0d offset=%0d expected=%0d fifo=%0d",$time,dut.current_session,dut.current_frame,dut.capture_timeout,dut.terminal_receive && dut.terminal_match && !dut.terminal[185],dut.mc_write_accept,dut.u_ledger.accepted_match,dut.accepted_delta[20:3],dut.u_ledger.word_count,dut.u_writer.S_fifo_rd_num);
        error_previous=dut.write_active && dut.u_ledger.error_now;
        read_pipe_valid<={read_pipe_valid[6:0],mc_en && mc_cmd==1};
        for(k=1;k<8;k=k+1)read_pipe[k]<=read_pipe[k-1];
        if(mc_en) begin
            slot_index=address_slot(mc_addr);word_index=address_word(mc_addr);
            check(word_index>=0 && word_index<172800,"MC address inside frame extent");
            if(mc_cmd==0) begin
                check(slot_source[slot_index]>=0,"MC slot has a granted source");
                check(!dut.u_ledger.leased[slot_index],"actual MC write never touches read lease");
                if(injected && !dut.write_active && cancelled_frames>stop_cancels) begin
                    unowned_writes=unowned_writes+1;
                    if(first_unowned_frame!=dut.current_frame) begin
                        first_unowned_frame=dut.current_frame;
                        $fdisplay(trace_file,"UNOWNED_FIRST t=%0t source=%0d current=%0d/%0d slot=%0d gen=%0d offset=%0d pending=%0d camera_we=%0d",$time,source_frame,dut.current_session,dut.current_frame,slot_index,dut.write_generation,word_index,dut.pending_writes,dut.camera_we);
                    end
                end
                accepted_frame=accepted_frame+1;
                for(byte_index=0;byte_index<16;byte_index=byte_index+1) begin
                    pixel_index=(word_index*16+byte_index)/3;channel=(word_index*16+byte_index)%3;
                    expected_pixel=pixel(slot_source[slot_index],pixel_index%1280,pixel_index/1280);
                    if(mc_data[127-byte_index*8-:8]!==((expected_pixel>>(8*(2-channel))) & 8'hff)) begin
                        frame_byte_errors=frame_byte_errors+1;total_byte_errors=total_byte_errors+1;
                        if(bad_logged_frame!=dut.current_frame) begin
                            bad_logged_frame=dut.current_frame;
                            $fdisplay(trace_file,"BYTE_ERROR_FIRST t=%0t source=%0d key=%0d/%0d active=%0d offset=%0d byte=%0d got=%h expected=%h",$time,slot_source[slot_index],dut.current_session,dut.current_frame,dut.write_active,word_index,byte_index,mc_data[127-byte_index*8-:8],expected_pixel);
                        end
                    end
                end
                memory[slot_index*172800+word_index]<=mc_data;writes=writes+1;
            end else begin
                check(dut.u_ledger.leased[slot_index],"every physical MC read retains its lease");
                if(injected && !resumed)leased_reads_during_stop=leased_reads_during_stop+1;
                read_pipe[0]<=memory[slot_index*172800+word_index];reads=reads+1;
            end
        end
        if(dut.cancelled) begin
            cancel_seen=cancel_seen+1;
            $fdisplay(trace_file,"CANCEL t=%0t source=%0d key=%0d/%0d accepted=%0d errors=%0d tick=%0d",$time,source_frame,dut.current_session,dut.current_frame,accepted_frame,frame_byte_errors,dut.ddr_tick);
        end
        if(dut.committed) begin
            check(accepted_frame==172800,"commit requires 172800 physical accepts");
            check(frame_byte_errors==0,"committed frame bytes equal independent spatial scene");
            if(injected)check(!(dut.current_session==stop_session && dut.current_frame==stop_frame),"interrupted frame cannot commit");
            if(resumed && slot_source[dut.write_slot]>stop_at)recovered_commits=recovered_commits+1;
            commits=commits+1;
            $fdisplay(trace_file,"COMMIT t=%0t source=%0d key=%0d/%0d slot=%0d gen=%0d accepts=%0d errors=%0d",$time,slot_source[dut.write_slot],dut.current_session,dut.current_frame,dut.write_slot,dut.write_generation,accepted_frame,frame_byte_errors);
        end
    end
    always @(posedge hdmi_clk) begin
        if(display_metadata_receive) begin
            metadata_packets=metadata_packets+1;
            $fdisplay(trace_file,"DISPLAY t=%0t key=%0d/%0d slot=%0d gen=%0d usable=%0d box=%0d/%0d",$time,display_metadata[279:248],display_metadata[247:216],display_metadata[313:312],display_metadata[311:280],display_metadata[87],display_metadata[151:120],display_metadata[119:88]);
            if(injected)check(!(display_metadata[279:248]==stop_session && display_metadata[247:216]==stop_frame),"interrupted frame cannot be selected");
            if(resumed && key_source[display_metadata[247:216]]>stop_at)recovery_display_packets=recovery_display_packets+1;
        end
    end
    initial begin
        if(!$value$plusargs("TRACE=%s",trace_path))$fatal(1,"missing trace path");
        if($value$plusargs("SOURCE=%d",stop_at))begin end
        if($value$plusargs("PAUSE_NS=%d",pause_ns))begin end
        if($value$plusargs("RESUME_NS=%d",resume_ns))begin end
        trace_file=$fopen(trace_path,"w");if(!trace_file)$fatal(1,"cannot create trace");
        for(i=0;i<4;i=i+1)slot_source[i]=-1;
        for(i=0;i<64;i=i+1)key_source[i]=-1;
        #40;rst_n=1;
        wait(source_frame==stop_at && source_line==360 && line_cycle==100 && awb_valid && dut.write_active && accepted_frame>0);
        @(posedge csi_clk);#1;
        check(commits>=3 && dut.u_ledger.leased!=0,"fault has existing complete frames and actual read lease");
        check(accepted_frame>0 && accepted_frame<172800,"fault is inside actual partial MC write");
        stop_session=dut.capture_session;stop_frame=dut.capture_frame;stop_slot=dut.write_slot;stop_generation=dut.write_generation;
        fault_leases=dut.u_ledger.leased;stop_cancels=cancelled_frames;
        injected=1;run_csi=0;stop_edges=csi_edges;stop_hdmi=hdmi_edges;stop_native=native_cycle;stop_tick=display_tick;
        $fdisplay(trace_file,"STOP t=%0t source=%0d key=%0d/%0d slot=%0d gen=%0d accepts=%0d fifo=%0d leases=%h",$time,source_frame,stop_session,stop_frame,stop_slot,stop_generation,accepted_frame,dut.u_writer.S_fifo_rd_num,dut.u_ledger.leased);
        #(pause_ns);
        check(csi_edges==stop_edges && native_cycle==stop_native,"CSI clock and source frozen");
        check(hdmi_edges-stop_hdmi>4000000 && display_tick-stop_tick>=64990,"HDMI continues through stop");
        check(cancelled_frames>stop_cancels && !dut.write_active && dut.pending_writes==0,"timeout cancellation drains issued writes");
        check(leased_reads_during_stop>0,"actual leased DDR reads continue while CSI stopped");
        $fdisplay(trace_file,"RESUME t=%0t cancels=%0d active=%0d pending=%0d fifo=%0d camera_we=%0d",$time,cancelled_frames,dut.write_active,dut.pending_writes,dut.u_writer.S_fifo_rd_num,dut.camera_we);
        resumed=1;run_csi=1;
        #(resume_ns);
        check(recovered_commits>=2,"two later complete frames recover");
        check(recovery_display_packets>0,"a recovered frame reaches HDMI metadata selection");
        check(injected && fault_leases!=0 && cancel_seen>0,"fault and cancellation coverage observed");
        $fdisplay(trace_file,"END unowned=%0d all_byte_errors=%0d reads_while_stopped=%0d recovered=%0d display=%0d",unowned_writes,total_byte_errors,leased_reads_during_stop,recovered_commits,recovery_display_packets);
        $fclose(trace_file);
        $display("PASS CANCEL_RECOVERY_TRACE checks=%0d commits=%0d recovered=%0d cancels=%0d unowned=%0d discarded_byte_errors=%0d",checks,commits,recovered_commits,cancelled_frames,unowned_writes,total_byte_errors);
        $finish;
    end
    initial begin forever begin #10000000;$display("TRACE_PROGRESS tick=%0d source=%0d injected=%0d resumed=%0d",display_tick,source_frame,injected,resumed);end end
    initial begin #180000000;$fatal(1,"trace timeout");end
endmodule
