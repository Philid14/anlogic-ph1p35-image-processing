module isp_top #(
    // Experimental RAW10 pedestal from the bundled, inactive BLC/BLC.v
    // reference. This is not a measured SC500CS black level.
    parameter [9:0] BLACK_LEVEL_RAW10 = 10'd15,
    parameter EDGE_ENABLE = 1,
    parameter [13:0] EDGE_THRESHOLD = 14'd80,
    parameter integer EDGE_CONTROL_ENABLE = 0,
    parameter integer DENOISE_ENABLE = 0,
    parameter integer NMS_ENABLE = 0,
    parameter integer QUALITY_ENABLE = 0,
    parameter integer QUALITY_HOPS = 4,
    parameter integer TEMPORAL_ENABLE = 0,
    parameter integer RELIABILITY_ENABLE = 0,
    parameter integer COLOR_COMPARE_ENABLE = 0,
    parameter integer INSPECTION_ENABLE = 0,
    parameter integer AUTO_DIMENSION = 0,
    parameter integer USABILITY_ENABLE = 0,
    parameter integer INSPECTION_V4 = 0
) (
    input 			axi4s_video_aclk,
    input [18:0] I_edge_config,
    input [31:0] I_fifo_event_counts,
    input [3:0] I_switch,input I_measure_key_n,
    input 			I_rst_n			,
    input 			I_tlast			,
    input 			I_tuser			,
    input [39:0] 	I_tdata			,
    input 			I_tvalid		,
    input [9:0] 	I_tdest			,
    input 			O_tready		,
    output [127:0] 	O_tdata			,
    output 			O_tlast			,
    output 			O_tuser			,
    output 			O_tvalid		,
    output 			I_tready
);
 
