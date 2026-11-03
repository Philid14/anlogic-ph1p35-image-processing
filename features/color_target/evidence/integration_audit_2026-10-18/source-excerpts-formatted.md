
## in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/design_top_wrapper.v
```text
47: 	wire        	S_pll_lock;
48:     wire        	S_rst_n;
49:
50: 	wire [15:0] 	S_ae;
201:
202:     assign S_rst_n 		= S_pll_lock;
203:     assign S_hdmi_rst_n = S_pll_lock;
204:
205:     always @(posedge S_csi_rx_clk or negedge S_rst_n) begin
206:         if(!S_rst_n)
207:             S_dbg_raw_seen <= 1'b0;
208:         else if(S_raw10_frame_start | S_axis_tvalid)
211:
212:     always @(posedge S_csi_rx_clk or negedge S_rst_n) begin
213:         if(!S_rst_n)
214:             S_dbg_isp_seen <= 1'b0;
215:         else if(S_ISP_O_tuser | S_ISP_O_tvalid)
218:
219:     always @(posedge S_ddr_clk or negedge S_rst_n) begin
220:         if(!S_rst_n)
221:             S_dbg_ddr_wr_seen <= 1'b0;
222:         else if(S_vi_ddr_wr_en)
225:
226:     always @(posedge S_ddr_clk or negedge S_rst_n) begin
227:         if(!S_rst_n)
228:             S_dbg_ddr_rd_seen <= 1'b0;
229:         else if(S_ddr_user_rd_valid)
232:
233:     always @(posedge S_24m_clk or negedge S_rst_n) begin
234:         if(!S_rst_n)
235:             S_dbg_cam_cfg_seen <= 1'b0;
236:         else if(S_cam_cfg_done)
239:
240:     always @(posedge S_csi_rx_clk or negedge S_rst_n) begin
241:         if(!S_rst_n)
242:             S_dbg_hs_seen <= 1'b0;
243:         else if(S_hs_rx_valid)
246:
247:     always @(posedge S_csi_rx_clk or negedge S_rst_n) begin
248:         if(!S_rst_n)
249:             S_dbg_csi_seen <= 1'b0;
250:         else if(S_csi_frame_start | S_csi_valid)
253:
254:     always @(posedge S_csi_rx_clk or negedge S_rst_n) begin
255:         if(!S_rst_n)
256:             S_dbg_raw10_seen <= 1'b0;
257:         else if(S_raw10_frame_start | S_raw10_valid)
260:
261:     always @(posedge S_csi_rx_clk or negedge S_rst_n) begin
262:         if(!S_rst_n)
263:             S_dbg_isp_fs_seen <= 1'b0;
264:         else if(S_ISP_O_tuser)
267:
268:     always @(posedge S_csi_rx_clk or negedge S_rst_n) begin
269:         if(!S_rst_n)
270:             S_dbg_isp_valid_seen <= 1'b0;
271:         else if(S_ISP_O_tvalid)
274:
275:     always @(posedge S_ddr_clk or negedge S_rst_n) begin
276:         if(!S_rst_n)
277:             S_dbg_ddr_req_seen <= 1'b0;
278:         else if(S_vi_ddr_wr_en)
281:
282:     always @(posedge S_ddr_clk or negedge S_rst_n) begin
283:         if(!S_rst_n)
284:             S_dbg_ddr_ready_seen <= 1'b0;
285:         else if(S_ddr_user_ready)
315:
316:     always @(posedge S_ddr_clk or negedge S_rst_n) begin
317:         if(!S_rst_n)
318:             S_dbg_mc_init_seen <= 1'b0;
319:         else if(S_init_calib_complete)
322:
323:     always @(posedge S_ddr_clk or negedge S_rst_n) begin
324:         if(!S_rst_n)
325:             S_dbg_mc_app_rdy_seen <= 1'b0;
326:         else if(S_mc_dbg_app_rdy)
329:
330:     always @(posedge S_ddr_clk or negedge S_rst_n) begin
331:         if(!S_rst_n)
332:             S_dbg_mc_wdf_rdy_seen <= 1'b0;
333:         else if(S_mc_dbg_wdf_rdy)
336:
337:     always @(posedge S_ddr_clk or negedge S_rst_n) begin
338:         if(!S_rst_n)
339:             S_dbg_mc_cmd_pop_seen <= 1'b0;
340:         else if(S_mc_dbg_cmd_pop)
440:   edge_key_control u_edge_keys (
441:       .clk(S_24m_clk), .rst_n(S_rst_n), .keys_n(I_button),
442:       .requested_config(S_edge_requested_config)
443:   );
444:   edge_config_cdc u_edge_config_cdc (
445:       .src_clk(S_24m_clk), .dst_clk(S_csi_rx_clk), .rst_n(S_rst_n),
446:       .requested_config(S_edge_requested_config),
447:       .received_config(S_edge_received_config)
453:       .I_clk(S_24m_clk),  //系统时钟输入
454:       .I_rst_n(S_rst_n),  //系统复位输入
455:       .I_ae_req(S_ae_req),
456:       .I_ae(S_ae),
471:         .I_lp_clk              ( S_100m_clk       ),
472:         .I_rst                 ( ~S_rst_n         ),
473:
474:         .I_clk_lane_in_delay   ( 6'd0             ),
513: .I_clk                 ( S_csi_rx_clk       ),
514: .I_rst_n               ( S_rst_n        	),
515: .I_hs_valid            ( S_hs_rx_valid     ),
516: .I_hs_data             ( S_hs_rx_data      ),
527: .I_clk  (S_csi_rx_clk),
528: .I_rst_n(S_rst_n),
529:
530: .I_csi_frame_start(S_csi_frame_start),
549: .I_native_clk(S_csi_rx_clk),
550: .I_rst_n     (S_rst_n),
551: .I_data      (S_raw10_data       ),
552: .I_data_valid(S_raw10_valid      ),
587: //ISP算法顶层模块
588: isp_top #(.EDGE_CONTROL_ENABLE(1)) u_isp_top (
589: .axi4s_video_aclk(S_csi_rx_clk),
590: .I_edge_config   (S_edge_received_config),
591: .I_rst_n         (S_rst_n),
592: .I_tlast         (S_raw_tlast	),
593: .I_tuser         (S_raw_tuser	),
605:
606:     video_in u_video_in(
607:         .I_rst_n              (  S_rst_n             ),
608:
609:         .I_camera_clk         ( S_csi_rx_clk          ),
612:         .I_camera_data        ( S_ISP_O_tdata  ),
613:         .I_mipi_rx_error      ( 1'b0			      ),
614:
615:         .I_ddr_clk            ( S_ddr_clk             ),
640:
641:     video_out u_video_out(
642:         .I_rst_n             ( S_video_out_rst_n    ),
643:         .I_ddr_clk           ( S_ddr_clk            ),
664:         .I_clk                   ( S_ddr_clk               ),
665:         .I_rst_n                 ( S_rst_n                 ),
666:
667:         .I_ddr_user_wr_en        ( S_ddr_user_wr_en        ),
692:         .I_sys_clk              ( I_sys_clk              ),
693:         .I_sys_rst_n            ( S_rst_n                ),
694:
695:         .O_ddr_clk              ( S_ddr_clk              ),
752:         .DEBUG_MODE ( 0    )
753:     )u_hdmi_mixer(
754:         .I_clk           ( S_hdmi_pixel_clk   ),
755:         .I_rst_n         ( S_hdmi_rst_n       ),
```

