`timescale 1ns / 1ps
module tb_nms_gradient_pair;
    parameter WIDTH=64,HEIGHT=16;
    reg clk=0;always #5 clk=~clk;
    reg rn=0,v=0,u=0,l=0;
    reg [27:0] mag=0;
    reg [3:0] dir=0;
    reg [13:0] threshold=0;
    wire [27:0] om,oc,on,op;
    wire [3:0] od;
    wire [1:0] ok;
    wire ov,ou,ol,dbg;
    wire [13:0] ot;
    nms_gradient_pair_3x3 #(.IMG_WIDTH(WIDTH),.IMG_HEIGHT(HEIGHT),.INPUT_BORDER(0)) dut (
        .clk(clk),.rst_n(rn),.I_magnitude(mag),.I_direction(dir),.I_valid(v),.I_user(u),.I_last(l),.I_threshold(threshold),
        .O_magnitude(om),.O_keep(ok),.O_valid(ov),.O_user(ou),.O_last(ol),.O_threshold(ot),
        .O_debug_valid(dbg),.O_center(oc),.O_direction(od),.O_negative(on),.O_positive(op));
    reg [118:0] expected[0:3];reg [13:0] th[0:3];
    reg [3:0] ev=0,eu=0,el=0;
    reg [2047:0] path;
    reg [27:0] im,em,ec,en,ep;
    reg [3:0] id,ed;
    reg [1:0] ek;
    reg [13:0] it;
    integer iv,iu,il,eb,fd,rc,j,cycles=0,beats=0,windows=0;
    task step;
        input sv,su,sl;input [13:0] st;input [27:0] sm;input [3:0] sd;input [118:0] ex;
        begin
            @(negedge clk);v=sv;u=su;l=sl;threshold=st;mag=sm;dir=sd;
            @(posedge clk);#1;
            for(j=3;j>0;j=j-1) begin expected[j]=expected[j-1];th[j]=th[j-1];end
            expected[0]=ex;th[0]=st;ev={ev[2:0],sv};eu={eu[2:0],su};el={el[2:0],sl};
            if(ov!==ev[3] || ou!==eu[3] || ol!==el[3] || ((ov||ou)&&ot!==th[3]))
                $fatal(1,"FAIL NMS metadata cycle%0d",cycles);
            if(ov) begin
                beats=beats+1;
                if({om,ok,dbg}!==expected[3][118:88]) $fatal(1,"FAIL NMS result cycle%0d got%h want%h",cycles,{om,ok,dbg},expected[3][118:88]);
                if(dbg) begin
                    windows=windows+2;
                    if({om,ok,dbg,oc,od,on,op}!==expected[3])
                        $fatal(1,"FAIL NMS center/direction/neighbors cycle%0d got%h want%h",cycles,{om,ok,dbg,oc,od,on,op},expected[3]);
                end
            end
            cycles=cycles+1;
        end
    endtask
    initial begin
        for(j=0;j<4;j=j+1) begin expected[j]=0;th[j]=0;end
        if(!$value$plusargs("STIM=%s",path)) $fatal(1,"FAIL NMS missing input");
        fd=$fopen(path,"r");if(!fd) $fatal(1,"FAIL NMS file open");
        repeat(8) @(negedge clk);rn=1;
        while(!$feof(fd)) begin
            rc=$fscanf(fd,"%d %d %d %h %h %h %h %h %d %h %h %h %h\n",iv,iu,il,it,im,id,em,ek,eb,ec,ed,en,ep);
            if(rc==13) step(iv!=0,iu!=0,il!=0,it,im,id,{em,ek,eb[0],ec,ed,en,ep});
            else if(!$feof(fd)) $fatal(1,"FAIL NMS malformed vector");
        end
        repeat(8) step(0,0,0,0,0,0,0);
        $display("PASS NMS unit: cycles=%0d beats=%0d checked_samples=%0d full14bit/center_axis/four_neighbors/equal_platform/SOF/recovery",cycles,beats,windows);
        $finish;
    end
endmodule
