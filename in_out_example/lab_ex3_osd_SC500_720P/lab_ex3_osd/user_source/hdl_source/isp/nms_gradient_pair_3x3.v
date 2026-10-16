`timescale 1ns / 1ps
// Two 14-bit gradient magnitudes per beat. Direction belongs to the CENTER.
// Gy points up: 0=W/E, 1=SW/NE, 2=N/S, 3=NW/SE (strict/inclusive).
// Four stages; early SOF and all valid beats preserved. No hysteresis here.
module nms_gradient_pair_3x3 #(
    parameter integer IMG_WIDTH=1280,
    parameter integer IMG_HEIGHT=720,
    parameter integer INPUT_BORDER=4
)(
    input clk,input rst_n,
    input [27:0] I_magnitude,input [3:0] I_direction,
    input I_valid,input I_user,input I_last,input [13:0] I_threshold,
    output reg [27:0] O_magnitude,output reg [1:0] O_keep,
    output O_valid,output O_user,output O_last,output [13:0] O_threshold,
    // Unused debug ports are optimized away in the actual FPGA top.
    output reg O_debug_valid,output reg [27:0] O_center,
    output reg [3:0] O_direction,output reg [27:0] O_negative,O_positive
);
    localparam GROUPS=IMG_WIDTH/4;
    reg [3:0] valid_p,user_p,last_p;
    reg [13:0] threshold_p[0:3];
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            valid_p<=0;user_p<=0;last_p<=0;
            for(i=0;i<4;i=i+1) threshold_p[i]<=14'd80;
        end else begin
            valid_p<={valid_p[2:0],I_valid};user_p<={user_p[2:0],I_user};last_p<={last_p[2:0],I_last};
            threshold_p[0]<=I_threshold;
            for(i=1;i<4;i=i+1) threshold_p[i]<=threshold_p[i-1];
        end
    end
    assign O_valid=valid_p[3];assign O_user=user_p[3];assign O_last=last_p[3];
    assign O_threshold=threshold_p[3];

    // N1: compact {dir,mag} per sample. Only the middle row needs direction.
    reg [31:0] pair_s1;
    reg [10:0] x_group,y,x_s1,y_s1;
    wire [10:0] x_now=I_user ? 11'd0 : x_group;
    wire [10:0] y_now=I_user ? 11'd0 : y;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin pair_s1<=0;x_group<=0;y<=0;x_s1<=0;y_s1<=0;end
        else begin
            if(I_user) begin x_group<=0;y<=0;end
            if(I_valid) begin
                pair_s1<={I_direction[3:2],I_magnitude[27:14],I_direction[1:0],I_magnitude[13:0]};
                x_s1<=x_now;y_s1<=y_now;
                if(x_now==GROUPS-1) begin x_group<=0;y<=(y_now==IMG_HEIGHT-1)?11'd0:y_now+1'b1;end
                else begin x_group<=x_now+1'b1;y<=y_now;end
            end
        end
    end
    // N2 old-data reads. AUTO inference, not an assumed ERAM implementation.
    // 320*32 + 320*28 = 19200bits for 640 samples. One read/write per row/clock.
    reg [31:0] row1[0:GROUPS-1];
    reg [27:0] row2[0:GROUPS-1];
    reg [27:0] top_s2,bot_s2;
    reg [31:0] mid_s2;
    reg [10:0] x_s2,y_s2;
    always @(posedge clk) begin
        if(valid_p[0]) begin
            top_s2<=row2[x_s1];mid_s2<=row1[x_s1];
            bot_s2<={pair_s1[29:16],pair_s1[13:0]};
            row1[x_s1]<=pair_s1;
        end
        if(valid_p[1]) row2[x_s2]<={mid_s2[29:16],mid_s2[13:0]};
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin x_s2<=0;y_s2<=0;end
        else begin x_s2<=x_s1;y_s2<=y_s1;end
    end

    function [27:0] neighbors;
        input [1:0] axis;
        input [13:0] w,e,n,s,nw,ne,sw,se;
        begin
            case(axis)
                0:neighbors={w,e};1:neighbors={sw,ne};
                2:neighbors={n,s};3:neighbors={nw,se};default:neighbors={w,e};
            endcase
        end
    endfunction
    // N3 select each center from the previous row and adjacent samples.
    reg [13:0] t2,t1,b2,b1;
    reg [15:0] m2,m1,center0_s3,center1_s3;
    reg [27:0] neighbor0_s3,neighbor1_s3;
    reg window_s3;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            t2<=0;t1<=0;b2<=0;b1<=0;m2<=0;m1<=0;
            center0_s3<=0;center1_s3<=0;neighbor0_s3<=0;neighbor1_s3<=0;window_s3<=0;
        end else begin
            window_s3<=valid_p[1] && y_s2>=INPUT_BORDER+2 && x_s2>=(INPUT_BORDER+2)/2 && !user_p[1];
            if(valid_p[1]) begin
                center0_s3<=m1;center1_s3<=mid_s2[31:16];
                neighbor0_s3<=neighbors(m1[15:14],m2[13:0],mid_s2[29:16],t1,b1,t2,top_s2[27:14],b2,bot_s2[27:14]);
                neighbor1_s3<=neighbors(mid_s2[31:30],m1[13:0],mid_s2[13:0],top_s2[27:14],bot_s2[27:14],t1,top_s2[13:0],b1,bot_s2[13:0]);
                t2<=top_s2[27:14];t1<=top_s2[13:0];b2<=bot_s2[27:14];b1<=bot_s2[13:0];
                m2<=mid_s2[31:16];m1<=mid_s2[15:0];
            end
            if(user_p[1] || (valid_p[1] && x_s2==GROUPS-1)) begin
                t2<=0;t1<=0;b2<=0;b1<=0;m2<=0;m1<=0;
            end
        end
    end
    wire keep0=window_s3 && center0_s3[13:0]>neighbor0_s3[27:14] && center0_s3[13:0]>=neighbor0_s3[13:0];
    wire keep1=window_s3 && center1_s3[13:0]>neighbor1_s3[27:14] && center1_s3[13:0]>=neighbor1_s3[13:0];
    // N4 suppress BEFORE threshold. Full 14-bit magnitudes are retained.
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            O_magnitude<=0;O_keep<=0;O_debug_valid<=0;O_center<=0;O_direction<=0;O_negative<=0;O_positive<=0;
        end else begin
            O_keep<={keep0,keep1};
            O_magnitude<={keep0 ? center0_s3[13:0]:14'd0,keep1 ? center1_s3[13:0]:14'd0};
            O_debug_valid<=window_s3;
            O_center<={center0_s3[13:0],center1_s3[13:0]};O_direction<={center0_s3[15:14],center1_s3[15:14]};
            O_negative<={neighbor0_s3[27:14],neighbor1_s3[27:14]};O_positive<={neighbor0_s3[13:0],neighbor1_s3[13:0]};
        end
    end
endmodule
