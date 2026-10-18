`timescale 1ns/1ps
// Characterizes current RTL. OPEN_GAP is reported by runner, not called PASS.
module tb_track_admission_audit;
    reg clk=0;always #10 clk=~clk;
    reg rst_n=0,strobe=0,valid=0,present=0;
    reg [31:0] sid=0,fid=0;
    wire [1:0] state;
    wire show;
    wire [31:0] os,of;
    color_target_track #(.ACQ_FRAMES(3),.LOST_FRAMES(2)) dut(
        .clk(clk),.rst_n(rst_n),.I_result_strobe(strobe),.I_result_valid(valid),.I_target_present(present),
        .I_pixel_count(20'd4),.I_xmin(11'd0),.I_xmax(11'd3),.I_center_x(11'd1),
        .I_ymin(10'd0),.I_ymax(10'd0),.I_center_y(10'd0),.I_session_id(sid),.I_frame_id(fid),
        .O_track_state(state),.O_show(show),.O_out_session_id(os),.O_out_frame_id(of));
    task reset;
        begin @(negedge clk);rst_n=0;strobe=0;valid=0;present=0;repeat(2) @(negedge clk);rst_n=1;end
    endtask
    task result;
        input [31:0] s,f;
        input v,p;
        begin @(negedge clk);sid=s;fid=f;strobe=1;valid=v;present=p;@(posedge clk);#1;end
    endtask
    task snapshot;
        input [255:0] name;
        begin $display("S %0s %0d %0d %0d %0d",name,state,show,os,of);end
    endtask
    task confirm;
        begin result(1,1,1,1);result(1,2,1,1);result(1,3,1,1);end
    endtask
    integer i;
    initial begin
        reset;result(1,99,1,1);result(1,99,1,1);result(1,99,1,1);snapshot("DUPLICATE");
        reset;result(1,3,1,1);result(1,2,1,1);result(1,1,1,1);snapshot("REORDER");
        reset;confirm;
        for(i=4;i<24;i=i+1) result(1,i,0,0);snapshot("INVALID_RUN");
        @(negedge clk);strobe=0;repeat(20) @(negedge clk);snapshot("SILENCE");
        reset;confirm;result(2,0,0,0);snapshot("SESSION_INVALID");
        result(2,1,1,1);snapshot("SESSION_VALID");result(1,99,1,1);snapshot("OLD_SESSION_RETURN");
        reset;confirm;result(1,4,1,0);snapshot("ABSENT_FIRST");result(1,5,1,0);snapshot("ABSENT_SECOND");
        $display("TRACK_AUDIT_COMPLETE");$finish;
    end
endmodule
