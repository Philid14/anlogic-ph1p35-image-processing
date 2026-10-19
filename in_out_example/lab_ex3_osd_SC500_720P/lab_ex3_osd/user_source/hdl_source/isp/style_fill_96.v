`timescale 1ns / 1ps
// Bounded local-region cartoon. Spatial lane0 is [95:72], left to right.
// Five registered stages, one 4-pixel beat per clock, no backpressure.
// Ping-pong line banks avoid read-during-write ambiguity. RAM is not reset;
// first-row/first-column qualification prevents stale/previous-frame use.
module style_fill_96 #(
    parameter integer IMG_WIDTH=1280,
    parameter integer IMG_HEIGHT=720
)(
    input clk, input rst_n,
    input [95:0] I_data,
    input I_valid, input I_user,
    output reg [95:0] O_data
);
    localparam GROUPS=IMG_WIDTH/4;
    localparam XB=(GROUPS>1)?$clog2(GROUPS):1;
    localparam YB=(IMG_HEIGHT>1)?$clog2(IMG_HEIGHT):1;
    reg [95:0] row_even[0:GROUPS-1];
    reg [95:0] row_odd [0:GROUPS-1];
    reg [XB-1:0] x;
    reg [YB-1:0] y;
    wire [XB-1:0] xn=I_user ? 0 : x;
    wire [YB-1:0] yn=I_user ? 0 : y;
    reg [95:0] current0;
    reg valid0, first_x0, first_y0;
    reg [23:0] left_current, left_upper;
    // Both RAM reads are synchronous, each bank is written only while the
    // other is being consumed. No same-bank read value is selected on write.
    reg [95:0] even_q, odd_q;
    reg bank0;
    always @(posedge clk) begin
        even_q<=row_even[xn]; odd_q<=row_odd[xn];
        if(rst_n && I_valid) begin
            if(yn[0]) row_odd[xn]<=I_data;
            else row_even[xn]<=I_data;
        end
    end
    wire [95:0] previous_row=bank0 ? even_q : odd_q;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n)begin
            x<=0;y<=0;current0<=0;valid0<=0;first_x0<=1;first_y0<=1;
            bank0<=0;left_current<=0;left_upper<=0;
        end else begin
            if(I_user)begin x<=0;y<=0;end
            if(I_valid)begin
                if(xn==GROUPS-1)begin x<=0;y<=(yn==IMG_HEIGHT-1)?0:yn+1'b1;end
                else begin x<=xn+1'b1;y<=yn;end
            end
            current0<=I_data;valid0<=I_valid;bank0<=yn[0];
            first_x0<=(xn==0);first_y0<=(yn==0);
            if(valid0)begin
                left_current<=current0[23:0];left_upper<=previous_row[23:0];
            end
        end
    end
    function [3:0] mn;input[3:0]a,b;begin mn=(a<b)?a:b;end endfunction
    function [3:0] mx;input[3:0]a,b;begin mx=(a>b)?a:b;end endfunction
    genvar lane,channel;
    generate for(lane=0;lane<4;lane=lane+1)begin:g_lane
        wire[23:0] a=previous_row[95-24*lane -:24];
        wire[23:0] c=current0[95-24*lane -:24];
        wire[23:0] b,d;
        if(lane==0)begin:g_left
            assign b=left_upper;assign d=left_current;
        end else begin:g_inner
            assign b=previous_row[119-24*lane -:24];
            assign d=current0[119-24*lane -:24];
        end
        reg border1,border2,border3;
        wire border=first_y0 || ((lane==0) && first_x0);
        wire[2:0] flat_channel, ink_channel;
        wire[23:0] palette;
        for(channel=0;channel<3;channel=channel+1)begin:g_channel
            wire[7:0] av=a[8*channel +:8],bv=b[8*channel +:8];
            wire[7:0] cv=c[8*channel +:8],dv=d[8*channel +:8];
            reg[3:0] minab1,mincd1,maxab1,maxcd1;
            reg[8:0] sumab1,sumcd1;
            reg[9:0] sum2;
            reg[3:0] min2,max2,span3;
            reg[1:0] point1,point2,point3,mean3;
            always @(posedge clk or negedge rst_n)begin
                if(!rst_n)begin
                    minab1<=0;mincd1<=0;maxab1<=0;maxcd1<=0;
                    sumab1<=0;sumcd1<=0;sum2<=0;min2<=0;max2<=0;
                    span3<=0;point1<=0;point2<=0;point3<=0;mean3<=0;
                end else begin
                    minab1<=mn(av[7:4],bv[7:4]);mincd1<=mn(cv[7:4],dv[7:4]);
                    maxab1<=mx(av[7:4],bv[7:4]);maxcd1<=mx(cv[7:4],dv[7:4]);
                    sumab1<={1'b0,av}+{1'b0,bv};sumcd1<={1'b0,cv}+{1'b0,dv};
                    sum2<={1'b0,sumab1}+{1'b0,sumcd1}+10'd2;
                    min2<=mn(minab1,mincd1);max2<=mx(maxab1,maxcd1);
                    span3<=max2-min2;mean3<=sum2[9:8];
                    point1<=cv[7:6];point2<=point1;point3<=point2;
                end
            end
            assign flat_channel[channel]=(span3<=2);
            assign ink_channel[channel]=(span3>=4);
            wire[1:0] q=(!border3 && (&flat_channel))?mean3:point3;
            assign palette[channel*8 +:8]={q,q,q,q};
        end
        always @(posedge clk or negedge rst_n)begin
            if(!rst_n)begin border1<=1;border2<=1;border3<=1;O_data[95-24*lane -:24]<=0;end
            else begin
                border1<=border;border2<=border1;border3<=border2;
                O_data[95-24*lane -:24]<=(!border3 && (|ink_channel))?24'd0:palette;
            end
        end
    end endgenerate
endmodule
