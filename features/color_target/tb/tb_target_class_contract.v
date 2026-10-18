`timescale 1ns/1ps
// Public-port probe only. Expected labels/counts are literal tables in runner.
module tb_target_class_contract;
    parameter integer CLASS=0;
    reg clk=0; always #10 clk=~clk;
    reg rst_n=0, valid=0, sof=0, eol=0, eof=0, abort_f=0;
    reg [95:0] data=0;
    reg [3:0] mask=0;
    reg [10:0] x=0;
    reg [9:0] y=0;
    reg [31:0] fid=0;
    wire hit;
    color_classify #(.TARGET_CLASS(CLASS)) classifier(
        .I_r(data[95:88]),.I_g(data[87:80]),.I_b(data[79:72]),.O_hit(hit));
    genvar p;
    generate for(p=0;p<4;p=p+1) begin : paths
        wire ready, rv, present;
        wire [1:0] cls;
        wire [19:0] count;
        wire [31:0] sid, frame;
        wire [10:0] xmin,xmax,cx;
        wire [9:0] ymin,ymax,cy;
        if(p==0) begin : old_detector
            color_target_detect #(.TARGET_CLASS(CLASS),.MIN_COUNT(1)) dut(
                .clk(clk),.rst_n(rst_n),.I_pixel_valid(valid),.I_data(data),.I_x0(x),.I_y(y),
                .I_sof(sof),.I_eol(eol),.I_eof(eof),.I_frame_abort(abort_f),
                .I_session_id(32'h1234),.I_frame_id(fid),
                .O_result_ready(ready),.O_result_valid(rv),.O_target_present(present),
                .O_res_session_id(sid),.O_res_frame_id(frame),.O_color_class(cls),.O_pixel_count(count),
                .O_xmin(xmin),.O_xmax(xmax),.O_ymin(ymin),.O_ymax(ymax),.O_center_x(cx),.O_center_y(cy));
        end else if(p<3) begin : rgb_stream
            color_target_detect_stream #(.TARGET_CLASS(CLASS),.MIN_COUNT(1),.WIDTH(8),.HEIGHT(3),.FILTER_ENABLE(p-1)) dut(
                .clk(clk),.rst_n(rst_n),.I_pixel_valid(valid),.I_data(data),.I_x0(x),.I_y(y),
                .I_sof(sof),.I_eol(eol),.I_eof(eof),.I_frame_abort(abort_f),
                .I_session_id(32'h1234),.I_frame_id(fid),
                .O_result_ready(ready),.O_result_valid(rv),.O_target_present(present),
                .O_res_session_id(sid),.O_res_frame_id(frame),.O_color_class(cls),.O_pixel_count(count),
                .O_xmin(xmin),.O_xmax(xmax),.O_ymin(ymin),.O_ymax(ymax),.O_center_x(cx),.O_center_y(cy));
        end else begin : mask_stats
            color_target_mask_stats #(.TARGET_CLASS(CLASS),.MIN_COUNT(1),.WIDTH(8),.HEIGHT(3)) dut(
                .clk(clk),.rst_n(rst_n),.I_pixel_valid(valid),.I_mask(mask),.I_x0(x),.I_y(y),
                .I_sof(sof),.I_eol(eol),.I_eof(eof),.I_frame_abort(abort_f),
                .I_session_id(32'h1234),.I_frame_id(fid),
                .O_result_ready(ready),.O_result_valid(rv),.O_target_present(present),
                .O_res_session_id(sid),.O_res_frame_id(frame),.O_color_class(cls),.O_pixel_count(count),
                .O_xmin(xmin),.O_xmax(xmax),.O_ymin(ymin),.O_ymax(ymax),.O_center_x(cx),.O_center_y(cy));
        end
        always @(posedge clk) begin
            #1;
            if(ready) $display("R %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",p,sid,frame,rv,present,cls,count,xmin,xmax,ymin,ymax,cx,cy);
        end
    end endgenerate
    always @(posedge clk) begin #1; if(valid && sof) $display("C %0d %0d",fid,hit); end
    task send_frame;
        input [23:0] rgb;
        input [3:0] m;
        input bad;
        input integer id;
        integer row,col;
        begin
            for(row=0;row<3;row=row+1) for(col=0;col<8;col=col+4) begin
                @(negedge clk); valid=1; data={4{rgb}}; mask=m; x=col; y=row;
                sof=(row==0 && col==0); eol=(col==4); eof=(row==2 && col==4); abort_f=bad; fid=id;
            end
            @(negedge clk); valid=0; sof=0; eol=0; eof=0; abort_f=0;
            repeat(12) @(negedge clk);
        end
    endtask
    initial begin
        repeat(2) @(negedge clk); rst_n=1;
        send_frame(24'hff0000,4'hf,0,1);
        send_frame(24'h00ff00,4'hf,0,2);
        send_frame(24'h0000ff,4'hf,0,3);
        send_frame(24'hffffff,4'h0,0,4);
        send_frame(24'hff0000,4'hf,1,5);
        $display("PASS target class probe completed"); $finish;
    end
endmodule
