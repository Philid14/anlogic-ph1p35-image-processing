`timescale 1ns/1ps
module tb_edge_quality_class;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;reg [13:0] high=80,a=0,b=0;reg [1:0] keep=0;
    wire [27:0] magnitudes={a,b};
    wire [95:0] od;
    edge_detect_96 #(.IMG_WIDTH(64),.IMG_HEIGHT(24),.DENOISE_ENABLE(1),.NMS_ENABLE(1),.QUALITY_ENABLE(1)) dut (
        .I_clk(clk),.I_rst_n(rst_n),.I_tlast(1'b0),.I_tuser(1'b0),.I_tdata(96'd0),.I_tvalid(1'b0),
        .I_tready(),.O_tlast(),.O_tuser(),.O_tdata(od),.O_tvalid(),.O_tready(1'b1),.I_threshold(8'd80));
    integer th,j,k,checks=0;
    reg [3:0] expected;
    initial begin
        force dut.nms_magnitude=magnitudes;force dut.nms_threshold=high;force dut.nms_keep=keep;
        repeat(5) @(negedge clk);rst_n=1;
        for(th=10;th<=250;th=th+1) begin
            for(j=0;j<6;j=j+1) begin
                @(negedge clk);high=th;
                case(j)
                    0:begin a=th/2-1;b=th/2;end
                    1:begin a=th/2+1;b=th-1;end
                    2:begin a=th;b=th+1;end
                    3:begin a=0;b=16383;end
                    4:begin a=th/2;b=th;end
                    5:begin a=16383;b=0;end
                endcase
                keep=j%4;
                expected={keep[1] && a>=th/2,keep[1] && a>=th,keep[0] && b>=th/2,keep[0] && b>=th};
                @(posedge clk);#1;
                if(dut.g_quality.classified!==expected) $fatal(1,"FAIL strong/weak equality th%0d j%0d got%h expected%h",th,j,dut.g_quality.classified,expected);
                checks=checks+2;
            end
        end
        $display("PASS actual S5 classification all241 high thresholds, odd/even low floor, keep masking and14bit endpoints sample_checks=%0d",checks);
        $finish;
    end
endmodule
