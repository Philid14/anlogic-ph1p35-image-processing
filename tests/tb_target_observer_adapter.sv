`timescale 1ns/1ps
module tb_target_observer_adapter;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0;
    reg [31:0] control_session=1;
    reg session_ready=1,time_valid=1;
    reg [63:0] now_tick=1234;
    reg raw_valid=0,raw_sof=0,raw_eol=0,native_frame_end=0;
    reg awb_user=0,awb_valid=0,awb_last=0,external_error=0;
    reg [95:0] awb_rgb=0;
    wire capture_start;
    wire [31:0] capture_session,capture_frame;
    wire [63:0] capture_time;
    wire pixel_valid; wire [95:0] pixel_rgb;
    wire sof,eol,eof;
    wire [10:0] x0; wire [9:0] y;
    wire [31:0] observation_session,observation_frame;
    wire [63:0] observation_time;
    wire frame_abort,raw_complete,raw_good,observer_done,observer_good,epoch_fault;
    wire [15:0] raw_error_count,observer_error_count;
    target_observer_adapter #(.WIDTH(16),.HEIGHT(4)) dut(.*);
    integer checks=0,rx,cx,cy;
    task check(input bit condition,input string label);
        begin checks=checks+1; if(!condition) begin $display("FAIL %s",label); $fatal(1); end end
    endtask
    task step; begin @(posedge clk); #1; @(negedge clk); end endtask
    task raw_frame(input bit good);
        begin
            for(rx=0;rx<16;rx=rx+1) begin
                raw_valid=1; raw_sof=rx==0; raw_eol=(rx%4)==3;
                if(!good && rx==5) raw_eol=1;
                step;
                if(rx==0) check(capture_start && capture_session==1 && capture_time==1234,"authoritative first-valid key/time");
            end
            raw_valid=0; raw_sof=0; raw_eol=0;
            native_frame_end=1; step; native_frame_end=0;
            check(raw_complete && raw_good==good,"native EOF and independent raw geometry");
        end
    endtask
    task awb_frame(input bit good);
        begin
            awb_user=1; step; awb_user=0;
            check(!sof && !pixel_valid,"early user is not normalized SOF");
            repeat(3) step;
            for(cy=0;cy<4;cy=cy+1) begin
                for(cx=0;cx<4;cx=cx+1) begin
                    awb_valid=1; awb_last=(cx==3);
                    if(!good && cy==1 && cx==1) awb_last=1;
                    awb_rgb={24'hff0000,24'h00ff00,24'h0000ff,24'hffffff};
                    #1;
                    check(pixel_valid && x0==cx*4 && y==cy,"full-width spatial coordinates with valid");
                    check(pixel_rgb==awb_rgb,"RGB order and bytes unchanged");
                    check(sof==(cx==0 && cy==0) && eol==(cx==3) && eof==(cx==3 && cy==3),"SOF/EOL/EOF on valid beat");
                    check(observation_session==capture_session && observation_frame==capture_frame && observation_time==1234,"metadata follows exact RAW identity");
                    step;
                end
                awb_valid=0; awb_last=0; repeat(2) step;
            end
            check(!pixel_valid && !sof && !eof,"no markers during idle");
            check(observer_good==good,"bad EOL poisons observation");
        end
    endtask
    initial begin
        #2; step; rst_n=1; step;
        raw_frame(1); check(capture_frame==0,"first session frame zero");
        awb_frame(1); check(!epoch_fault,"nonoverlapping normal frames");
        raw_frame(1); check(capture_frame==1,"one issuer advances capture identity");
        awb_frame(0);
        raw_frame(0); awb_user=1; step; awb_user=0;
        awb_valid=1; awb_last=0; #1;
        check(frame_abort,"raw errors reach target abort"); step; awb_valid=0;
        raw_valid=1; raw_sof=1; step; raw_valid=0; raw_sof=0;
        check(epoch_fault,"overlapping frame cannot be silently reassociated");
        $display("PASS OBSERVER_ADAPTER checks=%0d",checks); $finish;
    end
    initial begin #100000; $fatal(1,"timeout"); end
endmodule
