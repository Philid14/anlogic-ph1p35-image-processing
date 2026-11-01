`timescale 1ns/1ps
module tb_switch_status_v3;
    reg clk=0;always #5 clk=~clk;
    reg rst=0,v=0,u=0,l=0;reg[95:0] rgb=0;reg[3:0] sw=0;reg[2:0] rs=0;reg[18:0] cfg=0;
    wire[95:0] out;wire ov,ou,ol;
    edge_status_osd #(.IMG_HEIGHT(176),.RELIABILITY_ENABLE(1),.SWITCH_DIAG_ENABLE(1)) dut(
        .clk(clk),.rst_n(rst),.I_data(rgb),.I_valid(v),.I_user(u),.I_last(l),.I_config(cfg),
        .I_fifo_event_counts(32'h1234abcd),.I_switches(sw),.I_ruler_status(rs),
        .O_data(out),.O_valid(ov),.O_user(ou),.O_last(ol));
    reg[95:0] expected=0;reg ev=0,eu=0,el=0;
    integer fd,n,tv,tu,tl,ts,tr,tc,checks=0;reg[95:0] din,golden;reg[2047:0] path;
    initial begin
        if(!$value$plusargs("STIM=%s",path))$fatal(1,"FAIL vectors");fd=$fopen(path,"r");
        repeat(3)@(negedge clk);rst=1;
        while(!$feof(fd))begin
            n=$fscanf(fd,"%d %d %d %h %d %d %h %h\n",tv,tu,tl,tc,ts,tr,din,golden);
            if(n==8)begin
                @(negedge clk);v=tv;u=tu;l=tl;cfg=tc;sw=ts;rs=tr;rgb=din;
                @(posedge clk);#1;
                if(ov!==ev || ou!==eu || ol!==el || (ov && out!==expected))
                    $fatal(1,"FAIL status controls/metadata at %0d got%h expected%h",checks,out,expected);
                expected=golden;ev=tv;eu=tu;el=tl;checks=checks+1;
            end else if(!$feof(fd))$fatal(1,"FAIL format");
        end
        $display("PASS switch/error status 16 combinations, frame isolation, contrast and metadata %0d cycles",checks);$finish;
    end
endmodule
