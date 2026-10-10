`timescale 1ns / 1ps
// Stage 1 adaptation of the bundled edge_example edge_detect_96.v.
// Keep its pair-averaged luminance, Sobel kernel and duplicated binary output.
// 1280 output pixels represent 640 horizontal Sobel samples, not 1280 kernels.
// Local changes: early SOF support, synchronous line RAM, five pipeline stages,
// and explicit non-stalling stream semantics. See ALGORITHM_INTEGRATION_PLAN.md.
module edge_detect_96 #(
    parameter IMG_WIDTH = 1280,
    parameter IMG_HEIGHT = 720,
    parameter [13:0] EDGE_TH = 14'd80,
    parameter integer RUNTIME_THRESHOLD = 0
)(
    input I_clk,
    input I_rst_n,
    input I_tlast,
    input I_tuser,
    input [95:0] I_tdata,
    input I_tvalid,
    output I_tready,
    output O_tlast,
    output O_tuser,
    output reg [95:0] O_tdata,
    output O_tvalid,
    input O_tready,
    input [7:0] I_threshold
);
    // The camera/packer chain has no backpressure protocol. Never discard a
    // valid camera beat because its existing downstream ready is undriven.
    assign I_tready = 1'b1;
    localparam LINE_GROUPS = IMG_WIDTH / 4;

    function [7:0] gray;
        input [23:0] rgb;
        begin
            // Preserve the reference's separate truncations (white = 253).
            gray = {2'b0,rgb[23:18]} + {1'b0,rgb[15:9]}
                 + {2'b0,rgb[7:2]};
        end
    endfunction
    wire [8:0] pair_sum0 = {1'b0,gray(I_tdata[95:72])}
                         + {1'b0,gray(I_tdata[71:48])};
    wire [8:0] pair_sum1 = {1'b0,gray(I_tdata[47:24])}
                         + {1'b0,gray(I_tdata[23:0])};

    reg [4:0] valid_p, user_p, last_p;
    reg [7:0] threshold_p [0:3];
    integer th_stage;
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            valid_p <= 5'b0;
            user_p <= 5'b0;
            last_p <= 5'b0;
            for (th_stage=0; th_stage<4; th_stage=th_stage+1)
                threshold_p[th_stage] <= EDGE_TH[7:0];
        end else begin
            valid_p <= {valid_p[3:0],I_tvalid};
            user_p <= {user_p[3:0],I_tuser};
            last_p <= {last_p[3:0],I_tlast};
            threshold_p[0] <= I_threshold;
            for (th_stage=1; th_stage<4; th_stage=th_stage+1)
                threshold_p[th_stage] <= threshold_p[th_stage-1];
        end
    end
    assign O_tvalid = valid_p[4];
    assign O_tuser = user_p[4];
    assign O_tlast = last_p[4];

    // S1: one word per four RGB pixels. Count only valid beats; SOF also
    // resets counters when it arrives before the AWB delayed pixels.
    reg [10:0] x_grp, y_pos, x_s1, y_s1;
    reg [15:0] pair_s1;
    wire [10:0] x_now = I_tuser ? 11'd0 : x_grp;
    wire [10:0] y_now = I_tuser ? 11'd0 : y_pos;
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            x_grp <= 0; y_pos <= 0;
            x_s1 <= 0; y_s1 <= 0; pair_s1 <= 0;
        end else begin
            if (I_tuser) begin
                x_grp <= 0; y_pos <= 0;
            end
            if (I_tvalid) begin
                pair_s1 <= {pair_sum0[8:1],pair_sum1[8:1]};
                x_s1 <= x_now;
                y_s1 <= y_now;
                if (x_now == LINE_GROUPS-1) begin
                    x_grp <= 0;
                    y_pos <= (y_now == IMG_HEIGHT-1) ? 11'd0 : y_now+1'b1;
                end else begin
                    x_grp <= x_now+1'b1;
                    y_pos <= y_now;
                end
            end
        end
    end

    // S2: synchronous old-data reads. Do not reset the arrays; row masking
    // prevents stale/uninitialized data from contributing to an edge.
    (* ram_style = "block" *) reg [15:0] line1_mem [0:LINE_GROUPS-1];
    (* ram_style = "block" *) reg [15:0] line2_mem [0:LINE_GROUPS-1];
    reg [15:0] top_s2, mid_s2, bot_s2;
    reg [10:0] x_s2, y_s2;
    always @(posedge I_clk) begin
        if (valid_p[0]) begin
            top_s2 <= line2_mem[x_s1];
            mid_s2 <= line1_mem[x_s1];
            bot_s2 <= pair_s1;
            line1_mem[x_s1] <= pair_s1;
        end
        // Copy the already registered previous row one beat later. This
        // removes the reference's combinational RAM-to-RAM write path.
        if (valid_p[1])
            line2_mem[x_s2] <= mid_s2;
    end
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            x_s2 <= 0; y_s2 <= 0;
        end else begin
            x_s2 <= x_s1; y_s2 <= y_s1;
        end
    end

    function signed [12:0] sobel_gx;
        input [7:0] a00,a02,a10,a12,a20,a22;
        begin
            sobel_gx = -$signed({5'b0,a00}) + $signed({5'b0,a02})
                - $signed({4'b0,a10,1'b0}) + $signed({4'b0,a12,1'b0})
                - $signed({5'b0,a20}) + $signed({5'b0,a22});
        end
    endfunction
    function signed [12:0] sobel_gy;
        input [7:0] a00,a01,a02,a20,a21,a22;
        begin
            sobel_gy = $signed({5'b0,a00}) + $signed({4'b0,a01,1'b0})
                + $signed({5'b0,a02}) - $signed({5'b0,a20})
                - $signed({4'b0,a21,1'b0}) - $signed({5'b0,a22});
        end
    endfunction
    function [12:0] abs13;
        input signed [12:0] v;
        begin abs13 = v[12] ? (~v+1'b1) : v; end
    endfunction

    // S3: two causal 3x3 windows. Clear horizontal carry at every row end
    // and at SOF, including a SOF that has no accompanying valid pixel.
    reg [7:0] top_prev2,top_prev1,mid_prev2,mid_prev1,bot_prev2,bot_prev1;
    reg signed [12:0] gx0_s3,gy0_s3,gx1_s3,gy1_s3;
    reg window_s3;
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            top_prev2 <= 0; top_prev1 <= 0;
            mid_prev2 <= 0; mid_prev1 <= 0;
            bot_prev2 <= 0; bot_prev1 <= 0;
            gx0_s3 <= 0; gy0_s3 <= 0; gx1_s3 <= 0; gy1_s3 <= 0;
            window_s3 <= 0;
        end else begin
            window_s3 <= valid_p[1] && (y_s2 >= 2) && (x_s2 != 0) && !user_p[1];
            if (valid_p[1]) begin
                gx0_s3 <= sobel_gx(top_prev2,top_s2[15:8],mid_prev2,mid_s2[15:8],bot_prev2,bot_s2[15:8]);
                gy0_s3 <= sobel_gy(top_prev2,top_prev1,top_s2[15:8],bot_prev2,bot_prev1,bot_s2[15:8]);
                gx1_s3 <= sobel_gx(top_prev1,top_s2[7:0],mid_prev1,mid_s2[7:0],bot_prev1,bot_s2[7:0]);
                gy1_s3 <= sobel_gy(top_prev1,top_s2[15:8],top_s2[7:0],bot_prev1,bot_s2[15:8],bot_s2[7:0]);
                top_prev2 <= top_s2[15:8]; top_prev1 <= top_s2[7:0];
                mid_prev2 <= mid_s2[15:8]; mid_prev1 <= mid_s2[7:0];
                bot_prev2 <= bot_s2[15:8]; bot_prev1 <= bot_s2[7:0];
            end
            if (user_p[1] || (valid_p[1] && x_s2 == LINE_GROUPS-1)) begin
                top_prev2 <= 0; top_prev1 <= 0;
                mid_prev2 <= 0; mid_prev1 <= 0;
                bot_prev2 <= 0; bot_prev1 <= 0;
            end
        end
    end

    // S4: L1 gradient magnitude; S5: threshold and four-pixel RGB packing.
    reg [13:0] mag0_s4,mag1_s4;
    reg window_s4;
    wire [13:0] comparison_threshold = RUNTIME_THRESHOLD ? {6'd0,threshold_p[3]} : EDGE_TH;
    wire [23:0] edge0 = window_s4 && (mag0_s4 >= comparison_threshold) ? 24'hffffff : 24'h0;
    wire [23:0] edge1 = window_s4 && (mag1_s4 >= comparison_threshold) ? 24'hffffff : 24'h0;
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            mag0_s4 <= 0; mag1_s4 <= 0; window_s4 <= 0;
            O_tdata <= 0;
        end else begin
            mag0_s4 <= {1'b0,abs13(gx0_s3)} + {1'b0,abs13(gy0_s3)};
            mag1_s4 <= {1'b0,abs13(gx1_s3)} + {1'b0,abs13(gy1_s3)};
            window_s4 <= window_s3;
            O_tdata <= valid_p[3] ? {edge0,edge0,edge1,edge1} : 96'd0;
        end
    end
endmodule