## in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/uial2axis.v
```text
54:   assign axis_tvalid = I_data_valid ? 1'b1 : 1'b0;
55:   assign axis_tlast  = hcnt == IMG_WIDTH_4X - 1 && axis_tvalid ? 1'b1 : 1'b0;
56:   assign axis_tuser  = vcnt == 'b0 && hcnt == 'b0 && axis_tvalid ? 1'b1 : 1'b0;
57: /*********************************************************
58: ******************6.sequential declaration****************
```

## in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/awb.v
```text
235:         .DATA_WIDTH(96), .DELAY_CYCLE(50)
236:     ) signal_delay_d (
237:         .I_clk(I_clk), .I_rst_n(I_rst_n), .I_tuser(I_tuser),
238:         .I_valid(I_tvalid_r1), .I_data(I_tdata_d1),
279:             tuser_d1 <= 1'b0;
280:             valid_d2 <= 1'b0;
281:             tuser_d2 <= 1'b0;
282:             for (k = 0; k < 4; k = k + 1) begin
290:             tuser_d1 <= delayed_tuser;
291:             valid_d2 <= valid_d1;
292:             tuser_d2 <= tuser_d1;
293:             if (valid_d1) begin
302:
303:     assign O_tvalid = valid_d2;
304:     // video_in needs the original early frame pulse to reset its input FIFO
305:     // before the delayed valid pixels arrive. Use delayed_tuser only for gain.
306:     assign O_tuser = I_tuser;
307:     assign O_tlast = !valid_d1 && valid_d2;
308:     assign O_tdata = O_tvalid ? {
309:         sat_q16(mult_r[3]), green_d[3], sat_q16(mult_b[3]),
```

## in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/isp_top.v
```text
47:   wire         awb_O_tuser;  //synthesis keep
48:   wire [ 95:0] awb_O_tdata;  //synthesis keep
49:   wire         awb_O_tvalid;  //synthesis keep
50:   wire         awb_O_tready;  //synthesis keep
56:   wire [95:0] algorithm_data;
57:   wire algorithm_valid, algorithm_user, algorithm_last, algorithm_last_128;
58:   generate
59:   if (EDGE_CONTROL_ENABLE) begin : g_control
64:       end
65:       assign algorithm_last_128 = last_128;
66:       edge_control_stream u_control (
67:           .clk(axi4s_video_aclk), .rst_n(I_rst_n),
68:           .requested_config(I_edge_config),
80:       end
81:       assign algorithm_last_128 = last_128;
82:       edge_detect_96 #(.IMG_WIDTH(1280), .IMG_HEIGHT(720),
83:                        .EDGE_TH(EDGE_THRESHOLD)) u_edge (
92:       assign awb_O_tready = O_tready;
93:       assign algorithm_data = awb_O_tdata;
94:       assign algorithm_valid = awb_O_tvalid;
95:       assign algorithm_user = awb_O_tuser;
96:       assign algorithm_last = awb_O_tlast;
97:       assign algorithm_last_128 = awb_O_tlast;
98:   end
99:   endgenerate
100:   assign O_tdata  = awb_O_tdata_128;
101:   assign O_tlast  = algorithm_last_128;
102:   assign O_tuser  = awb_O_tuser_128    ;
103:   assign O_tvalid = awb_O_tvalid_128   ;
142:     .IMG_WIDTH (1280)
143: ) u_awb (
144:     .I_clk   (axi4s_video_aclk),
145:     .I_rst_n (I_rst_n),
```

