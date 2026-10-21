`timescale 1ns / 1ps
// Capture and display replay are separate test phases. No frame RAM is added
// to the product. Display queries happen after results/text have settled.
module tb_color_target_replay;
    parameter integer WIDTH=64, HEIGHT=48, FILTER_ENABLE=0;
    parameter integer TARGET_CLASS=0, HUE_HALF_WIDTH_DEG=30, C_MIN=24, V_MIN=32, MIN_COUNT=4;
    parameter integer ACQ_FRAMES=2, LOST_FRAMES=2, MAX_JUMP=0;
    reg clk=0;
    always #10 clk=~clk;
    reg rst_n=0, valid=0, sof=0, eol=0, eof=0, abort_f=0, probe=0;
    reg [95:0] data=0;
    reg [10:0] x=0, dx=0, glyph_x=0;
    reg [9:0] y=0, dy=0, glyph_y=0;
    reg [31:0] sid=0, fid=0;
    wire rr, rv, present, error;
    wire [1:0] cls;
    wire [19:0] count;
    wire [10:0] xmin,xmax,cx;
    wire [9:0] ymin,ymax,cy;
    wire [31:0] rs,rf;
    wire lr,lv,lp;
    wire [1:0] lc;
    wire [19:0] ln;
    wire [10:0] lx0,lx1,lcx;
    wire [9:0] ly0,ly1,lcy;
    wire [31:0] ls,lf;
    generate if(FILTER_ENABLE==0) begin : g_legacy
        color_target_detect #(.TARGET_CLASS(TARGET_CLASS),.HUE_HALF_WIDTH_DEG(HUE_HALF_WIDTH_DEG),
            .C_MIN(C_MIN),.V_MIN(V_MIN),.MIN_COUNT(MIN_COUNT)) legacy (
            .clk(clk),.rst_n(rst_n),.I_pixel_valid(valid),.I_data(data),.I_x0(x),.I_y(y),
            .I_sof(sof),.I_eol(eol),.I_eof(eof),.I_session_id(sid),.I_frame_id(fid),.I_frame_abort(abort_f),
            .O_res_session_id(ls),.O_res_frame_id(lf),.O_result_valid(lv),.O_target_present(lp),
            .O_color_class(lc),.O_pixel_count(ln),.O_xmin(lx0),.O_xmax(lx1),.O_center_x(lcx),
            .O_ymin(ly0),.O_ymax(ly1),.O_center_y(lcy),.O_result_ready(lr));
    end else begin : g_no_legacy
        assign lr=0;
    end endgenerate
    color_target_detect_stream #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.FILTER_ENABLE(FILTER_ENABLE),
        .TARGET_CLASS(TARGET_CLASS),.HUE_HALF_WIDTH_DEG(HUE_HALF_WIDTH_DEG),
        .C_MIN(C_MIN),.V_MIN(V_MIN),.MIN_COUNT(MIN_COUNT)) dut (
        .clk(clk),.rst_n(rst_n),.I_pixel_valid(valid),.I_data(data),.I_x0(x),.I_y(y),
        .I_sof(sof),.I_eol(eol),.I_eof(eof),.I_session_id(sid),.I_frame_id(fid),
        .I_frame_abort(abort_f),.O_res_session_id(rs),.O_res_frame_id(rf),
        .O_result_valid(rv),.O_target_present(present),.O_color_class(cls),.O_pixel_count(count),
        .O_xmin(xmin),.O_xmax(xmax),.O_center_x(cx),.O_ymin(ymin),.O_ymax(ymax),.O_center_y(cy),
        .O_result_ready(rr),.O_protocol_error(error));
    wire [1:0] state;
    wire show, change;
    wire [19:0] tc;
    wire [10:0] txmin,txmax,tcx;
    wire [9:0] tymin,tymax,tcy;
    wire [31:0] ts,tf;
    color_target_track #(.ACQ_FRAMES(ACQ_FRAMES),.LOST_FRAMES(LOST_FRAMES),.MAX_JUMP(MAX_JUMP)) track (
        .clk(clk),.rst_n(rst_n),.I_result_strobe(rr),.I_result_valid(rv),.I_target_present(present),
        .I_pixel_count(count),.I_xmin(xmin),.I_xmax(xmax),.I_center_x(cx),
        .I_ymin(ymin),.I_ymax(ymax),.I_center_y(cy),.I_session_id(rs),.I_frame_id(rf),
        .O_track_state(state),.O_show(show),.O_out_count(tc),.O_out_xmin(txmin),.O_out_xmax(txmax),
        .O_out_center_x(tcx),.O_out_ymin(tymin),.O_out_ymax(tymax),.O_out_center_y(tcy),
        .O_out_session_id(ts),.O_out_frame_id(tf),.O_state_change(change));
    reg rr_d=0, consumed=0;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin rr_d<=0; consumed<=0; end
        else begin rr_d<=rr; consumed<=rr; end
    end
    wire ov;
    wire [23:0] orgb;
    color_target_overlay #(.BOX_THICK(1),.CROSS_ARM(3)) box (
        .I_pixel_valid(probe),.I_x(dx),.I_y(dy),.I_result_valid(show),.I_target_present(show),
        .I_xmin(txmin),.I_xmax(txmax),.I_ymin(tymin),.I_ymax(tymax),.I_center_x(tcx),.I_center_y(tcy),
        .O_overlay_valid(ov),.O_overlay_rgb(orgb));
    wire tov;
    wire [23:0] trgb;
    wire [7:0] ch;
    wire [3:0] grow;
    wire [15:0] gbits;
    ct_text_font font (.I_char(ch),.I_row(grow),.O_row_bits(gbits));
    color_target_text_overlay text (
        .clk(clk),.rst_n(rst_n),.I_pixel_valid(1'b1),.I_x(glyph_x),.I_y(glyph_y),
        .I_update(rr_d),.I_show(show),.I_state(state),.I_count(tc),.I_center_x(tcx),.I_center_y(tcy),
        .O_glyph_char(ch),.O_glyph_row(grow),.I_glyph_bits(gbits),.O_overlay_valid(tov),.O_overlay_rgb(trgb));
    integer fin,fout,rc,n=0,k;
    reg [2047:0] spath,opath;
    reg ri,vi,si,li,ei,ai,pi;
    reg [95:0] di;
    reg [31:0] xi,yi,ssi,ffi,pxi,pyi;
    reg [111:0] line0,line1;
    reg pixel_text_on;
    reg [23:0] pixel_text_rgb;
    initial begin
        if(!$value$plusargs("STIM=%s",spath) || !$value$plusargs("OUT=%s",opath)) begin
            $display("FAIL missing path"); $finish; end
        fin=$fopen(spath,"r"); fout=$fopen(opath,"w");
        if(fin==0 || fout==0) begin $display("FAIL open files"); $finish; end
        repeat(3) @(negedge clk);
        while(!$feof(fin)) begin
            rc=$fscanf(fin,"%d %d %h %d %d %d %d %d %d %d %d %d %d %d\n",
                       ri,vi,di,xi,yi,si,li,ei,ssi,ffi,ai,pi,pxi,pyi);
            if(rc==14) begin
                @(negedge clk);
                rst_n=ri; valid=vi; data=di; x=xi; y=yi; sof=si; eol=li; eof=ei;
                sid=ssi; fid=ffi; abort_f=ai; probe=pi; dx=pxi; dy=pyi;
                @(posedge clk); #1;
                if(!rst_n && (rr!==0 || show!==0 || state!==0 || error!==0)) begin
                    $display("FAIL reset"); $finish; end
                if(rr) $fwrite(fout,"R %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d\n",
                    n,rs,rf,rv,present,cls,count,xmin,xmax,ymin,ymax,cx,cy,error);
                if(lr) $fwrite(fout,"L %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d\n",
                    n,ls,lf,lv,lp,lc,ln,lx0,lx1,ly0,ly1,lcx,lcy);
                if(consumed) $fwrite(fout,"T %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d\n",
                    n,ts,tf,state,show,tc,txmin,txmax,tymin,tymax,tcx,tcy,change);
                if(probe) begin
                    glyph_x=dx; glyph_y=dy; #0.01;
                    pixel_text_on=tov; pixel_text_rgb=trgb;
                    line0=0; line1=0;
                    for(k=0;k<28;k=k+1) begin
                        glyph_x=16+(k%14)*16; glyph_y=(k<14) ? 600 : 618;
                        #0.01;
                        if(!tov || grow!=0) begin $display("FAIL glyph probe"); $finish; end
                        if(k<14) line0={line0[103:0],ch}; else line1={line1[103:0],ch};
                    end
                    $fwrite(fout,"P %0d %0d %0d %0d %06h %0d %06h %028h %028h\n",
                        n,dx,dy,ov,orgb,pixel_text_on,pixel_text_rgb,line0,line1);
                end
                n=n+1;
            end else if(!$feof(fin)) begin $display("FAIL stimulus"); $finish; end
        end
        $fclose(fin); $fclose(fout);
        $display("PASS color_target_replay cycles=%0d",n); $finish;
    end
endmodule
