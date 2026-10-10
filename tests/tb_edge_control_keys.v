`timescale 1ns / 1ps
module tb_edge_control_keys;
    reg clk=0,dclk=0,rst_n=0;
    always #5 clk=~clk;
    always #7 dclk=~dclk;
    reg [1:0] keys=2'b11;
    wire [8:0] cfg, received;
    edge_key_control #(.DEBOUNCE_CYCLES(5),.LONG_CYCLES(35)) dut (
        .clk(clk),.rst_n(rst_n),.keys_n(keys),.requested_config(cfg));
    edge_config_cdc mailbox (.src_clk(clk),.dst_clk(dclk),.rst_n(rst_n),
        .requested_config(cfg),.received_config(received));
    reg [8:0] held_previous;
    reg req_previous, was_busy;
    integer events=0, i;
    always @(posedge clk) begin
        if (rst_n) begin
            if (was_busy && mailbox.held_config !== held_previous)
                $fatal(1,"FAIL CDC bus changed before ACK");
            held_previous=mailbox.held_config;
            was_busy=mailbox.req_toggle != mailbox.ack_sync;
            if (cfg[7:0]<10 || cfg[7:0]>250) $fatal(1,"FAIL config out of range");
        end else begin held_previous={1'b1,8'd80};was_busy=0;end
    end
    task ticks;
        input integer n;
        begin repeat(n) @(negedge clk); end
    endtask
    task expect_threshold;
        input [7:0] th;
        begin
            ticks(3);
            if(cfg[7:0] !== th) $fatal(1,"FAIL threshold got %0d expected %0d",cfg[7:0],th);
        end
    endtask
    task short_key4;
        begin keys[1]=0;ticks(12);keys[1]=1;ticks(12);end
    endtask
    task long_key4;
        input [7:0] expected;
        begin
            keys[1]=0;ticks(70);expect_threshold(expected);
            ticks(70);expect_threshold(expected);
            keys[1]=1;ticks(12);expect_threshold(expected);
        end
    endtask
    initial begin
        ticks(5);rst_n=1;ticks(5);
        // Chatter shorter than debounce cannot toggle the mode.
        repeat(5) begin keys[0]=0;ticks(1);keys[0]=1;ticks(1);end
        ticks(10);
        if(cfg !== {1'b1,8'd80}) $fatal(1,"FAIL chatter generated event");
        keys[0]=0;ticks(12);
        if(cfg[8]!==0) $fatal(1,"FAIL mode press");
        ticks(100);
        if(cfg[8]!==0) $fatal(1,"FAIL held mode repeated");
        keys[0]=1;ticks(12);
        short_key4();expect_threshold(70);
        short_key4();expect_threshold(60);
        long_key4(70);long_key4(80);long_key4(90);long_key4(100);
        for(i=0;i<12;i=i+1) short_key4();expect_threshold(10);
        short_key4();expect_threshold(10);
        for(i=20;i<=250;i=i+10) long_key4(i);
        long_key4(250);
        // Simultaneous keys, and repeated release chatter.
        keys=0;ticks(12);keys=3;ticks(12);expect_threshold(240);
        if(cfg[8]!==1) $fatal(1,"FAIL concurrent mode press");
        repeat(5) begin keys[1]=0;ticks(1);keys[1]=1;ticks(1);end
        ticks(15);expect_threshold(240);
        ticks(30);
        if(received!==cfg) $fatal(1,"FAIL latest CDC config not delivered");
        $display("PASS checkpoint_A keys: bounce, single mode, short/long exclusivity, 80/70/60/90/100, 10/250 saturation, CDC ACK");
        $finish;
    end
endmodule

module tb_edge_control_mailbox;
    reg sc=0,dc=0,rn=0;
    always #3 sc=~sc;
    always #11 dc=~dc;
    reg [8:0] requested={1'b1,8'd80};
    wire [8:0] received;
    edge_config_cdc dut (.src_clk(sc),.dst_clk(dc),.rst_n(rn),
        .requested_config(requested),.received_config(received));
    integer i;
    reg [7:0] next_threshold;
    reg [8:0] sent_packets [0:255];
    reg [8:0] sampled_request, previous_received={1'b1,8'd80};
    reg previous_toggle=0;
    integer launched=0,delivered=0;
    always @(posedge sc) begin
        sampled_request=requested;
        #1;
        if(!rn) begin launched=0;previous_toggle=0;end
        else if(dut.req_toggle!==previous_toggle) begin
            sent_packets[launched]=sampled_request;launched=launched+1;
            previous_toggle=dut.req_toggle;
        end
    end
    always @(posedge dc) begin
        #1;
        if(!rn) begin delivered=0;previous_received={1'b1,8'd80};end
        else if(received!==previous_received) begin
            if(delivered>=launched || received!==sent_packets[delivered])
                $fatal(1,"FAIL CDC torn/out-of-order packet %0d got %h expected %h",delivered,received,sent_packets[delivered]);
            delivered=delivered+1;previous_received=received;
        end
    end
    initial begin
        repeat(4) @(negedge sc);rn=1;
        for(i=0;i<200;i=i+1) begin
            @(negedge sc);next_threshold=10+10*(i%25);requested={i[0],next_threshold};
        end
        repeat(80) @(negedge sc);
        if(received!==requested || delivered!=launched) $fatal(1,"FAIL coalesced CDC latest request");
        rn=0;repeat(5) @(negedge sc);rn=1;
        repeat(80) @(negedge sc);
        if(received!==requested || delivered!=launched) $fatal(1,"FAIL mailbox reset recovery");
        $display("PASS checkpoint_A mailbox: asynchronous clocks, 200 fast requests, exact atomic packet order, latest state, common reset recovery");
        $finish;
    end
endmodule