## in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/data128_96/data128_96.v
```text
15:
16:   assign O_tdata = {I_tdata[23:0], I_tdata[55:32], I_tdata[87:64], I_tdata[119:96]};
17:   //assign O_tdata = {I_tdata, I_tdata, I_tdata[55:32], I_tdata[23:0]};
18:
19: endmodule
```

## in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/demosaic_4x_2_0/bilinear_interpolation.v
```text
881:         else if(I_tvalid_r[3])begin
882:             rgb_data0 <= {8'b0, r0_mean_d, g0_mean_d, b0_mean_d};
883:             rgb_data1 <= {8'b0, r1_mean_d, g1_mean_d, b1_mean_d};
884:             rgb_data2 <= {8'b0, r2_mean_d, g2_mean_d, b2_mean_d};
885:             rgb_data3 <= {8'b0, r3_mean_d, g3_mean_d, b3_mean_d};
886:         end
887:     end
```

## in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/edge_control_stream.v
```text
2: // Runtime ORIGIN/EDGE, with five-stage Original delay and frame configuration.
3: // SOF is the existing AWB early notification; it need not coincide with valid.
4: module edge_control_stream #(
5:     parameter integer IMG_WIDTH = 1280,
26:         if (!rst_n) begin
27:             valid_p <= 0; user_p <= 0; last_p <= 0;
28:             for (i=0; i<5; i=i+1) begin
29:                 original_p[i] <= 0; config_p[i] <= {1'b1,8'd80};
35:             end
36:             valid_p <= {valid_p[3:0],I_valid};
37:             user_p <= {user_p[3:0],I_user};
38:             last_p <= {last_p[3:0],I_last};
48:     );
49:     wire [95:0] selected_data = config_p[4][8] ? edge_data : original_p[4];
50:     edge_status_osd #(.IMG_WIDTH(IMG_WIDTH), .IMG_HEIGHT(IMG_HEIGHT),
51:                      .ENABLE(OSD_ENABLE)) u_status (
52:         .clk(clk), .rst_n(rst_n), .I_data(selected_data),
53:         .I_valid(valid_p[4]), .I_user(user_p[4]), .I_last(last_p[4]),
54:         .I_config(config_p[4]), .O_data(O_data), .O_valid(O_valid),
```

## in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/video_in.v
```text
9:     input wire[127:0]  I_camera_data,
10:     input wire         I_mipi_rx_error,
11:
12:     input wire         I_ddr_clk,
16:     output wire        O_video_in_wr_busy,
17:     output reg[1:0]    O_video_out_rp,     ///读指针
18:
19:     output reg         O_ddr_user_wr_en,
31:     wire        S_frame_start;
32:     reg[1:0]    S_video_in_wp;       ///写指针
33:     wire[8:0]   S_fifo_rd_num;
34:     wire        S_fifo_rd_en;
97:
98:     assign S_frame_start = ~S_camera_frame_start_extend_3d & S_camera_frame_start_extend_2d;
99:
100: 	/*
104:         if(!I_rst_n)
105:             S_video_in_wp <= 'd0;
106:         else
107:             if(I_display_pause)
108:                 S_video_in_wp <= S_video_in_wp;
109:             else if(S_frame_start)
110:                 begin
111:                     if(I_mipi_rx_error)
112:                         S_video_in_wp <= S_video_in_wp;
113:                     else
114:                         S_video_in_wp <= S_video_in_wp + 'd1;
115:                 end
116:             else
117:                 S_video_in_wp <= S_video_in_wp;
118:     end
119:
122:         if(!I_rst_n)
123:             O_video_out_rp <= 'd0;
124:         else
125:             if(I_display_pause)
126:                 O_video_out_rp <= O_video_out_rp;
127:             else if(S_frame_start)
128:                 begin
129:                     case(S_video_in_wp)
130:                         'd0: O_video_out_rp <= 'd2;
131:                         'd1: O_video_out_rp <= 'd3;
132:                         'd2: O_video_out_rp <= 'd0;
133:                         'd3: O_video_out_rp <= 'd1;
134:                     endcase
135:                 end
136:             else
137:                 O_video_out_rp <= O_video_out_rp;
138:     end
139:
179:         else
180:             if(S_frame_start && (!I_mipi_rx_error))
181:                 begin
182:                     case(S_video_in_wp)
183:                         'd0: O_ddr_user_addr <= IMAGE_BASE_ADDR_0;
184:                         'd1: O_ddr_user_addr <= IMAGE_BASE_ADDR_1;
188:                 end
189: 			else if(S_frame_start && I_mipi_rx_error)
190: 				begin
191:                 	case(S_video_in_wp)
192:                         'd0: O_ddr_user_addr <= IMAGE_BASE_ADDR_3;
193:                         'd1: O_ddr_user_addr <= IMAGE_BASE_ADDR_0;
```

