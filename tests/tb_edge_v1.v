`timescale 1ns / 1ps
module tb_edge_v1;
    parameter WIDTH=64, HEIGHT=16, THRESHOLD=80, CHECK_PACK=1;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, v=0, u=0, l=0, ready=0;
    reg [95:0] data=0;
    wire ov,ou,ol,ir;
    wire [95:0] od;
    wire pv,pu;
    wire [127:0] pd;
    edge_detect_96 #(.IMG_WIDTH(WIDTH),.IMG_HEIGHT(HEIGHT),.EDGE_TH(THRESHOLD)) dut (
        .I_clk(clk),.I_rst_n(rst_n),.I_tvalid(v),.I_tuser(u),.I_tlast(l),
        .I_tdata(data),.O_tready(ready),.I_tready(ir),
        .O_tvalid(ov),.O_tuser(ou),.O_tlast(ol),.O_tdata(od)
    );
    data_96bit_to_128bit packer (
        .I_clk(clk),.I_rst_n(rst_n),.I_96b_frame_start(ou),
        .I_96b_valid(ov),.I_96b_data(od),.O_128b_frame_start(pu),
        .O_128b_valid(pv),.O_128b_data(pd)
    );
    reg [95:0] golden [0:4];
    reg [4:0] ev=0,eu=0,el=0;
    reg prev_user=0;
    integer inf,pf,rc,j,iv,iu,il,cycles=0,beats=0,words=0,expected_words;
    reg [95:0] din,expected;
    reg [127:0] expected_pack;
    reg [2047:0] input_path,pack_path;
    task step;
        input tv,tu,tl;
        input [95:0] td,ex;
        begin
            @(negedge clk);
            v=tv;u=tu;l=tl;data=td;ready=~ready;
            @(posedge clk); #1;
            for(j=4;j>0;j=j-1) golden[j]=golden[j-1];
            golden[0]=ex;
            ev={ev[3:0],tv};eu={eu[3:0],tu};el={el[3:0],tl};
            if(ov !== ev[4] || ou !== eu[4] || ol !== el[4] || ir !== 1'b1) begin
                $display("FAIL metadata cycle=%0d got=%b%b%b expected=%b%b%b ready=%b",cycles,ov,ou,ol,ev[4],eu[4],el[4],ir);
                $finish;
            end
            if(od !== (ev[4] ? golden[4] : 96'b0)) begin
                $display("FAIL pixel cycle=%0d got=%h expected=%h",cycles,od,golden[4]);
                $finish;
            end
            if(pu !== prev_user) begin
                $display("FAIL pack SOF cycle=%0d",cycles);$finish;
            end
            prev_user=eu[4];
            if(ov) beats=beats+1;
            if(CHECK_PACK && pv) begin
                rc=$fscanf(pf,"%h\n",expected_pack);
                if(rc != 1 || pd !== expected_pack) begin
                    $display("FAIL packed word=%0d got=%h expected=%h read=%0d",words,pd,expected_pack,rc);$finish;
                end
                words=words+1;
            end
            cycles=cycles+1;
        end
    endtask
    initial begin
        if(!$value$plusargs("STIM=%s",input_path)) begin $display("FAIL missing STIM");$finish;end
        if(!$value$plusargs("PACK=%s",pack_path)) begin $display("FAIL missing PACK");$finish;end
        if(!$value$plusargs("WORDS=%d",expected_words)) begin $display("FAIL missing WORDS");$finish;end
        inf=$fopen(input_path,"r");pf=$fopen(pack_path,"r");
        if(inf==0 || pf==0) begin $display("FAIL open vectors");$finish;end
        for(j=0;j<5;j=j+1) golden[j]=0;
        repeat(8) @(negedge clk);
        rst_n=1;
        while(!$feof(inf)) begin
            rc=$fscanf(inf,"%d %d %d %h %h\n",iv,iu,il,din,expected);
            if(rc==5) step(iv!=0,iu!=0,il!=0,din,expected);
            else if(!$feof(inf)) begin $display("FAIL malformed vector");$finish;end
        end
        repeat(10) step(0,0,0,0,0);
        if(CHECK_PACK && words != expected_words) begin
            $display("FAIL word count %0d expected %0d",words,expected_words);$finish;
        end
        $display("PASS edge_v1 width=%0d height=%0d threshold=%0d cycles=%0d valid_beats=%0d packed_words=%0d",WIDTH,HEIGHT,THRESHOLD,cycles,beats,words);
        $finish;
    end
endmodule
