`timescale 1ns/1ps
module tb_frame_bundle_cdc;
    reg src_clk=0,dst_clk=0,src_rst_n=0,dst_rst_n=0;
    always #7 src_clk=~src_clk;
    reg run_dst=1;
    always begin #5; if(run_dst) dst_clk=~dst_clk; end
    reg send=0; reg [255:0] payload=0;
    wire ready,overflow,receive,src_online,dst_online;
    wire [15:0] overflow_count; wire [255:0] received_payload;
    frame_bundle_cdc #(.WIDTH(256)) dut(.*);
    integer checks=0, received=0; reg [255:0] expected;
    task check(input bit value,input string label);
        begin checks=checks+1; if(!value) begin $display("FAIL %s",label); $fatal(1); end end
    endtask
    task source_step; begin @(posedge src_clk); #1; @(negedge src_clk); end endtask
    task wait_ready;
        integer n;
        begin n=0; while(!ready && n<100) begin source_step; n=n+1; end
            check(ready,"bounded online/ack service"); end
    endtask
    always @(posedge dst_clk) if(receive) begin
        received=received+1;
        check(received_payload===expected,"entire bus atomic without torn words");
    end
    integer k, saved;
    initial begin
        #2; source_step; src_rst_n=1; dst_rst_n=1; wait_ready;
        for(k=0;k<40;k=k+1) begin
            payload={8{32'h01020304 ^ (k*32'h10203040)}}; expected=payload;
            send=1; source_step; send=0;
            // Changing live input immediately must not affect held payload.
            payload=~payload;
            wait_ready;
        end
        check(received==40,"exactly one receive per accepted send");
        run_dst=0; #20; saved=received;
        expected=256'h1234; payload=expected; send=1; source_step; send=0;
        repeat(4) source_step;
        payload=256'hdead; send=1; source_step; send=0;
        check(overflow && overflow_count==1 && !ready,"full mailbox explicit fault");
        check(received==saved,"stopped consumer cannot fabricate service");
        // A one-sided reset cancels the outstanding bundle at both endpoints.
        dst_rst_n=0; #3; check(!src_online && !dst_online,"destination reset closes both ends");
        run_dst=1; repeat(2) source_step; dst_rst_n=1; wait_ready;
        repeat(10) source_step; check(received==saved,"old request cannot revive after reset");
        payload=256'hbeef; expected=payload; send=1; source_step; send=0; wait_ready;
        check(received==saved+1,"fresh transaction after reset");
        payload=256'h999; send=1; source_step; send=0;
        src_rst_n=0; #2; check(!dst_online,"source-only reset closes destination");
        repeat(2) source_step; src_rst_n=1; wait_ready;
        repeat(10) source_step; check(received==saved+1,"source reset cancels old bundle");
        $display("PASS FRAME_CDC checks=%0d receives=%0d",checks,received); $finish;
    end
    initial begin #100000; $fatal(1,"timeout"); end
endmodule
