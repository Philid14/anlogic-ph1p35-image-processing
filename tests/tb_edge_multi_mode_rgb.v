`timescale 1ns / 1ps
module tb_edge_multi_mode_rgb;
    reg [95:0] rgb;
    reg [7:0] threshold;
    wire [95:0] gray, binary;
    integer fd, rc, checks;
    reg [95:0] next_rgb, expected_gray, expected_binary;
    integer next_threshold;
    reg [2047:0] vector_path;

    rgb_effects_96 dut (
        .I_rgb(rgb), .I_binary_threshold(threshold),
        .O_gray(gray), .O_binary(binary)
    );

    initial begin
        checks = 0;
        if (!$value$plusargs("STIM=%s", vector_path)) $fatal(1, "missing vectors");
        fd = $fopen(vector_path, "r");
        if (!fd) $fatal(1, "cannot open vectors");
        while (!$feof(fd)) begin
            rc = $fscanf(fd, "%h %h %h %d\n", next_rgb, expected_gray,
                         expected_binary, next_threshold);
            if (rc == 4) begin
                rgb = next_rgb;
                threshold = next_threshold;
                #1;
                if (gray !== expected_gray)
                    $fatal(1, "FAIL gray input=%h output=%h expected=%h",
                           rgb, gray, expected_gray);
                if (binary !== expected_binary)
                    $fatal(1, "FAIL binary input=%h threshold=%0d output=%h expected=%h",
                           rgb, threshold, binary, expected_binary);
                checks = checks + 1;
            end else if (!$feof(fd)) begin
                $fatal(1, "malformed RGB vector");
            end
        end
        $display("PASS rgb gray/binary beats=%0d pixels=%0d", checks, checks*4);
        $finish;
    end
endmodule
