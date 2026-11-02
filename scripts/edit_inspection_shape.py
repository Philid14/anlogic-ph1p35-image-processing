"""One-time bounded MAIN integration; exact anchors fail on unexpected source."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
H=R/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source'
def edit(name, pairs):
 p=H/name;s=p.read_text()
 for old,new in pairs:
  assert old in s,(name,old[:90]);s=s.replace(old,new)
 p.write_text(s)

for name in ('isp/isp_top.v','isp/edge_control_stream.v','edge_status_osd.v'):
 edit(name,[('parameter integer COMPACT_FONT = 0','parameter integer INSPECTION_V5 = 0,\n    parameter integer COMPACT_FONT = 0')])
edit('isp/isp_top.v',[('.COMPACT_FONT(COMPACT_FONT)', '.COMPACT_FONT(COMPACT_FONT),.INSPECTION_V5(INSPECTION_V5)')])
edit('design_top_wrapper.v',[('.COMPACT_FONT(1)', '.COMPACT_FONT(1),.INSPECTION_V5(1)')])
edit('vision/vision_source_observer.v',[
 ('output reg [19:0] target_count,','output reg [43:0] target_box,output reg [19:0] target_count,'),
 ('last_target_valid<=0;target_x<=0;','last_target_valid<=0;target_box<=0;target_x<=0;'),
 ('last_target_valid<=det_valid && det_present;target_frame<=det_fid;', 'last_target_valid<=det_valid && det_present;target_frame<=det_fid;\n                target_box<=det_valid && det_present?{dx0,dx1,1\'b0,dy0,1\'b0,dy1}:44\'d0;')])
edit('edge_status_osd.v',[
 ('input [19:0] I_target_count,','input [43:0] I_target_box,input [19:0] I_target_count,'),
 ('reg [11:0] mn_f;', 'reg [43:0] tb_f;\n    reg [11:0] mn_f;'),
 ('tx_f<=0;ty_f<=0;', 'tb_f<=0;tx_f<=0;ty_f<=0;'),
 ('tx_f<=I_target_x;', 'tb_f<=I_target_box;tx_f<=I_target_x;'),
 ('integer lane;','wire [10:0] bx0=tb_f[43:33],bx1=tb_f[32:22],by0=tb_f[21:11],by1=tb_f[10:0];\n    reg [3:0] outline,outline_s1;integer lane,bl;reg[12:0] bpx;\n    always @*begin\n        outline=0;bpx=0;\n        for(bl=0;bl<4;bl=bl+1)begin\n            bpx=pixel_x+bl;\n            outline[3-bl]=INSPECTION_V5 && ENABLE && VISION_ENABLE && mode==5 && target_valid_f &&\n                bx1>=bx0 && by1>=by0 && bpx>=bx0 && bpx<=bx1 && y_now>=by0 && y_now<=by1 &&\n                (bpx<=bx0+1 || bpx+1>=bx1 || y_now<=by0+1 || y_now+1>=by1);\n        end\n    end'),
 ('rgb_s1<=0; O_data<=0;', 'outline_s1<=0;rgb_s1<=0; O_data<=0;'),
 ('rgb_s1<=I_data;', 'outline_s1<=outline;rgb_s1<=I_data;'),
 ('else O_data[95-lane*24 -:24] <= rgb_s1[95-lane*24 -:24];', 'else if(outline_s1[3-lane])O_data[95-lane*24-:24]<=24\'h00ff80;\n                else O_data[95-lane*24 -:24] <= rgb_s1[95-lane*24 -:24];')])
edit('isp/edge_control_stream.v',[
 ('wire [31:0] target_frame,motion_frame;', 'wire [43:0] target_box;wire [31:0] target_frame,motion_frame;'),
 ('.target_count(target_count),', '.target_box(target_box),.target_count(target_count),'),
 ('assign target_count=0;', 'assign target_box=0;assign target_count=0;'),
 ('if(VISION_ENABLE && config_p[EDGE_STAGES-1][18:16]==3\'d5', 'if(VISION_ENABLE && !INSPECTION_V5 && config_p[EDGE_STAGES-1][18:16]==3\'d5'),
 ('.I_target_count(target_count),', '.I_target_box(target_box),.I_target_count(target_count),'),
 ('.COMPACT_FONT(COMPACT_FONT)', '.COMPACT_FONT(COMPACT_FONT),.INSPECTION_V5(INSPECTION_V5)'),
 ('wire [1:0] dim_gap;', 'wire dim_round,dim_background;wire[2:0] bg_status;wire [1:0] dim_gap;'),
 ('planar_measure_stats #(.WIDTH(IMG_WIDTH),.HEIGHT(IMG_HEIGHT)) u_dimension(', '''wire[3:0] measured_pixels;wire mv,mu,ml,mb;wire[7:0] mt;
            if(INSPECTION_V5)begin:g_background
                wire applied,ready;reg[1:0] bright_pipe;reg[7:0] cut0,cut1;reg background_result;
                measure_background #(.WIDTH(IMG_WIDTH),.HEIGHT(IMG_HEIGHT)) u_background(
                    .clk(clk),.rst_n(rst_n),.gray({gray_p[0][95:88],gray_p[0][71:64],gray_p[0][47:40],gray_p[0][23:16]}),
                    .fallback_pixels({binary_p[0][95],binary_p[0][71],binary_p[0][47],binary_p[0][23]}),
                    .valid(valid_p[0]),.user(user_p[0]),.last(last_p[0]),.bright(ui_pipe[0][2]),
                    .learn_enable(ui_switches[1] && !ui_switches[3] && beat_config[18:16]==MODE_ORIGIN),
                    .clear(ui_switches[1] && ui_switches[3]),.request_toggle(capture_toggle),
                    .pixels(measured_pixels),.out_valid(mv),.out_user(mu),.out_last(ml),.applied(applied),.ready(ready),.status(bg_status));
                always @(posedge clk or negedge rst_n)begin
                    if(!rst_n)begin bright_pipe<=0;cut0<=0;cut1<=0;background_result<=0;end
                    else begin bright_pipe<={bright_pipe[0],ui_pipe[0][2]};cut0<=config_p[0][7:0];cut1<=cut0;
                        if(mu)background_result<=applied;end
                end
                assign mb=bright_pipe[1];assign mt=cut1;assign dim_background=background_result;
            end else begin:g_fixed
                assign measured_pixels={binary_p[0][95],binary_p[0][71],binary_p[0][47],binary_p[0][23]};
                assign mv=valid_p[0];assign mu=user_p[0];assign ml=last_p[0];assign mb=ui_pipe[0][2];assign mt=config_p[0][7:0];
                assign dim_background=0;assign bg_status=0;
            end
            planar_measure_stats #(.WIDTH(IMG_WIDTH),.HEIGHT(IMG_HEIGHT),.SHAPE_ENABLE(INSPECTION_V5),.MIN_ROW(INSPECTION_V5?6:8)) u_dimension('''),
 ('.binary_pixels({binary_p[0][95],binary_p[0][71],binary_p[0][47],binary_p[0][23]}),\n                .valid(valid_p[0]),.user(user_p[0]),.last(last_p[0]),.bright(ui_pipe[0][2]),\n                .threshold(config_p[0][7:0])', '.binary_pixels(measured_pixels),\n                .valid(mv),.user(mu),.last(ml),.bright(mb),.round_present(dim_round),\n                .threshold(mt)'),
 ('assign dim_gap_coords=0;', 'assign dim_round=0;assign dim_background=0;assign bg_status=0;assign dim_gap_coords=0;'),
 ('.dim_sizes(dim_sizes),', '.dim_round(dim_round),.background_applied(dim_background),.background_status(bg_status),.dim_sizes(dim_sizes),')])

edit('isp/planar_measure_stats.v',[
 ('parameter MIN_ROW=8,', 'parameter SHAPE_ENABLE=0,MIN_ROW=8,'),
 ('output reg result_valid,present,','output reg round_present,output reg result_valid,present,'),
 ('wire geometry=last', '''// Envelope area fills internal holes/highlights, but not a missing silhouette.
    wire[10:0] spanx=maxx-minx+11'd1,spany=maxy-miny+11'd1;
    wire[10:0] rspan=next_max-next_min+11'd1;
    reg[19:0] envelope;reg[21:0] bbox_area;
    reg[10:0] tip_span,q1_span,q3_span;
    wire[10:0] old_y0=box_coords[21:11],old_y1=box_coords[10:0];
    wire[10:0] old_h=old_y1-old_y0+11'd1;
    wire[10:0] q1y=old_y0+(old_h>>2),q3y=old_y1-(old_h>>2);
    reg shape_ok;
    wire near_square=spanx>=24 && spany>=24 &&
        (spanx>spany?spanx-spany:spany-spanx)<=(spanx>>3);
    wire stable_y=(miny>old_y0?miny-old_y0:old_y0-miny)<=2 &&
        (maxy>old_y1?maxy-old_y1:old_y1-maxy)<=2;
    wire quarter_ok=q1_span>=(spanx-(spanx>>2)) && q3_span>=(spanx-(spanx>>2)) &&
        q1_span<=(spanx-(spanx>>4)) && q3_span<=(spanx-(spanx>>4)) &&
        (q1_span>q3_span?q1_span-q3_span:q3_span-q1_span)<=(spanx>>3);
    // Computed below ROI, long before SOF. One small product, no pixel critical path.
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin envelope<=0;bbox_area<=0;tip_span<=2047;q1_span<=0;q3_span<=0;shape_ok<=0;end
        else if(user)begin envelope<=0;tip_span<=2047;q1_span<=0;q3_span<=0;shape_ok<=0;end
        else if(SHAPE_ENABLE && valid)begin
            if(px==WIDTH-4 && py>=Y0 && py<Y1 && next_count>=MIN_ROW)begin
                envelope<=envelope+rspan;
                if(rspan<tip_span)tip_span<=rspan;
                if(py+1>=q1y && py<=q1y+1 && rspan>q1_span)q1_span<=rspan;
                if(py+1>=q3y && py<=q3y+1 && rspan>q3_span)q3_span<=rspan;
            end
            if(py==Y1 && px==0)bbox_area<=spanx*spany;
            if(py==Y1 && px==4)shape_ok<=near_square && stable_y && quarter_ok &&
                tip_span<spanx-(spanx>>2) && envelope>=(bbox_area>>1)+(bbox_area>>3) &&
                envelope<=(bbox_area>>1)+(bbox_area>>2)+(bbox_area>>3);
        end
    end
    wire geometry=last'''),
 ('result_valid<=0;present<=0;', 'round_present<=0;result_valid<=0;present<=0;'),
 ('result_valid<=complete;present<=complete && object_ok;', 'round_present<=SHAPE_ENABLE && complete && object_ok && shape_ok;\n            result_valid<=complete;present<=complete && object_ok;')])

edit('isp/color_compare_osd.v',[
 ('INSPECTION_V4=0,COMPACT_FONT=0,','INSPECTION_V4=0,COMPACT_FONT=0,INSPECTION_V5=0,'),
 ('input [43:0] dim_sizes,', 'input dim_round,background_applied,input[2:0]background_status,input [43:0] dim_sizes,'),
 ('reg held_dim_valid,held_present;', 'reg held_dim_valid,held_present,held_round,held_background;reg[2:0]held_bg_status;'),
 ('show_color<=0;', 'held_round<=0;held_background<=0;held_bg_status<=0;show_color<=0;'),
 ('show_color<=display_enable', 'held_round<=dim_round;held_background<=background_applied;held_bg_status<=background_status;\n            show_color<=display_enable'),
 ('1:pixel_span=held_sizes[32:22];', '1:pixel_span=INSPECTION_V5 && held_round?held_sizes[43:33]:held_sizes[32:22];'),
 ('axis_span=(field==1 || field==3)?held_span_y:held_span_x;', 'axis_span=((field==1 && !(INSPECTION_V5 && held_round)) || field==3)?held_span_y:held_span_x;'),
 ('if(field<4)number=held_calibrated ? pixel_span*20\'d1000+(axis_span>>1) : pixel_span*20\'d10;', 'if(field<4)begin\n                number=held_calibrated ? pixel_span*20\'d1000 : pixel_span*20\'d10;\n                if(INSPECTION_V5 && held_round && field==1)number=number>>1;\n                if(held_calibrated)number=number+(axis_span>>1);\n            end'),
 ('.AREA_ENABLE(INSPECTION_V4)) u_drawing', '.AREA_ENABLE(INSPECTION_V4),.SHAPE_ENABLE(INSPECTION_V5)) u_drawing'),
 ('.x(px),.y(py),.cal(held_cal)', '.round_object(held_round),.background_applied(held_background),.background_status(held_bg_status),.x(px),.y(py),.cal(held_cal)')])
edit('isp/engineering_dimension_marks.v',[
 ('parameter SEARCH_ENABLE=0,AREA_ENABLE=0)', 'parameter SEARCH_ENABLE=0,AREA_ENABLE=0,SHAPE_ENABLE=0)'),
 ('input cal,calibrated,', 'input round_object,background_applied,input[2:0]background_status,\n    input cal,calibrated,'),
 ('reg [10:0] tx,ty,q;', 'wire[10:0] midx=({1\'b0,xmin}+{1\'b0,xmax})>>1,midy=({1\'b0,ymin}+{1\'b0,ymax})>>1;\n    wire round_mode=SHAPE_ENABLE && round_object;\n    reg [10:0] tx,ty,q;'),
 ('marks[3-k]=line_ink;','''if(round_mode)begin
                    // D above, R along the actual center-to-circumference radius.
                    line_ink=(y==ymin-8 && q>=xmin && q<=xmax) ||
                        ((q==xmin || q==xmax) && y>=ymin-12 && y<=ymin-2) ||
                        (y==midy && q>=midx && q<=xmax) ||
                        (q==midx && y+3>=midy && y<=midy+3) ||
                        ((y+1==midy || y==midy+1) && q+2==xmax) ||
                        ((y+2==midy || y==midy+2) && q+4==xmax);
                end
                marks[3-k]=line_ink;'''),
 ('0:character=field==0?"W":field==1?"H":field==2?"X":"Y";', '0:character=field==0?(round_mode?"D":"W"):field==1?(round_mode?"R":"H"):field==2?"X":"Y";'),
 ('\n    end\nendmodule', '''
        if(SHAPE_ENABLE && !cal && x>=256 && x<1024 && y>=560 && y<576)begin
            text_valid=1;glyph_col=x[3:0];glyph_row=y-560;
            case((x-256)>>4)
                0:character="B";1:character="G";2:character=":";
                3:character=background_status==3?"O":background_status==0?"N":background_status==4?"F":"W";
                4:character=background_status==3?"K":background_status==0?"E":background_status==4?"A":"A";
                5:character=background_status==0?"E":background_status==4?"I":background_status==3?" ":"I";
                6:character=background_status==0?"D":background_status==4?"L":background_status==3?" ":"T";
                8:character="K";9:character="4";11:character="E";12:character="M";13:character="P";14:character="T";15:character="Y";
                17:character=background_applied?"A":"C";18:character=background_applied?"U":"U";19:character=background_applied?"T":"T";
                20:character=background_applied?"O":" ";21:character=background_applied?"1":" ";22:character=background_applied?"2":" ";
                default:character=" ";
            endcase
        end
    end
endmodule''')])

p=R/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display.al'
s=p.read_text();idx=s.index('  </Files>') if '  </Files>' in s else -1
# Clone previous native FileInfo entry and use the next order.
import re
entry=re.search(r'\s*<File Path="[^\"]*inspection_font_rom.v"[\s\S]*?</File>',s).group()
new=entry.replace('inspection_font_rom.v','measure_background.v').replace('180','181')
s=s.replace(entry,entry+new);p.write_text(s)
