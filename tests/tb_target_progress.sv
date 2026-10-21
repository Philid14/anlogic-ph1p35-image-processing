`timescale 1ns/1ps
module tb_target_progress;
    initial begin
        forever begin #1000000; $display("SIM_PROGRESS_NS %0d",$time); end
    end
endmodule
