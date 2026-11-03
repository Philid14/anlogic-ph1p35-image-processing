`timescale 1ns / 1ps
module tb_color_target_support3;
    parameter integer WIDTH=32, HEIGHT=9, XW=11, YW=10, GATE=0;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, valid=0, sof=0, eol=0, eof=0, abort_f=0;
    reg [3:0] mask=0;
    reg [XW-1:0] x=0;
    reg [YW-1:0] y=0;
    reg [31:0] sid=0, fid=0;
    wire ov, os, ol, oe, oa, err;
    wire [3:0] om;
    wire [XW-1:0] ox;
    wire [YW-1:0] oy;
    wire [31:0] osi, ofi;
    wire bv, bs, bl, be, ba, berr;
    wire [3:0] bm;
    wire [XW-1:0] bx;
    wire [YW-1:0] by;
    wire [31:0] bsi, bfi;
    reg [1:0] observe_sel=0;
    wire [31:0] observe;
    reg [95:0] snapshot=0;
    wire unused_pad;
    generate if (GATE == 0) begin : g_rtl
    assign observe=0;
    color_target_support3 #(.ENABLE(1),.WIDTH(WIDTH),.HEIGHT(HEIGHT),.XW(XW),.YW(YW)) dut (
        .clk(clk),.rst_n(rst_n),.I_pixel_valid(valid),.I_mask(mask),.I_x0(x),.I_y(y),
        .I_sof(sof),.I_eol(eol),.I_eof(eof),.I_session_id(sid),.I_frame_id(fid),
        .I_frame_abort(abort_f),.O_pixel_valid(ov),.O_mask(om),.O_x0(ox),.O_y(oy),
        .O_sof(os),.O_eol(ol),.O_eof(oe),.O_session_id(osi),.O_frame_id(ofi),
        .O_frame_abort(oa),.O_protocol_error(err));
    end else begin : g_gate
        PH1P_PHY_GSR PH1P_PHY_GSR();
        support3_synth_top dut (
            .clk(clk),.rst_n(rst_n),.I_pixel_valid(valid),.I_mask(mask),.I_x0(x),.I_y(y),
            .I_sof(sof),.I_eol(eol),.I_eof(eof),.I_session_id(sid),.I_frame_id(fid),
            .I_frame_abort(abort_f),.observe_sel(observe_sel),.observe(observe));
        assign {unused_pad,ov,om,ox,oy,os,ol,oe,osi,ofi,oa,err}=snapshot;
    end endgenerate
    // Leave ENABLE unspecified: test the shipped default, not an explicit 0.
    color_target_support3 #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.XW(XW),.YW(YW)) bypass (
        .clk(clk),.rst_n(rst_n),.I_pixel_valid(valid),.I_mask(mask),.I_x0(x),.I_y(y),
        .I_sof(sof),.I_eol(eol),.I_eof(eof),.I_session_id(sid),.I_frame_id(fid),
        .I_frame_abort(abort_f),.O_pixel_valid(bv),.O_mask(bm),.O_x0(bx),.O_y(by),
        .O_sof(bs),.O_eol(bl),.O_eof(be),.O_session_id(bsi),.O_frame_id(bfi),
        .O_frame_abort(ba),.O_protocol_error(berr));
    integer fin, fout, rc, n=0, j;
    reg [2047:0] spath, opath;
    reg ri, vi, si, li, ei, ai;
    reg [3:0] mi;
    reg [31:0] xi, yi, sidi, fidi;
    initial begin
        if (!$value$plusargs("STIM=%s",spath) || !$value$plusargs("OUT=%s",opath)) begin
            $display("FAIL missing paths"); $finish; end
        fin=$fopen(spath,"r"); fout=$fopen(opath,"w");
        if (fin==0 || fout==0) begin $display("FAIL open files"); $finish; end
        repeat(3) @(negedge clk);
        while (!$feof(fin)) begin
            rc=$fscanf(fin,"%d %d %h %d %d %d %d %d %d %d %d\n",
                       ri,vi,mi,xi,yi,si,li,ei,sidi,fidi,ai);
            if (rc==11) begin
                @(negedge clk);
                rst_n=ri; valid=vi; mask=mi; x=xi; y=yi;
                sof=si; eol=li; eof=ei; sid=sidi; fid=fidi; abort_f=ai;
                @(posedge clk); #1;
                if (GATE != 0) begin
                    for (j=0;j<3;j=j+1) begin
                        // Vendor LUT/pad models include propagation delay.
                        // All three public probes still fit before next edge.
                        observe_sel=j; #1;
                        snapshot[j*32 +: 32]=observe;
                    end
                    #0.01;
                end
                if (!rst_n) begin
                    if (ov!==0 || bv!==0 || err!==0) begin $display("FAIL reset"); $finish; end
                end else if ({bv,bm,bx,by,bs,bl,be,bsi,bfi,ba,berr} !==
                             {valid,mask,x,y,sof,eol,eof,sid,fid,abort_f,1'b0}) begin
                    $display("FAIL default bypass cycle=%0d",n); $finish;
                end
                $fwrite(fout,"%0d %b %h %0d %0d %b %b %b %0d %0d %b %b\n",
                        n,ov,om,ox,oy,os,ol,oe,osi,ofi,oa,err);
                n=n+1;
            end else if (!$feof(fin)) begin $display("FAIL stimulus"); $finish; end
        end
        $fclose(fin); $fclose(fout);
        $display("PASS support3 cycles=%0d",n); $finish;
    end
endmodule
