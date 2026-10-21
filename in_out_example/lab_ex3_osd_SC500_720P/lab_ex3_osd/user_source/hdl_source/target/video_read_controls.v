// The native 128->24 reader registers read-enable once and RGB once.
// Request pixels using the original raster DE, then carry all five control
// signals through the same two clocks before the mixer RGB/control pipeline.
// This adapter changes neither raster lengths nor the DDR request count.
module video_read_controls(
    input clk, rst_n,
    input vs,hs,de,user,last,
    output read_enable,
    output aligned_vs,aligned_hs,aligned_de,aligned_user,aligned_last
);
    reg [4:0] first,second;
    assign read_enable=de;
    assign {aligned_vs,aligned_hs,aligned_de,aligned_user,aligned_last}=second;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin first<=0; second<=0; end
        else begin first<={vs,hs,de,user,last}; second<=first; end
    end
endmodule
