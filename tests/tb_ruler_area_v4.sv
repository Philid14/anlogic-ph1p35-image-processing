`timescale 1ns/1ps
module tb_ruler_area_v4;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,v=0,u=0,l=0,en=0,req=0;reg [31:0] gray=0;
    wire [10:0] span;wire ok;wire [2:0] status;
    ruler_area_calibration #(.WIDTH(896),.HEIGHT(128),.X0(64),.Y0(32),.SEARCH_HEIGHT(48)) dut(
        .clk(clk),.rst_n(rst_n),.gray(gray),.valid(v),.user(u),.last(l),
        .enable(en),.request_toggle(req),.span(span),.calibrated(ok),.status(status));
    integer fd,n,rv,rr,vu,vl,ve,vq,es,eo,et,check,cycles=0,checks=0;
    reg[31:0] data;reg[2047:0] path;
    initial begin
        if(!$value$plusargs("STIM=%s",path))$fatal(1,"FAIL no stimulus");
        fd=$fopen(path,"r");
        while(!$feof(fd))begin
            n=$fscanf(fd,"%d %d %d %d %d %d %h %d %d %d %d\n",rr,rv,vu,vl,ve,vq,data,check,es,eo,et);
            if(n==11)begin
                @(negedge clk);rst_n=rr;v=rv;u=vu;l=vl;en=ve;req=vq;gray=data;
                @(posedge clk);#1;cycles=cycles+1;
                if(check)begin
                    if(ok!==eo || status!==et || (eo && ((^span===1'bx) || (check==2 ? (span+1<es || span>es+1) : span!==es))))
                        begin $display("debug state%0d row%0d pos%0d band%0d low%0d high%0d anchor%0d bestcnt%0d weight%0d q%0d",dut.state,dut.line_no,dut.pos,dut.band_y,dut.lows[0],dut.highs[0],dut.anchor,dut.best_count,dut.best_weight,dut.qnext); $fatal(1,"FAIL ruler cycle%0d got span%0d ok%0d status%0d expected %0d/%0d/%0d",cycles,span,ok,status,es,eo,et);end
                    checks=checks+1;
                end
            end else if(!$feof(fd))$fatal(1,"FAIL stimulus format");
        end
        $display("PASS ruler auto calibration %0d checks, %0d cycles",checks,cycles);$finish;
    end
endmodule
