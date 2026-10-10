// Only for ISP routing/parameter unit tests. The TB injects AWB outputs;
// these are not functional models of the frozen demosaic or AWB IP.
module demosaic #(
    parameter IMG_HEIGHT=720, IMG_WIDTH=1280,
    parameter data_complete_delay=50, BAYER_MODE="BGGR"
)(
    input I_clk,I_rst_n,
    input [39:0] axi4s_video_tdata,
    input [9:0] axi4s_video_tdest,
    input axi4s_video_tlast,axi4s_video_tvalid,axi4s_video_tuser,
    output axi4s_video_tready,
    output O_tlast,O_tuser,O_tvalid,
    output [127:0] O_tdata,
    input O_tready
);
    assign O_tdata=0;
    assign {O_tlast,O_tuser,O_tvalid}=0;
    assign axi4s_video_tready=O_tready;
endmodule
module awb #(parameter IMG_HEIGHT=720, IMG_WIDTH=1280)(
    input I_clk,I_rst_n,I_tlast,I_tuser,I_tvalid,
    input [95:0] I_tdata,
    output I_tready,O_tlast,O_tuser,O_tvalid,
    output [95:0] O_tdata,
    input O_tready
);
    assign O_tdata=0;
    assign {O_tlast,O_tuser,O_tvalid}=0;
    assign I_tready=O_tready;
endmodule
