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
    parameter integer RELIABILITY_ENABLE = 0,
    parameter integer SWITCH_DIAG_ENABLE = 0,
    parameter integer VISION_ENABLE = 0,
    parameter integer INSPECTION_V5 = 0,
    parameter integer COMPACT_FONT = 0
)(
    input clk, input rst_n,
    input [95:0] I_data, input I_valid, input I_user, input I_last,
    input [18:0] I_config,
    input [31:0] I_fifo_event_counts,input [3:0] I_switches,input [2:0] I_ruler_status,
    input [1:0] I_track_state,input I_target_valid,input [10:0] I_target_x,input [9:0] I_target_y,
    input [43:0] I_target_box,input [19:0] I_target_count,input [31:0] I_target_frame,
    input I_motion_valid,input [11:0] I_motion_count,input [2:0] I_motion_state,
    input [31:0] I_motion_frame,input I_observer_error,
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
    wire row3=SWITCH_DIAG_ENABLE && local_y>=120 && local_y<152;
    wire row2=RELIABILITY_ENABLE && local_y>=80 && local_y<112;
    wire analytic=VISION_ENABLE && I_config[18:16]>=5 && I_config[18:16]<=6;
    wire a_hit=analytic && pixel_x>=32 && pixel_x<1056 && y_now>=192 && y_now<288;
    wire [1:0] a_row=(y_now-192)>>5;
    wire [4:0] a_col=(pixel_x-32)>>5;
    wire box_hit = ENABLE && ((pixel_x >= X0 && pixel_x < X0+448
                          && y_now >= Y0 && (y_now < Y0+72 || row2 || row3)) || a_hit);
    wire row0 = local_y < 32;
    wire row1 = local_y >= 40 && local_y < 72;
    wire [10:0] text_y = row3 ? local_y-11'd120 : row2 ? local_y-11'd80 : (row1 ? local_y-11'd40 : local_y);
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
    wire [2:0] mode = I_config[18:16];
    wire [7:0] active_threshold = (mode==3'd2) ? I_config[7:0] : I_config[15:8];
    wire threshold_applicable = (mode==3'd2) || (mode==3'd3);
    wire [11:0] digits = decimal3(active_threshold);
    reg [31:0] fifo_frame;reg [3:0] switch_frame;reg [2:0] ruler_frame;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin fifo_frame<=0;switch_frame<=0;ruler_frame<=0;end
        else if(I_user)begin fifo_frame<=I_fifo_event_counts;switch_frame<=I_switches;ruler_frame<=I_ruler_status;end
    end
    function [7:0] hexchar;input[3:0] n;
        begin hexchar=n<10 ? 8'h30+n : 8'h41+n-10;end
    endfunction
    reg [7:0] character;
    reg [1:0] track_f;reg target_valid_f,motion_valid_f,error_f;
    reg [10:0] tx_f;reg [9:0] ty_f;reg [19:0] tn_f;reg [31:0] tf_f,mf_f;
    reg [43:0] tb_f;
    reg [11:0] mn_f;reg [2:0] ms_f;
    generate if(VISION_ENABLE)begin:g_analytics
        always @(posedge clk or negedge rst_n)begin
            if(!rst_n)begin track_f<=0;target_valid_f<=0;motion_valid_f<=0;error_f<=0;
                tb_f<=0;tx_f<=0;ty_f<=0;tn_f<=0;tf_f<=0;mf_f<=0;mn_f<=0;ms_f<=0;end
            else if(I_user)begin track_f<=I_track_state;target_valid_f<=I_target_valid;
                motion_valid_f<=I_motion_valid;error_f<=I_observer_error;
                tb_f<=I_target_box;tx_f<=I_target_x;ty_f<=I_target_y;tn_f<=I_target_count;tf_f<=I_target_frame;
                mf_f<=I_motion_frame;mn_f<=I_motion_count;ms_f<=I_motion_state;end
        end
    end endgenerate
    reg [255:0] analytic_text;
    reg [63:0] state_text;
    reg [31:0] shown_frame;
    always @(*)begin
        shown_frame=mode==5?tf_f:mf_f;
        if(mode==5)begin
            case(track_f)
                1:state_text="ACQUIRE ";2:state_text="TRACK   ";3:state_text="HOLD    ";default:state_text="SEARCH  ";
            endcase
        end else begin
            case(ms_f)
                1:state_text="WARMUP  ";2:state_text="STILL   ";3:state_text="MOTION  ";4:state_text="GLOBAL  ";default:state_text="INVALID ";
            endcase
        end
        analytic_text="                                ";
        case(a_row)
            0: analytic_text=mode==5?{"RED TRACK: ",state_text,"             "}:{"GRID32X16: ",state_text," TH012       "};
            1: analytic_text=mode==5?"LAST HEX X:000 Y:000 N:00000    ":"LAST CHANGED HEX:000            ";
            2: analytic_text="FRAME:00000000 VALID:0 ERR:0    ";
            default: ;
        endcase
    end
    always @(*) begin
        character=8'h20;
        if(row3)begin
            case(char_column)
                0:character="S";1:character="W";2:character=":";
                3:character="0"+switch_frame[0];4:character="0"+switch_frame[1];
                5:character="0"+switch_frame[2];6:character="0"+switch_frame[3];
                8:character="R";9:character=":";10:character="0"+ruler_frame;
                12:character=switch_frame[1]?"M":switch_frame[0]?"C":"-";
                13:character=switch_frame[1] && switch_frame[3]?"A":" ";
                default:character=" ";
            endcase
        end else if(row2)begin
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
                6: character=(mode==3'd4) ? "S" : (mode==3'd0) ? "O" :
                             (mode==3'd1) ? "G" :
                             (mode==3'd2) ? "B" : "E";
                7: character=(mode==3'd4) ? "T" : (mode==3'd0) ? "R" :
                             (mode==3'd1) ? "R" :
                             (mode==3'd2) ? "I" : "D";
                8: character=(mode==3'd4) ? "Y" : (mode==3'd0) ? "I" :
                             (mode==3'd1) ? "A" :
                             (mode==3'd2) ? "N" : "G";
                9: character=(mode==3'd4) ? "L" : (mode==3'd0) ? "G" :
                             (mode==3'd1) ? "Y" :
                             (mode==3'd2) ? "A" : "E";
                10: character=(mode==3'd4) ? "E" : (mode==3'd0) ? "I" :
                              (mode==3'd2) ? "R" : " ";
                11: character=(mode==3'd0) ? "N" :
                              (mode==3'd2) ? "Y" : " ";
                default: character=" ";
            endcase
        end else if (row1) begin
            case (char_column)
                0: character="T"; 1: character="H"; 2: character="R";
                3: character="E"; 4: character="S"; 5: character="H";
                6: character="O"; 7: character="L"; 8: character="D";
                9: character=":";
                11: character=threshold_applicable ? 8'h30+{4'd0,digits[11:8]} : " ";
                12: character=threshold_applicable ? 8'h30+{4'd0,digits[7:4]} : " ";
                13: character=threshold_applicable ? 8'h30+{4'd0,digits[3:0]} : " ";
                default: character=" ";
            endcase
        end
        if(VISION_ENABLE && mode==5 && row0)begin
            case(char_column)
                6:character="T";7:character="R";8:character="A";9:character="C";10:character="K";11:character=" ";default:;
            endcase
        end
        if(VISION_ENABLE && mode==6 && row0)begin
            case(char_column)
                6:character="M";7:character="O";8:character="T";9:character="I";10:character="O";11:character="N";default:;
            endcase
        end
        if(a_hit)begin
            character=analytic_text[255-a_col*8-:8];
            if(a_row==1 && mode==5)begin
                case(a_col)
                    11:character=hexchar({1'b0,tx_f[10:8]});12:character=hexchar(tx_f[7:4]);13:character=hexchar(tx_f[3:0]);
                    17:character=hexchar({2'b0,ty_f[9:8]});18:character=hexchar(ty_f[7:4]);19:character=hexchar(ty_f[3:0]);
                    23:character=hexchar(tn_f[19:16]);24:character=hexchar(tn_f[15:12]);
                    25:character=hexchar(tn_f[11:8]);26:character=hexchar(tn_f[7:4]);27:character=hexchar(tn_f[3:0]);default:;
                endcase
            end else if(a_row==1 && mode==6 && a_col>=17 && a_col<20)
                character=hexchar(mn_f>>(4*(19-a_col)));
            if(a_row==2)begin
                if(a_col>=6 && a_col<14)character=hexchar(shown_frame>>(4*(13-a_col)));
                if(a_col==21)character="0"+(mode==5?target_valid_f:motion_valid_f);
                if(a_col==27)character="0"+error_f;
            end
        end
    end
    reg [7:0] char_s1;
    reg [3:0] row_s1, col_s1;
    reg diag_s1;reg hit_s1, glyph_s1, valid_s1, user_s1, last_s1;
    reg [95:0] rgb_s1;
    wire [15:0] glyph_bits;
    generate if(COMPACT_FONT)begin:g_font_ram
        inspection_font_rom u_font(.clk(clk),.character(character),.row(a_hit?y_now[4:1]:text_y[4:1]),.bits(glyph_bits));
    end else begin:g_font_logic
        osd_char_lib u_font (.I_char(char_s1), .I_row(row_s1), .O_row_bits(glyph_bits));
    end endgenerate
    wire [10:0] bx0=tb_f[43:33],bx1=tb_f[32:22],by0=tb_f[21:11],by1=tb_f[10:0];
    reg [3:0] outline,outline_s1;integer lane,bl;reg[12:0] bpx;
    always @*begin
        outline=0;bpx=0;
        for(bl=0;bl<4;bl=bl+1)begin
            bpx=pixel_x+bl;
            outline[3-bl]=INSPECTION_V5 && ENABLE && VISION_ENABLE && mode==5 && target_valid_f &&
                bx1>=bx0 && by1>=by0 && bpx>=bx0 && bpx<=bx1 && y_now>=by0 && y_now<=by1 &&
                (bpx<=bx0+1 || bpx+1>=bx1 || y_now<=by0+1 || y_now+1>=by1);
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            x_group<=0; y<=0; char_s1<=0; row_s1<=0; col_s1<=0;
            diag_s1<=0;hit_s1<=0; glyph_s1<=0; valid_s1<=0; user_s1<=0; last_s1<=0;
            outline_s1<=0;rgb_s1<=0; O_data<=0; O_valid<=0; O_user<=0; O_last<=0;
        end else begin
            if (I_user) begin x_group<=0; y<=0; end
            if (I_valid) begin
                if (x_now==GROUPS-1) begin
                    x_group<=0; y<=(y_now==IMG_HEIGHT-1) ? 11'd0 : y_now+1'b1;
                end else begin x_group<=x_now+1'b1; y<=y_now; end
            end
            char_s1<=character; row_s1<=a_hit?y_now[4:1]:text_y[4:1]; col_s1<=a_hit?pixel_x[4:1]:local_x[4:1];
            hit_s1<=box_hit; glyph_s1<=a_hit||row0||row1||row2||row3;diag_s1<=row3||a_hit;
            outline_s1<=outline;rgb_s1<=I_data; valid_s1<=I_valid; user_s1<=I_user; last_s1<=I_last;
            O_valid<=valid_s1; O_user<=user_s1; O_last<=last_s1;
            for (lane=0; lane<4; lane=lane+1) begin
                if (hit_s1 && glyph_s1 && glyph_bits[15-col_s1-(lane/2)])
                    O_data[95-lane*24 -:24] <= (diag_s1 && rgb_s1[87-lane*24])?24'h101030:24'hffff00;
                else if(outline_s1[3-lane])O_data[95-lane*24-:24]<=24'h00ff80;
                else O_data[95-lane*24 -:24] <= rgb_s1[95-lane*24 -:24];
            end
        end
    end
endmodule