## in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/video_out.v
```text
6:
7:     input wire        I_ddr_clk,
8:     output wire       O_video_out_rd_busy,
9:     input wire        I_video_in_wr_busy,
10:     input wire[1:0]   I_video_out_rp,
11:     output wire       O_ddr_user_rd_en,
12:     output reg[24:0]  O_ddr_user_addr,
16:
17:     input wire        I_dsi_clk,
18:     input wire        I_video_vsync,
19:     input wire        I_video_rd_en,
30:     reg         S_video_vsync_3d;
31:     wire        S_video_frame_start;
32:     wire        S_ddr_rd_trig;
33:     reg         S_ddr_rd_valid;
48:
49:     always @(posedge I_ddr_clk) begin
50:         S_video_vsync_1d <= I_video_vsync;
51:         S_video_vsync_2d <=S_video_vsync_1d;
54:
55:     assign S_video_frame_start = ~S_video_vsync_3d & S_video_vsync_2d;
56:
57:
58:     always @(posedge I_ddr_clk or negedge I_rst_n) begin
59:         if(!I_rst_n)
60:             S_fifo_rst <= 1'b0;
61:         else
62:             if(S_video_frame_start)
63:                 S_fifo_rst <= 1'b1;
64:             else if(S_fifo_rst_cnt == 'd10)
70:
71:     always @(posedge I_ddr_clk) begin
72:         if(S_fifo_rst)
73:             S_fifo_rst_cnt <= S_fifo_rst_cnt + 'd1;
86:     */
87:     always @(posedge I_ddr_clk or negedge I_rst_n) begin
88:         if(!I_rst_n)
89:             S_ddr_rd_valid <= 1'b0;
100:
101:     always @(posedge I_ddr_clk) begin
102:         if(S_ddr_rd_valid)
103:             begin
113:
114:     always @(posedge I_ddr_clk or negedge I_rst_n) begin
115:         if(!I_rst_n)
116:             O_ddr_user_addr <= 'd0;
117:         else
118:             if(S_video_frame_start)
119:                 begin
120:                     case(I_video_out_rp)
121:                         'd0: O_ddr_user_addr <= IMAGE_BASE_ADDR_0;
122:                         'd1: O_ddr_user_addr <= IMAGE_BASE_ADDR_1;
139:
140:         .clkw       ( I_ddr_clk           ),
141:         .we         ( I_ddr_user_rd_valid ),
142:         .di         ( I_ddr_user_rd_data  ),
146:
147:         .clkr       ( I_dsi_clk           ),
148:         .re         ( S_fifo_rd_en        ),
149:         .dout       ( S_fifo_rd_data      ),
156:
157:    always @(posedge I_dsi_clk) begin
158:        if(I_video_rd_en)
159:            S_fifo_rd_cnt <= S_fifo_rd_cnt + 'd1;
167:
168:    always @(posedge I_dsi_clk) begin
169:        S_video_rd_en_1d  <= I_video_rd_en;
170:        S_fifo_rd_cnt_1d  <= S_fifo_rd_cnt;
173:
174:    always @(posedge I_dsi_clk) begin
175:        if(S_video_rd_en_1d)
176:            begin
```

