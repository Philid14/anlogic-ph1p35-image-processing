`timescale 1ns / 1ps
module tb_edge_control_decimal;
    reg clk=0;
    always #5 clk=~clk;
    wire [95:0] data;
    edge_status_osd dut (.clk(clk),.rst_n(1'b0),.I_data(96'd0),
        .I_valid(1'b0),.I_user(1'b0),.I_last(1'b0),.I_config(9'd0),
        .O_data(data),.O_valid(),.O_user(),.O_last());
    integer n;
    reg [11:0] digits;
    initial begin
        for(n=0;n<256;n=n+1) begin
            digits=dut.decimal3(n);
            if(digits[11:8]!==n/100 || digits[7:4]!==((n%100)/10) || digits[3:0]!==n%10)
                $fatal(1,"FAIL decimal %0d gives %h",n,digits);
        end
        $display("PASS checkpoint_D decimal: all 256 values, 010/080/100/200/250, correct carries");
        $finish;
    end
endmodule
