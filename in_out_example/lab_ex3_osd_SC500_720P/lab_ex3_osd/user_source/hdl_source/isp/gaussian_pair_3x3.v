`timescale 1ns / 1ps
// Two consecutive 8-bit samples/beat, causal 3x3 [1 2 1]^T[1 2 1]/16.
// Four fixed stages, no stalls. Input and output beat/early-SOF contracts match.
module gaussian_pair_3x3 #(
    parameter integer IMG_WIDTH = 1280,
    parameter integer IMG_HEIGHT = 720
)(
    input clk, input rst_n,
    input [15:0] I_pair,
    input I_valid, input I_user, input I_last,
    input [7:0] I_threshold,
    output reg [15:0] O_pair,
    output O_valid, output O_user, output O_last,
    output [7:0] O_threshold
);
    localparam GROUPS = IMG_WIDTH/4;
    reg [3:0] valid_p, user_p, last_p;
    reg [7:0] threshold_p [0:3];
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_p<=0; user_p<=0; last_p<=0;
            for(i=0;i<4;i=i+1) threshold_p[i]<=8'd80;
        end else begin
            valid_p<={valid_p[2:0],I_valid};
            user_p<={user_p[2:0],I_user};
            last_p<={last_p[2:0],I_last};
            threshold_p[0]<=I_threshold;
            for(i=1;i<4;i=i+1) threshold_p[i]<=threshold_p[i-1];
        end
    end
    assign O_valid=valid_p[3];
    assign O_user=user_p[3];
    assign O_last=last_p[3];
    assign O_threshold=threshold_p[3];

    // G1: capture both samples and their position. SOF can precede valid.
    reg [10:0] x_group,y,x_s1,y_s1;
    wire [10:0] x_now=I_user ? 11'd0 : x_group;
    wire [10:0] y_now=I_user ? 11'd0 : y;
    reg [15:0] pair_s1;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin x_group<=0;y<=0;x_s1<=0;y_s1<=0;pair_s1<=0; end
        else begin
            if(I_user) begin x_group<=0;y<=0;end
            if(I_valid) begin
                pair_s1<=I_pair;x_s1<=x_now;y_s1<=y_now;
                if(x_now==GROUPS-1) begin
                    x_group<=0;y<=(y_now==IMG_HEIGHT-1) ? 11'd0 : y_now+1'b1;
                end else begin x_group<=x_now+1'b1;y<=y_now;end
            end
        end
    end

    // G2: old-data row reads; G3 copies the registered previous row. Each
    // history row has one read and one write/clock, even at full throughput.
    // Arrays deliberately have no reset; G3/G4 border masks reject stale data.
    wire [15:0] top_s2,mid_s2;reg[15:0]bot_s2;
    reg [10:0] x_s2,y_s2;
    edge_row_history u_rows(.clk(clk),.read_en(valid_p[0]),.read_address(x_s1[9:0]),.data(pair_s1),
        .copy_en(valid_p[1]),.copy_address(x_s2[9:0]),.copy_data(mid_s2),.middle(mid_s2),.top(top_s2));
    always @(posedge clk) begin
        if(valid_p[0]) begin
            bot_s2<=pair_s1;
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin x_s2<=0;y_s2<=0;end
        else begin x_s2<=x_s1;y_s2<=y_s1;end
    end

    function [9:0] horizontal;
        input [7:0] a,b,c;
        begin horizontal={2'b0,a}+{1'b0,b,1'b0}+{2'b0,c};end
    endfunction
    // G3: both causal windows, one ending at each current sample. Retain the
    // last two samples per row; reset at every row boundary and early SOF.
    reg [7:0] t2,t1,m2,m1,b2,b1;
    reg [9:0] ht0,hm0,hb0,ht1,hm1,hb1;
    reg window_s3;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            t2<=0;t1<=0;m2<=0;m1<=0;b2<=0;b1<=0;
            ht0<=0;hm0<=0;hb0<=0;ht1<=0;hm1<=0;hb1<=0;window_s3<=0;
        end else begin
            window_s3<=valid_p[1] && y_s2>=2 && x_s2!=0 && !user_p[1];
            if(valid_p[1]) begin
                ht0<=horizontal(t2,t1,top_s2[15:8]);
                hm0<=horizontal(m2,m1,mid_s2[15:8]);
                hb0<=horizontal(b2,b1,bot_s2[15:8]);
                ht1<=horizontal(t1,top_s2[15:8],top_s2[7:0]);
                hm1<=horizontal(m1,mid_s2[15:8],mid_s2[7:0]);
                hb1<=horizontal(b1,bot_s2[15:8],bot_s2[7:0]);
                t2<=top_s2[15:8];t1<=top_s2[7:0];
                m2<=mid_s2[15:8];m1<=mid_s2[7:0];
                b2<=bot_s2[15:8];b1<=bot_s2[7:0];
            end
            if(user_p[1] || (valid_p[1] && x_s2==GROUPS-1)) begin
                t2<=0;t1<=0;m2<=0;m1<=0;b2<=0;b1<=0;
            end
        end
    end
    // G4: exact weighted 12-bit sum (max4080), one final floor(/16).
    wire [11:0] sum0={2'b0,ht0}+{1'b0,hm0,1'b0}+{2'b0,hb0};
    wire [11:0] sum1={2'b0,ht1}+{1'b0,hm1,1'b0}+{2'b0,hb1};
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) O_pair<=0;
        else O_pair<=window_s3 ? {sum0[11:4],sum1[11:4]} : 16'd0;
    end
endmodule
