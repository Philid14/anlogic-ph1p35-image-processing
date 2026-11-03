`timescale 1ns / 1ps
module tb_edge_multi_mode_keys;
    reg clk=0, dclk=0, rst_n=0;
    always #5 clk=~clk;
    always #7 dclk=~dclk;
    reg [1:0] keys=2'b11;
    wire [17:0] cfg, received;

    edge_key_control #(.DEBOUNCE_CYCLES(5),.LONG_CYCLES(35)) dut (
        .clk(clk), .rst_n(rst_n), .keys_n(keys), .requested_config(cfg)
    );
    edge_config_cdc mailbox (
        .src_clk(clk), .dst_clk(dclk), .rst_n(rst_n),
        .requested_config(cfg), .received_config(received)
    );

    reg [17:0] held_previous;
    reg was_busy;
    always @(posedge clk) begin
        if (rst_n) begin
            if (was_busy && mailbox.held_config !== held_previous)
                $fatal(1, "FAIL CDC bus changed before ACK");
            held_previous = mailbox.held_config;
            was_busy = mailbox.req_toggle != mailbox.ack_sync;
            if (cfg[15:8] < 10 || cfg[15:8] > 250 ||
                cfg[7:0] < 10 || cfg[7:0] > 250)
                $fatal(1, "FAIL threshold out of range");
        end else begin
            held_previous = 18'h35082;
            was_busy = 0;
        end
    end

    task ticks;
        input integer n;
        begin repeat(n) @(negedge clk); end
    endtask
    task expect_config;
        input [1:0] mode;
        input [7:0] edge_threshold, binary_threshold;
        begin
            ticks(3);
            if (cfg !== {mode,edge_threshold,binary_threshold})
                $fatal(1, "FAIL config got %h expected %h",
                       cfg, {mode,edge_threshold,binary_threshold});
        end
    endtask
    task press_mode;
        begin
            keys[0]=0; ticks(12);
            ticks(50);
            keys[0]=1; ticks(12);
        end
    endtask
    task short_k4;
        begin keys[1]=0; ticks(12); keys[1]=1; ticks(12); end
    endtask
    task long_k4;
        input [17:0] expected;
        begin
            keys[1]=0; ticks(45);
            if (cfg !== expected) $fatal(1, "FAIL long press got %h expected %h", cfg, expected);
            ticks(35);
            if (cfg !== expected) $fatal(1, "FAIL held long press repeated");
            keys[1]=1; ticks(12);
            if (cfg !== expected) $fatal(1, "FAIL long release changed config");
        end
    endtask

    integer i, launched=0, delivered=0;
    reg [17:0] sent_packets [0:255];
    reg [17:0] sampled_request, previous_received;
    reg previous_toggle;
    always @(posedge clk) begin
        sampled_request = cfg;
        #1;
        if (!rst_n) begin
            launched = 0; previous_toggle = 0;
        end else if (mailbox.req_toggle !== previous_toggle) begin
            sent_packets[launched] = sampled_request;
            launched = launched + 1;
            previous_toggle = mailbox.req_toggle;
        end
    end
    always @(posedge dclk) begin
        #1;
        if (!rst_n) begin
            delivered = 0; previous_received = 18'h35082;
        end else if (received !== previous_received) begin
            if (delivered >= launched || received !== sent_packets[delivered])
                $fatal(1, "FAIL CDC torn/out-of-order packet %0d got %h expected %h",
                       delivered, received, sent_packets[delivered]);
            delivered = delivered + 1;
            previous_received = received;
        end
    end

    initial begin
        ticks(5); rst_n=1; ticks(5);
        expect_config(2'b11, 8'd80, 8'd130);
        repeat(5) begin keys[0]=0; ticks(1); keys[0]=1; ticks(1); end
        ticks(10);
        expect_config(2'b11, 8'd80, 8'd130);

        // EDGE -> ORIGIN -> GRAY -> BINARY -> EDGE, one step per press.
        press_mode(); expect_config(2'b00, 8'd80, 8'd130);
        short_k4(); long_k4(18'h05082);
        press_mode(); expect_config(2'b01, 8'd80, 8'd130);
        short_k4(); long_k4(18'h15082);
        press_mode(); expect_config(2'b10, 8'd80, 8'd130);

        short_k4(); expect_config(2'b10, 8'd80, 8'd120);
        long_k4(18'h25082);  // BINARY -> 130, EDGE remains 80
        long_k4({2'b10,8'd80,8'd140});
        press_mode(); expect_config(2'b11, 8'd80, 8'd140);
        short_k4(); expect_config(2'b11, 8'd70, 8'd140);
        long_k4(18'h3508c);  // EDGE -> 80, BINARY remains 140
        long_k4(18'h35a8c);

        // Three more presses land on BINARY; both saved thresholds survive.
        press_mode(); expect_config(2'b00, 8'd90, 8'd140);
        press_mode(); expect_config(2'b01, 8'd90, 8'd140);
        press_mode(); expect_config(2'b10, 8'd90, 8'd140);
        short_k4(); expect_config(2'b10, 8'd90, 8'd130);
        press_mode(); expect_config(2'b11, 8'd90, 8'd130);

        // Saturating endpoints.
        for (i=0;i<12;i=i+1) short_k4();
        expect_config(2'b11, 8'd10, 8'd130);
        short_k4(); expect_config(2'b11, 8'd10, 8'd130);
        for (i=20;i<=250;i=i+10) long_k4({2'b11,i[7:0],8'd130});
        long_k4(18'h3fa82);
        if (cfg !== 18'h3fa82) $fatal(1, "FAIL EDGE upper saturation");

        repeat(80) @(negedge clk);
        if (received !== cfg || delivered != launched)
            $fatal(1, "FAIL latest CDC config not delivered");
        $display("PASS multi-mode keys: K3 cycle/debounce/hold, K4 short/long, independent 10..250 thresholds, CDC ACK");
        $finish;
    end
endmodule

module tb_edge_multi_mode_mailbox;
    reg sc=0, dc=0, rn=0;
    always #3 sc=~sc;
    always #11 dc=~dc;
    reg [17:0] requested={2'b11,8'd80,8'd130};
    wire [17:0] received;
    edge_config_cdc dut (
        .src_clk(sc), .dst_clk(dc), .rst_n(rn),
        .requested_config(requested), .received_config(received)
    );
    integer i, launched=0, delivered=0;
    reg [17:0] sent_packets [0:255];
    reg [17:0] sampled_request, previous_received;
    reg previous_toggle=0;
    reg [7:0] edge_value, binary_value;
    always @(posedge sc) begin
        sampled_request=requested;
        #1;
        if(!rn) begin launched=0;previous_toggle=0;end
        else if(dut.req_toggle!==previous_toggle) begin
            sent_packets[launched]=sampled_request;
            launched=launched+1;
            previous_toggle=dut.req_toggle;
        end
    end
    always @(posedge dc) begin
        #1;
        if(!rn) begin delivered=0;previous_received=18'h35082;end
        else if(received!==previous_received) begin
            if(delivered>=launched || received!==sent_packets[delivered])
                $fatal(1,"FAIL CDC torn/out-of-order packet %0d got %h expected %h",
                       delivered,received,sent_packets[delivered]);
            delivered=delivered+1;
            previous_received=received;
        end
    end
    initial begin
        repeat(4) @(negedge sc); rn=1;
        for(i=0;i<200;i=i+1) begin
            @(negedge sc);
            edge_value=10+10*((i*7)%25);
            binary_value=10+10*((i*11)%25);
            requested={i[1:0],edge_value,binary_value};
        end
        repeat(80) @(negedge sc);
        if(received!==requested || delivered!=launched)
            $fatal(1,"FAIL coalesced CDC latest request");
        rn=0; repeat(5) @(negedge sc); rn=1;
        repeat(80) @(negedge sc);
        if(received!==requested || delivered!=launched)
            $fatal(1,"FAIL mailbox reset recovery");
        $display("PASS multi-mode mailbox: 200 fast atomic 18-bit packets, latest state, reset recovery");
        $finish;
    end
endmodule
