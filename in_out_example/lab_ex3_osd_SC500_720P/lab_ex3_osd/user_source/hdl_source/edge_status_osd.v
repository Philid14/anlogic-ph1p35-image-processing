`timescale 1ns / 1ps
// Two-stage 4-pixel status overlay BEFORE DDR. Text is cached with its frame.
// Reuse the frozen formal osd_char_lib. One glyph lookup serves all four lanes:
// x is a multiple of four; a 32-pixel cell never straddles a beat.
module edge_status_osd #(
    parameter integer IMG_WIDTH = 1280,
    parameter integer IMG_HEIGHT = 720,
    parameter integer ENABLE = 1,
    parameter integer X0 = 800,
    parameter integer Y0 = 16,
    parameter integer RELIABILITY_ENABLE = 0
)(
    input clk, input rst_n,
    input [95:0] I_data, input I_valid, input I_user, input I_last,
    input [8:0] I_config,
    input [31:0] I_fifo_event_counts,
    output reg [95:0] O_data,
    output reg O_valid, output reg O_user, output reg O_last
);
    localparam GROUPS = IMG_WIDTH/4;
    reg [10:0] x_group, y;
    wire [10:0] x_now = I_user ? 11'd0 : x_group;
    wire [10:0] y_now = I_user ? 11'd0 : y;
    wire [12:0] pixel_x = {x_now,2'b00};
    wire [12:0] local_x = pixel_x-X0;
    wire [10:0] local_y = y_now-Y0;
    wire row2=RELIABILITY_ENABLE && local_y>=80 && local_y<112;
    wire box_hit = ENABLE && pixel_x >= X0 && pixel_x < X0+448
                          && y_now >= Y0 && (y_now < Y0+72 || row2);
    wire row0 = local_y < 32;
    wire row1 = local_y >= 40 && local_y < 72;
    wire [10:0] text_y = row2 ? local_y-11'd80 : (row1 ? local_y-11'd40 : local_y);
    wire [3:0] char_column = local_x[8:5];

    // All 0..255 values are defined; no hundreds truncation or division IP.
    function [11:0] decimal3;
        input [7:0] value;
        reg [7:0] remainder;
        reg [3:0] hundreds, tens;
        begin
            if (value >= 200) begin hundreds=2; remainder=value-8'd200; end
            else if (value >= 100) begin hundreds=1; remainder=value-8'd100; end
            else begin hundreds=0; remainder=value; end
            if      (remainder >= 90) tens=9;
            else if (remainder >= 80) tens=8;
            else if (remainder >= 70) tens=7;
            else if (remainder >= 60) tens=6;
            else if (remainder >= 50) tens=5;
            else if (remainder >= 40) tens=4;
            else if (remainder >= 30) tens=3;
            else if (remainder >= 20) tens=2;
            else if (remainder >= 10) tens=1;
            else tens=0;
            remainder=remainder-({tens,3'b000}+{tens,1'b0});
            decimal3={hundreds,tens,remainder[3:0]};
        end
    endfunction
    wire [11:0] digits = decimal3(I_config[7:0]);
    reg [31:0] fifo_frame;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)fifo_frame<=0;else if(I_user)fifo_frame<=I_fifo_event_counts;
    end
    function [7:0] hexchar;input[3:0] n;
        begin hexchar=n<10 ? 8'h30+n : 8'h41+n-10;end
    endfunction
    reg [7:0] character;
    always @(*) begin
        character=8'h20;
        if(row2)begin
            case(char_column)
                0:character="B";1:character=":";
                2:character=hexchar(fifo_frame[31:28]);3:character=hexchar(fifo_frame[27:24]);
                4:character=hexchar(fifo_frame[23:20]);5:character=hexchar(fifo_frame[19:16]);
                7:character="S";8:character=":";
                9:character=hexchar(fifo_frame[15:12]);10:character=hexchar(fifo_frame[11:8]);
                11:character=hexchar(fifo_frame[7:4]);12:character=hexchar(fifo_frame[3:0]);
                default:character=" ";
            endcase
        end else if (row0) begin
            case (char_column)
                0: character="M"; 1: character="O"; 2: character="D";
                3: character="E"; 4: character=":";
                6: character=I_config[8] ? "E" : "O";
                7: character=I_config[8] ? "D" : "R";
                8: character=I_config[8] ? "G" : "I";
                9: character=I_config[8] ? "E" : "G";
                10: character=I_config[8] ? " " : "I";
                11: character=I_config[8] ? " " : "N";
                default: character=" ";
            endcase
        end else if (row1) begin
            case (char_column)
                0: character="T"; 1: character="H"; 2: character="R";
                3: character="E"; 4: character="S"; 5: character="H";
                6: character="O"; 7: character="L"; 8: character="D";
                9: character=":";
                11: character=8'h30+{4'd0,digits[11:8]};
                12: character=8'h30+{4'd0,digits[7:4]};
                13: character=8'h30+{4'd0,digits[3:0]};
                default: character=" ";
            endcase
        end
    end
    reg [7:0] char_s1;
    reg [3:0] row_s1, col_s1;
    reg hit_s1, glyph_s1, valid_s1, user_s1, last_s1;
    reg [95:0] rgb_s1;
    wire [15:0] glyph_bits;
    osd_char_lib u_font (.I_char(char_s1), .I_row(row_s1), .O_row_bits(glyph_bits));
    integer lane;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            x_group<=0; y<=0; char_s1<=0; row_s1<=0; col_s1<=0;
            hit_s1<=0; glyph_s1<=0; valid_s1<=0; user_s1<=0; last_s1<=0;
            rgb_s1<=0; O_data<=0; O_valid<=0; O_user<=0; O_last<=0;
        end else begin
            if (I_user) begin x_group<=0; y<=0; end
            if (I_valid) begin
                if (x_now==GROUPS-1) begin
                    x_group<=0; y<=(y_now==IMG_HEIGHT-1) ? 11'd0 : y_now+1'b1;
                end else begin x_group<=x_now+1'b1; y<=y_now; end
            end
            char_s1<=character; row_s1<=text_y[4:1]; col_s1<=local_x[4:1];
            hit_s1<=box_hit; glyph_s1<=row0||row1||row2;
            rgb_s1<=I_data; valid_s1<=I_valid; user_s1<=I_user; last_s1<=I_last;
            O_valid<=valid_s1; O_user<=user_s1; O_last<=last_s1;
            for (lane=0; lane<4; lane=lane+1) begin
                if (hit_s1)
                    O_data[95-lane*24 -:24] <= (glyph_s1 && glyph_bits[15-col_s1-(lane/2)])
                        ? 24'hffff00 : 24'h101010;
                else O_data[95-lane*24 -:24] <= rgb_s1[95-lane*24 -:24];
            end
        end
    end
endmodule
