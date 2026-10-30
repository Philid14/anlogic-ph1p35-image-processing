// Two-cycle MAIN overlay. Snapshot LAST completed post-AWB frame at early SOF.
// Shared font is unchanged; four adjacent pixels share one 32px glyph cell.
module color_compare_osd #(
    parameter integer WIDTH=1280,HEIGHT=720,UI_ENABLE=0,
    parameter integer REF_X=256,TEST_X=896,ROI_Y=256,ROI_W=128,ROI_H=128
)(
    input clk,rst_n,input [95:0] rgb,input valid,user,last,
    input [47:0] means,input result_valid,input [15:0] sample_id,
    input display_enable,
    output reg [95:0] out_rgb,output reg out_valid,out_user,out_last
);
    reg show_color;
    wire enabled=UI_ENABLE?show_color:1'b1;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)show_color<=0;else if(user)show_color<=display_enable;
    end
    reg [10:0] x;reg [9:0] y;
    wire [10:0] px=user?11'd0:x;wire [9:0] py=user?10'd0:y;
    reg [47:0] held_rgb;reg [15:0] held_id;
    reg held_valid,formatted,busy;reg [3:0] field,step;
    reg [9:0] binary_shift;reg [11:0] bcd;
    reg [11:0] digits[0:10];
    reg [7:0] dr,dg,db;reg [3:0] class_ref,class_test;
    wire [9:0] l1={2'd0,dr}+{2'd0,dg}+{2'd0,db};
    wire [7:0] max_difference=dr>dg?(dr>db?dr:db):(dg>db?dg:db);
    wire compare_match=max_difference<=12;
    function [7:0] absdiff;input[7:0]a,b;begin absdiff=a>b?a-b:b-a;end endfunction
    // Coarse camera-RGB hue category, not a calibrated material classification.
    function [3:0] classify;
        input [23:0] v;reg [7:0]r,g,b,mx,mn,mid,chroma;
        begin
            r=v[23:16];g=v[15:8];b=v[7:0];
            mx=r>g?(r>b?r:b):(g>b?g:b);mn=r<g?(r<b?r:b):(g<b?g:b);
            chroma=mx-mn;
            if(mx<32)classify=0;
            else if(chroma<=24)classify=mn>=224?1:2;
            else begin
                mid=({2'b0,r}+{2'b0,g}+{2'b0,b})-mx-mn;
                if(({1'b0,mid}-{1'b0,mn})*2 >= {1'b0,chroma})
                    classify=b==mn?6:(r==mn?7:8);
                else classify=r==mx?3:(g==mx?4:5);
            end
        end
    endfunction
    function [7:0] hexchar;input[3:0]n;begin hexchar=n<10?8'h30+n:8'h41+n-10;end endfunction
    function [7:0] color_letter;input[3:0]c;input[2:0]pos;
        begin color_letter=" ";case({c,pos})
            7'd0:color_letter="B";
            7'd1:color_letter="L";
            7'd2:color_letter="A";
            7'd3:color_letter="C";
            7'd4:color_letter="K";
            7'd8:color_letter="W";
            7'd9:color_letter="H";
            7'd10:color_letter="I";
            7'd11:color_letter="T";
            7'd12:color_letter="E";
            7'd16:color_letter="G";
            7'd17:color_letter="R";
            7'd18:color_letter="A";
            7'd19:color_letter="Y";
            7'd24:color_letter="R";
            7'd25:color_letter="E";
            7'd26:color_letter="D";
            7'd32:color_letter="G";
            7'd33:color_letter="R";
            7'd34:color_letter="E";
            7'd35:color_letter="E";
            7'd36:color_letter="N";
            7'd40:color_letter="B";
            7'd41:color_letter="L";
            7'd42:color_letter="U";
            7'd43:color_letter="E";
            7'd48:color_letter="Y";
            7'd49:color_letter="E";
            7'd50:color_letter="L";
            7'd51:color_letter="L";
            7'd52:color_letter="O";
            7'd53:color_letter="W";
            7'd56:color_letter="C";
            7'd57:color_letter="Y";
            7'd58:color_letter="A";
            7'd59:color_letter="N";
            7'd64:color_letter="M";
            7'd65:color_letter="A";
            7'd66:color_letter="G";
            7'd67:color_letter="E";
            7'd68:color_letter="N";
            7'd69:color_letter="T";
            7'd70:color_letter="A";
        endcase end
    endfunction
    function [7:0] match_letter;input ok;input[2:0]pos;
        begin
            match_letter=" ";
            if(ok)case(pos)0:match_letter="M";1:match_letter="A";2:match_letter="T";3:match_letter="C";4:match_letter="H";endcase
            else case(pos)0:match_letter="D";1:match_letter="I";2:match_letter="F";3:match_letter="F";endcase
        end
    endfunction
    reg [9:0] number;
    always @*begin
        number=0;
        case(field)
            0:number=held_rgb[47:40];1:number=held_rgb[39:32];2:number=held_rgb[31:24];
            3:number=held_rgb[23:16];4:number=held_rgb[15:8];5:number=held_rgb[7:0];
            6:number=dr;7:number=dg;8:number=db;9:number=l1;10:number=max_difference;
        endcase
    end
    reg [11:0] adjusted;integer n;
    always @*begin
        adjusted=bcd;
        for(n=0;n<3;n=n+1)if(bcd[n*4+:4]>=5)adjusted[n*4+:4]=bcd[n*4+:4]+3;
    end
    integer j;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            held_rgb<=0;held_id<=0;held_valid<=0;formatted<=0;busy<=0;
            field<=0;step<=0;binary_shift<=0;bcd<=0;dr<=0;dg<=0;db<=0;class_ref<=0;class_test<=0;
            for(j=0;j<11;j=j+1)digits[j]<=0;
        end else if(user)begin
            held_rgb<=means;held_id<=sample_id;held_valid<=result_valid;
            dr<=absdiff(means[47:40],means[23:16]);dg<=absdiff(means[39:32],means[15:8]);db<=absdiff(means[31:24],means[7:0]);
            class_ref<=classify(means[47:24]);class_test<=classify(means[23:0]);
            busy<=1;field<=0;step<=0;formatted<=0;
        end else if(busy)begin
            if(step==0)begin binary_shift<=number;bcd<=0;step<=1;end
            else begin
                bcd<={adjusted[10:0],binary_shift[9]};binary_shift<={binary_shift[8:0],1'b0};
                if(step==10)begin
                    digits[field]<={adjusted[10:0],binary_shift[9]};step<=0;
                    if(field==10)begin busy<=0;formatted<=1;end else field<=field+1'b1;
                end else step<=step+1'b1;
            end
        end
    end
    wire panel=px>=32 && px<1248 && py>=544 && py<672;
    wire [10:0] lx=px-32;wire [9:0] ly=py-544;
    wire [5:0] column=lx[10:5];wire [1:0] row=ly[6:5];
    wire ref_box=px>=REF_X-4 && px<REF_X+ROI_W+4 && py>=ROI_Y-2 && py<ROI_Y+ROI_H+2 &&
        (px<REF_X || px>=REF_X+ROI_W || py<ROI_Y || py>=ROI_Y+ROI_H);
    wire test_box=px>=TEST_X-4 && px<TEST_X+ROI_W+4 && py>=ROI_Y-2 && py<ROI_Y+ROI_H+2 &&
        (px<TEST_X || px>=TEST_X+ROI_W || py<ROI_Y || py>=ROI_Y+ROI_H);
    reg [7:0] character;
    always @*begin
        character=" ";
        case({row,column})
            8'd0:character="R";
            8'd1:character="E";
            8'd2:character="F";
            8'd5:character="R";
            8'd6:character=":";
            8'd7:character=8'h30+digits[0][11 -:4];
            8'd8:character=8'h30+digits[0][7 -:4];
            8'd9:character=8'h30+digits[0][3 -:4];
            8'd11:character="G";
            8'd12:character=":";
            8'd13:character=8'h30+digits[1][11 -:4];
            8'd14:character=8'h30+digits[1][7 -:4];
            8'd15:character=8'h30+digits[1][3 -:4];
            8'd17:character="B";
            8'd18:character=":";
            8'd19:character=8'h30+digits[2][11 -:4];
            8'd20:character=8'h30+digits[2][7 -:4];
            8'd21:character=8'h30+digits[2][3 -:4];
            8'd23:character="C";
            8'd24:character=":";
            8'd25:character=color_letter(class_ref,3'd0);
            8'd26:character=color_letter(class_ref,3'd1);
            8'd27:character=color_letter(class_ref,3'd2);
            8'd28:character=color_letter(class_ref,3'd3);
            8'd29:character=color_letter(class_ref,3'd4);
            8'd30:character=color_letter(class_ref,3'd5);
            8'd31:character=color_letter(class_ref,3'd6);
            8'd64:character="T";
            8'd65:character="E";
            8'd66:character="S";
            8'd67:character="T";
            8'd69:character="R";
            8'd70:character=":";
            8'd71:character=8'h30+digits[3][11 -:4];
            8'd72:character=8'h30+digits[3][7 -:4];
            8'd73:character=8'h30+digits[3][3 -:4];
            8'd75:character="G";
            8'd76:character=":";
            8'd77:character=8'h30+digits[4][11 -:4];
            8'd78:character=8'h30+digits[4][7 -:4];
            8'd79:character=8'h30+digits[4][3 -:4];
            8'd81:character="B";
            8'd82:character=":";
            8'd83:character=8'h30+digits[5][11 -:4];
            8'd84:character=8'h30+digits[5][7 -:4];
            8'd85:character=8'h30+digits[5][3 -:4];
            8'd87:character="C";
            8'd88:character=":";
            8'd89:character=color_letter(class_test,3'd0);
            8'd90:character=color_letter(class_test,3'd1);
            8'd91:character=color_letter(class_test,3'd2);
            8'd92:character=color_letter(class_test,3'd3);
            8'd93:character=color_letter(class_test,3'd4);
            8'd94:character=color_letter(class_test,3'd5);
            8'd95:character=color_letter(class_test,3'd6);
            8'd128:character="A";
            8'd129:character="B";
            8'd130:character="S";
            8'd133:character="R";
            8'd134:character=":";
            8'd135:character=8'h30+digits[6][11 -:4];
            8'd136:character=8'h30+digits[6][7 -:4];
            8'd137:character=8'h30+digits[6][3 -:4];
            8'd139:character="G";
            8'd140:character=":";
            8'd141:character=8'h30+digits[7][11 -:4];
            8'd142:character=8'h30+digits[7][7 -:4];
            8'd143:character=8'h30+digits[7][3 -:4];
            8'd145:character="B";
            8'd146:character=":";
            8'd147:character=8'h30+digits[8][11 -:4];
            8'd148:character=8'h30+digits[8][7 -:4];
            8'd149:character=8'h30+digits[8][3 -:4];
            8'd192:character="L";
            8'd193:character="1";
            8'd194:character=":";
            8'd195:character=8'h30+digits[9][11 -:4];
            8'd196:character=8'h30+digits[9][7 -:4];
            8'd197:character=8'h30+digits[9][3 -:4];
            8'd199:character="M";
            8'd200:character="A";
            8'd201:character="X";
            8'd202:character=":";
            8'd203:character=8'h30+digits[10][11 -:4];
            8'd204:character=8'h30+digits[10][7 -:4];
            8'd205:character=8'h30+digits[10][3 -:4];
            8'd207:character="L";
            8'd208:character="I";
            8'd209:character="M";
            8'd210:character=":";
            8'd211:character="0";
            8'd212:character="1";
            8'd213:character="2";
            8'd215:character=match_letter(compare_match,3'd0);
            8'd216:character=match_letter(compare_match,3'd1);
            8'd217:character=match_letter(compare_match,3'd2);
            8'd218:character=match_letter(compare_match,3'd3);
            8'd219:character=match_letter(compare_match,3'd4);
            8'd221:character="L";
            8'd222:character="A";
            8'd223:character="S";
            8'd224:character="T";
            8'd225:character=":";
            8'd226:character=hexchar(held_id[15 -:4]);
            8'd227:character=hexchar(held_id[11 -:4]);
            8'd228:character=hexchar(held_id[7 -:4]);
            8'd229:character=hexchar(held_id[3 -:4]);
        endcase
        if(!held_valid || !formatted)begin
            character=" ";
            if(row==3)case(column)
                0:character="W";1:character="A";2:character="I";3:character="T";
                5:character="F";6:character="O";7:character="R";
                9:character="F";10:character="U";11:character="L";12:character="L";
                14:character="F";15:character="R";16:character="A";17:character="M";18:character="E";
            endcase
        end
    end
    reg [7:0] char_d;reg [3:0] row_d,col_d;
    reg panel_d,ref_d,test_d,v_d,u_d,l_d;reg [95:0] rgb_d;
    reg [23:0] ink_d;wire [15:0] bits;
    osd_char_lib u_font(.I_char(char_d),.I_row(row_d),.O_row_bits(bits));
    integer lane;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            x<=0;y<=0;char_d<=0;row_d<=0;col_d<=0;panel_d<=0;ref_d<=0;test_d<=0;v_d<=0;u_d<=0;l_d<=0;rgb_d<=0;ink_d<=0;
            out_rgb<=0;out_valid<=0;out_user<=0;out_last<=0;
        end else begin
            if(user)begin x<=0;y<=0;end
            if(valid)begin x<=px==WIDTH-4?0:px+4;if(px==WIDTH-4)y<=py==HEIGHT-1?0:py+1'b1;else y<=py;end
            char_d<=character;row_d<=ly[4:1];col_d<=lx[4:1];
            panel_d<=panel && enabled;ref_d<=ref_box && enabled;test_d<=test_box && enabled;
            ink_d<=row==0?24'h40ff80:row==1?24'h40dfff:row==2?24'hffff80:
                (!held_valid || !formatted)?24'hffff00:compare_match?24'h40ff80:24'hff8040;
            rgb_d<=rgb;v_d<=valid;u_d<=user;l_d<=last;
            out_valid<=v_d;out_user<=u_d;out_last<=l_d;
            for(lane=0;lane<4;lane=lane+1)
                out_rgb[95-lane*24-:24]<=panel_d && bits[15-col_d-lane/2]?ink_d:
                    ref_d?24'h40ff80:test_d?24'h40dfff:rgb_d[95-lane*24-:24];
        end
    end
endmodule
