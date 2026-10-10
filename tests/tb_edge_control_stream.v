`timescale 1ns / 1ps
module tb_edge_control_stream;
    parameter WIDTH=64,HEIGHT=16;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0,v=0,u=0,l=0,ready=0;
    reg [95:0] data=0;
    reg [8:0] cfg={1'b1,8'd80};
    wire [95:0] od;
    wire ov,ou,ol,ir,pv,pu;
    wire [127:0] pd;
    edge_control_stream #(.IMG_WIDTH(WIDTH),.IMG_HEIGHT(HEIGHT)) dut (
        .clk(clk),.rst_n(rst_n),.requested_config(cfg),
        .I_data(data),.I_valid(v),.I_user(u),.I_last(l),.O_ready(ready),
        .O_data(od),.O_valid(ov),.O_user(ou),.O_last(ol),.I_ready(ir));
    data_96bit_to_128bit packer (.I_clk(clk),.I_rst_n(rst_n),
        .I_96b_frame_start(ou),.I_96b_valid(ov),.I_96b_data(od),
        .O_128b_frame_start(pu),.O_128b_valid(pv),.O_128b_data(pd));
    wire iv128,iu128,il128;
    wire [127:0] id128;
    reg last128=0;
    always @(posedge clk) last128<=ol;
    isp_top #(.EDGE_CONTROL_ENABLE(1)) integrated (
        .axi4s_video_aclk(clk),.I_rst_n(rst_n),.I_edge_config(cfg),
        .I_tlast(1'b0),.I_tuser(1'b0),.I_tdata(40'b0),.I_tvalid(1'b0),
        .I_tdest(10'b0),.O_tready(ready),.I_tready(),
        .O_tdata(id128),.O_tvalid(iv128),.O_tuser(iu128),.O_tlast(il128));
    reg [95:0] golden [0:6];
    reg [6:0] ev=0,eu=0,el=0;
    reg prev_user=0;
    integer inf,pf,rc,j,iv,iu,il,cycles=0,beats=0,words=0,expected_words;
    reg [95:0] din,expected;
    reg [8:0] next_cfg;
    reg [127:0] expected_pack;
    reg [2047:0] input_path,pack_path;
    task step;
        input tv,tu,tl;
        input [8:0] tc;
        input [95:0] td,ex;
        begin
            @(negedge clk);v=tv;u=tu;l=tl;data=td;cfg=tc;ready=~ready;
            @(posedge clk);#1;
            for(j=6;j>0;j=j-1) golden[j]=golden[j-1];golden[0]=ex;
            ev={ev[5:0],tv};eu={eu[5:0],tu};el={el[5:0],tl};
            if(ov!==ev[6] || ou!==eu[6] || ol!==el[6] || ir!==1'b1)
                $fatal(1,"FAIL stream metadata cycle %0d",cycles);
            if(ov && od!==golden[6])
                $fatal(1,"FAIL stream pixel cycle %0d got %h expected %h",cycles,od,golden[6]);
            if(pu!==prev_user) $fatal(1,"FAIL pack SOF cycle %0d",cycles);
            prev_user=eu[6];
            if(ov) beats=beats+1;
            if(WIDTH==1280 && HEIGHT==720 &&
               (iv128!==pv || iu128!==pu || il128!==last128 || (pv && id128!==pd)))
                $fatal(1,"FAIL actual ISP runtime integration cycle %0d",cycles);
            if(pv) begin
                rc=$fscanf(pf,"%h\n",expected_pack);
                if(rc!=1 || pd!==expected_pack)
                    $fatal(1,"FAIL pack word %0d got %h expected %h",words,pd,expected_pack);
                words=words+1;
            end
            cycles=cycles+1;
        end
    endtask
    initial begin
        if(!$value$plusargs("STIM=%s",input_path) || !$value$plusargs("PACK=%s",pack_path)
            || !$value$plusargs("WORDS=%d",expected_words)) $fatal(1,"FAIL missing vectors");
        inf=$fopen(input_path,"r");pf=$fopen(pack_path,"r");
        if(!inf || !pf) $fatal(1,"FAIL opening vectors");
        for(j=0;j<7;j=j+1) golden[j]=0;
        force integrated.awb_O_tdata=data;
        force integrated.awb_O_tvalid=v;
        force integrated.awb_O_tuser=u;
        force integrated.awb_O_tlast=l;
        repeat(8) @(negedge clk);rst_n=1;
        while(!$feof(inf)) begin
            rc=$fscanf(inf,"%d %d %d %h %h %h\n",iv,iu,il,next_cfg,din,expected);
            if(rc==6) step(iv!=0,iu!=0,il!=0,next_cfg,din,expected);
            else if(!$feof(inf)) $fatal(1,"FAIL malformed vector");
        end
        repeat(12) step(0,0,0,cfg,0,0);
        if(words!=expected_words) $fatal(1,"FAIL packed count %0d expected %0d",words,expected_words);
        $display("PASS checkpoints_B_C_D stream width=%0d height=%0d cycles=%0d valid_beats=%0d packed_words=%0d",WIDTH,HEIGHT,cycles,beats,words);
        $finish;
    end
endmodule
