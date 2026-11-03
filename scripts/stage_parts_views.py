"""Resource-bounded display revision; preserve the all-at-once checkpoint."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
HDL=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source'
OUT=ROOT/'tmp/inspection_parts_motion/staging/isp'
BASE='6ad4f7cd70b5614240c07db2a16775aa492d9f14'
def base(name):return subprocess.check_output(['git','show',BASE+':'+(HDL/'isp'/name).relative_to(ROOT).as_posix()],cwd=ROOT).decode()
def main():
 assert not OUT.exists();OUT.mkdir(parents=True)
 s=base('engineering_dimension_marks.v')
 s=s.replace('AREA_ENABLE=0,SHAPE_ENABLE=0)','AREA_ENABLE=0,SHAPE_ENABLE=0,VIEW_ENABLE=0)')
 s=s.replace('input [79:0] digits,','input [79:0] digits,input[2:0]view_kind,')
 s=s.replace('    reg [10:0] tx,ty,q;', '''    wire[7:0]label_x=VIEW_ENABLE && view_kind==1?"S":VIEW_ENABLE && view_kind==3?"A":VIEW_ENABLE && view_kind==4?"B":"W";
    wire[7:0]label_y=VIEW_ENABLE && view_kind==1?"V":VIEW_ENABLE && view_kind!=0?"T":"H";
    reg [10:0] tx,ty,q;''')
 s=s.replace('(round_mode?"D":"W")','(round_mode?"D":label_x)').replace('(round_mode?"R":"H")','(round_mode?"R":label_y)')
 s=s.replace('35:character=round_mode?"R":"H";', '''35:character=round_mode?"R":"H";
                37:character=VIEW_ENABLE && view_kind!=0?"V":" ";
                38:character=VIEW_ENABLE && view_kind!=0?"I":" ";
                39:character=VIEW_ENABLE && view_kind!=0?"E":" ";
                40:character=VIEW_ENABLE && view_kind!=0?"W":" ";
                41:character=VIEW_ENABLE && view_kind!=0?":":" ";
                42:character=VIEW_ENABLE && view_kind!=0?label_x:" ";
                43:character=VIEW_ENABLE && view_kind!=0?"/":" ";
                44:character=VIEW_ENABLE && view_kind!=0?label_y:" ";''')
 (OUT/'engineering_dimension_marks.v').write_text(s)
 s=base('color_compare_osd.v')
 s=s.replace('INSPECTION_V5=0,','INSPECTION_V5=0,VIEW_ENABLE=0,',1)
 s=s.replace('input [15:0] dim_id,','input [15:0] dim_id,input[2:0]view_kind,')
 s=s.replace('    wire dimension=','    reg[2:0]held_view;\n    wire dimension=',1)
 s=s.replace('            held_round<=0;','            held_view<=0;held_round<=0;',1)
 s=s.replace('            held_round<=dim_round;','            held_view<=VIEW_ENABLE?view_kind:3\'d0;held_round<=dim_round;',1)
 s=s.replace('.SHAPE_ENABLE(INSPECTION_V5)) u_drawing','.SHAPE_ENABLE(INSPECTION_V5),.VIEW_ENABLE(VIEW_ENABLE)) u_drawing')
 s=s.replace('.digits({digits[0],digits[1],digits[2],digits[3]})','.view_kind(held_view),.digits({digits[0],digits[1],digits[2],digits[3]})')
 (OUT/'color_compare_osd.v').write_text(s)
 s=subprocess.check_output(['git','show','7c32412:'+ (HDL/'isp/edge_control_stream.v').relative_to(ROOT).as_posix()],cwd=ROOT).decode()
 marker='        color_compare_osd #('
 i=s.index(marker)
 s=s[:i]+'''        wire[43:0]view_sizes,view_box,view_gap_coords;wire[1:0]view_gap;wire[2:0]view_kind;
        parts_measure_view u_part_view(.enabled(INSPECTION_V5 && dim_part_valid && !dim_round && dim_valid && dim_present),
            .sample_id(dim_id),.sizes(dim_sizes),.box_coords(dim_box),.gap_coords(dim_gap_coords),.gap_valid(dim_gap),
            .part_coords(dim_part_coords),.view_sizes(view_sizes),.view_box(view_box),.view_gap_coords(view_gap_coords),.view_gap(view_gap),.kind(view_kind));
'''+s[i:]
 s=s.replace('.PARTS_ENABLE(INSPECTION_V5),\n            .REF_X','.VIEW_ENABLE(INSPECTION_V5),\n            .REF_X')
 s=s.replace('.dim_sizes(dim_sizes),.dim_box(dim_box),.dim_gap_coords(dim_gap_coords)','.dim_sizes(view_sizes),.dim_box(view_box),.dim_gap_coords(view_gap_coords)')
 s=s.replace('.dim_part_valid(dim_part_valid),.dim_part_coords(dim_part_coords),','.view_kind(view_kind),')
 s=s.replace('.dim_present(dim_present),.dim_gap_valid(dim_gap)','.dim_present(dim_present),.dim_gap_valid(view_gap)')
 s+='''
// Display one genuine measured rectangle at a time; 32 acquisition-frame
// dwell, unaffected by repeated HDMI refreshes. Phases5..7 retain whole W/H.
// Derived rectangle dimensions share the ORIGINAL 4-field formatter/drawing.
module parts_measure_view(input enabled,input[15:0]sample_id,
 input[43:0]sizes,box_coords,gap_coords,input[1:0]gap_valid,input[33:0]part_coords,
 output reg[43:0]view_sizes,view_box,view_gap_coords,output reg[1:0]view_gap,output reg[2:0]kind);
 wire[10:0]xl=box_coords[43:33],xr=box_coords[32:22],yt=box_coords[21:11],yb=box_coords[10:0];
 wire[10:0]nl=part_coords[32:22],nr=part_coords[21:11],split=part_coords[10:0];
 wire[10:0]bar_top=part_coords[33]?yt:split,bar_bottom=part_coords[33]?split-11'd1:yb;
 reg[10:0]a,b,c,d;
 always @*begin
  a=xl;b=xr;c=yt;d=yb;kind=0;
  view_sizes=sizes;view_box=box_coords;view_gap_coords=gap_coords;view_gap=gap_valid;
  if(enabled)begin
   case(sample_id[7:5])
    1:begin kind=1;a=nl;b=nr;c=part_coords[33]?split:yt;d=part_coords[33]?yb:split-11'd1;end
    2:begin kind=2;c=bar_top;d=bar_bottom;end
    3:begin kind=nl>xl?3:2;b=nl>xl?nl-11'd1:xr;c=bar_top;d=bar_bottom;end
    4:begin kind=nr<xr?4:2;a=nr<xr?nr+11'd1:xl;c=bar_top;d=bar_bottom;end
   endcase
   if(kind!=0)begin view_box={a,b,c,d};view_sizes={b-a+11'd1,d-c+11'd1,22'd0};view_gap_coords=0;view_gap=0;end
  end
 end
endmodule
'''
 (OUT/'edge_control_stream.v').write_text(s)
 print('Prepared three staged view-only adapters; formal RTL remains unchanged')
if __name__=='__main__':main()
