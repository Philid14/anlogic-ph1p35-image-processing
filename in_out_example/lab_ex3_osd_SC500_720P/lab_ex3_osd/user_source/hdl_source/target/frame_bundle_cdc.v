// One-entry bundled-data mailbox. No video backpressure. The sender must retain
// unaccepted transactions or treat overflow as an epoch-invalidating fault.
// Both local resets asynchronously assert the whole mailbox; each domain then
// releases synchronously and waits for the peer's synchronized ready level.
// This cancels in-flight metadata; it does NOT drain external DDR/pixel FIFOs.
module frame_bundle_cdc #(parameter integer WIDTH=128)(
    input src_clk, src_rst_n, input dst_clk, dst_rst_n,
    input send, input [WIDTH-1:0] payload,
    output ready, output reg overflow, output reg [15:0] overflow_count,
    output reg receive, output reg [WIDTH-1:0] received_payload,
    output src_online, output dst_online
);
    wire both_rst_n=src_rst_n && dst_rst_n;
    reg [2:0] src_release, dst_release;
    (* async_reg="true" *) reg [2:0] src_up_sync, dst_up_sync;
    (* async_reg="true" *) reg [2:0] ack_sync, request_sync;
    reg request, ack;
    reg [WIDTH-1:0] held_payload;
    reg [1:0] settle;
    wire source_up=&src_release;
    wire dest_up=&dst_release;
    assign src_online=source_up && (&dst_up_sync);
    assign dst_online=dest_up && (&src_up_sync);
    assign ready=src_online && request==ack_sync[2];
    always @(posedge src_clk or negedge both_rst_n) begin
        if(!both_rst_n) begin
            src_release<=0; dst_up_sync<=0; ack_sync<=0;
            request<=0; held_payload<=0; overflow<=0; overflow_count<=0;
        end else begin
            src_release<={src_release[1:0],1'b1};
            dst_up_sync<={dst_up_sync[1:0],dest_up};
            ack_sync<={ack_sync[1:0],ack};
            if(send) begin
                if(ready) begin held_payload<=payload; request<=~request; end
                else begin
                    overflow<=1;
                    if(!(&overflow_count)) overflow_count<=overflow_count+1'b1;
                end
            end
        end
    end
    always @(posedge dst_clk or negedge both_rst_n) begin
        if(!both_rst_n) begin
            dst_release<=0; src_up_sync<=0; request_sync<=0;
            ack<=0; settle<=0; receive<=0; received_payload<=0;
        end else begin
            dst_release<={dst_release[1:0],1'b1};
            src_up_sync<={src_up_sync[1:0],source_up};
            request_sync<={request_sync[1:0],request};
            receive<=0;
            if(!dst_online || request_sync[2]==ack) settle<=0;
            else if(settle!=2) settle<=settle+1'b1;
            else begin
                // The complete bus has been held since request launch. Three
                // request synchronizer stages plus two settling cycles precede
                // this sample. Ack follows the sample, never precedes it.
                received_payload<=held_payload; receive<=1;
                ack<=request_sync[2]; settle<=0;
            end
        end
    end
endmodule
