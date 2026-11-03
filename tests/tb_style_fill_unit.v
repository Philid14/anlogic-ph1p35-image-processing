`timescale 1ns/1ps
module tb_style_fill_unit;
    parameter WIDTH=128, HEIGHT=72;
    reg clk=0;always #5 clk=~clk;
    reg rn=0,v=0,u=0;reg[95:0]d=0;
    wire[95:0]q;
    style_fill_96 #(.IMG_WIDTH(WIDTH),.IMG_HEIGHT(HEIGHT)) dut(
        .clk(clk),.rst_n(rn),.I_data(d),.I_valid(v),.I_user(u),.O_data(q));
    reg[95:0]gold[0:4];reg[4:0]ev=0;
    reg[2047:0]path;
    integer fd,rc,tr,tv,tu,j,cycles=0,pixels=0;
    reg[95:0]td,ex;
    initial begin
        if(!$value$plusargs("STIM=%s",path))$fatal(1,"FAIL path");
        fd=$fopen(path,"r");if(!fd)$fatal(1,"FAIL file");
        for(j=0;j<5;j=j+1)gold[j]=0;
        repeat(3)@(negedge clk);
        while(!$feof(fd))begin
            rc=$fscanf(fd,"%d %d %d %h %h\n",tr,tv,tu,td,ex);
            if(rc==5)begin
                @(negedge clk);rn=tr;v=tv;u=tu;d=td;
                @(posedge clk);#1;
                if(!rn)begin ev=0;for(j=0;j<5;j=j+1)gold[j]=0;end
                else begin
                    for(j=4;j>0;j=j-1)gold[j]=gold[j-1];gold[0]=ex;
                    ev={ev[3:0],v};
                    if(ev[4])begin
                        if(q!==gold[4])$fatal(1,"FAIL style cycle %0d got %h expected %h",cycles,q,gold[4]);
                        pixels=pixels+4;
                    end
                end
                cycles=cycles+1;
            end
        end
        $display("PASS style unit width=%0d height=%0d cycles=%0d pixels=%0d",WIDTH,HEIGHT,cycles,pixels);
        $finish;
    end
endmodule
