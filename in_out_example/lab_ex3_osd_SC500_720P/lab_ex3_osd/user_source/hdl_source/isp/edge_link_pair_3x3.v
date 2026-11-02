`timescale 1ns / 1ps
// One bounded eight-neighbor propagation step, TWO samples per clock.
// A sample is {weak_candidate, active}; weak is delayed with its own center.
// Three stages: capture, synchronous old-data row reads, boolean window.
// No feedback within a stage: instantiating four stages means FOUR hops only.
module edge_link_pair_3x3 #(
    parameter integer IMG_WIDTH=1280,
    parameter integer IMG_HEIGHT=720,
    parameter integer INPUT_BORDER=6
)(
    input clk,input rst_n,
    input [3:0] I_labels,input I_valid,input I_user,input I_last,
    output reg [3:0] O_labels,output O_valid,output O_user,output O_last
);
    localparam GROUPS=IMG_WIDTH/4;
    localparam WORDS=(GROUPS+3)/4;
    localparam ADDR_BITS=(WORDS>1) ? $clog2(WORDS):1;
    reg [2:0] valid_p,user_p,last_p;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin valid_p<=0;user_p<=0;last_p<=0;end
        else begin
            valid_p<={valid_p[1:0],I_valid};user_p<={user_p[1:0],I_user};last_p<={last_p[1:0],I_last};
        end
    end
    assign O_valid=valid_p[2];assign O_user=user_p[2];assign O_last=last_p[2];

    // L1 counts only valid beats. SOF may precede the first valid sample.
    reg [10:0] x_group,y,x_s1,y_s1;
    reg [3:0] labels_s1;
    wire [10:0] x_now=I_user ? 11'd0:x_group;
    wire [10:0] y_now=I_user ? 11'd0:y;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin x_group<=0;y<=0;x_s1<=0;y_s1<=0;labels_s1<=0;end
        else begin
            if(I_user) begin x_group<=0;y<=0;end
            if(I_valid) begin
                x_s1<=x_now;y_s1<=y_now;labels_s1<=I_labels;
                if(x_now==GROUPS-1) begin x_group<=0;y<=(y_now==IMG_HEIGHT-1)?11'd0:y_now+1'b1;end
                else begin x_group<=x_now+1'b1;y<=y_now;end
            end
        end
    end
    // L2: coalesce FOUR beats; store top-row ACTIVE bits only.
    // 80*(16+8)=1920 logical bits/hop, versus R0's 320*4*2=2560.
    // Read the old word four times; write row1 after its fourth read.
    // Row2 copies registered old mid active bits one clock after that read.
    reg [7:0] top_word_s2;
    wire [15:0] mid_word_s2;
    reg [11:0] pending;
    reg [3:0] bot_s2;
    reg [10:0] x_s2,y_s2;
    wire [ADDR_BITS-1:0] read_address=x_s1[ADDR_BITS+1:2];
    wire [ADDR_BITS-1:0] copy_address=x_s2[ADDR_BITS+1:2];
    wire [3:0] mid_s2=(mid_word_s2 >> (4*(3-x_s2[1:0])));
    wire [1:0] top_active=(top_word_s2 >> (2*(3-x_s2[1:0])));
    wire [3:0] top_s2={1'b0,top_active[1],1'b0,top_active[0]};
    // Shift away stale prefix bits for an incomplete final word (generic widths).
    wire [15:0] assembled=(GROUPS%4==0) ? {pending,labels_s1} :
        ({pending,labels_s1} << (4*(3-x_s1[1:0])));
    always @(posedge clk) begin
        if(valid_p[0]) begin
            bot_s2<=labels_s1;
            pending<={pending[7:0],labels_s1};
        end
    end
    generate if(GROUPS%4==0 && WORDS<=512)begin:g_shared_rows
        // Port A reads row1 every beat, READBEFOREWRITE on quarter3.
        // Row2 is prefetched on quarter3 into a register for the next word.
        // Its old value is cached on quarter0 before port B copies old row1
        // on quarter1. Thus B never needs different read/write addresses in
        // one clock. Regions0..WORDS-1 and512..512+WORDS-1 are disjoint.
        wire prefetch=valid_p[0] && x_s1[1:0]==3;
        wire copy=valid_p[1] && x_s2[1:0]==0;
        wire [ADDR_BITS-1:0] next_address=read_address==WORDS-1?0:read_address+1'b1;
        wire [9:0] a_address=read_address;
        wire [9:0] b_address=10'd512+(copy?copy_address:next_address);
        wire [7:0] copied={mid_word_s2[14],mid_word_s2[12],mid_word_s2[10],mid_word_s2[8],
                          mid_word_s2[6],mid_word_s2[4],mid_word_s2[2],mid_word_s2[0]};
        wire [15:0] top_prefetched;reg [7:0] top_hold;
        PH1P_LOGIC_ERAM #(.DATA_WIDTH_A(16),.DATA_WIDTH_B(16),.ADDR_WIDTH_A(10),.ADDR_WIDTH_B(10),
          .DATA_DEPTH_A(1024),.DATA_DEPTH_B(1024),.MODE("DP"),.CLKMODE("SYNC"),
          .REGMODE_A("NOREG"),.REGMODE_B("NOREG"),.WRITEMODE_A("READBEFOREWRITE"),
          .WRITEMODE_B("NORMAL"),.INIT_FILE("NONE"),.FILL_ALL("NONE"),.FORCE_KEEP("ON")) u_rows(
          .clka(clk),.cea(valid_p[0]),.ocea(1'b1),.addra(a_address),.dia(assembled),.wea(x_s1[1:0]==3),
          .rsta(1'b0),.bea(1'b1),.doa(mid_word_s2),
          .clkb(clk),.ceb(prefetch||copy),.oceb(1'b1),.addrb(b_address),.dib({8'd0,copied}),.web(copy),
          .rstb(1'b0),.beb(1'b1),.dob(top_prefetched),
          .ecc_sbiterrinj(1'b0),.ecc_dbiterrinj(1'b0),.ecc_sbiterr(),.ecc_dbiterr());
        always @(posedge clk)if(valid_p[0])begin
            top_word_s2<=x_s1[1:0]==0?top_prefetched[7:0]:top_hold;
            if(x_s1[1:0]==0)top_hold<=top_prefetched[7:0];
        end
    end else begin:g_partial_words
        // Preserve the established generic partial-word schedule unchanged.
        reg [15:0] row1[0:WORDS-1];reg [7:0] row2[0:WORDS-1];reg[15:0] mid;
        assign mid_word_s2=mid;
        always @(posedge clk)begin
            if(valid_p[0])begin
                top_word_s2<=row2[read_address];mid<=row1[read_address];
                if(x_s1[1:0]==3 || x_s1==GROUPS-1)row1[read_address]<=assembled;
            end
            if(valid_p[1] && (x_s2[1:0]==3 || x_s2==GROUPS-1))
                row2[copy_address]<={mid_word_s2[14],mid_word_s2[12],mid_word_s2[10],mid_word_s2[8],
                                  mid_word_s2[6],mid_word_s2[4],mid_word_s2[2],mid_word_s2[0]};
        end
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin x_s2<=0;y_s2<=0;end
        else begin x_s2<=x_s1;y_s2<=y_s1;end
    end

    // L3: true previous-row centers are m1 (cross-beat) and mid_s2[3:2].
    // Only active bits are needed in top/bottom horizontal carry.
    reg t2,t1,b2,b1;
    reg [1:0] m2,m1;
    wire window_valid=valid_p[1] && !user_p[1] &&
        y_s2>=INPUT_BORDER+2 && x_s2>=(INPUT_BORDER+2)/2;
    wire near0=t2|t1|top_s2[2]|m2[0]|mid_s2[2]|b2|b1|bot_s2[2];
    wire near1=t1|top_s2[2]|top_s2[0]|m1[0]|mid_s2[0]|b1|bot_s2[2]|bot_s2[0];
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin t2<=0;t1<=0;b2<=0;b1<=0;m2<=0;m1<=0;O_labels<=0;end
        else begin
            O_labels<=window_valid ?
                {m1[1],m1[1] & (m1[0]|near0),mid_s2[3],mid_s2[3] & (mid_s2[2]|near1)}:4'd0;
            if(valid_p[1]) begin
                t2<=top_s2[2];t1<=top_s2[0];b2<=bot_s2[2];b1<=bot_s2[0];
                m2<=mid_s2[3:2];m1<=mid_s2[1:0];
            end
            if(user_p[1] || (valid_p[1] && x_s2==GROUPS-1)) begin
                t2<=0;t1<=0;b2<=0;b1<=0;m2<=0;m1<=0;
            end
        end
    end
endmodule
