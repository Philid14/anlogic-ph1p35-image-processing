// Drawing-style dimensions on the single observed plane (not CAD reconstruction).
// Native 16px glyphs, transparent backgrounds. All text anchors are 4px aligned.
module engineering_dimension_marks #(parameter SEARCH_ENABLE=0,AREA_ENABLE=0)(
    input [10:0] x,input [9:0] y,
    input cal,calibrated,object_valid,formatted,
    input [2:0] cal_status,
    input [43:0] box_coords,gap_coords,
    input [1:0] gap_valid,
    input [79:0] digits,
    output reg [3:0] marks,
    output reg text_valid,output reg [7:0] character,
    output reg [3:0] glyph_row,glyph_col
);
    wire [10:0] xmin=box_coords[43:33],xmax=box_coords[32:22];
    wire [10:0] ymin=box_coords[21:11],ymax=box_coords[10:0];
    wire [10:0] gl=gap_coords[43:33],gr=gap_coords[32:22];
    wire [10:0] gt=gap_coords[21:11],gb=gap_coords[10:0];
    wire [10:0] wx=((({1'b0,xmin}+{1'b0,xmax})>>1)-96)&11'h7fc;
    wire [10:0] hy=((({1'b0,ymin}+{1'b0,ymax})>>1)-8);
    wire [10:0] gx=((({1'b0,gl}+{1'b0,gr})>>1)-96)&11'h7fc;
    wire [10:0] gy=((({1'b0,gt}+{1'b0,gb})>>1)-24);
    reg [10:0] tx,ty,q;reg [3:0] col;
    reg [1:0] field;reg active;reg [19:0] value;
    wire scan_y=SEARCH_ENABLE ? (y==288 || y==291 || y==294 || y==297 || y==300 || y==303 || y==306 || y==309 || y==312 || y==315 || y==318 || y==321) : (y==304 || y==306 || y==308);
    reg line_ink;integer k;
    function [7:0] message;input [5:0] i;input [2:0] s;begin
        message=" ";
        case(i)
            0:message="C";1:message="A";2:message="L";3:message=":";
            5:message=s==3?"O":s==1?"W":s==2?"B":s==0?"N":"F";
            6:message=s==3?"K":s==1?"A":s==2?"U":s==0?"E":"A";
            7:message=s==1?"I":s==2?"S":s==0?"E":s==3?" ":"I";
            8:message=s==1?"T":s==2?"Y":s==0?"D":s==3?" ":"L";
            10:message="K";11:message="4";13:message="C";14:message="A";
            15:message="P";16:message="T";17:message="U";18:message="R";19:message="E";
        endcase
    end endfunction
    always @*begin
        marks=0;text_valid=0;character=" ";glyph_row=0;glyph_col=0;
        tx=0;ty=0;col=0;field=0;active=0;value=0;line_ink=0;q=0;
        if(cal)begin
            // Put the millimetre tick baseline across all three scan lines.
            for(k=0;k<4;k=k+1)begin
                q=x+k;
                marks[3-k]=(q>=(AREA_ENABLE?252:380) && q<=(AREA_ENABLE?1027:899) && y>=(AREA_ENABLE?190:288) && y<=(AREA_ENABLE?481:324) &&
                    (q<(AREA_ENABLE?256:384) || q>=(AREA_ENABLE?1024:896) || y==(AREA_ENABLE?190:288) || y==(AREA_ENABLE?481:324))) ||
                    (!AREA_ENABLE && q>=384 && q<896 && scan_y && q[3:0]<4);
            end
            if(x>=(AREA_ENABLE?256:384) && x<(AREA_ENABLE?736:864) && y>=(AREA_ENABLE?168:240) && y<(AREA_ENABLE?184:256))begin
                text_valid=1;glyph_col=x[3:0];glyph_row=y-(AREA_ENABLE?168:240);
                case((x-(AREA_ENABLE?256:384))>>4)
                    0:character="1";1:character=AREA_ENABLE?"C":"M";2:character="M";
                    4:character="R";5:character="U";6:character="L";7:character="E";8:character="R";
                    10:character=AREA_ENABLE?"L":"B";11:character=AREA_ENABLE?"O":"L";
                    12:character=AREA_ENABLE?"N":"A";13:character=AREA_ENABLE?"G":"C";14:character=AREA_ENABLE?" ":"K";
                    15:character=AREA_ENABLE?"T":" ";16:character=AREA_ENABLE?"I":"T";
                    17:character=AREA_ENABLE?"C":"I";18:character=AREA_ENABLE?"K":"C";
                    19:character=AREA_ENABLE?"S":"K";20:character=AREA_ENABLE?" ":"S";
                    default:character=" ";
                endcase
            end
            if(x>=(AREA_ENABLE?256:384) && x<(AREA_ENABLE?736:864) && y>=(AREA_ENABLE?496:352) && y<(AREA_ENABLE?512:368))begin
                text_valid=1;glyph_col=x[3:0];glyph_row=y-(AREA_ENABLE?496:352);
                character=message((x-(AREA_ENABLE?256:384))>>4,cal_status);
            end
        end else if(object_valid && formatted)begin
            // Outer dimension extension lines and inward-pointing arrowheads.
            for(k=0;k<4;k=k+1)begin
                q=x+k;
                line_ink=(y==ymin-8 && q>=xmin && q<=xmax) ||
                    ((q==xmin || q==xmax) && y>=ymin-12 && y<=ymin-2) ||
                    (q==xmax+20 && y>=ymin && y<=ymax) ||
                    ((y==ymin || y==ymax) && q>=xmax+2 && q<=xmax+24);
                // Open arrowheads with constant offsets; no wide variable subtract/absolute paths.
                line_ink=line_ink ||
                    ((y==ymin-9 || y==ymin-7) && (q==xmin+2 || q+2==xmax)) ||
                    ((y==ymin-10 || y==ymin-6) && (q==xmin+4 || q+4==xmax)) ||
                    ((y==ymin-11 || y==ymin-5) && (q==xmin+6 || q+6==xmax)) ||
                    ((q==xmax+19 || q==xmax+21) && (y==ymin+2 || y+2==ymax)) ||
                    ((q==xmax+18 || q==xmax+22) && (y==ymin+4 || y+4==ymax)) ||
                    ((q==xmax+17 || q==xmax+23) && (y==ymin+6 || y+6==ymax));
                if(gap_valid[1])line_ink=line_ink ||
                    (y==352 && q>=gl && q<=gr) || ((q==gl || q==gr) && y>=348 && y<=356);
                if(gap_valid[0])line_ink=line_ink ||
                    (q==640 && y>=gt && y<=gb) || ((y==gt || y==gb) && q>=636 && q<=644);
                marks[3-k]=line_ink;
            end
            if(x>=wx && x<wx+192 && y>=ymin-30 && y<ymin-14)begin
                active=1;field=0;tx=wx;ty=ymin-30;
            end else if(x>=((xmax+36)&11'h7fc) && x<((xmax+36)&11'h7fc)+192 && y>=hy && y<hy+16)begin
                active=1;field=1;tx=(xmax+36)&11'h7fc;ty=hy;
            end else if(gap_valid[1] && x>=gx && x<gx+192 && y>=364 && y<380)begin
                active=1;field=2;tx=gx;ty=364;
            end else if(gap_valid[0] && x>=652 && x<844 && y>=gy && y<gy+16)begin
                active=1;field=3;tx=652;ty=gy;
            end
            if(active)begin
                text_valid=1;glyph_col=x-tx;glyph_row=y-ty;col=(x-tx)>>4;
                case(field)0:value=digits[79:60];1:value=digits[59:40];
                    2:value=digits[39:20];3:value=digits[19:0];endcase
                case(col)
                    0:character=field==0?"W":field==1?"H":field==2?"X":"Y";
                    2:character=value[19:16]!=0?"0"+value[19:16]:" ";
                    3:character=value[19:12]!=0?"0"+value[15:12]:" ";
                    4:character=value[19:8]!=0?"0"+value[11:8]:" ";
                    5:character="0"+value[7:4];6:character=".";7:character="0"+value[3:0];
                    9:character=calibrated?"M":"P";10:character=calibrated?"M":"X";
                    default:character=" ";
                endcase
            end
        end else if(x>=384 && x<864 && y>=184 && y<200)begin
            text_valid=1;glyph_col=x[3:0];glyph_row=y-184;
            if(!calibrated)character=message((x-(AREA_ENABLE?256:384))>>4,cal_status);
            else case((x-384)>>4)
                0:character="N";1:character="O";3:character="V";4:character="A";5:character="L";
                6:character="I";7:character="D";9:character="O";10:character="B";11:character="J";
                12:character="E";13:character="C";14:character="T";default:character=" ";endcase
        end
    end
endmodule
