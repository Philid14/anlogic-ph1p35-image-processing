// Two-cycle MAIN overlay. Snapshot LAST completed post-AWB frame at early SOF.
// Shared font is unchanged; four adjacent pixels share one 32px glyph cell.
module color_compare_osd #(
    parameter integer WIDTH=1280,HEIGHT=720,UI_ENABLE=0,AUTO_DIMENSION=0,USABILITY_ENABLE=0,INSPECTION_V4=0,COMPACT_FONT=0,INSPECTION_V5=0,PARTS_ENABLE=0,
    parameter integer REF_X=256,TEST_X=896,ROI_Y=256,ROI_W=128,ROI_H=128
)(
    input clk,rst_n,input [95:0] rgb,input valid,user,last,
    input [47:0] means,input result_valid,input [15:0] sample_id,
    input display_enable,dimension_enable,cal_mode,axis_y,calibrated,
    input [10:0] span_x,span_y,input [1:0] cal_visited,
    input dim_round,background_applied,input[2:0]background_status,input [43:0] dim_sizes,dim_box,dim_gap_coords,input [2:0] cal_status,input dim_valid,dim_present,
    input [1:0] dim_gap_valid,input [7:0] dim_threshold,
    input [15:0] dim_id,input dim_part_valid,input[33:0]dim_part_coords,
    output reg [95:0] out_rgb,output reg out_valid,out_user,out_last
);
    reg show_color,show_dimension,held_cal,held_axis,held_calibrated;
    reg [10:0] held_span_x,held_span_y;
    reg [1:0] held_visited,held_gap;
    reg [43:0] held_sizes,held_box,held_gap_coords;reg [2:0] held_cal_status;
    reg held_dim_valid,held_present,held_round,held_background;reg[2:0]held_bg_status;
    reg [7:0] held_cut;
    reg [15:0] held_dim_id;
    reg held_part_valid;reg[33:0]held_part_coords;
    wire parts=PARTS_ENABLE && held_part_valid && !held_round;
    wire[10:0]part_left=held_part_coords[32:22],part_right=held_part_coords[21:11],part_split=held_part_coords[10:0];
    wire[10:0]part_top=held_box[21:11],part_bottom=held_box[10:0];
    wire[10:0]part_bar=held_part_coords[33]?part_split-part_top:part_bottom-part_split+11'd1;
    wire[10:0]part_leg=held_part_coords[33]?part_bottom-part_split+11'd1:part_split-part_top;
    wire dimension=UI_ENABLE && show_dimension;
    wire enabled=UI_ENABLE?show_color:1'b1;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            held_part_valid<=0;held_part_coords<=0;
            held_round<=0;held_background<=0;held_bg_status<=0;show_color<=0;show_dimension<=0;held_cal<=0;held_axis<=0;held_calibrated<=0;
            held_span_x<=256;held_span_y<=256;held_visited<=0;held_sizes<=0;held_box<=0;
            held_gap_coords<=0;held_cal_status<=0;held_dim_valid<=0;held_present<=0;held_gap<=0;held_cut<=0;held_dim_id<=0;
        end else if(user)begin
            held_part_valid<=PARTS_ENABLE && dim_part_valid;held_part_coords<=PARTS_ENABLE?dim_part_coords:34'd0;
            held_round<=dim_round;held_background<=background_applied;held_bg_status<=background_status;
            show_color<=display_enable && !dimension_enable;show_dimension<=dimension_enable;
            held_cal<=cal_mode;held_axis<=axis_y;held_calibrated<=calibrated;
            held_span_x<=span_x;held_span_y<=span_y;held_visited<=cal_visited;
            held_gap_coords<=dim_gap_coords;held_cal_status<=cal_status;held_sizes<=dim_sizes;held_box<=dim_box;held_dim_valid<=dim_valid;
            held_present<=dim_present;held_gap<=dim_gap_valid;held_cut<=dim_threshold;held_dim_id<=dim_id;
        end
    end
    reg [10:0] x;reg [9:0] y;
    wire [10:0] px=user?11'd0:x;wire [9:0] py=user?10'd0:y;
    reg [47:0] held_rgb;reg [15:0] held_id;
    reg held_valid,formatted,busy;reg [3:0] field;reg [4:0] step;reg dividing;
    reg [19:0] binary_shift;reg [19:0] bcd;
    reg [19:0] dividend,quotient;reg [11:0] remainder;
    reg [10:0] denominator;
    wire [11:0] trial={remainder[10:0],dividend[19]};
    wire quotient_bit=trial>={1'b0,denominator};
    wire [19:0] quotient_next={quotient[18:0],quotient_bit};
    reg [19:0] digits[0:12];
    reg normalizing;reg [2:0] norm_field;reg [7:0] normalized[0:5];
    wire [9:0] ref_sum={2'b0,held_rgb[47:40]}+{2'b0,held_rgb[39:32]}+{2'b0,held_rgb[31:24]};
    wire [9:0] test_sum={2'b0,held_rgb[23:16]}+{2'b0,held_rgb[15:8]}+{2'b0,held_rgb[7:0]};
    wire [7:0] ref_value=held_rgb[47:40]>held_rgb[39:32]?(held_rgb[47:40]>held_rgb[31:24]?held_rgb[47:40]:held_rgb[31:24]):(held_rgb[39:32]>held_rgb[31:24]?held_rgb[39:32]:held_rgb[31:24]);
    wire [7:0] test_value=held_rgb[23:16]>held_rgb[15:8]?(held_rgb[23:16]>held_rgb[7:0]?held_rgb[23:16]:held_rgb[7:0]):(held_rgb[15:8]>held_rgb[7:0]?held_rgb[15:8]:held_rgb[7:0]);
    wire [7:0] nr=absdiff(normalized[0],normalized[3]),ng=absdiff(normalized[1],normalized[4]),nb=absdiff(normalized[2],normalized[5]);
    wire [7:0] chroma_difference=nr>ng?(nr>nb?nr:nb):(ng>nb?ng:nb);
    wire [7:0] value_difference=absdiff(ref_value,test_value);
    wire chroma_reliable=ref_sum>=96 && test_sum>=96 && ref_value>=32 && test_value>=32 && ref_value<254 && test_value<254;
    // 0 MATCH(raw), 1 DIFF, 2 LIGHT(possible multiplicative shading), 3 CHECK.
    // No shade compensation rewrites the measured RGB or automatically certifies a material match.
    reg [7:0] dr,dg,db;reg [3:0] class_ref,class_test;
    wire [9:0] l1={2'd0,dr}+{2'd0,dg}+{2'd0,db};
    wire [7:0] max_difference=dr>dg?(dr>db?dr:db):(dg>db?dg:db);
    wire compare_match=max_difference<=12;
    wire [1:0] comparison_status=!INSPECTION_V4?(compare_match?0:1):!chroma_reliable?3:compare_match?0:chroma_difference<=6?2:1;
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
    function [7:0] comparison_letter;input[1:0]st;input[2:0]pos;
        begin
            comparison_letter=" ";
            case(st)
                0:comparison_letter=match_letter(1'b1,pos);
                1:comparison_letter=match_letter(1'b0,pos);
                2:case(pos)0:comparison_letter="L";1:comparison_letter="I";2:comparison_letter="G";3:comparison_letter="H";4:comparison_letter="T";endcase
                3:case(pos)0:comparison_letter="C";1:comparison_letter="H";2:comparison_letter="E";3:comparison_letter="C";4:comparison_letter="K";endcase
            endcase
        end
    endfunction
    reg [19:0] number;reg [10:0] pixel_span,axis_span;reg [7:0] norm_channel;
    always @*begin
        number=0;pixel_span=0;axis_span=1;norm_channel=0;
        case(field)
            0:number=held_rgb[47:40];1:number=held_rgb[39:32];2:number=held_rgb[31:24];
            3:number=held_rgb[23:16];4:number=held_rgb[15:8];5:number=held_rgb[7:0];
            6:number=dr;7:number=dg;8:number=db;9:number=l1;10:number=max_difference;11:number=chroma_difference;12:number=value_difference;
        endcase
        if(dimension)begin
            case(field)
                0:pixel_span=held_sizes[43:33];1:pixel_span=INSPECTION_V5 && held_round?held_sizes[43:33]:held_sizes[32:22];
                2:pixel_span=held_sizes[21:11];3:pixel_span=held_sizes[10:0];
                default:pixel_span=0;
            endcase
            if(parts)case(field)
                2:pixel_span=part_right-part_left+11'd1;
                3:pixel_span=part_bar;
                4:pixel_span=part_left-held_box[43:33];
                5:pixel_span=held_box[32:22]-part_right;
                6:pixel_span=part_leg;
                default:pixel_span=pixel_span;
            endcase
            axis_span=((field==1 && !(INSPECTION_V5 && held_round)) || field==3)?held_span_y:held_span_x;
            if(parts && field==6)axis_span=held_span_y;
            if(axis_span==0)axis_span=1;
            if(field<(parts?7:4))begin
                number=held_calibrated ? pixel_span*20'd1000 : pixel_span*20'd10;
                if(INSPECTION_V5 && held_round && field==1)number=number>>1;
                if(held_calibrated)number=number+(axis_span>>1);
            end
            else if(!AUTO_DIMENSION)case(field)
                4:number=held_cut;5:number=held_span_x;6:number=held_span_y;
                default:number=0;
            endcase
        end
        if(normalizing)begin
            case(norm_field)
                0:norm_channel=held_rgb[47:40];1:norm_channel=held_rgb[39:32];2:norm_channel=held_rgb[31:24];
                3:norm_channel=held_rgb[23:16];4:norm_channel=held_rgb[15:8];5:norm_channel=held_rgb[7:0];
            endcase
            axis_span=norm_field<3?{1'b0,ref_sum}:{1'b0,test_sum};
            if(axis_span==0)axis_span=1;
            number=norm_channel*20'd255+(axis_span>>1);
        end
    end
    reg [19:0] adjusted;integer n;
    always @*begin
        adjusted=bcd;
        for(n=0;n<5;n=n+1)if(bcd[n*4+:4]>=5)adjusted[n*4+:4]=bcd[n*4+:4]+3;
    end
    integer j;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            held_rgb<=0;held_id<=0;held_valid<=0;formatted<=0;busy<=0;
            field<=0;step<=0;binary_shift<=0;bcd<=0;dividing<=0;dividend<=0;quotient<=0;remainder<=0;denominator<=1;dr<=0;dg<=0;db<=0;class_ref<=0;class_test<=0;
            normalizing<=0;norm_field<=0;
            for(j=0;j<13;j=j+1)digits[j]<=0;
            for(j=0;j<6;j=j+1)normalized[j]<=0;
        end else if(user)begin
            held_rgb<=means;held_id<=sample_id;held_valid<=result_valid;
            dr<=absdiff(means[47:40],means[23:16]);dg<=absdiff(means[39:32],means[15:8]);db<=absdiff(means[31:24],means[7:0]);
            class_ref<=classify(means[47:24]);class_test<=classify(means[23:0]);
            busy<=1;field<=0;step<=0;formatted<=0;dividing<=0;normalizing<=INSPECTION_V4 && !dimension_enable;norm_field<=0;
        end else if(busy)begin
            if(dividing)begin
                dividend<={dividend[18:0],1'b0};quotient<=quotient_next;
                remainder<=quotient_bit ? trial-{1'b0,denominator} : trial;
                if(step==20)begin
                    dividing<=0;
                    if(normalizing)begin
                        normalized[norm_field]<=quotient_next[7:0];step<=0;
                        if(norm_field==5)normalizing<=0;else norm_field<=norm_field+1'b1;
                    end else begin binary_shift<=quotient_next;bcd<=0;step<=1;end
                end else step<=step+1'b1;
            end else if(step==0)begin
                if(normalizing || (dimension && held_calibrated && field<(parts?7:4)))begin
                    dividing<=1;dividend<=number;denominator<=axis_span;
                    remainder<=0;quotient<=0;step<=1;
                end else begin binary_shift<=number;bcd<=0;step<=1;end
            end else begin
                bcd<={adjusted[18:0],binary_shift[19]};binary_shift<={binary_shift[18:0],1'b0};
                if(step==20)begin
                    digits[field]<={adjusted[18:0],binary_shift[19]};step<=0;
                    if(field==(dimension?(AUTO_DIMENSION?(parts?6:3):6):(INSPECTION_V4?12:10)))begin busy<=0;formatted<=1;end else field<=field+1'b1;
                end else step<=step+1'b1;
            end
        end
    end
    wire panel=px>=32 && px<1248 && py>=544 && py<(INSPECTION_V4?704:672);
    wire [10:0] lx=px-32;wire [9:0] ly=py-544;
    wire [5:0] column=lx[10:5];wire [2:0] row=ly[7:5];
    wire ref_box=px>=REF_X-4 && px<REF_X+ROI_W+4 && py>=ROI_Y-2 && py<ROI_Y+ROI_H+2 &&
        (px<REF_X || px>=REF_X+ROI_W || py<ROI_Y || py>=ROI_Y+ROI_H);
    wire test_box=px>=TEST_X-4 && px<TEST_X+ROI_W+4 && py>=ROI_Y-2 && py<ROI_Y+ROI_H+2 &&
        (px<TEST_X || px>=TEST_X+ROI_W || py<ROI_Y || py>=ROI_Y+ROI_H);
    wire [10:0] xmin=held_box[43:33],xmax=held_box[32:22],ymin=held_box[21:11],ymax=held_box[10:0];
    wire work_outline=(px>=252 && px<1028 && py>=158 && py<546) &&
        (px<256 || px>=1024 || py<160 || py>=544);
    wire box_outline=held_dim_valid && held_present && px+3>=xmin && px<=xmax && py>=ymin && py<=ymax &&
        (px<((xmin>>2)<<2)+4 || px>=((xmax>>2)<<2) || py==ymin || py==ymax);
    wire crosshair=(px==640 && py>=340 && py<=364) || (py==352 && px>=628 && px<=652);
    wire [10:0] xa=640-(held_span_x>>1),xb=640+(held_span_x>>1);
    wire [10:0] ya=352-(held_span_y>>1),yb=352+(held_span_y>>1);
    wire cal_x_mark=(py==352 && px>=xa && px<=xb) ||
        ((px==((xa>>2)<<2) || px==((xb>>2)<<2)) && py>=328 && py<=376);
    wire cal_y_mark=(px==640 && py>=ya && py<=yb) ||
        ((py==ya || py==yb) && px>=616 && px<=664);
    wire old_dim_mark=dimension && (held_cal ? (held_axis?cal_y_mark:cal_x_mark) :
        (work_outline || box_outline || crosshair));
    wire [3:0] engineering_marks;
    wire engineering_text;wire [7:0] engineering_char;wire [3:0] engineering_row,engineering_col;
    generate if(AUTO_DIMENSION)begin:g_drawing
        engineering_dimension_marks #(.SEARCH_ENABLE(USABILITY_ENABLE),.AREA_ENABLE(INSPECTION_V4),.SHAPE_ENABLE(INSPECTION_V5),.PARTS_ENABLE(PARTS_ENABLE)) u_drawing(.round_object(held_round),.background_applied(held_background),.background_status(held_bg_status),.x(px),.y(py),.cal(held_cal),.calibrated(held_calibrated),
            .object_valid(held_dim_valid && held_present),.formatted(formatted),.cal_status(held_cal_status),
            .box_coords(held_box),.gap_coords(held_gap_coords),.gap_valid(parts?2'd0:held_gap),
            .parts(parts),.part_coords(held_part_coords),.part_digits({digits[2],digits[3],digits[4],digits[5],digits[6]}),
            .digits({digits[0],digits[1],digits[2],digits[3]}),.marks(engineering_marks),
            .text_valid(engineering_text),.character(engineering_char),.glyph_row(engineering_row),.glyph_col(engineering_col));
    end else begin:g_no_drawing
        assign engineering_marks=0;assign engineering_text=0;assign engineering_char=32;
        assign engineering_row=0;assign engineering_col=0;
    end endgenerate
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
            8'd215:character=INSPECTION_V4?comparison_letter(comparison_status,3'd0):match_letter(compare_match,3'd0);
            8'd216:character=INSPECTION_V4?comparison_letter(comparison_status,3'd1):match_letter(compare_match,3'd1);
            8'd217:character=INSPECTION_V4?comparison_letter(comparison_status,3'd2):match_letter(compare_match,3'd2);
            8'd218:character=INSPECTION_V4?comparison_letter(comparison_status,3'd3):match_letter(compare_match,3'd3);
            8'd219:character=INSPECTION_V4?comparison_letter(comparison_status,3'd4):match_letter(compare_match,3'd4);
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
        if(INSPECTION_V4 && row==4)begin
            character=" ";
            case(column)
                0:character="C";1:character="H";2:character="R";3:character=":";
                4:character="0"+digits[11][11:8];5:character="0"+digits[11][7:4];6:character="0"+digits[11][3:0];
                8:character="D";9:character="V";10:character=":";
                11:character="0"+digits[12][11:8];12:character="0"+digits[12][7:4];13:character="0"+digits[12][3:0];
                15:character="C";16:character="L";17:character="I";18:character="M";19:character=":";
                20:character="0";21:character="0";22:character="6";
                24:character="R";25:character="G";26:character="B";28:character="R";29:character="A";30:character="W";
            endcase
            if(!chroma_reliable && column>=4 && column<=6)character="-";
        end
        if(!held_valid || !formatted)begin
            character=" ";
            if(row==3)case(column)
                0:character="W";1:character="A";2:character="I";3:character="T";
                5:character="F";6:character="O";7:character="R";
                9:character="F";10:character="U";11:character="L";12:character="L";
                14:character="F";15:character="R";16:character="A";17:character="M";18:character="E";
            endcase
        end
        if(dimension && !AUTO_DIMENSION)begin
            character=" ";
            case({row,column})
                8'd0:character="S";
                8'd1:character="I";
                8'd2:character="Z";
                8'd3:character="E";
                8'd5:character="W";
                8'd6:character=":";
                8'd7:character="0";
                8'd8:character="0";
                8'd9:character="0";
                8'd10:character="0";
                8'd11:character=".";
                8'd12:character="0";
                8'd14:character="H";
                8'd15:character=":";
                8'd16:character="0";
                8'd17:character="0";
                8'd18:character="0";
                8'd19:character="0";
                8'd20:character=".";
                8'd21:character="0";
                8'd23:character="M";
                8'd24:character="M";
                8'd64:character="G";
                8'd65:character="A";
                8'd66:character="P";
                8'd67:character="X";
                8'd68:character=":";
                8'd69:character="0";
                8'd70:character="0";
                8'd71:character="0";
                8'd72:character="0";
                8'd73:character=".";
                8'd74:character="0";
                8'd76:character="G";
                8'd77:character="A";
                8'd78:character="P";
                8'd79:character="Y";
                8'd80:character=":";
                8'd81:character="0";
                8'd82:character="0";
                8'd83:character="0";
                8'd84:character="0";
                8'd85:character=".";
                8'd86:character="0";
                8'd88:character="M";
                8'd89:character="M";
                8'd128:character="C";
                8'd129:character="U";
                8'd130:character="T";
                8'd131:character=":";
                8'd132:character="0";
                8'd133:character="0";
                8'd134:character="0";
                8'd136:character="D";
                8'd137:character="A";
                8'd138:character="R";
                8'd139:character="K";
                8'd141:character="C";
                8'd142:character="A";
                8'd143:character="L";
                8'd144:character=":";
                8'd145:character="N";
                8'd146:character="E";
                8'd147:character="E";
                8'd148:character="D";
                8'd149:character="E";
                8'd150:character="D";
                8'd192:character="L";
                8'd193:character="A";
                8'd194:character="S";
                8'd195:character="T";
                8'd196:character=":";
                8'd197:character="0";
                8'd198:character="0";
                8'd199:character="0";
                8'd200:character="0";
                8'd202:character="A";
                8'd203:character="L";
                8'd204:character="I";
                8'd205:character="G";
                8'd206:character="N";
                8'd208:character="E";
                8'd209:character="D";
                8'd210:character="G";
                8'd211:character="E";
                8'd212:character="S";
                8'd214:character="T";
                8'd215:character="O";
                8'd217:character="X";
                8'd218:character="/";
                8'd219:character="Y";
                default:character=" ";
            endcase
            if(row==0 && column==7)character=8'h30+digits[0][19 -:4];
            if(row==0 && column==8)character=8'h30+digits[0][15 -:4];
            if(row==0 && column==9)character=8'h30+digits[0][11 -:4];
            if(row==0 && column==10)character=8'h30+digits[0][7 -:4];
            if(row==0 && column==11)character=".";
            if(row==0 && column==12)character=8'h30+digits[0][3 -:4];
            if(row==0 && column>=7 && column<13 &&
                (!formatted || !held_dim_valid || !held_present))character="-";
            if(row==0 && column==16)character=8'h30+digits[1][19 -:4];
            if(row==0 && column==17)character=8'h30+digits[1][15 -:4];
            if(row==0 && column==18)character=8'h30+digits[1][11 -:4];
            if(row==0 && column==19)character=8'h30+digits[1][7 -:4];
            if(row==0 && column==20)character=".";
            if(row==0 && column==21)character=8'h30+digits[1][3 -:4];
            if(row==0 && column>=16 && column<22 &&
                (!formatted || !held_dim_valid || !held_present))character="-";
            if(row==1 && column==5)character=8'h30+digits[2][19 -:4];
            if(row==1 && column==6)character=8'h30+digits[2][15 -:4];
            if(row==1 && column==7)character=8'h30+digits[2][11 -:4];
            if(row==1 && column==8)character=8'h30+digits[2][7 -:4];
            if(row==1 && column==9)character=".";
            if(row==1 && column==10)character=8'h30+digits[2][3 -:4];
            if(row==1 && column>=5 && column<11 &&
                (!formatted || !held_dim_valid || !held_present || !held_gap[1]))character="-";
            if(row==1 && column==17)character=8'h30+digits[3][19 -:4];
            if(row==1 && column==18)character=8'h30+digits[3][15 -:4];
            if(row==1 && column==19)character=8'h30+digits[3][11 -:4];
            if(row==1 && column==20)character=8'h30+digits[3][7 -:4];
            if(row==1 && column==21)character=".";
            if(row==1 && column==22)character=8'h30+digits[3][3 -:4];
            if(row==1 && column>=17 && column<23 &&
                (!formatted || !held_dim_valid || !held_present || !held_gap[0]))character="-";
            if(row==0 && column==23)character=held_calibrated?"M":"P";
            if(row==0 && column==24)character=held_calibrated?"M":"X";
            if(row==1 && column==24)character=held_calibrated?"M":"P";
            if(row==1 && column==25)character=held_calibrated?"M":"X";
            if(row==2 && column>=4 && column<7)case(column)
                4:character=8'h30+digits[4][11:8];5:character=8'h30+digits[4][7:4];
                6:character=8'h30+digits[4][3:0];endcase
            if(row==2 && column>=8 && column<14)begin
                character=" ";
                if(held_axis)case(column)8:character="B";9:character="R";10:character="I";
                    11:character="G";12:character="H";13:character="T";endcase
                else case(column)8:character="D";9:character="A";10:character="R";11:character="K";endcase
            end
            if(row==2 && column>=14)begin
                character=" ";case(column)14:character="C";15:character="A";16:character="L";17:character=":";
                    18:character=held_calibrated?"O":"N";19:character=held_calibrated?"K":"E";
                    20:character=held_calibrated?" ":"E";21:character=held_calibrated?" ":"D";
                    22:character=held_calibrated?" ":"E";23:character=held_calibrated?" ":"D";endcase
            end
            if(row==3 && column>=5 && column<9)case(column)
                5:character=hexchar(held_dim_id[15:12]);6:character=hexchar(held_dim_id[11:8]);
                7:character=hexchar(held_dim_id[7:4]);8:character=hexchar(held_dim_id[3:0]);endcase
            if(row==3 && column>=10 && (!held_dim_valid || !held_present))begin
                character=" ";case(column)10:character="N";11:character="O";13:character="V";
                    14:character="A";15:character="L";16:character="I";17:character="D";
                    19:character="O";20:character="B";21:character="J";22:character="E";
                    23:character="C";24:character="T";endcase
            end
            if(held_cal)begin
            case({row,column})
                8'd0:character="C";
                8'd1:character="A";
                8'd2:character="L";
                8'd4:character="X";
                8'd6:character="1";
                8'd7:character="0";
                8'd8:character="0";
                8'd9:character=".";
                8'd10:character="0";
                8'd12:character="M";
                8'd13:character="M";
                8'd15:character="S";
                8'd16:character="P";
                8'd17:character="A";
                8'd18:character="N";
                8'd19:character=":";
                8'd20:character="0";
                8'd21:character="0";
                8'd22:character="0";
                8'd23:character="0";
                8'd25:character="P";
                8'd26:character="X";
                8'd64:character="K";
                8'd65:character="4";
                8'd67:character="S";
                8'd68:character="H";
                8'd69:character="O";
                8'd70:character="R";
                8'd71:character="T";
                8'd73:character="-";
                8'd74:character="4";
                8'd76:character="H";
                8'd77:character="O";
                8'd78:character="L";
                8'd79:character="D";
                8'd81:character="+";
                8'd82:character="4";
                8'd128:character="S";
                8'd129:character="W";
                8'd130:character="2";
                8'd132:character="X";
                8'd133:character="/";
                8'd134:character="Y";
                8'd136:character="S";
                8'd137:character="W";
                8'd138:character="3";
                8'd140:character="O";
                8'd141:character="F";
                8'd142:character="F";
                8'd144:character="C";
                8'd145:character="O";
                8'd146:character="N";
                8'd147:character="F";
                8'd148:character="I";
                8'd149:character="R";
                8'd150:character="M";
                8'd192:character="A";
                8'd193:character="L";
                8'd194:character="I";
                8'd195:character="G";
                8'd196:character="N";
                8'd198:character="R";
                8'd199:character="U";
                8'd200:character="L";
                8'd201:character="E";
                8'd202:character="R";
                8'd204:character="I";
                8'd205:character="N";
                8'd207:character="W";
                8'd208:character="O";
                8'd209:character="R";
                8'd210:character="K";
                8'd212:character="P";
                8'd213:character="L";
                8'd214:character="A";
                8'd215:character="N";
                8'd216:character="E";
                default:character=" ";
            endcase

                if(row==0 && column==4)character=held_axis?"Y":"X";
                if(row==0 && column>=20 && column<24)case(column)
                    20:character=8'h30+digits[held_axis?6:5][15:12];
                    21:character=8'h30+digits[held_axis?6:5][11:8];
                    22:character=8'h30+digits[held_axis?6:5][7:4];
                    23:character=8'h30+digits[held_axis?6:5][3:0];endcase
            end
        end
    end
    reg [7:0] char_d;reg [3:0] row_d,col_d;
    reg panel_d,ref_d,test_d,dim_d,v_d,u_d,l_d;reg [3:0] marks_d;reg native_d;reg [95:0] rgb_d;
    reg [23:0] ink_d;wire [15:0] bits;
    generate if(COMPACT_FONT)begin:g_font_ram
        inspection_font_rom u_font(.clk(clk),.character(dimension && AUTO_DIMENSION?engineering_char:character),
            .row(dimension && AUTO_DIMENSION?engineering_row:ly[4:1]),.bits(bits));
    end else begin:g_font_logic
        osd_char_lib u_font(.I_char(char_d),.I_row(row_d),.O_row_bits(bits));
    end endgenerate
    integer lane;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            marks_d<=0;native_d<=0;x<=0;y<=0;char_d<=0;row_d<=0;col_d<=0;panel_d<=0;ref_d<=0;test_d<=0;dim_d<=0;v_d<=0;u_d<=0;l_d<=0;rgb_d<=0;ink_d<=0;
            out_rgb<=0;out_valid<=0;out_user<=0;out_last<=0;
        end else begin
            if(user)begin x<=0;y<=0;end
            if(valid)begin x<=px==WIDTH-4?0:px+4;if(px==WIDTH-4)y<=py==HEIGHT-1?0:py+1'b1;else y<=py;end
            char_d<=dimension && AUTO_DIMENSION?engineering_char:character;
            row_d<=dimension && AUTO_DIMENSION?engineering_row:ly[4:1];
            col_d<=dimension && AUTO_DIMENSION?engineering_col:lx[4:1];
            native_d<=dimension && AUTO_DIMENSION;marks_d<=dimension?engineering_marks:0;
            panel_d<=dimension && AUTO_DIMENSION?engineering_text:panel && (enabled || dimension);dim_d<=!AUTO_DIMENSION && old_dim_mark;ref_d<=ref_box && enabled;test_d<=test_box && enabled;
            ink_d<=dimension && AUTO_DIMENSION?24'hffff80:row==0?24'h40ff80:row==1?24'h40dfff:row==2?24'hffff80:
                (!held_valid || !formatted)?24'hffff00:comparison_status==0?24'h40ff80:comparison_status==2?24'hffff00:24'hff8040;
            rgb_d<=rgb;v_d<=valid;u_d<=user;l_d<=last;
            out_valid<=v_d;out_user<=u_d;out_last<=l_d;
            for(lane=0;lane<4;lane=lane+1)
                out_rgb[95-lane*24-:24]<=panel_d && bits[15-col_d-(native_d?lane:lane/2)]?((native_d && rgb_d[87-lane*24])?24'h101030:ink_d):
                    (dim_d || marks_d[3-lane])?((native_d && rgb_d[87-lane*24])?24'h101030:24'hffff80):ref_d?24'h40ff80:test_d?24'h40dfff:rgb_d[95-lane*24-:24];
        end
    end
endmodule
