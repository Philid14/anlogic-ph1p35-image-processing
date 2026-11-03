`timescale 1ns / 1ps
module tb_nms_axis;
    wire [95:0] unused;
    edge_detect_96 dut(.I_clk(1'b0),.I_rst_n(1'b0),.I_tlast(1'b0),.I_tuser(1'b0),
        .I_tdata(96'd0),.I_tvalid(1'b0),.I_tready(),.O_tlast(),.O_tuser(),.O_tdata(unused),.O_tvalid(),.O_tready(1'b1),.I_threshold(8'd80));
    integer count=0;
    task check;
        input integer x,y,expected;
        reg signed [12:0] gx,gy;
        reg [1:0] got;
        begin
            gx=x;gy=y;got=dut.gradient_axis(gx,gy);
            if(got!==expected[1:0]) $fatal(1,"FAIL axis gx%0d gy%0d got%0d expected%0d",x,y,got,expected);
            count=count+1;
        end
    endtask
    initial begin
        #1;
        check(0,0,0);check(16,0,0);check(-16,0,0);check(0,16,2);check(0,-16,2);
        check(16,8,0);check(16,9,1);check(8,16,2);check(9,16,1);
        check(-16,-8,0);check(-16,-9,1);check(-8,-16,2);check(-9,-16,1);
        check(-16,9,3);check(16,-9,3);check(9,-16,3);check(-9,16,3);
        check(16,16,1);check(-16,-16,1);check(16,-16,3);check(-16,16,3);
        check(-4096,-4096,1);check(4095,-4096,3);check(-4096,0,0);check(0,-4096,2);
        $display("PASS axis: %0d signed13bit/zero/ratio_equal/boundary/polarity/Gy-up tests",count);$finish;
    end
endmodule
