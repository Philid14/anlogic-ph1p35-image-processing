`timescale 1ns/1ps
module tb_frame_transaction_ledger;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, barrier=0, io_drained=0;
    reg [31:0] next_session=1;
    wire ready; wire [31:0] session_id;
    reg start=0,allocation_permitted=1; reg [31:0] start_session=1,start_frame=0;
    reg [63:0] capture_tick=100;
    wire allocated,dropped; wire [1:0] write_slot; wire [31:0] write_generation;
    reg write_accept=0; reg [1:0] accepted_slot=0;
    reg [31:0] accepted_generation=0; reg [17:0] accepted_offset=0;
    reg raster_done=0,raster_good=0,cancel=0;
    wire committed,cancelled; wire [31:0] terminal_frame;
    reg result_strobe=0; reg [31:0] result_session=1,result_frame=0;
    reg [1:0] result_slot=0; reg [31:0] result_generation=0;
    reg [111:0] result_annotation=112'h123456789;
    wire result_accepted,result_rejected;
    reg select_scan=0,release_scan=0;
    wire scan_selected,scan_valid; wire [1:0] scan_slot;
    wire [31:0] scan_generation,scan_session,scan_frame;
    wire [63:0] scan_capture_tick; wire scan_annotation_valid;
    wire [111:0] scan_annotation;
    wire [15:0] drop_count,cancel_count,result_reject_count;
    wire [3:0] complete_slots,leased_slots;
    wire write_active,barrier_pending;
    frame_transaction_ledger #(.WORDS(4)) dut(.*);
    integer checks=0;
    task check(input bit condition,input string label);
        begin checks=checks+1; if(!condition) begin
            $display("FAIL check %0d: %s",checks,label); $fatal(1);
        end end
    endtask
    task step; begin @(posedge clk); #1; @(negedge clk); end endtask
    task begin_frame(input [31:0] id);
        begin start_frame=id; capture_tick=100+id; start=1; step; start=0; end
    endtask
    task publish;
        begin result_slot=write_slot; result_generation=write_generation;
            result_frame=start_frame; result_strobe=1; step; result_strobe=0; end
    endtask
    task words;
        integer n;
        begin accepted_slot=write_slot; accepted_generation=write_generation;
            write_accept=1;
            for(n=0;n<4;n=n+1) begin accepted_offset=n; step; end
            write_accept=0;
        end
    endtask
    task finish_raster(input bit good);
        begin raster_done=1; raster_good=good; step; raster_done=0; end
    endtask
    reg [1:0] lease_saved;
    reg [31:0] generation_saved;
    initial begin
        #2; step; rst_n=1; step;
        check(!ready && barrier_pending,"startup requires actual drain");
        io_drained=1; step; io_drained=0;
        check(ready && session_id==1,"new session after drain");
        begin_frame(1); check(allocated && write_active,"capture allocation");
        publish; check(result_accepted && complete_slots==0,"early result is not DDR completion");
        select_scan=1; step; select_scan=0;
        check(!scan_valid,"incomplete frame unavailable");
        finish_raster(1); check(!committed && complete_slots==0,"detector EOF does not commit");
        words; check(committed && terminal_frame==1,"last accepted DDR word commits");
        select_scan=1; step; select_scan=0;
        check(scan_selected && scan_valid && scan_frame==1,"select committed identity");
        check(scan_annotation_valid && scan_annotation==112'h123456789,"annotation atomic snapshot");
        check(scan_capture_tick==101 && scan_session==1,"capture tick/key conserved");
        lease_saved=scan_slot; generation_saved=scan_generation;
        begin_frame(2); check(allocated && write_slot!=lease_saved,"writer excludes leased slot");
        finish_raster(1); words;
        check(committed && scan_frame==1 && scan_generation==generation_saved,"scan immutable while newer commits");
        select_scan=1; step; select_scan=0;
        check(!scan_selected && scan_frame==1,"cannot replace outstanding lease");
        release_scan=1; select_scan=1; step; release_scan=0; select_scan=0;
        check(scan_selected && scan_frame==2 && !scan_annotation_valid,"missing annotation hides group");
        result_slot=scan_slot; result_generation=scan_generation; result_frame=2;
        result_strobe=1; step; result_strobe=0;
        check(result_accepted && !scan_annotation_valid,"late result waits next scan");
        release_scan=1; select_scan=1; step; release_scan=0; select_scan=0;
        check(scan_frame==2 && scan_annotation_valid,"repeat frame can receive same-frame late result");
        result_strobe=1; step; result_strobe=0;
        check(result_rejected,"duplicate result rejected");
        result_generation=scan_generation-1; result_strobe=1; step; result_strobe=0;
        check(result_rejected,"retired generation rejected");
        result_generation=scan_generation; result_session=0; result_strobe=1; step; result_strobe=0;
        check(result_rejected,"old session rejected"); result_session=1;
        begin_frame(2); check(dropped,"duplicate capture rejected");
        begin_frame(1); check(dropped,"reordered capture rejected");
        begin_frame(3); check(allocated,"new frame accepted");
        accepted_slot=write_slot; accepted_generation=write_generation;
        write_accept=1; accepted_offset=1; step; write_accept=0;
        check(write_active && !committed,"bad address sequence cannot commit");
        io_drained=1; step; io_drained=0;
        check(cancelled && terminal_frame==3,"bad write cancelled only after physical drain");
        begin_frame(4); finish_raster(0);
        check(write_active && !committed,"bad raster awaits drain");
        io_drained=1; step; io_drained=0; check(cancelled,"bad raster cancelled");
        begin_frame(5); words;
        check(write_active && !committed,"exact words without raster/EOF not enough");
        cancel=1; step; cancel=0; check(write_active,"missing EOF explicit cancel keeps I/O active");
        io_drained=1; step; io_drained=0; check(cancelled,"missing EOF retired after drain");
        begin_frame(6); begin_frame(7); check(dropped,"busy writer drops whole new frame");
        cancel=1; io_drained=1; step; cancel=0; io_drained=0;
        begin_frame(7); check(dropped,"dropped identity remains retired");
        begin_frame(8); finish_raster(1); words; check(committed,"recovery frame complete");
        barrier=1; step; barrier=0;
        check(!ready && leased_slots!=0 && barrier_pending,"barrier preserves physical read lease");
        next_session=2; step;
        check(!ready && leased_slots!=0,"cleared metadata does not mean drained");
        io_drained=1; step; io_drained=0;
        check(ready && session_id==2 && leased_slots==0 && complete_slots==0,"new epoch after physical drain");
        check(!scan_valid && !scan_annotation_valid,"old scan cannot revive");
        start_session=1; begin_frame(9); check(dropped,"old epoch capture rejected");
        start_session=2; begin_frame(0); check(allocated,"frame counter can restart only in new epoch");
        barrier=1; step; barrier=0; next_session=2; io_drained=1; step;
        check(!ready,"same session cannot reopen barrier");
        next_session=3; step; io_drained=0;
        begin_frame(32'hffffffff); check(dropped,"frame wrap requires issuer barrier");
        check(drop_count==6 && cancel_count==4 && result_reject_count==3,"separate exact diagnostics");
        $display("PASS FRAME_LEDGER checks=%0d",checks); $finish;
    end
    initial begin #100000; $fatal(1,"timeout"); end
endmodule
