`timescale 1ns/1ps
module tb_edge_link_pair;
    localparam W=64,H=24;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,v=0,u=0,l=0;
    reg [3:0] data=0;
    wire [3:0] labels[0:4];wire [4:0] vv,uu,ll;
    assign labels[0]=data;assign vv[0]=v;assign uu[0]=u;assign ll[0]=l;
    genvar g;
    generate for(g=0;g<4;g=g+1) begin : hops
        edge_link_pair_3x3 #(.IMG_WIDTH(W),.IMG_HEIGHT(H),.INPUT_BORDER(2*g)) dut (
            .clk(clk),.rst_n(rst_n),.I_labels(labels[g]),.I_valid(vv[g]),.I_user(uu[g]),.I_last(ll[g]),
            .O_labels(labels[g+1]),.O_valid(vv[g+1]),.O_user(uu[g+1]),.O_last(ll[g+1]));
    end endgenerate
    reg [3:0] expected[0:3][0:11];reg [11:0] ev=0,eu=0,el=0;
    integer inf,rc,i,j,iv,iu,il,cycles=0,beats=0,checks=0;
    reg [3:0] din,e0,e1,e2,e3;reg [2047:0] path;
    task step;
        input tv,tu,tl;input [3:0] td,x0,x1,x2,x3;
        begin
            @(negedge clk);v=tv;u=tu;l=tl;data=td;
            @(posedge clk);#1;
            for(i=0;i<4;i=i+1) for(j=11;j>0;j=j-1) expected[i][j]=expected[i][j-1];
            expected[0][0]=x0;expected[1][0]=x1;expected[2][0]=x2;expected[3][0]=x3;
            ev={ev[10:0],tv};eu={eu[10:0],tu};el={el[10:0],tl};
            for(i=1;i<=4;i=i+1) begin
                if(vv[i]!==ev[3*i-1] || uu[i]!==eu[3*i-1] || ll[i]!==el[3*i-1])
                    $fatal(1,"FAIL hop%0d metadata cycle%0d",i,cycles);
                if(vv[i]) begin
                    if(labels[i]!==expected[i-1][3*i-1])
                        $fatal(1,"FAIL hop%0d labels cycle%0d got%h expected%h",i,cycles,labels[i],expected[i-1][3*i-1]);
                    checks=checks+2;
                end
            end
            if(tv) beats=beats+1;cycles=cycles+1;
        end
    endtask
    initial begin
        for(i=0;i<4;i=i+1) for(j=0;j<12;j=j+1) expected[i][j]=0;
        if(!$value$plusargs("STIM=%s",path)) $fatal(1,"FAIL no stimulus");
        inf=$fopen(path,"r");if(!inf) $fatal(1,"FAIL open stimulus");
        repeat(8) @(negedge clk);rst_n=1;
        while(!$feof(inf)) begin
            rc=$fscanf(inf,"%d %d %d %h %h %h %h %h\n",iv,iu,il,din,e0,e1,e2,e3);
            if(rc==8) step(iv!=0,iu!=0,il!=0,din,e0,e1,e2,e3);
            else if(!$feof(inf)) $fatal(1,"FAIL malformed stimulus");
        end
        repeat(16) step(0,0,0,0,0,0,0,0);
        $display("PASS edge_link four independent spatial stage references beats=%0d sample_stage_checks=%0d cycles=%0d",beats,checks,cycles);
        $finish;
    end
endmodule