## in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/hdmi_mixer.v
```text
24:     output reg        O_hdmi_de,
25:     output reg[23:0]  O_hdmi_data
26: );
27:
34:     reg [23:0] S_video_data_1d;
35:     reg [23:0] S_video_data_2d;
36:     reg [11:0] S_x;
37:     reg [11:0] S_y;
38:     reg [11:0] S_x_1d;
39:     reg [11:0] S_x_2d;
40:     reg [11:0] S_y_1d;
41:     reg [11:0] S_y_2d;
550:             S_x_1d <= 12'd0;
551:             S_x_2d <= 12'd0;
552:             S_y_1d <= 12'd0;
553:             S_y_2d <= 12'd0;
556:             S_x_1d <= S_x;
557:             S_x_2d <= S_x_1d;
558:             S_y_1d <= S_y;
559:             S_y_2d <= S_y_1d;
614:         if(S_video_de_2d) begin
615:             if((S_x_2d >= LOGO_X) && (S_x_2d < (LOGO_X + LOGO_W)) &&
616:                (S_y_2d >= LOGO_Y) && (S_y_2d < (LOGO_Y + LOGO_H))) begin
617:                 S_logo_x = S_x_2d - LOGO_X;
618:                 S_logo_y = S_y_2d - LOGO_Y;
619:                 S_logo_addr = S_logo_y * LOGO_W + S_logo_x;
626:             if((!S_osd_hit) &&
627:                (S_x_2d >= DYN_OSD_X) && (S_x_2d < (DYN_OSD_X + DYN_OSD_W)) &&
628:                (S_y_2d >= DYN_OSD_Y) && (S_y_2d < (DYN_OSD_Y + DYN_OSD_H))) begin
629:                 S_dyn_x = S_x_2d - DYN_OSD_X;
630:                 S_dyn_y = S_y_2d - DYN_OSD_Y;
631:
829:             O_hdmi_de        <= 1'b0;
830:             O_hdmi_data      <= 24'd0;
831:         end
832:         else begin
844:             S_video_data_1d  <= I_video_rd_data;
845:             S_video_data_2d  <= S_video_data_1d;
846:
847:             if(DEBUG_MODE == 1) begin
849:                     if(S_x < 12'd128)
850:                         O_hdmi_data <= 24'hff0000;
851:                     else if(S_x < 12'd256)
852:                         O_hdmi_data <= 24'h00ff00;
853:                     else if(S_x < 12'd384)
854:                         O_hdmi_data <= 24'h0000ff;
855:                     else if(S_x < 12'd512)
856:                         O_hdmi_data <= 24'hffff00;
857:                     else if(S_x < 12'd640)
858:                         O_hdmi_data <= 24'h00ffff;
859:                     else if(S_x < 12'd768)
860:                         O_hdmi_data <= 24'hff00ff;
861:                     else if(S_x < 12'd896)
862:                         O_hdmi_data <= 24'hffffff;
863:                     else
864:                         O_hdmi_data <= 24'h202020;
865:                 end
866:                 else begin
867:                     O_hdmi_data <= 24'd0;
868:                 end
869:             end
872:                     case (I_debug_status)
873:                         4'b0000: O_hdmi_data <= 24'h000000;
874:                         4'b0001: O_hdmi_data <= 24'hff0000;
875:                         4'b0011: O_hdmi_data <= 24'hffff00;
876:                         4'b0111: O_hdmi_data <= 24'h00ff00;
877:                         4'b1111: O_hdmi_data <= I_video_rd_data;
878:                         default: O_hdmi_data <= 24'h0000ff;
879:                     endcase
880:                 end
881:                 else begin
882:                     O_hdmi_data <= 24'd0;
883:                 end
884:             end
887:                     if(S_x < 12'd256)
888:                         O_hdmi_data <= I_debug_status[0] ? 24'hff8000 : 24'h201000;
889:                     else if(S_x < 12'd512)
890:                         O_hdmi_data <= I_debug_status[1] ? 24'hffff00 : 24'h202000;
891:                     else if(S_x < 12'd768)
892:                         O_hdmi_data <= I_debug_status[2] ? 24'hff0000 : 24'h200000;
893:                     else
894:                         O_hdmi_data <= I_debug_status[3] ? 24'h00ffff : 24'h002020;
895:                 end
896:                 else begin
897:                     O_hdmi_data <= 24'd0;
898:                 end
899:             end
901:                 if(S_osd_hit)
902:                     O_hdmi_data <= S_osd_color;
903:                 else
904:                     O_hdmi_data <= S_video_data_2d;
905:             end
906:         end
```

## in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/data_96bit_to_128bit.v
```text
26:
27: 		O_128b_frame_start <= I_96b_frame_start;
28:     end
29:
32:         if(I_96b_valid)
33:             S_cnt <= S_cnt + 'd1;
34:         else
35:             S_cnt <= 'd0;
36:     end
37:
44:                         begin
45:                             O_128b_valid <= 1'b0;
46:                             O_128b_data  <= 'd0;
47:                         end
49:                         begin
50:                             O_128b_valid <= 1'b1;
51:                             O_128b_data  <= {S_96b_data_1d,I_96b_data[95:64]};
52:                         end
54:                         begin
55:                             O_128b_valid <= 1'b1;
56:                             O_128b_data  <= {S_96b_data_1d[63:0],I_96b_data[95:32]};
57:                         end
59:                         begin
60:                             O_128b_valid <= 1'b1;
61:                             O_128b_data  <= {S_96b_data_1d[31:0],I_96b_data};
62:                         end
64:                         begin
65:                             O_128b_valid <= 1'b0;
66:                             O_128b_data  <= 'd0;
67:                         end
71:             begin
72:                 O_128b_valid <= 1'b0;
73:                 O_128b_data  <= 'd0;
74:             end
```

