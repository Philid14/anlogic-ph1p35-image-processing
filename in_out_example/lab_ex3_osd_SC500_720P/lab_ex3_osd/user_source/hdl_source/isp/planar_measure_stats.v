// Single thin silhouette inside a fixed rectangular working region.
// Uses every source pixel; 3-pixel horizontal runs, >=8 qualified pixels/row
// reject isolated specks. Coordinates never derive from the half-width Edge.
// GAPX/GAPY are center cross-section gaps, not automatic circle fitting.
module planar_measure_stats #(
    parameter WIDTH=1280,HEIGHT=720,X0=256,X1=1024,Y0=160,Y1=544,
    parameter CX=(X0+X1)/2,CY=(Y0+Y1)/2,
    parameter SHAPE_ENABLE=0,COMPACT_COUNT=0,MIN_ROW=8,MIN_ROWS=3,MIN_AREA=64
)(input clk,rst_n,input [3:0] binary_pixels,input valid,user,last,
  input bright,input [7:0] threshold,
  output reg round_present,output reg result_valid,present,output reg [1:0] gap_valid,
  output reg [43:0] sizes,box_coords,output reg [43:0] gap_coords,output reg [15:0] sample_id,
  output reg [7:0] result_threshold,output reg result_bright);
    reg[10:0] x,y;wire[10:0] px=user?0:x,py=user?0:y;
    reg armed,bad,finished;reg[15:0] seq;
    reg polarity;reg[7:0] cut;
    localparam SMALL_COUNT=SHAPE_ENABLE||COMPACT_COUNT;
    localparam COUNT_W=SMALL_COUNT?7:11,AREA_W=SMALL_COUNT?7:20;
    reg[10:0] minx,maxx,miny,maxy,row_min,row_max,rows;
    reg[COUNT_W-1:0]row_count;
    reg[AREA_W-1:0] area;
    reg[1:0] run_h,run_v;
    reg[10:0] hx_left,hx_right,vy_top,vy_bottom;
    reg hx_lfound,hx_rfound,vy_tfound,vy_bfound,hcenter,vcenter;
    reg[10:0] next_min,next_max;reg[COUNT_W-1:0]next_count;
    reg[1:0] next_run;
    reg[10:0] next_hleft,next_hright,next_vtop,next_vbottom;
    reg next_hlf,next_hrf,next_vtf,next_vbf,next_hcenter,next_vcenter;
    reg[1:0] next_vrun;
    reg fg;reg[10:0] q,start;
    integer k;
    always @*begin
        next_min=row_min;next_max=row_max;next_count=row_count;next_run=run_h;
        next_hleft=hx_left;next_hright=hx_right;next_hlf=hx_lfound;next_hrf=hx_rfound;
        next_vtop=vy_top;next_vbottom=vy_bottom;next_vtf=vy_tfound;next_vbf=vy_bfound;
        next_hcenter=hcenter;next_vcenter=vcenter;next_vrun=run_v;
        fg=0;q=0;start=0;
        for(k=0;k<4;k=k+1)begin
            q=px+k;
            fg=polarity?binary_pixels[3-k]:!binary_pixels[3-k];
            if(q>=X0 && q<X1 && py>=Y0 && py<Y1)begin
                if(py==CY && q>=CX-1 && q<=CX+1 && fg)next_hcenter=1;
                if(q==CX)begin
                    if(py>=CY-1 && py<=CY+1 && fg)next_vcenter=1;
                    if(fg)begin
                        if(next_vrun<3)next_vrun=next_vrun+1'b1;
                        if(next_vrun==3)begin
                            if(py<CY)begin next_vtop=py;next_vtf=1;end
                            if(py>=CY && !next_vbf)begin
                                next_vbottom=py-2;next_vbf=1;
                            end
                        end
                    end else next_vrun=0;
                end
                if(fg)begin
                    if(next_run<3)begin
                        next_run=next_run+1'b1;
                        if(next_run==3)begin
                            start=q-2;
                            if(start<next_min)next_min=start;
                            next_max=q;if(!SMALL_COUNT || next_count<64)next_count=next_count+3;
                        end
                    end else begin next_max=q;if(!SMALL_COUNT || next_count<64)next_count=next_count+1'b1;end
                    if(py==CY && next_run==3)begin
                        if(q<CX)begin next_hleft=q;next_hlf=1;end
                        if(q>=CX && !next_hrf)begin
                            next_hright=q-2;next_hrf=1;
                        end
                    end
                end else next_run=0;
            end else next_run=0;
        end
    end
    // Envelope area fills internal holes/highlights, but not a missing silhouette.
    wire[10:0] spanx=maxx-minx+11'd1,spany=maxy-miny+11'd1;
    wire[10:0] rspan=next_max-next_min+11'd1;
    reg[19:0] envelope;reg[21:0] bbox_area;
    reg[10:0] center_min,center_max;
    wire[10:0] row_center=({1'b0,next_min}+{1'b0,next_max})>>1;
    reg shape_ok;
    wire near_square=spanx>=24 && spany>=24 &&
        (spanx>spany?spanx-spany:spany-spanx)<=(spanx>>3);
    // Computed below ROI, long before SOF. One small product, no pixel critical path.
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin envelope<=0;bbox_area<=0;center_min<=2047;center_max<=0;shape_ok<=0;end
        else if(user)begin envelope<=0;center_min<=2047;center_max<=0;shape_ok<=0;end
        else if(SHAPE_ENABLE && valid)begin
            if(px==WIDTH-4 && py>=Y0 && py<Y1 && next_count>=MIN_ROW)begin
                envelope<=envelope+rspan;
                if(row_center<center_min)center_min<=row_center;
                if(row_center>center_max)center_max<=row_center;
            end
            if(py==Y1 && px==0)bbox_area<=spanx*spany;
            if(py==Y1 && px==4)shape_ok<=near_square && center_max-center_min<=(spanx>>3) &&
                envelope>=(bbox_area>>1)+(bbox_area>>3) &&
                envelope<=(bbox_area>>1)+(bbox_area>>2)+(bbox_area>>3);
        end
    end
    wire[7:0]small_area={1'b0,area[6:0]}+{1'b0,next_count[6:0]};
    wire geometry=last!=(px==WIDTH-4);
    // Raster counters advance only on valid. Correct EOL geometry and one
    // finished raster, with no later beats, prove the exact frame size.
    wire complete=armed && finished && !bad;
    wire object_ok=rows>=MIN_ROWS && area>=MIN_AREA && maxx>=minx && maxy>=miny &&
        minx>X0 && maxx<X1-1 && miny>Y0 && maxy<Y1-1;
    wire gapx_ok=hx_lfound && hx_rfound && !hcenter && hx_right>hx_left+1;
    wire gapy_ok=vy_tfound && vy_bfound && !vcenter && vy_bottom>vy_top+1;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            x<=0;y<=0;armed<=0;bad<=0;finished<=0;seq<=0;
            polarity<=0;cut<=0;minx<=2047;maxx<=0;miny<=2047;maxy<=0;
            row_min<=2047;row_max<=0;row_count<=0;rows<=0;area<=0;run_h<=0;run_v<=0;
            hx_left<=0;hx_right<=0;vy_top<=0;vy_bottom<=0;
            hx_lfound<=0;hx_rfound<=0;vy_tfound<=0;vy_bfound<=0;hcenter<=0;vcenter<=0;
            round_present<=0;result_valid<=0;present<=0;gap_valid<=0;sizes<=0;box_coords<=0;gap_coords<=0;sample_id<=0;result_threshold<=0;result_bright<=0;
        end else if(user)begin
            round_present<=SHAPE_ENABLE && complete && object_ok && shape_ok;
            result_valid<=complete;present<=complete && object_ok;
            gap_valid<={complete && object_ok && gapx_ok,complete && object_ok && gapy_ok};
            sizes<={maxx-minx+11'd1,maxy-miny+11'd1,
                gapx_ok?(hx_right-hx_left-11'd1):11'd0,
                gapy_ok?(vy_bottom-vy_top-11'd1):11'd0};
            gap_coords<={hx_left+11'd1,hx_right-11'd1,vy_top+11'd1,vy_bottom-11'd1};
            box_coords<={minx,maxx,miny,maxy};sample_id<=seq;seq<=seq+1'b1;
            result_threshold<=cut;result_bright<=polarity;
            // Production ROI starts well after the first beat, so no ROI
            // contribution is discarded when SOF coincides with valid.
            x<=valid?4:0;y<=0;armed<=1;finished<=0;bad<=valid && geometry;
            polarity<=bright;cut<=threshold;
            minx<=2047;maxx<=0;miny<=2047;maxy<=0;row_min<=2047;row_max<=0;row_count<=0;
            rows<=0;area<=0;run_h<=0;run_v<=0;
            hx_left<=0;hx_right<=0;vy_top<=0;vy_bottom<=0;
            hx_lfound<=0;hx_rfound<=0;vy_tfound<=0;vy_bfound<=0;hcenter<=0;vcenter<=0;
        end else if(valid)begin
            if(!armed || finished || geometry)bad<=1;
            x<=px==WIDTH-4?0:px+4;
            if(px==WIDTH-4)begin y<=py+1'b1;if(py==HEIGHT-1)finished<=1;end
            row_min<=next_min;row_max<=next_max;row_count<=next_count;run_h<=next_run;
            hx_left<=next_hleft;hx_right<=next_hright;hx_lfound<=next_hlf;hx_rfound<=next_hrf;
            vy_top<=next_vtop;vy_bottom<=next_vbottom;vy_tfound<=next_vtf;vy_bfound<=next_vbf;
            hcenter<=next_hcenter;vcenter<=next_vcenter;run_v<=next_vrun;
            if(px==WIDTH-4)begin
                if(next_count>=MIN_ROW && py>=Y0 && py<Y1)begin
                    if(next_min<minx)minx<=next_min;if(next_max>maxx)maxx<=next_max;
                    if(py<miny)miny<=py;maxy<=py;rows<=rows+1'b1;
                    if(SMALL_COUNT)area<=small_area>=64?7'd64:small_area[6:0];else area<=area+next_count;
                end
                row_min<=2047;row_max<=0;row_count<=0;run_h<=0;
            end
        end else if(last)bad<=1;
    end
endmodule
