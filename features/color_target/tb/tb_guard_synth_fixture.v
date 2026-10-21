`timescale 1ns/1ps
// Literal public-output smoke test of the NEW measurement fixture wiring.
// This is not a replacement for the existing 818-check guard RTL contract.
module tb_guard_synth_fixture;
    reg clk=0,rst_n=0,load_en=0,fire=0;
    reg [31:0] load_data=0;
    reg [3:0] load_slot=0;
    reg [4:0] observe_sel=0;
    wire [31:0] observe;
    always #5 clk=~clk;
    guard_synth_top dut(.clk(clk),.rst_n(rst_n),.load_data(load_data),
        .load_slot(load_slot),.load_en(load_en),.fire(fire),
        .observe_sel(observe_sel),.observe(observe));
    integer checks=0,failures=0,i;
    reg [319:0] input_words;
    reg [671:0] actual;
    reg [662:0] expected;
    task check;
        input condition;
        input [255:0] label;
        begin
            checks=checks+1;
            if(condition!==1'b1) begin failures=failures+1;$display("FAIL fixture %s",label);end
        end
    endtask
    task send;
        input barrier;
        input [31:0] frame;
        begin
            // Independent 316-bit literal vector, default 64-bit time profile.
            input_words={4'b0,32'd7,64'd100,64'd100,32'd7,frame,2'd1,20'd77,
                11'd10,11'd20,11'd15,10'd30,10'd40,10'd35,
                barrier,1'b1,!barrier,1'b1,1'b1,1'b0,1'b1};
            for(i=0;i<10;i=i+1) begin
                @(negedge clk);load_en=1;load_slot=i;load_data=input_words[i*32+:32];
            end
            @(negedge clk);load_en=0;fire=1;
            @(negedge clk);fire=0;
            repeat(3) @(negedge clk);
        end
    endtask
    task read_all;
        begin
            actual=0;
            for(i=0;i<21;i=i+1) begin
                observe_sel=i;#1;actual[i*32+:32]=observe;
            end
        end
    endtask
    initial begin
        repeat(2) @(negedge clk);rst_n=1;
        check(dut.INPUT_W==316,"input width");
        check(dut.OUTPUT_W==663,"output width");
        send(1,0);
        send(0,1);send(0,2);send(0,3);
        read_all;
        // Stable third admitted positive observation, after event strobes end.
        expected={1'b1,32'd7,3'b0,8'd0,1'b0,2'd2,3'b111,
            32'd7,32'd3,32'd7,32'd3,64'd0,64'd0,64'd100,64'd100,
            2'd1,20'd77,11'd10,11'd20,11'd15,10'd30,10'd40,10'd35,144'd0};
        check(actual[662:0]===expected,"all output words");
        check(actual[671:663]===9'd0,"padding");
        observe_sel=31;#1;check(observe===32'd0,"outside output range");
        send(0,3);read_all;
        // Duplicate must be visible in the public diagnostic word.
        expected[143:128]=16'd1;
        check(actual[662:0]===expected,"duplicate diagnostic mapping");
        $display("GUARD_FIXTURE_COMPLETE checks=%0d failures=%0d",checks,failures);
        $finish;
    end
endmodule