## in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display.al
```text
1: <?xml version="1.0" encoding="UTF-8"?>
2: <Project Version="3" Minor="2" Path="D:/anlogic_formal_project/in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project">
3:     <Project_Created_Time></Project_Created_Time>
4:     <TD_Encoding>UTF-8</TD_Encoding>
53:             </File>
54:             <File Path="../user_source/hdl_source/awb.v">
55:                 <FileInfo>
56:                     <Attr Name="UsedInSyn" Val="true"/>
411:         <SDC_FILE>
412:             <File Path="camera_to_dsi_display.sdc">
413:                 <FileInfo>
414:                     <Attr Name="UsedInSyn" Val="true"/>
493:     </FileSets>
494:     <TOP_MODULE>
495:         <LABEL>design_top_wrapper</LABEL>
496:         <MODULE>design_top_wrapper</MODULE>
497:         <CREATEINDEX>user</CREATEINDEX>
498:     </TOP_MODULE>
499:     <Property>
500:     </Property>
511:     <Runs>
512:         <Run Name="syn_1" Type="Synthesis" ConstraintSet="constraint_1" Description="" Active="true" useDefaultScript="false">
513:             <Strategy Name="Default_Synthesis_Strategy">
514:             </Strategy>
517:         </Run>
518:         <Run Name="phy_1" Type="PhysicalDesign" ConstraintSet="constraint_1" Description="" SynRun="syn_1" Active="true">
519:             <Strategy Name="Default_PhysicalDesign_Strategy">
520:                 <BitgenProperty::GeneralOption>
```

## in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display.sdc
```text
1: create_clock -name {sys_clk_50m} -period 20.000 -waveform {0.000 10.000} [get_ports {I_sys_clk}]
2: create_clock -name {mipi_rx_ck_pad} -period 4.167 -waveform {0.000 2.083} [get_nets {IO_rx_clk_pad_p}]
3:
4: derive_clocks
5:
6: rename_clock -name {pll_clk_100m} [get_clocks {u_PLL/ph1p_phy_pll_wrapper_25a56e5ce2f9_Inst/u_PH1P_PHY_PLL.clkc[0]}]
7: rename_clock -name {pll_clk_24m} [get_clocks {u_PLL/ph1p_phy_pll_wrapper_25a56e5ce2f9_Inst/u_PH1P_PHY_PLL.clkc[1]}]
8: rename_clock -name {HDMI_PIXEL_CLK} [get_clocks {u_PLL/ph1p_phy_pll_wrapper_25a56e5ce2f9_Inst/u_PH1P_PHY_PLL.clkc[4]}]
9: rename_clock -name {HDMI_SERIAL_CLK} [get_clocks {u_PLL/ph1p_phy_pll_wrapper_25a56e5ce2f9_Inst/u_PH1P_PHY_PLL.clkc[5]}]
10:
11: rename_clock -name {MIPI_RX_BYTE_CLK} [get_clocks {u_mipi_dphy_rx_ph1p_mipiio_wrapper/u_ph1p_mipiio_rx_wrapper/u_PH1P_LOGIC_DPHY_MIPI_RX.o_fabric_div4_8_clk}]
12:
13:
14: set_clock_groups -asynchronous \
15:     -group [get_clocks {mipi_rx_ck_pad MIPI_RX_BYTE_CLK}] \
16:     -group [get_clocks {sys_clk_50m pll_clk_100m pll_clk_24m HDMI_PIXEL_CLK HDMI_SERIAL_CLK}] \
```

## in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/ip_source/PLL/Design.xml
```text
25:                 <ipxact:configurableElementValue referenceId="CLK0_ENABLE_DISP">&quot;ENABLE&quot;</ipxact:configurableElementValue>
26:                 <ipxact:configurableElementValue referenceId="CLK0_REQUEST_FREQ_DISP">100.000000</ipxact:configurableElementValue>
27:                 <ipxact:configurableElementValue referenceId="CLK0_REQUEST_FREQ_UNIT_DISP">&quot;MHz&quot;</ipxact:configurableElementValue>
28:                 <ipxact:configurableElementValue referenceId="CLK0_DIVISION_FACTOR_SET_DISP">15</ipxact:configurableElementValue>
32:                 <ipxact:configurableElementValue referenceId="CLK1_ENABLE_DISP">&quot;ENABLE&quot;</ipxact:configurableElementValue>
33:                 <ipxact:configurableElementValue referenceId="CLK1_REQUEST_FREQ_DISP">24.000000</ipxact:configurableElementValue>
34:                 <ipxact:configurableElementValue referenceId="CLK1_REQUEST_FREQ_UNIT_DISP">&quot;MHz&quot;</ipxact:configurableElementValue>
35:                 <ipxact:configurableElementValue referenceId="CLK1_DIVISION_FACTOR_SET_DISP">63</ipxact:configurableElementValue>
43:                 <ipxact:configurableElementValue referenceId="CLK4_ENABLE_DISP">&quot;ENABLE&quot;</ipxact:configurableElementValue>
44:                 <ipxact:configurableElementValue referenceId="CLK4_REQUEST_FREQ_DISP">74.250000</ipxact:configurableElementValue>
45:                 <ipxact:configurableElementValue referenceId="CLK5_ENABLE_DISP">&quot;ENABLE&quot;</ipxact:configurableElementValue>
46:                 <ipxact:configurableElementValue referenceId="CLK5_REQUEST_FREQ_DISP">371.250000</ipxact:configurableElementValue>
47:                 <ipxact:configurableElementValue referenceId="CLK6_ENABLE_DISP">&quot;DISABLE&quot;</ipxact:configurableElementValue>
48:                 <ipxact:configurableElementValue referenceId="CLK7_ENABLE_DISP">&quot;DISABLE&quot;</ipxact:configurableElementValue>
362:                 <ipxact:configurableElementValue referenceId="FBMODE_IS_ZERODELAY">0</ipxact:configurableElementValue>
363:                 <ipxact:configurableElementValue referenceId="CLK7_REQUEST_FREQ_DISP">100.000000</ipxact:configurableElementValue>
364:                 <ipxact:configurableElementValue referenceId="CLK7_DIVISION_FACTOR_SET_DISP">12</ipxact:configurableElementValue>
365:                 <ipxact:configurableElementValue referenceId="CLK7_REQUEST_PHASE_SHIFT_DISP">0.0000</ipxact:configurableElementValue>
```