wire         m_aixs_tvalid;  //synthesis keep 
  wire [127:0] m_aixs_tdata;  //synthesis keep 
  wire         m_aixs_tuser;  //synthesis keep 
  wire         m_aixs_tlast;  //synthesis keep 
  wire         m_aixs_tready;  //synthesis keep 
  
  wire [ 95:0] m_aixs_tdata_96;  //synthesis keep 

  // Apply one identical saturating offset to all four Bayer RAW10 samples.
  // Combinational placement preserves tvalid/tuser/tlast/ready timing.
  wire [39:0] blc_raw10;
  genvar blc_p;
  generate for (blc_p = 0; blc_p < 4; blc_p = blc_p + 1) begin : blc_pixel
      wire [9:0] raw_sample;
      assign raw_sample = I_tdata[blc_p*10 +: 10];
      assign blc_raw10[blc_p*10 +: 10] =
          (raw_sample > BLACK_LEVEL_RAW10) ?
          (raw_sample - BLACK_LEVEL_RAW10) : 10'd0;
  end endgenerate


  wire         awb_O_tlast;  //synthesis keep 
  wire         awb_O_tuser;  //synthesis keep 
  wire [ 95:0] awb_O_tdata;  //synthesis keep 
  wire         awb_O_tvalid;  //synthesis keep 
  wire         awb_O_tready;  //synthesis keep 

  wire         awb_O_tuser_128;  //synthesis keep 
  wire         awb_O_tvalid_128;  //synthesis keep 
  wire [127:0] awb_O_tdata_128;  //synthesis keep 

  wire [95:0] algorithm_data;
  wire algorithm_valid, algorithm_user, algorithm_last, algorithm_last_128;
  generate
  if (EDGE_CONTROL_ENABLE) begin : g_control
      reg last_128;
      always @(posedge axi4s_video_aclk or negedge I_rst_n) begin
          if (!I_rst_n) last_128 <= 1'b0;
          else last_128 <= algorithm_last;
      end
      assign algorithm_last_128 = last_128;
      edge_control_stream #(.DENOISE_ENABLE(DENOISE_ENABLE), .NMS_ENABLE(NMS_ENABLE), .QUALITY_ENABLE(QUALITY_ENABLE), .QUALITY_HOPS(QUALITY_HOPS), .TEMPORAL_ENABLE(TEMPORAL_ENABLE), .RELIABILITY_ENABLE(RELIABILITY_ENABLE),.COLOR_COMPARE_ENABLE(COLOR_COMPARE_ENABLE),.INSPECTION_ENABLE(INSPECTION_ENABLE),.AUTO_DIMENSION(AUTO_DIMENSION),.USABILITY_ENABLE(USABILITY_ENABLE),.INSPECTION_V4(INSPECTION_V4)) u_control (
          .clk(axi4s_video_aclk), .rst_n(I_rst_n),
          .requested_config(I_edge_config),
          .I_fifo_event_counts(I_fifo_event_counts),
          .I_switch(I_switch),.I_measure_key_n(I_measure_key_n),
          .I_data(awb_O_tdata), .I_valid(awb_O_tvalid),
          .I_user(awb_O_tuser), .I_last(awb_O_tlast),
          .I_ready(awb_O_tready), .O_ready(O_tready),
          .O_data(algorithm_data), .O_valid(algorithm_valid),
          .O_user(algorithm_user), .O_last(algorithm_last)
      );
  end else if (EDGE_ENABLE) begin : g_edge
      reg last_128;
      always @(posedge axi4s_video_aclk or negedge I_rst_n) begin
          if (!I_rst_n) last_128 <= 1'b0;
          else last_128 <= algorithm_last;
      end
      assign algorithm_last_128 = last_128;
      edge_detect_96 #(.IMG_WIDTH(1280), .IMG_HEIGHT(720),
                       .EDGE_TH(EDGE_THRESHOLD), .DENOISE_ENABLE(DENOISE_ENABLE), .NMS_ENABLE(NMS_ENABLE), .QUALITY_ENABLE(QUALITY_ENABLE), .QUALITY_HOPS(QUALITY_HOPS)) u_edge (
          .I_clk(axi4s_video_aclk), .I_rst_n(I_rst_n),
          .I_tlast(awb_O_tlast), .I_tuser(awb_O_tuser), .I_threshold(8'd80),
          .I_tdata(awb_O_tdata), .I_tvalid(awb_O_tvalid),
          .I_tready(awb_O_tready), .O_tready(O_tready),
          .O_tlast(algorithm_last), .O_tuser(algorithm_user),
          .O_tdata(algorithm_data), .O_tvalid(algorithm_valid)
      );
  end else begin : g_original
      assign awb_O_tready = O_tready;
      assign algorithm_data = awb_O_tdata;
      assign algorithm_valid = awb_O_tvalid;
      assign algorithm_user = awb_O_tuser;
      assign algorithm_last = awb_O_tlast;
      assign algorithm_last_128 = awb_O_tlast;
  end
  endgenerate
  assign O_tdata  = awb_O_tdata_128;
  assign O_tlast  = algorithm_last_128;
  assign O_tuser  = awb_O_tuser_128    ;
  assign O_tvalid = awb_O_tvalid_128   ;
  
  //assign m_aixs_tready = O_tready;
  //assign O_tdata  = m_aixs_tdata;
  //assign O_tlast  = m_aixs_tlast    ;
  //assign O_tuser  = m_aixs_tuser    ;
  //assign O_tvalid = m_aixs_tvalid   ;
 
 
demosaic #(
    .IMG_HEIGHT          (720 ), // 图像高度
    .IMG_WIDTH           (1280), // 图像宽度
    .data_complete_delay (50  ),
    .BAYER_MODE          ("BGGR")
)
u_demosaic
(
    .I_clk   			(axi4s_video_aclk)	,   // 时钟信号
    .I_rst_n 			(I_rst_n)	,   // 复位信号，低有效
    .axi4s_video_tdata 	(blc_raw10)	,  // RAW10 BLC before demosaic
    .axi4s_video_tdest 	(I_tdest)	,
    .axi4s_video_tlast 	(I_tlast)	,  // 行结束信号
    .axi4s_video_tvalid	(I_tvalid)	,  // 数据有效信号
    .axi4s_video_tuser 	(I_tuser)	,  // 帧开始信号
    .axi4s_video_tready	(I_tready)	,  // 从模块准备好接受数据
    .O_tlast  			(m_aixs_tlast)	,  // 输出行结束信号
    .O_tuser  			(m_aixs_tuser)	,  // 输出帧开始信号
    .O_tdata  			(m_aixs_tdata)	,  // 输出数据
    .O_tvalid 			(m_aixs_tvalid)	,  // 输出数据有效信号
    .O_tready   		(m_aixs_tready)	   // 输出数据准备好信号
);
 
data128_96 u_data128_96 (
    .I_tdata(m_aixs_tdata),
    .O_tdata(m_aixs_tdata_96)
);

awb #(
    .IMG_HEIGHT(720 ),
    .IMG_WIDTH (1280)
) u_awb (
    .I_clk   (axi4s_video_aclk),
    .I_rst_n (I_rst_n),
    .I_tlast (m_aixs_tlast),
    .I_tuser (m_aixs_tuser),
    .I_tdata (m_aixs_tdata_96),
    .I_tvalid(m_aixs_tvalid),
    .I_tready(m_aixs_tready),
    .O_tlast (awb_O_tlast ),
    .O_tuser (awb_O_tuser ),
    .O_tdata (awb_O_tdata ),
    .O_tvalid(awb_O_tvalid),
    .O_tready(awb_O_tready)
);

    data_96bit_to_128bit u_data_96bit_to_128bit(
        .I_clk              ( axi4s_video_aclk  ),
        .I_rst_n            ( I_rst_n           ),
	
        .I_96b_frame_start  ( algorithm_user     ),
        .I_96b_valid        ( algorithm_valid    ),
        .I_96b_data         ( algorithm_data     ),
	
        .O_128b_frame_start ( awb_O_tuser_128  	),
        .O_128b_valid       ( awb_O_tvalid_128 	),
        .O_128b_data        ( awb_O_tdata_128  	)
    );



//data96_128 u_data96_128 (
//    .I_tdata(awb_O_tdata),
//    .O_tdata(awb_O_tdata_128)
//);
	
endmodule
