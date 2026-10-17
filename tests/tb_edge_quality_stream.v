`timescale 1ns / 1ps
module tb_edge_quality_stream;
    parameter WIDTH=64,HEIGHT=16,DENOISE=1,NMS=1,QUALITY=1;
    localparam DEPTH = (DENOISE ? 11 : 7)+(NMS ? 4:0)+(QUALITY ? 12:0);
    localparam GS = DENOISE ? 7:3;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0,v=0,u=0,l=0,ready=0;
    reg [95:0] data=0;
    reg [8:0] cfg={1'b1,8'd80};
    wire [95:0] od;
    wire ov,ou,ol,ir,pv,pu;
    wire [127:0] pd;
    edge_control_stream #(.IMG_WIDTH(WIDTH),.IMG_HEIGHT(HEIGHT),.DENOISE_ENABLE(DENOISE),.NMS_ENABLE(NMS),.QUALITY_ENABLE(QUALITY)) dut (
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
    isp_top #(.EDGE_CONTROL_ENABLE(1),.DENOISE_ENABLE(DENOISE),.NMS_ENABLE(NMS),.QUALITY_ENABLE(QUALITY)) integrated (
        .axi4s_video_aclk(clk),.I_rst_n(rst_n),.I_edge_config(cfg),
        .I_tlast(1'b0),.I_tuser(1'b0),.I_tdata(40'b0),.I_tvalid(1'b0),
        .I_tdest(10'b0),.O_tready(ready),.I_tready(),
        .O_tdata(id128),.O_tvalid(iv128),.O_tuser(iu128),.O_tlast(il128));
    reg [95:0] golden [0:DEPTH-1];
    reg [DEPTH-1:0] ev=0,eu=0,el=0;
    reg [51:0] gxgy_p[0:GS-1];
    reg [27:0] mag_p[0:GS];
    reg [3:0] dir_p[0:GS];
    reg [GS:0] gw_p=0;
    reg [51:0] next_gxgy;
    reg [27:0] next_mag;
    reg [3:0] next_dir;
    integer next_window;
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
        input [51:0] gg;input [27:0] mm;input [3:0] dd;input ww;
        begin
            @(negedge clk);v=tv;u=tu;l=tl;data=td;cfg=tc;ready=~ready;
            @(posedge clk);#1;
            for(j=DEPTH-1;j>0;j=j-1) golden[j]=golden[j-1];golden[0]=ex;
            ev={ev[DEPTH-2:0],tv};eu={eu[DEPTH-2:0],tu};el={el[DEPTH-2:0],tl};
            if(ov!==ev[DEPTH-1] || ou!==eu[DEPTH-1] || ol!==el[DEPTH-1] || ir!==1'b1)
                $fatal(1,"FAIL stream metadata cycle %0d",cycles);
            if(ov && od!==golden[DEPTH-1])
                $fatal(1,"FAIL stream pixel cycle %0d got %h expected %h",cycles,od,golden[DEPTH-1]);
            if(pu!==prev_user) $fatal(1,"FAIL pack SOF cycle %0d",cycles);
            prev_user=eu[DEPTH-1];
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
            for(j=GS;j>0;j=j-1) begin mag_p[j]=mag_p[j-1];dir_p[j]=dir_p[j-1];end
            for(j=GS-1;j>0;j=j-1) gxgy_p[j]=gxgy_p[j-1];
            mag_p[0]=mm;dir_p[0]=dd;gxgy_p[0]=gg;gw_p={gw_p[GS-1:0],ww};
            if(gw_p[GS-1] && {dut.u_edge.gx0_s3,dut.u_edge.gy0_s3,dut.u_edge.gx1_s3,dut.u_edge.gy1_s3}!==gxgy_p[GS-1])
                $fatal(1,"FAIL actual Sobel Gx/Gy cycle%0d",cycles);
            if(gw_p[GS] && {dut.u_edge.mag0_s4,dut.u_edge.mag1_s4}!==mag_p[GS])
                $fatal(1,"FAIL actual Sobel magnitude cycle%0d",cycles);
            cycles=cycles+1;
        end
    endtask
    generate if(NMS) begin : check_axis
        always @(posedge clk) begin
            #2;
            if(gw_p[GS] && {dut.u_edge.g_nms.dir0_s4,dut.u_edge.g_nms.dir1_s4}!==dir_p[GS])
                $fatal(1,"FAIL actual Sobel gradient direction cycle%0d",cycles);
        end
    end endgenerate
    initial begin
        for(j=0;j<GS;j=j+1) gxgy_p[j]=0;
        for(j=0;j<=GS;j=j+1) begin mag_p[j]=0;dir_p[j]=0;end
        if(!$value$plusargs("STIM=%s",input_path) || !$value$plusargs("PACK=%s",pack_path)
            || !$value$plusargs("WORDS=%d",expected_words)) $fatal(1,"FAIL missing vectors");
        inf=$fopen(input_path,"r");pf=$fopen(pack_path,"r");
        if(!inf || !pf) $fatal(1,"FAIL opening vectors");
        for(j=0;j<DEPTH;j=j+1) golden[j]=0;
        force integrated.awb_O_tdata=data;
        force integrated.awb_O_tvalid=v;
        force integrated.awb_O_tuser=u;
        force integrated.awb_O_tlast=l;
        repeat(8) @(negedge clk);rst_n=1;
        while(!$feof(inf)) begin
            rc=$fscanf(inf,"%d %d %d %h %h %h %h %h %h %d\n",iv,iu,il,next_cfg,din,expected,next_gxgy,next_mag,next_dir,next_window);
            if(rc==10) step(iv!=0,iu!=0,il!=0,next_cfg,din,expected,next_gxgy,next_mag,next_dir,next_window!=0);
            else if(!$feof(inf)) $fatal(1,"FAIL malformed vector");
        end
        repeat(DEPTH+5) step(0,0,0,cfg,0,0,0,0,0,0);
        if(words!=expected_words) $fatal(1,"FAIL packed count %0d expected %0d",words,expected_words);
        $display("PASS checkpoints_B_C_D stream width=%0d height=%0d cycles=%0d valid_beats=%0d packed_words=%0d denoise=%0d nms=%0d depth=%0d",WIDTH,HEIGHT,cycles,beats,words,DENOISE,NMS,DEPTH);
        $finish;
    end
endmodule
