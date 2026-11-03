//======================================================================
// tb_frame_event_bridge.v - loss accounting test (TARGET review P1)
//
// 1) destination clock paused -> 20 legal events, depth 16: 16 delivered,
//    4 dropped and MUST be visible in lost_count (old design was silent);
// 2) after resume, 3 events one cycle apart: the first is delivered, the next
//    two are dropped -> lost_count +2 (old toggle could cancel an even count).
//======================================================================
`timescale 1ns/1ps
module tb_frame_event_bridge;
    reg clk_cap = 1'b0;
    always #5 clk_cap = ~clk_cap;           // 10 ns

    reg clk_raw = 1'b0;
    always #7 clk_raw = ~clk_raw;           // 14 ns
    reg clk_en = 1'b1;
    wire clk = clk_en ? clk_raw : 1'b0;     // gated destination clock (test only)

    reg rst_cap_n = 1'b0, rst_n = 1'b0;
    reg cap_event = 1'b0;
    reg [1:0] cap_kind = 2'd0;
    reg [31:0] cap_sid = 32'd1, cap_fid = 32'd0;
    reg flush_req = 1'b0;

    wire [65:0] evt_data;
    wire evt_valid, evt_gap_alarm, lost_event;
    wire [7:0] lost_count;

    frame_event_bridge #(.SID_W(32), .FID_W(32), .DEPTH_LOG2(4),
                         .MIN_GAP_SRC(2), .MIN_GAP_DST(3)) dut (
        .clk_cap(clk_cap), .rst_cap_n(rst_cap_n), .cap_event(cap_event), .cap_kind(cap_kind),
        .cap_sid(cap_sid), .cap_fid(cap_fid),
        .clk(clk), .rst_n(rst_n), .evt_ready(1'b1), .flush_req(flush_req),
        .evt_data(evt_data), .evt_valid(evt_valid), .evt_gap_alarm(evt_gap_alarm),
        .lost_event(lost_event), .lost_count(lost_count)
    );

    integer delivered = 0;
    integer i;
    always @(posedge clk) if (evt_valid) delivered = delivered + 1;

    task cap_pulse;
        begin
            @(posedge clk_cap); #1 cap_event = 1'b1;
            @(posedge clk_cap); #1 cap_event = 1'b0;
        end
    endtask

    initial begin
        repeat (4) @(negedge clk_cap);
        rst_n = 1'b1; rst_cap_n = 1'b1;
        repeat (6) @(negedge clk_cap);   // let the auto flush settle

        // 1) pause the destination and send 20 legal events
        clk_en = 1'b0;
        for (i = 0; i < 20; i = i + 1) begin
            cap_fid = i[31:0];
            cap_pulse;
            repeat (2) @(negedge clk_cap);   // >= MIN_GAP_SRC between events
        end
        repeat (4) @(negedge clk_cap);
        $display("PAUSED lost=%0d delivered=%0d", lost_count, delivered);

        // 2) resume and drain
        clk_en = 1'b1;
        repeat (40) @(negedge clk_raw);
        $display("DRAINED lost=%0d delivered=%0d", lost_count, delivered);

        // 3) three events one capture cycle apart: 1 delivered, 2 dropped
        cap_fid = 32'd100; cap_pulse;
        cap_fid = 32'd101; cap_pulse;
        cap_fid = 32'd102; cap_pulse;
        repeat (10) @(negedge clk_raw);
        $display("RAPID lost=%0d delivered=%0d", lost_count, delivered);
        $display("FINAL lost=%0d delivered=%0d", lost_count, delivered);
        $finish;
    end

    initial begin
        #200000; $display("TB_ERRORS=1 timeout"); $finish;
    end
endmodule
