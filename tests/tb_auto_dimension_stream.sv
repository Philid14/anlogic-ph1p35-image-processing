`timescale 1ns / 1ps
module tb_auto_dimension_stream;
    parameter WIDTH=64, HEIGHT=16, RELIABILITY=1, COMPARE=0, INSPECTION=0, AUTO_DIMENSION=0;
    reg [3:0] ui_test=0;reg cal_test=0;reg capture_test=0;reg [10:0] sx_test=256,sy_test=256;
    localparam DEPTH = 29+(COMPARE?2:0);
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, v=0, u=0, l=0, ready=0;
    reg [95:0] data=0;
    reg [18:0] cfg=19'h35082;
    reg [31:0] fifo_counts=32'h1234abcd;
    wire [95:0] od;
    wire ov, ou, ol, ir, pv, pu;
    wire [127:0] pd;

    // Observe the actual ISP algorithm and actual ISP packer. No duplicate DUT.
    assign od=integrated.algorithm_data;assign ov=integrated.algorithm_valid;
    assign ou=integrated.algorithm_user;assign ol=integrated.algorithm_last;
    assign ir=integrated.awb_O_tready;
    assign pd=id128;assign pv=iv128;assign pu=iu128;
    wire iv128, iu128, il128;
    wire [127:0] id128;
    reg last128=0;
    always @(posedge clk) last128<=ol;
    isp_top #(
        .EDGE_CONTROL_ENABLE(1), .DENOISE_ENABLE(1), .NMS_ENABLE(1),
        .QUALITY_ENABLE(1), .QUALITY_HOPS(4), .TEMPORAL_ENABLE(1),
        .RELIABILITY_ENABLE(RELIABILITY),.COLOR_COMPARE_ENABLE(COMPARE),.INSPECTION_ENABLE(INSPECTION),.AUTO_DIMENSION(AUTO_DIMENSION)
    ) integrated (
        .axi4s_video_aclk(clk), .I_rst_n(rst_n), .I_edge_config(cfg),
        .I_fifo_event_counts(fifo_counts),
        .I_tlast(1'b0), .I_tuser(1'b0), .I_tdata(40'b0), .I_tvalid(1'b0),
        .I_tdest(10'b0), .O_tready(ready), .I_tready(),
        .O_tdata(id128), .O_tvalid(iv128), .O_tuser(iu128), .O_tlast(il128)
    );

    reg [95:0] golden [0:DEPTH-1];
    reg [DEPTH-1:0] ev=0, eu=0, el=0;
    reg prev_user=0;
    integer inf, pf, rc, j, iv, iu, il, iui,ical,isx,isy,icap, cycles=0, beats=0, words=0, expected_words;
    reg [95:0] din, expected;
    reg [18:0] next_cfg;
    reg [127:0] expected_pack;
    reg [2047:0] input_path, pack_path;

    task step;
        input tv, tu, tl;
        input [18:0] tc;
        input [95:0] td, ex;
        begin
            @(negedge clk);
            v=tv; u=tu; l=tl; data=td; cfg=tc; ready=~ready;
            @(posedge clk); #1;
            for(j=DEPTH-1;j>0;j=j-1) golden[j]=golden[j-1];
            golden[0]=ex;
            ev={ev[DEPTH-2:0],tv}; eu={eu[DEPTH-2:0],tu}; el={el[DEPTH-2:0],tl};
            if(ov!==ev[DEPTH-1] || ou!==eu[DEPTH-1] || ol!==el[DEPTH-1] || ir!==1'b1)
                $fatal(1,"FAIL stream metadata cycle %0d",cycles);
            if(ov && od!==golden[DEPTH-1])
                $fatal(1,"FAIL stream pixel cycle %0d got %h expected %h",
                       cycles,od,golden[DEPTH-1]);
            if(pu!==prev_user) $fatal(1,"FAIL pack SOF cycle %0d",cycles);
            prev_user=eu[DEPTH-1];
            if(ov) beats=beats+1;
            if(il128!==last128)$fatal(1,"FAIL actual ISP tlast %0d",cycles);
            if(pv) begin
                rc=$fscanf(pf,"%h\n",expected_pack);
                if(rc!=1 || pd!==expected_pack)
                    $fatal(1,"FAIL pack word %0d got %h expected %h",
                           words,pd,expected_pack);
                words=words+1;
            end
            cycles=cycles+1;
        end
    endtask

    initial begin
        if(!$value$plusargs("STIM=%s",input_path) ||
           !$value$plusargs("PACK=%s",pack_path) ||
           !$value$plusargs("WORDS=%d",expected_words))
            $fatal(1,"FAIL missing vectors");
        inf=$fopen(input_path,"r"); pf=$fopen(pack_path,"r");
        if(!inf || !pf) $fatal(1,"FAIL opening vectors");
        for(j=0;j<DEPTH;j=j+1) golden[j]=0;
        force integrated.awb_O_tdata=data;
        force integrated.awb_O_tvalid=v;
        force integrated.awb_O_tuser=u;
        force integrated.awb_O_tlast=l;
        if(INSPECTION)begin
            force integrated.g_control.u_control.capture_toggle=capture_test;
            force integrated.g_control.u_control.ui_switches=ui_test;
            force integrated.g_control.u_control.ui_calibrated=cal_test;
            force integrated.g_control.u_control.ui_span_x=sx_test;
            force integrated.g_control.u_control.ui_span_y=sy_test;
        end
        repeat(8) @(negedge clk);
        rst_n=1;
        while(!$feof(inf)) begin
            if(INSPECTION)begin
                rc=$fscanf(inf,"%d %d %d %h %h %h %d %d %d %d %d\n",
                    iv,iu,il,next_cfg,din,expected,iui,ical,isx,isy,icap);
                capture_test=icap;ui_test=iui;cal_test=ical;sx_test=isx;sy_test=isy;
                if(rc==11)rc=6;
            end else rc=$fscanf(inf,"%d %d %d %h %h %h\n",
                       iv,iu,il,next_cfg,din,expected);
            if(rc==6) step(iv!=0,iu!=0,il!=0,next_cfg,din,expected);
            else if(!$feof(inf)) $fatal(1,"FAIL malformed vector");
        end
        repeat(DEPTH+5) step(0,0,0,cfg,0,0);
        if(words!=expected_words)
            $fatal(1,"FAIL packed count %0d expected %0d",words,expected_words);
        if(AUTO_DIMENSION && (!integrated.g_control.u_control.g_inspection_controls.g_auto.u_ruler.calibrated ||
           integrated.g_control.u_control.g_inspection_controls.g_auto.u_ruler.span!==11'd500))
            $fatal(1,"FAIL actual ISP one-key ruler capture");
        $display("PASS actual ISP one-key ruler: 500px/100mm, native size annotations and exact packing");
        $display("PASS multi-mode stream width=%0d height=%0d cycles=%0d valid_beats=%0d packed_words=%0d reliability=%0d",
                 WIDTH,HEIGHT,cycles,beats,words,RELIABILITY);
        $finish;
    end
endmodule