## in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/ph1p35_ddr/ph1p35_324_ddr_wrapper.v
```text
60:     assign O_init_calib_complete = ddrphy_rdy;
61:     assign O_ddr_clk = dhi_clk;
62:
63:     assign paxi_awaddr              = I_mc_app_cmd[0]  ? 'b0 : I_mc_app_addr    ;
82:         .apb_prst_n   ( I_sys_rst_n  ),
83:         .dhi_clk      ( dhi_clk      ),
84:         .cfg_clk      (  ),
85:         .ddrphy_rst_n (  ),
```

## features/color_target/rtl/color_target_detect_stream.v
```text
6: module color_target_detect_stream #(
7:     parameter integer FILTER_ENABLE=0, WIDTH=1280, HEIGHT=720, XW=11, YW=10,
8:     parameter integer TARGET_CLASS=0, HUE_HALF_WIDTH_DEG=30,
9:     parameter integer C_MIN=24, V_MIN=32, MIN_COUNT=64
34:     // that frame's autonomous tail (there is no longer an open input frame).
35:     reg input_open, input_bad;
36:     always @(posedge clk or negedge rst_n) begin
37:         if (!rst_n) begin input_open<=0; input_bad<=0; end
38:         else if (I_pixel_valid && I_sof) begin
39:             input_open<=!I_eof; input_bad<=I_frame_abort;
40:         end else begin
41:             if (I_frame_abort && input_open) input_bad<=1;
42:             if (I_pixel_valid && I_eof) input_open<=0;
43:         end
44:     end
50:     wire [31:0] fsession, fframe;
51:     color_target_support3 #(.ENABLE(FILTER_ENABLE),.WIDTH(WIDTH),.HEIGHT(HEIGHT),
52:         .XW(XW),.YW(YW)) u_filter (
53:         .clk(clk),.rst_n(rst_n),.I_pixel_valid(I_pixel_valid),.I_mask(mask),
57:         .O_session_id(fsession),.O_frame_id(fframe),.O_frame_abort(fa),.O_protocol_error(filter_error));
58:     color_target_mask_stats #(.WIDTH(WIDTH),.HEIGHT(HEIGHT),.XW(XW),.YW(YW),
59:         .MIN_COUNT(MIN_COUNT),.TARGET_CLASS(TARGET_CLASS)) u_stats (
60:         .clk(clk),.rst_n(rst_n),.I_pixel_valid(fv),.I_mask(fm),.I_x0(fx),.I_y(fy),
```

## features/color_target/rtl/color_target_track.v
```text
59:     output reg [YW-1:0] O_out_ymin, O_out_ymax, O_out_center_y,
60:     output reg [31:0]   O_out_session_id, O_out_frame_id,
61:     output reg          O_state_change     // 状态发生变化时的一拍脉冲
62: );
80:
81:     wire strobe = I_result_strobe && I_result_valid;
82:     wire session_new = (I_session_id != cur_session);
83:
84:     // 新会话一律按"未开始跟踪"评估本帧，而不是把它丢掉
85:     wire [1:0] eff_state = session_new ? S_SEARCH : state;
86:     wire [7:0] eff_acq   = session_new ? 8'd0     : acq_cnt;
87:     wire [7:0] eff_lost  = session_new ? 8'd0     : lost_cnt;
88:     wire eff_tracked = (eff_state == S_TRACK) || (eff_state == S_HOLD);
89:
105:         nxt_lost  = eff_lost;
106:         if (strobe) begin
107:             if (accept) begin
108:                 nxt_acq  = eff_acq + 8'd1;
141:             O_out_ymin <= {YW{1'b0}}; O_out_ymax <= {YW{1'b0}}; O_out_center_y <= {YW{1'b0}};
142:             O_out_session_id <= 32'd0; O_out_frame_id <= 32'd0;
143:         end else begin
144:             if (strobe) begin
145:                 state    <= nxt_state;
146:                 acq_cnt  <= nxt_acq;
155:                     O_out_center_x  <= I_center_x;  O_out_center_y <= I_center_y;
156:                     O_out_session_id<= I_session_id;O_out_frame_id <= I_frame_id;
157:                 end
158:                 O_track_state  <= nxt_state;
```

## features/color_target/rtl/color_target_text_overlay.v
```text
139:                           (I_state    != raw_state) || (I_show != raw_show);
140:     wire start = (cst == C_IDLE) && (I_update || inputs_changed);
141:
142:     // 本轮要转换的值（只从本事务快照取）
170:                     if (start) begin
171:                         raw_c <= I_count; raw_x <= I_center_x; raw_y <= I_center_y;
172:                         raw_state <= I_state; raw_show <= I_show;
173:                         round <= 2'd0;
196:                         default: begin
197:                             dig_c <= next_c; dig_x <= next_x; dig_y <= bcd[11:0];
198:                             shown_state <= raw_state; shown_show <= raw_show;
199:                         end
```

