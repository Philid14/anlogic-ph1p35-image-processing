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
    // V2: shared-lightness palette, neutral protection and dark-side luma ink.
    function [7:0] mn;input[7:0]a,b;begin mn=(a<b)?a:b;end endfunction
    function [7:0] mx;input[7:0]a,b;begin mx=(a>b)?a:b;end endfunction
    function [11:0] color_bins;input[23:0]p;
        begin color_bins={p[23:20],p[15:12],p[7:4]};end
    endfunction
    function [7:0] luma;input[23:0]p;
        begin luma={2'b0,p[23:18]}+{1'b0,p[15:9]}+{2'b0,p[7:2]};end
    endfunction
    function [23:0] mean4;input[23:0]a,b,c,d;
        reg[9:0]s;integer k;
        begin for(k=0;k<3;k=k+1)begin
            s={2'b0,a[8*k +:8]}+{2'b0,b[8*k +:8]}+
              {2'b0,c[8*k +:8]}+{2'b0,d[8*k +:8]}+10'd2;
            mean4[8*k +:8]=s[9:2];
        end end
    endfunction
    function [8:0] absdiff;input[8:0]a,b;
        begin absdiff=(a>b)?a-b:b-a;end
    endfunction
    function [7:0] tone;input[7:0]l;
        reg[8:0]r;
        begin r={1'b0,l}+9'd16;tone=(l>=240)?8'd255:{r[7:5],5'b0};end
    endfunction
    function [7:0] shifted;input[7:0]c;input signed[8:0]delta;
        reg signed[9:0]s;
        begin
            s=$signed({2'b00,c})+$signed({delta[8],delta});
            if(s<0)shifted=0;else if(s>255)shifted=255;else shifted=s[7:0];
        end
    endfunction
    genvar lane;
    generate for(lane=0;lane<4;lane=lane+1)begin:g_lane
        wire[23:0] up=previous_row[95-24*lane -:24];
        wire[23:0] cur=current0[95-24*lane -:24];
        wire[23:0] ul,left;
        if(lane==0)begin:g_left
            assign ul=left_upper;assign left=left_current;
        end else begin:g_inner
            assign ul=previous_row[119-24*lane -:24];
            assign left=current0[119-24*lane -:24];
        end
        reg border1,border2;
        wire border=first_y0 || ((lane==0) && first_x0);
        wire flat=(color_bins(ul)==color_bins(cur)) && (color_bins(up)==color_bins(cur)) && (color_bins(left)==color_bins(cur));
        reg[23:0] base1,base2,base3;
        reg[7:0] yul1,yu1,yl1,yc1,low2,high2,gray3;
        reg[8:0] dx2,dy2;
        reg dark2,ink3,neutral3;
        reg signed[8:0] delta3;
        wire[8:0] right_sum={1'b0,yu1}+{1'b0,yc1};
        wire[8:0] left_sum={1'b0,yul1}+{1'b0,yl1};
        wire[8:0] top_sum={1'b0,yul1}+{1'b0,yu1};
        wire[8:0] bottom_sum={1'b0,yl1}+{1'b0,yc1};
        wire[9:0] all_sum={1'b0,right_sum}+{1'b0,left_sum};
        wire[8:0] light_sum={1'b0,low2}+{1'b0,high2}+9'd1;
        wire[7:0] light=light_sum[8:1];
        wire[7:0] quantized=tone(light);
        always @(posedge clk or negedge rst_n)begin
            if(!rst_n)begin
                border1<=1;border2<=1;base1<=0;base2<=0;base3<=0;
                yul1<=0;yu1<=0;yl1<=0;yc1<=0;low2<=0;high2<=0;gray3<=0;
                dx2<=0;dy2<=0;dark2<=0;ink3<=0;neutral3<=0;delta3<=0;
                O_data[95-24*lane -:24]<=0;
            end
            else begin
                // S1: flatten only a genuinely low-variation color window.
                border1<=border;
                base1<=(!border && flat)?mean4(ul,up,left,cur):cur;
                yul1<=luma(ul);yu1<=luma(up);yl1<=luma(left);yc1<=luma(cur);
                // S2: local luminance coherence and current-pixel polarity.
                border2<=border1;base2<=base1;
                low2<=mn(mn(base1[23:16],base1[15:8]),base1[7:0]);
                high2<=mx(mx(base1[23:16],base1[15:8]),base1[7:0]);
                dx2<=absdiff(right_sum,left_sum);dy2<=absdiff(bottom_sum,top_sum);
                dark2<=({yc1,2'b00}<=all_sum);
                // S3: one common offset, never three independent RGB levels.
                base3<=base2;gray3<=quantized;
                delta3<=$signed({1'b0,quantized})-$signed({1'b0,light});
                neutral3<=((high2-low2)<=8'd12);
                ink3<=!border2 && dark2 && ((dx2>=96)||(dy2>=96));
                // S4: signed saturation. No cross-frame history is used.
                if(ink3)O_data[95-24*lane -:24]<=0;
                else if(neutral3)O_data[95-24*lane -:24]<={gray3,gray3,gray3};
                else O_data[95-24*lane -:24]<=
                    {shifted(base3[23:16],delta3),shifted(base3[15:8],delta3),shifted(base3[7:0],delta3)};
            end
        end
    end endgenerate
endmodule
