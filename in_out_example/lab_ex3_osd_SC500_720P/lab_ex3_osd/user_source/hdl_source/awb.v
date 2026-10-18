/*****************************************************************
Company : MiLianKe Electronic Technology Co., Ltd.
WebSite:https://www.milianke.com
TechWeb:https://www.uisrc.com
Copyright (c) MiLianKe. All rights reserved.

AWB_V2: select low-chroma pixels for frame-constant RGB gain. The module
interface, signal_delay RAM and Anlogic divider IP remain unchanged.
*****************************************************************/
module awb #(
    parameter IMG_HEIGHT = 1080,
    parameter IMG_WIDTH  = 1920
)(
    input             I_clk,
    input             I_rst_n,
    input             I_tlast,
    input             I_tuser,
    input      [95:0] I_tdata,
    input             I_tvalid,
    output            I_tready,
    output            O_tlast,
    output            O_tuser,
    output     [95:0] O_tdata,
    output            O_tvalid,
    input             O_tready,
    // Read-only diagnostic taps, aligned to O_tvalid/O_tdata. No gain override.
    output [95:0]     O_diag_pre,
    output [39:0]     O_diag_gain,
    output [143:0]    O_diag_stats
);
    // Q4.16: 1.0 = 0x10000. Bound attenuation to preserve primary colors.
    localparam [19:0] GAIN_ONE  = 20'h10000;
    localparam [19:0] GAIN_MIN  = 20'h0c000; // 0.75
    localparam [19:0] GAIN_MAX  = 20'h30000; // 3.00
    localparam [19:0] GAIN_STEP = 20'h02000; // 0.125 per frame
    localparam [20:0] MIN_SAMPLES = 21'd1024;
    localparam [20:0] MAX_SAMPLES = IMG_WIDTH * IMG_HEIGHT;
    // RGB888 trial threshold: tolerate moderate cast on gray/white regions
    // while rejecting strongly colored red/green/blue regions.
    localparam [7:0] CHROMA_THRESHOLD = 8'd32;

    function pixel_usable;
        input [23:0] pixel;
        reg [7:0] r, g, b, max_rg, max_rgb, min_rg, min_rgb;
        begin
            r = pixel[23:16];
            g = pixel[15:8];
            b = pixel[7:0];
            max_rg = (r > g) ? r : g;
            max_rgb = (max_rg > b) ? max_rg : b;
            min_rg = (r < g) ? r : g;
            min_rgb = (min_rg < b) ? min_rg : b;
            // Use only plausible neutral surfaces for Gray World statistics.
            // A frame without >= MIN_SAMPLES candidates holds prior gains.
            pixel_usable = (max_rgb >= 8'd24) && (max_rgb < 8'd240) &&
                           ((max_rgb - min_rgb) < CHROMA_THRESHOLD);
        end
    endfunction

    function [19:0] clamp_gain;
        input [47:0] quotient;
        begin
            if (|quotient[47:20])
                clamp_gain = GAIN_MAX;
            else if (quotient[19:0] > GAIN_MAX)
                clamp_gain = GAIN_MAX;
            else if (quotient[19:0] < GAIN_MIN)
                clamp_gain = GAIN_MIN;
            else
                clamp_gain = quotient[19:0];
        end
    endfunction

    function [19:0] slew_gain;
        input [19:0] current_gain;
        input [19:0] target_gain;
        begin
            if (target_gain > current_gain) begin
                if ((target_gain - current_gain) > GAIN_STEP)
                    slew_gain = current_gain + GAIN_STEP;
                else
                    slew_gain = target_gain;
            end else if ((current_gain - target_gain) > GAIN_STEP) begin
                slew_gain = current_gain - GAIN_STEP;
            end else begin
                slew_gain = target_gain;
            end
        end
    endfunction

    function [7:0] sat_q16;
        input [27:0] product;
        begin
            if (|product[27:24])
                sat_q16 = 8'hff;
            else
                sat_q16 = product[23:16];
        end
    endfunction

    // Four RGB888 pixels arrive per beat, low 24 bits first. Register
    // partial sums before accumulation to keep the pixel clock path short.
    wire [23:0] in_pixel[0:3];
    wire use_pixel[0:3];
    genvar p;
    generate for (p = 0; p < 4; p = p + 1) begin : pixel_select
        assign in_pixel[p] = I_tdata[p*24 +: 24];
        assign use_pixel[p] = pixel_usable(in_pixel[p]);
    end endgenerate

    wire [9:0] beat_r_comb =
        (use_pixel[0] ? {2'b00,in_pixel[0][23:16]} : 10'd0) +
        (use_pixel[1] ? {2'b00,in_pixel[1][23:16]} : 10'd0) +
        (use_pixel[2] ? {2'b00,in_pixel[2][23:16]} : 10'd0) +
        (use_pixel[3] ? {2'b00,in_pixel[3][23:16]} : 10'd0);
    wire [9:0] beat_g_comb =
        (use_pixel[0] ? {2'b00,in_pixel[0][15:8]} : 10'd0) +
        (use_pixel[1] ? {2'b00,in_pixel[1][15:8]} : 10'd0) +
        (use_pixel[2] ? {2'b00,in_pixel[2][15:8]} : 10'd0) +
        (use_pixel[3] ? {2'b00,in_pixel[3][15:8]} : 10'd0);
    wire [9:0] beat_b_comb =
        (use_pixel[0] ? {2'b00,in_pixel[0][7:0]} : 10'd0) +
        (use_pixel[1] ? {2'b00,in_pixel[1][7:0]} : 10'd0) +
        (use_pixel[2] ? {2'b00,in_pixel[2][7:0]} : 10'd0) +
        (use_pixel[3] ? {2'b00,in_pixel[3][7:0]} : 10'd0);
    wire [2:0] beat_count_comb =
        {2'b00,use_pixel[0]} + {2'b00,use_pixel[1]} +
        {2'b00,use_pixel[2]} + {2'b00,use_pixel[3]};

    reg [9:0] beat_r, beat_g, beat_b;
    reg [2:0] beat_count;
    reg beat_valid, beat_tuser, beat_tlast;
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            beat_r <= 10'd0;
            beat_g <= 10'd0;
            beat_b <= 10'd0;
            beat_count <= 3'd0;
            beat_valid <= 1'b0;
            beat_tuser <= 1'b0;
            beat_tlast <= 1'b0;
        end else begin
            beat_r <= beat_r_comb;
            beat_g <= beat_g_comb;
            beat_b <= beat_b_comb;
            beat_count <= beat_count_comb;
            beat_valid <= I_tvalid;
            beat_tuser <= I_tuser;
            beat_tlast <= I_tlast;
        end
    end

    // 1280*720*255 = 235008000, well within 32 unsigned bits.
    reg [31:0] sum_r, sum_g, sum_b;
    reg [20:0] sample_count;
    reg [10:0] line_count;
    reg [31:0] frame_r, frame_g, frame_b;
    reg frame_ready;
    wire [31:0] final_r = sum_r + (beat_valid ? {22'd0,beat_r} : 32'd0);
    wire [31:0] final_g = sum_g + (beat_valid ? {22'd0,beat_g} : 32'd0);
    wire [31:0] final_b = sum_b + (beat_valid ? {22'd0,beat_b} : 32'd0);
    wire [20:0] final_count = sample_count +
                              (beat_valid ? {18'd0,beat_count} : 21'd0);

    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            sum_r <= 32'd0;
            sum_g <= 32'd0;
            sum_b <= 32'd0;
            sample_count <= 21'd0;
            line_count <= 11'd0;
            frame_r <= 32'd0;
            frame_g <= 32'd0;
            frame_b <= 32'd0;
            frame_ready <= 1'b0;
        end else begin
            frame_ready <= 1'b0;
            if (beat_tuser) begin
                sum_r <= beat_valid ? {22'd0,beat_r} : 32'd0;
                sum_g <= beat_valid ? {22'd0,beat_g} : 32'd0;
                sum_b <= beat_valid ? {22'd0,beat_b} : 32'd0;
                sample_count <= beat_valid ? {18'd0,beat_count} : 21'd0;
                line_count <= 11'd0;
            end else if (beat_valid && (sample_count < MAX_SAMPLES)) begin
                sum_r <= final_r;
                sum_g <= final_g;
                sum_b <= final_b;
                sample_count <= final_count;
            end

            if (beat_tlast && !beat_tuser) begin
                line_count <= line_count + 11'd1;
                if (line_count == IMG_HEIGHT - 1) begin
                    frame_r <= final_r;
                    frame_g <= final_g;
                    frame_b <= final_b;
                    frame_ready <= (final_count >= MIN_SAMPLES) &&
                                   (final_r != 0) && (final_g != 0) &&
                                   (final_b != 0);
                end
            end
        end
    end

    // Start both Anlogic divider IPs only for a complete valid frame.
    wire [47:0] quotient_r, quotient_b;
    wire done_r, done_b;
    divider div_gen_G_R_r1 (
        .clk(I_clk), .rst(!I_rst_n), .start(frame_ready),
        .denominator(frame_r), .numerator({frame_g,16'd0}),
        .quotient(quotient_r), .done(done_r)
    );
    divider divide_G_B_r1 (
        .clk(I_clk), .rst(!I_rst_n), .start(frame_ready),
        .denominator(frame_b), .numerator({frame_g,16'd0}),
        .quotient(quotient_b), .done(done_b)
    );

    // Preserve the reference design's 50-clock RAM pixel delay.
    reg I_tvalid_r0, I_tvalid_r1;
    reg [95:0] I_tdata_d0, I_tdata_d1;
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            I_tvalid_r0 <= 1'b0;
            I_tvalid_r1 <= 1'b0;
            I_tdata_d0 <= 96'd0;
            I_tdata_d1 <= 96'd0;
        end else begin
            I_tvalid_r0 <= I_tvalid;
            I_tvalid_r1 <= I_tvalid_r0;
            I_tdata_d0 <= I_tdata;
            I_tdata_d1 <= I_tdata_d0;
        end
    end
    wire [95:0] data_d0;
    wire valid_d0, delayed_tuser;
    signal_delay #(
        .IMG_HEIGHT(IMG_HEIGHT), .IMG_WIDTH(IMG_WIDTH),
        .DATA_WIDTH(96), .DELAY_CYCLE(50)
    ) signal_delay_d (
        .I_clk(I_clk), .I_rst_n(I_rst_n), .I_tuser(I_tuser),
        .I_valid(I_tvalid_r1), .I_data(I_tdata_d1),
        .O_valid(valid_d0), .O_data(data_d0),
        .O_tuser(delayed_tuser)
    );

    reg [19:0] gain_r, gain_b, target_r, target_b;
    reg pending_gain;
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            gain_r <= GAIN_ONE;
            gain_b <= GAIN_ONE;
            target_r <= GAIN_ONE;
            target_b <= GAIN_ONE;
            pending_gain <= 1'b0;
        end else begin
            // Active gains change only at the delayed frame boundary.
            if (delayed_tuser) begin
                if (pending_gain) begin
                    gain_r <= slew_gain(gain_r, target_r);
                    gain_b <= slew_gain(gain_b, target_b);
                end
                pending_gain <= 1'b0;
            end
            if (done_r && done_b) begin
                target_r <= clamp_gain(quotient_r);
                target_b <= clamp_gain(quotient_b);
                pending_gain <= 1'b1;
            end
        end
    end

    reg [95:0] data_d1;
    reg valid_d1, tuser_d1;
    reg valid_d2, tuser_d2;
    reg [27:0] mult_r[0:3], mult_b[0:3];
    reg [7:0] green_d[0:3];
    reg [95:0] diag_pre;
    reg [39:0] diag_gain;
    reg [20:0] diag_samples;
    reg [15:0] diag_stats_seq;
    reg diag_stats_valid;
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            diag_pre<=0;diag_gain<=0;diag_samples<=0;
            diag_stats_seq<=0;diag_stats_valid<=0;
        end else begin
            if(valid_d1) begin
                diag_pre<=data_d1;
                diag_gain<={gain_r,gain_b};
            end
            if(beat_tlast && !beat_tuser && line_count==IMG_HEIGHT-1) begin
                diag_samples<=final_count;diag_stats_seq<=diag_stats_seq+1'b1;
                diag_stats_valid<=(final_count>=MIN_SAMPLES)&&(final_r!=0)&&(final_g!=0)&&(final_b!=0);
            end
        end
    end
    assign O_diag_pre=diag_pre;
    assign O_diag_gain=diag_gain;
    // Last completed INPUT statistics, not statistics of the current ROI frame.
    assign O_diag_stats={10'd0,diag_stats_valid,diag_stats_seq,diag_samples,frame_r,frame_g,frame_b};
    integer k;
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            data_d1 <= 96'd0;
            valid_d1 <= 1'b0;
            tuser_d1 <= 1'b0;
            valid_d2 <= 1'b0;
            tuser_d2 <= 1'b0;
            for (k = 0; k < 4; k = k + 1) begin
                mult_r[k] <= 28'd0;
                mult_b[k] <= 28'd0;
                green_d[k] <= 8'd0;
            end
        end else begin
            data_d1 <= data_d0;
            valid_d1 <= valid_d0;
            tuser_d1 <= delayed_tuser;
            valid_d2 <= valid_d1;
            tuser_d2 <= tuser_d1;
            if (valid_d1) begin
                for (k = 0; k < 4; k = k + 1) begin
                    mult_r[k] <= gain_r * data_d1[k*24+16 +: 8];
                    green_d[k] <= data_d1[k*24+8 +: 8];
                    mult_b[k] <= gain_b * data_d1[k*24 +: 8];
                end
            end
        end
    end

    assign O_tvalid = valid_d2;
    // video_in needs the original early frame pulse to reset its input FIFO
    // before the delayed valid pixels arrive. Use delayed_tuser only for gain.
    assign O_tuser = I_tuser;
    assign O_tlast = !valid_d1 && valid_d2;
    assign O_tdata = O_tvalid ? {
        sat_q16(mult_r[3]), green_d[3], sat_q16(mult_b[3]),
        sat_q16(mult_r[2]), green_d[2], sat_q16(mult_b[2]),
        sat_q16(mult_r[1]), green_d[1], sat_q16(mult_b[1]),
        sat_q16(mult_r[0]), green_d[0], sat_q16(mult_b[0])
    } : 96'd0;
    assign I_tready = O_tready;
endmodule
