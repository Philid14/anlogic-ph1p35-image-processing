// Single thin silhouette inside a fixed rectangular working region.
// Uses every source pixel; 3-pixel horizontal runs, >=8 qualified pixels/row
// reject isolated specks. Coordinates never derive from the half-width Edge.
// GAPX/GAPY are center cross-section gaps, not automatic circle fitting.
module planar_measure_stats #(
    parameter WIDTH=1280,HEIGHT=720,X0=256,X1=1024,Y0=160,Y1=544,
    parameter CX=(X0+X1)/2,CY=(Y0+Y1)/2,
    parameter SHAPE_ENABLE=0,COMPACT_COUNT=0,PARTS_ENABLE=0,MIN_ROW=8,MIN_ROWS=3,MIN_AREA=64
)(input clk,rst_n,input [3:0] binary_pixels,input valid,user,last,
  input bright,input [7:0] threshold,
  output reg round_present,output reg result_valid,present,output reg [1:0] gap_valid,
  output reg [43:0] sizes,box_coords,output reg [43:0] gap_coords,output reg [15:0] sample_id,
  output reg [7:0] result_threshold,output reg result_bright,
  output part_valid,output [33:0] part_coords);
    reg[10:0] x,y;wire[10:0] px=user?0:x,py=user?0:y;
    reg armed,bad,finished;reg[15:0] seq;
    reg polarity;reg[7:0] cut;
    localparam SMALL_COUNT=SHAPE_ENABLE||COMPACT_COUNT;
    localparam COUNT_W=SMALL_COUNT?7:11,AREA_W=SMALL_COUNT?7:20;
    localparam ROWS_W=SMALL_COUNT?((MIN_ROWS<1)?1:$clog2(MIN_ROWS+1)):11;
    reg[10:0] minx,maxx,miny,maxy,row_min,row_max;reg[ROWS_W-1:0]rows;
    reg[COUNT_W-1:0]row_count;
    reg[AREA_W-1:0] area;
    reg[1:0] run_h,run_v;
    reg[10:0] hx_left,hx_right,vy_top,vy_bottom;
    reg hx_lfound,hx_rfound,vy_tfound,vy_bfound,hcenter,vcenter;
    reg[10:0] next_min,next_max;reg[COUNT_W-1:0]next_count;
    reg[1:0] next_run;reg[3:0]increment;reg[7:0]count_sum;
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
        fg=0;q=0;start=0;increment=0;count_sum=0;
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
                            next_max=q;if(SMALL_COUNT)increment=increment+4'd3;else next_count=next_count+3;
                        end
                    end else begin next_max=q;if(SMALL_COUNT)increment=increment+4'd1;else next_count=next_count+1'b1;end
                    if(py==CY && next_run==3)begin
                        if(q<CX)begin next_hleft=q;next_hlf=1;end
                        if(q>=CX && !next_hrf)begin
                            next_hright=q-2;next_hrf=1;
                        end
                    end
                end else next_run=0;
            end else next_run=0;
        end
        if(SMALL_COUNT)begin
            count_sum={1'b0,row_count[6:0]}+increment;
            next_count=count_sum>=8'd64 ? 7'd64 : count_sum[6:0];
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
    generate if(PARTS_ENABLE)begin:g_parts
        planar_two_band_profile u_profile(.clk(clk),.rst_n(rst_n),.sof(user),
            .row_end(valid && !user && px==WIDTH-4 && py>=Y0 && py<Y1),
            .row_good(next_count>=MIN_ROW),.left_x(next_min),.right_x(next_max),.row_y(py),
            .commit(complete && object_ok),.box_coords({minx,maxx,miny,maxy}),
            .result_valid(part_valid),.coords(part_coords));
    end else begin:g_no_parts assign part_valid=0;assign part_coords=0;end endgenerate
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
                    if(py<miny)miny<=py;maxy<=py;if(!SMALL_COUNT || rows<MIN_ROWS)rows<=rows+1'b1;
                    if(SMALL_COUNT)area<=small_area>=64?7'd64:small_area[6:0];else area<=area+next_count;
                end
                row_min<=2047;row_max<=0;row_count<=0;run_h<=0;
            end
        end else if(last)bad<=1;
    end
endmodule

// Single orthogonal silhouette with exactly two stable, nested row envelopes.
// Coordinates quantized to 4px; a one-bucket tolerance handles raster jitter.
// Reject taper, third band, row holes, short bands and incomplete frames.
// This is a constrained T/L profile, not general contour/CAD reconstruction.
module planar_two_band_profile(
 input clk,rst_n,sof,row_end,row_good,commit,
 input[10:0]left_x,right_x,row_y,input[43:0]box_coords,
 output reg result_valid,output reg[33:0]coords);
 reg[1:0]state;reg ended,first_tall;reg[2:0]band_rows;
 reg[8:0]al,ar,bl,br;
 reg[10:0]split;
 wire[8:0]l=left_x[10:2],r=right_x[10:2];
 wire[8:0]ref_l=state==1?al:bl,ref_r=state==1?ar:br;
 // Modulo deltas of -1/0/+1 share one subtractor per endpoint. Valid ROI
 // buckets are far from the 0/511 wrap boundary, so no false wrap admission.
 wire[8:0]dl=l-ref_l,dr=r-ref_r;
 wire same_band=(dl==0 || dl==1 || dl==9'h1ff) && (dr==0 || dr==1 || dr==9'h1ff);
 wire[8:0]aw=ar-al,bw=br-bl;
 wire a_wide={1'b0,al}<={1'b0,bl}+10'd1 && {1'b0,ar}+10'd1>={1'b0,br} && {1'b0,aw}>={1'b0,bw}+10'd3;
 wire b_wide={1'b0,bl}<={1'b0,al}+10'd1 && {1'b0,br}+10'd1>={1'b0,ar} && {1'b0,bw}>={1'b0,aw}+10'd3;
 wire[10:0]xmin=box_coords[43:33],xmax=box_coords[32:22];
 wire[10:0]ymin=box_coords[21:11],ymax=box_coords[10:0];
 wire[10:0]nl={a_wide?bl:al,2'b00},nr={a_wide?br:ar,2'b11};
 // Each chosen interval came from a qualified row included in the envelope:
 // its 4px bucket cannot lie outside the envelope's bucket. Clamp only the
 // two low bits; this is identical to the full-width clamp for valid results.
 wire[1:0]low_l=nl[10:2]==xmin[10:2]?xmin[1:0]:2'b00;
 wire[1:0]low_r=nr[10:2]==xmax[10:2]?xmax[1:0]:2'b11;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=0;ended<=0;first_tall<=0;band_rows<=0;al<=0;ar<=0;bl<=0;br<=0;split<=0;result_valid<=0;coords<=0;end
  else if(sof)begin
   result_valid<=commit && state==2 && (a_wide || b_wide) && first_tall && band_rows==6;
   coords<={a_wide,nl[10:2],low_l,nr[10:2],low_r,split};
   state<=0;ended<=0;first_tall<=0;band_rows<=0;
  end else if(row_end)begin

   if(row_good)begin
    if(state==0)begin state<=1;al<=l;ar<=r;band_rows<=1;end
    else if(ended)state<=3;
    else if(state==1 && !same_band)begin state<=2;bl<=l;br<=r;split<=row_y;first_tall<=band_rows==6;band_rows<=1;end
    else if(state==2 && !same_band)state<=3;
    else if(band_rows<6)band_rows<=band_rows+1'b1;
   end else if(state!=0)ended<=1;
  end
 end
endmodule
