`timescale 1ns / 1ps
module tb_gaussian_pair;
    parameter WIDTH=64,HEIGHT=16;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0,v=0,u=0,l=0;
    reg [15:0] pair=0;
    reg [7:0] threshold=0;
    wire [15:0] op;
    wire ov,ou,ol;
    wire [7:0] ot;
    gaussian_pair_3x3 #(.IMG_WIDTH(WIDTH),.IMG_HEIGHT(HEIGHT)) dut (
        .clk(clk),.rst_n(rst_n),.I_pair(pair),.I_valid(v),.I_user(u),.I_last(l),
        .I_threshold(threshold),.O_pair(op),.O_valid(ov),.O_user(ou),.O_last(ol),.O_threshold(ot));
    reg [15:0] golden[0:3];
    reg [7:0] th[0:3];
    reg [3:0] ev=0,eu=0,el=0;
    reg [2047:0] path;
    reg [15:0] next_pair,expected;
    reg [7:0] next_threshold;
    integer fd,rc,tv,tu,tl,i,cycles=0,beats=0;
    task step;
        input sv,su,sl;
        input [7:0] st;
        input [15:0] sp,ex;
        begin
            @(negedge clk);v=sv;u=su;l=sl;threshold=st;pair=sp;
            @(posedge clk);#1;
            for(i=3;i>0;i=i-1) begin golden[i]=golden[i-1];th[i]=th[i-1];end
            golden[0]=ex;th[0]=st;
            ev={ev[2:0],sv};eu={eu[2:0],su};el={el[2:0],sl};
            if(ov!==ev[3] || ou!==eu[3] || ol!==el[3] || ((ov||ou) && ot!==th[3]))
                $fatal(1,"FAIL Gaussian metadata cycle%0d",cycles);
            if(ov && op!==golden[3])
                $fatal(1,"FAIL Gaussian pixel cycle%0d got%h expected%h",cycles,op,golden[3]);
            if(ov) beats=beats+1;
            cycles=cycles+1;
        end
    endtask
    initial begin
        for(i=0;i<4;i=i+1) begin golden[i]=0;th[i]=0;end
        if(!$value$plusargs("STIM=%s",path)) $fatal(1,"FAIL missing Gaussian vectors");
        fd=$fopen(path,"r");if(!fd) $fatal(1,"FAIL open Gaussian vectors");
        repeat(6) @(negedge clk);rst_n=1;
        while(!$feof(fd)) begin
            rc=$fscanf(fd,"%d %d %d %h %h %h\n",tv,tu,tl,next_threshold,next_pair,expected);
            if(rc==6) step(tv!=0,tu!=0,tl!=0,next_threshold,next_pair,expected);
            else if(!$feof(fd)) $fatal(1,"FAIL malformed Gaussian vectors");
        end
        repeat(8) step(0,0,0,0,0,0);
        $display("PASS Gaussian spatial: cycles=%0d valid_beats=%0d full8bit/earlySOF/bubbles/threshold alignment",cycles,beats);
        $finish;
    end
endmodule
