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
    parameter integer PROBE_ENABLE = 0
)(
    input clk, input rst_n,
    input [95:0] I_data, input I_valid, input I_user, input I_last,
    input [8:0] I_config,
    input [319:0] I_probe_panel,
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
    wire box_hit = ENABLE && pixel_x >= X0 && pixel_x < X0+448
                          && y_now >= Y0 && y_now < Y0+72;
    wire row0 = local_y < 32;
    wire row1 = local_y >= 40 && local_y < 72;
    wire [10:0] text_y = row1 ? local_y-11'd40 : local_y;
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
    reg [7:0] character;
    always @(*) begin
        character=8'h20;
        if (row0) begin
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
    // Diagnostic extension reuses the SAME glyph lookup and two registers.
    // Raw/capture measurements are explicitly historical, not same-frame ISP.
    reg [319:0] probe_frame;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)probe_frame<=0;
        else if(I_user)probe_frame<=I_probe_panel;
    end
    wire [12:0] px= pixel_x-13'd16;
    wire [10:0] py= y_now-11'd352;
    wire probe_hit=PROBE_ENABLE && pixel_x>=16 && pixel_x<528 && y_now>=352 && y_now<672;
    wire [3:0] prow=py[8:5],pcol=px[8:5];
    reg [63:0] caption;reg [31:0] word;reg [7:0] probe_char;
    reg [3:0] nibble;
    always @(*)begin
        caption="        ";word=0;
        case(prow)
          1:begin caption="SEQ     ";word=probe_frame[287:256];end
          2:begin caption="IN      ";word=probe_frame[255:224];end
          3:begin caption="PACK    ";word=probe_frame[223:192];end
          4:begin caption="CRC     ";word=probe_frame[191:160];end
          5:begin caption="LINE    ";word=probe_frame[159:128];end
          6:begin caption="GAP     ";word=probe_frame[127:96];end
          7:begin caption="ERR     ";word=probe_frame[95:64];end
          8:begin caption="COUNT   ";word=probe_frame[63:32];end
          9:begin caption="FLAG    ";word=probe_frame[31:0];end
        endcase
        nibble=(word >> ((7-pcol[2:0])*4));
        probe_char=pcol<8 ? (caption >> ((7-pcol[2:0])*8)) :
            (nibble<10 ? 8'h30+{4'd0,nibble}:8'h41+{4'd0,nibble}-8'd10);
        if(prow==0)begin
          case(pcol)
           0:probe_char="P";1:probe_char="R";2:probe_char="O";3:probe_char="B";4:probe_char="E";
           6:probe_char="F";7:probe_char="I";8:probe_char="X";9:probe_char="E";10:probe_char="D";
           12:probe_char="V";13:probe_char="1";
           15:probe_char=probe_frame[0]?"V":"W";
           default:probe_char=" ";
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
            char_s1<=probe_hit?probe_char:character;
            row_s1<=probe_hit?py[4:1]:text_y[4:1]; col_s1<=probe_hit?px[4:1]:local_x[4:1];
            hit_s1<=box_hit||probe_hit; glyph_s1<=probe_hit||row0||row1;
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
