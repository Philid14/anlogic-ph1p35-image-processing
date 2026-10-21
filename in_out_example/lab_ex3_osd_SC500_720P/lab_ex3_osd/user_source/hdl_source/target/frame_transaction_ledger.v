// MAIN DDR-domain transaction owner. Not a FIFO or an implicit drained model.
// Adapters MUST supply accepted (not merely issued) write events and must not
// assert io_drained until command FIFO, read returns and pixel scans are empty.
// A barrier keeps read leases and the active write until that physical proof.
module frame_transaction_ledger #(
    parameter integer WORDS=172800,
    parameter integer ANNOT_W=112
)(
    input clk, input rst_n,
    input barrier, input io_drained,
    input [31:0] next_session,
    output reg ready, output reg [31:0] session_id,
    input start, input allocation_permitted, input [31:0] start_session, start_frame,
    input [63:0] capture_tick,
    output reg allocated, dropped,
    output reg [1:0] write_slot, output reg [31:0] write_generation,
    input write_accept, input [1:0] accepted_slot,
    input [31:0] accepted_generation, input [17:0] accepted_offset,
    input raster_done, input raster_good, input cancel,
    output reg committed, cancelled,
    output reg [31:0] terminal_frame,
    input result_strobe, input [31:0] result_session, result_frame,
    input [1:0] result_slot, input [31:0] result_generation,
    input [ANNOT_W-1:0] result_annotation,
    output reg result_accepted, result_rejected,
    input select_scan, input release_scan,
    output reg scan_selected, output reg scan_valid,
    output reg [1:0] scan_slot, output reg [31:0] scan_generation,
    output reg [31:0] scan_session, scan_frame,
    output reg [63:0] scan_capture_tick,
    output reg scan_annotation_valid,
    output reg [ANNOT_W-1:0] scan_annotation,
    output reg [15:0] drop_count, cancel_count, result_reject_count,
    output [3:0] complete_slots, leased_slots,
    output wire write_active, output wire barrier_pending
);
    reg [3:0] complete, leased, annotation_valid;
    reg [31:0] frames[0:3], generations[0:3];
    // Validity/state bits reset; payload RAM never does. Synchronous selection
    // is its only read port. This avoids resetting thousands of metadata FFs.
    reg [63:0] ticks[0:3] /* fehdl force_ram=1, ram_style="bram_fast" */;
    reg [ANNOT_W-1:0] annotations[0:3] /* fehdl force_ram=1, ram_style="bram_fast" */;
    reg active, bad, have_raster, draining;
    reg [17:0] word_count;
    reg [31:0] high_water;
    reg have_high_water;
    integer i, j;
    reg free_found, newest_found;
    reg [1:0] free_slot, newest_slot;
    reg [31:0] newest_frame;
    assign complete_slots=complete;
    assign leased_slots=leased;
    assign write_active=active;
    assign barrier_pending=draining;
    function [15:0] satinc;
        input [15:0] value;
        begin satinc=(&value) ? value : value+1'b1; end
    endfunction
    // Keep the current latest complete frame as a fallback. Four slots allow
    // one read lease, one last-complete fallback and one writer concurrently.
    always @* begin
        newest_found=0; newest_slot=0; newest_frame=0;
        for(i=0;i<4;i=i+1) begin
            if(complete[i] && (!newest_found || frames[i]>newest_frame)) begin
                newest_found=1; newest_slot=i; newest_frame=frames[i];
            end
        end
        free_found=0; free_slot=0;
        for(i=0;i<4;i=i+1) begin
            if(!free_found && !leased[i] && (!active || write_slot!=i) &&
               (!newest_found || newest_slot!=i) && generations[i]!=32'hffffffff) begin
                free_found=1; free_slot=i;
            end
        end
    end
    wire accepted_match=active && accepted_slot==write_slot &&
        accepted_generation==write_generation && accepted_offset==word_count;
    wire final_accept=write_accept && accepted_match && word_count==WORDS-1;
    wire enough_words=(word_count==WORDS) || final_accept;
    wire raster_complete=have_raster || (raster_done && raster_good);
    wire error_now=cancel || (raster_done && !raster_good) ||
        (write_accept && (!accepted_match || word_count>=WORDS));
    wire result_match=result_session==session_id &&
        frames[result_slot]==result_frame && generations[result_slot]==result_generation &&
        ((active && result_slot==write_slot && !bad && !error_now) || complete[result_slot]);
    wire fresh_start=start_session==session_id &&
        (!have_high_water || start_frame>high_water) && start_frame!=32'hffffffff;
    wire allocate_now=start && allocation_permitted && fresh_start && !active && free_found;

    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            ready<=0; session_id<=0; draining<=1;
            complete<=0; leased<=0; annotation_valid<=0;
            active<=0; bad<=0; have_raster<=0; word_count<=0;
            high_water<=0; have_high_water<=0;
            allocated<=0; dropped<=0; write_slot<=0; write_generation<=0;
            committed<=0; cancelled<=0; terminal_frame<=0;
            result_accepted<=0; result_rejected<=0;
            scan_selected<=0; scan_valid<=0; scan_slot<=0; scan_generation<=0;
            scan_session<=0; scan_frame<=0; scan_capture_tick<=0;
            scan_annotation_valid<=0; scan_annotation<=0;
            drop_count<=0; cancel_count<=0; result_reject_count<=0;
            for(j=0;j<4;j=j+1) begin
                frames[j]<=0; generations[j]<=0;
            end
        end else begin
            allocated<=0; dropped<=0; committed<=0; cancelled<=0;
            result_accepted<=0; result_rejected<=0; scan_selected<=0;
            if(barrier) begin
                ready<=0; draining<=1; complete<=0; annotation_valid<=0;
                scan_annotation_valid<=0;
                // Do not release leases or erase active I/O at this point.
            end else if(draining) begin
                if(io_drained && next_session!=0 && next_session>session_id) begin
                    ready<=1; draining<=0; session_id<=next_session;
                    complete<=0; leased<=0; annotation_valid<=0;
                    scan_valid<=0; scan_annotation_valid<=0;
                    active<=0; bad<=0; word_count<=0; have_raster<=0;
                    have_high_water<=0;
                    for(j=0;j<4;j=j+1) generations[j]<=0;
                end
            end else if(ready) begin
                if(release_scan) begin leased<=0; scan_valid<=0; scan_annotation_valid<=0; end
                if(select_scan) begin
                    // Selection never changes an outstanding read lease.
                    if((leased==0 || release_scan) && newest_found) begin
                        leased<=4'b0001<<newest_slot;
                        scan_selected<=1; scan_valid<=1; scan_slot<=newest_slot;
                        scan_generation<=generations[newest_slot]; scan_session<=session_id;
                        scan_frame<=frames[newest_slot]; scan_capture_tick<=ticks[newest_slot];
                        scan_annotation_valid<=annotation_valid[newest_slot];
                        scan_annotation<=annotations[newest_slot];
                    end
                end
                if(start) begin
                    if(fresh_start) begin high_water<=start_frame; have_high_water<=1; end
                    if(!allocate_now) begin
                        dropped<=1; drop_count<=satinc(drop_count);
                    end else begin
                        allocated<=1; active<=1; bad<=0; have_raster<=0; word_count<=0;
                        write_slot<=free_slot; write_generation<=generations[free_slot]+1;
                        generations[free_slot]<=generations[free_slot]+1;
                        frames[free_slot]<=start_frame; ticks[free_slot]<=capture_tick;
                        complete[free_slot]<=0; annotation_valid[free_slot]<=0;
                    end
                end
                if(active) begin
                    if(raster_done && raster_good) have_raster<=1;
                    if(error_now) bad<=1;
                    if(write_accept && accepted_match && word_count<WORDS) word_count<=word_count+1'b1;
                    if(!bad && !error_now && raster_complete && enough_words) begin
                        committed<=1; complete[write_slot]<=1; active<=0;
                        terminal_frame<=frames[write_slot];
                    end else if((bad || error_now) && io_drained) begin
                        cancelled<=1; active<=0; complete[write_slot]<=0;
                        annotation_valid[write_slot]<=0;
                        terminal_frame<=frames[write_slot]; cancel_count<=satinc(cancel_count);
                    end
                end
                if(result_strobe) begin
                    if(result_match && !annotation_valid[result_slot] &&
                       !(allocate_now && free_slot==result_slot)) begin
                        result_accepted<=1; annotation_valid[result_slot]<=1;
                        annotations[result_slot]<=result_annotation;
                    end else begin
                        result_rejected<=1; result_reject_count<=satinc(result_reject_count);
                    end
                end
            end
        end
    end
endmodule