## scripts/prepare_td_runs.py
```text
2:
3: TD's .al text contains an unescaped '&' in attribute names, so preserve its
4: native format rather than parsing/reformatting with a standard XML library.
5: Existing TD settings.cfg must have been generated by opening the project once.
6: """
7: from pathlib import Path
18:         directory = PROJECT / f"{NAME}_Runs" / run
19:         if not (directory / "settings.cfg").exists():
20:             raise RuntimeError("Open the .al in TD to generate run settings first")
21:         prepared = re.sub(
29:         prepared = re.sub(r"    <Project_Settings>.*?</Project_Settings>\s*", "", prepared, flags=re.S)
30:         (directory / f"{NAME}.prj").write_text(prepared, encoding="utf-8")
31:         print(f"Prepared {run}: {len(re.findall('<File Path=', prepared))} source/IP/constraint entries")
32:
```

## artifacts/bitstreams/EDGE_CONTROL_V1/BUILD_INFO.md
```text
5: | Version / Git Branch | `EDGE_CONTROL_V1` / `main` |
6: | Git Commit SHA（实际构建源码/配置） | `dff499a75cf0a348aaf2167548b4fe34bf4a78a9` |
7: | Git Tag（归档candidate提交） | `edge-control-v1-candidate`；`git rev-parse edge-control-v1-candidate^{commit}` 得到包含本bit/报告的唯一提交SHA；RTL/配置与上列构建提交一致 |
8: | Build Time | 2026-10-10，Synthesis 23:00:26–23:04:16；Physical/Timing/bitgen 23:05:00–23:09:25，TD本地时间 |
18: | DSP | 9 / 40（22.50%） |
19: | Setup WNS / TNS / 违例端点 | +0.100 ns / 0.000 ns / 0 |
20: | Hold WNS / TNS / 违例端点 | +0.020 ns / 0.000 ns / 0 |
21: | 新的关键warning | 无新增关键类型；既有PHY-5060与PHY-5079保留，未宣称无warning |
22: | Board Test Status | **待用户上板**；功能实测与至少30分钟稳定性尚未完成 |
23:
24: ## 控制、冻结与实现
25:
26: 用户允许修改旧未使用的按键输入。用户原理图第3/8文件确认K3=KEY2/B9→I_button[0]，K4=KEY3/C7→I_button[1]，3.3V上拉、低有效；N2/J14是扩展GPIO。K3一次消抖按下切换一次；K4短按释放−10，长按约0.7秒+10一次且释放不减；10–250饱和，默认EDGE/080。两级输入同步，480000周期消抖/16800000周期长按，按24MHz名义约20ms/0.7s；冻结STA时钟为23.810MHz（约20.16ms/0.706s），未修改PLL或SDC。
27:
28: 解除Top的ae_set实例，S_ae_req固定0，S_ae固定1990，S_ag固定未使用值0，不可由按键触发曝光/增益写入。初始化表及其控制保持原样：Exposure1990 half-lines、VTS1000、HTS1600、Gain1f/3f=15.75×、Digital Gain、BLC15、AWB_V2全部参数、demosaic、MIPI、DDR配置、HDMI、PLL/SDC冻结。pin.adc只修改两键为纯INPUT/B9/C7并移除这两项无效DRIVESTRENGTH。
41:
42: 相对固定EDGE增加550 LUT6、761 FF、442 Slice、5 ERAM，DSP不变。工具恢复彩色数据通路/FIFO并重新优化，不能把总资源差简单全归因于按键模块。最差setup仍在HDMI_PIXEL_CLK；MIPI_RX_BYTE_CLK本域Setup WNS+2.402ns。STA覆盖96.14%，既有异步时钟分组及IP约束未改；不能将零违例解释成覆盖全部异步物理行为。
43:
44: ## 验证证据与失败记录
```

## artifacts/bitstreams/EDGE_CONTROL_V1/build_evidence/final_timing_summary.txt
```text
7: Speed               : 3
8: STA coverage        : 96.14%
9: Constraint File     : D:/anlogic_formal_project/in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display.sdc;
10: Confidence          : Routed
26: --------------------
27: 	SWNS: 0.100ns, STNS: 0.000ns
28: 	HWNS: 0.020ns, HTNS: 0.000ns
29: 	Period Check WNS: 12.200ns
30:
36: --------------------------------------------------------------------------------
37:            clk0:       59.995         5776   MIPI_RX_BYTE_CLK
38:            clk1:       66.667         2413   u_ph1p35_324_ddr_wrapper/u_ddr2/usr_clk
39:            clk2:       75.002         1011   HDMI_PIXEL_CLK
40:            clk3:       23.810          108   pll_clk_24m
41:            clk4:       50.000           92   sys_clk_50m
42:            clk5:      375.094           38   HDMI_SERIAL_CLK
```
