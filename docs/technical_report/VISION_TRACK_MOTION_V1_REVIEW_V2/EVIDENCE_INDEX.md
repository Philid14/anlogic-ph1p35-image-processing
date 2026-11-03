# 技术报告证据索引

本稿读取固定提交 `123186a9d339990b207b846cb15e6a7e309c22a7`，实际TD输入 `c3bdf9240647d9f98a2ff68c416693ad1e20f4b9`。候选不等于已合并main；文档分支从main `c42168e26026425660f2a6f51eec76b04c85eea0`创建。

| 支撑内容 | 固定来源 |
| --- | --- |
| 整体结构、TRACK/MOTION、完整性与LAST | [docs/VISION_TRACK_MOTION_V1_DESIGN.md](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/docs/VISION_TRACK_MOTION_V1_DESIGN.md) |
| 17帧回归与资源比较、已知限制 | [docs/VISION_TRACK_MOTION_V1_REPORT.md](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/docs/VISION_TRACK_MOTION_V1_REPORT.md) |
| 候选身份、bit哈希、Board NOT_RUN | [artifacts/bitstreams/VISION_TRACK_MOTION_V1/BUILD_INFO.json](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/artifacts/bitstreams/VISION_TRACK_MOTION_V1/BUILD_INFO.json) |
| 实际布局布线面积 | [artifacts/bitstreams/VISION_TRACK_MOTION_V1/build_evidence/phy_camera_to_dsi_display_phy.area](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/artifacts/bitstreams/VISION_TRACK_MOTION_V1/build_evidence/phy_camera_to_dsi_display_phy.area) |
| 实际最终时序、时钟与覆盖率 | [artifacts/bitstreams/VISION_TRACK_MOTION_V1/build_evidence/phy_final_timing.rpt](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/artifacts/bitstreams/VISION_TRACK_MOTION_V1/build_evidence/phy_final_timing.rpt) |
| 全图搜索、可靠性、共用X/Y尺度 | [docs/INSPECTION_USABILITY_V4_DESIGN.md](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/docs/INSPECTION_USABILITY_V4_DESIGN.md) |
| 自动标尺的1mm输入与100mm等效跨度 | [docs/INSPECTION_AUTO_DIMENSION_V2_DESIGN.md](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/docs/INSPECTION_AUTO_DIMENSION_V2_DESIGN.md) |
| 当前板测步骤 | [docs/VISION_TRACK_MOTION_V1_BOARD_TEST.md](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/docs/VISION_TRACK_MOTION_V1_BOARD_TEST.md) |

## 源码定位

| 文件 | 行号与内容 |
| --- | --- |
| [design_top_wrapper.v](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/design_top_wrapper.v) | L55: `wire 			S_ae_req;`<br>L437: `assign S_ae_req = 1'b0;`<br>L439: `assign S_ag = 16'd0; // unused while S_ae_req=0, not a sensor gain encoding`<br>L441: `edge_key_control #(.VISION_ENABLE(1)) u_edge_keys (`<br>L456: `.I_ae_req(S_ae_req),`<br>L591: `isp_top #(.EDGE_CONTROL_ENABLE(1), .DENOISE_ENABLE(1), .NMS_ENABLE(1), .QUALITY_ENABLE(1), .QUALITY_HOPS(4), .RELIABILITY_ENABLE(1), .TEMPORAL_ENABLE(1), .COLOR_COMPARE_ENABLE(1), .INSPECTION_ENABLE(1),.AUTO_DIMENSION(1),.USABILITY_ENABLE(1),.INSPECTION_V4(1),.VISION_ENABLE(1)) u_isp_top (`<br>L737: `.H_FrameSize  ( 1650 ),`<br>L741: `.V_FrameSize  ( 750  ),` |
| [edge_key_control.v](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/edge_key_control.v) | L49: `parameter integer VISION_ENABLE = 0,`<br>L54: `output reg [18:0] requested_config`<br>L71: `if (!rst_n) requested_config <= {MODE_EDGE,8'd80,8'd130};`<br>L75: `case(requested_config[18:16])`<br>L76: `MODE_EDGE: requested_config[18:16]<=MODE_ORIGIN;`<br>L77: `MODE_ORIGIN: requested_config[18:16]<=MODE_GRAY;`<br>L78: `MODE_GRAY: requested_config[18:16]<=MODE_BINARY;`<br>L79: `MODE_BINARY: requested_config[18:16]<=MODE_STYLE;` |
| [color_compare_osd.v](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/color_compare_osd.v) | L57: `wire chroma_reliable=ref_sum>=96 && test_sum>=96 && ref_value>=32 && test_value>=32 && ref_value<254 && test_value<254;`<br>L64: `wire [1:0] comparison_status=!INSPECTION_V4?(compare_match?0:1):!chroma_reliable?3:compare_match?0:chroma_difference<=6?2:1;`<br>L165: `if(field<4)number=held_calibrated ? pixel_span*20'd1000+(axis_span>>1) : pixel_span*20'd10;`<br>L178: `number=norm_channel*20'd255+(axis_span>>1);`<br>L380: `if(!chroma_reliable && column>=4 && column<=6)character="-";`<br>L656: `(!held_valid \|\| !formatted)?24'hffff00:comparison_status==0?24'h40ff80:comparison_status==2?24'hffff00:24'hff8040;` |
| [planar_measure_stats.v](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/planar_measure_stats.v) | L6: `parameter WIDTH=1280,HEIGHT=720,X0=256,X1=1024,Y0=160,Y1=544,`<br>L8: `parameter MIN_ROW=8,MIN_ROWS=3,MIN_AREA=64`<br>L73: `wire object_ok=rows>=MIN_ROWS && area>=MIN_AREA && maxx>=minx && maxy>=miny &&` |
| [ruler_area_calibration.v](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/ruler_area_calibration.v) | L164: `if(best_count>=24 && best_weight>=256 &&`<br>L174: `if(qnext>=200 && qnext<=1600)begin`<br>L176: `span<=(qnext+anchor+1'b1)>>1;calibrated<=1;status<=3;state<=IDLE;` |
| [vision_source_observer.v](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/vision/vision_source_observer.v) | L4: `module vision_source_observer #(parameter WIDTH=1280,HEIGHT=720,MAX_AGE_CYCLES=6000000)(`<br>L5: `input clk,rst_n,input [95:0] rgb,input [31:0] gray,`<br>L10: `output reg [19:0] target_count,output reg [31:0] target_frame,`<br>L12: `output [2:0] motion_state,output [31:0] motion_frame,`<br>L16: `reg [17:0] beats;reg [31:0] fid,sid;reg [63:0] now_tick,capture_tick,retire_tick;`<br>L17: `reg session_start,cancel_pending,last_target_valid,gap_expired;reg [31:0] cancel_fid,cancel_sid;`<br>L28: `wire [31:0] pixel_fid=user?fid+1'b1:fid;`<br>L30: `wire [31:0] pixel_sid=restart ? sid+1'b1 : sid;` |
| [vision_motion_grid.v](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/vision/vision_motion_grid.v) | L5: `parameter WIDTH=1280,HEIGHT=720,THRESHOLD=12,MIN_CELLS=3`<br>L15: `reg [12:0] horizontal;`<br>L23: `wire [12:0] hsum=(x[4:0]==0?13'd0:horizontal)+beat_sum;`<br>L30: `wire [12:0] final_count={1'b0,count}+changed;`<br>L31: `// 4096x8 true dual-port history: each bank occupies 2048 addresses.`<br>L34: `PH1P_LOGIC_ERAM #(.DATA_WIDTH_A(8),.DATA_WIDTH_B(8),.ADDR_WIDTH_A(12),.ADDR_WIDTH_B(12),`<br>L35: `.DATA_DEPTH_A(4096),.DATA_DEPTH_B(4096),.MODE("DP"),.CLKMODE("SYNC"),`<br>L71: `changed_cells<=pair_valid?final_count[11:0]:12'd0;` |

## 初稿与用户确认

PR #19固定提交 `36cb263c080859d4541dac34212780e268318063` 提供五部分提纲及章节字数上限；它是仓库初稿来源，不据此宣称本轮重新查证了官网所有格式政策。
PR #25固定提交 `449f03ec516c8dc7766ae4dc0750190e4613f440` 提供原Word/PDF，原文件SHA见INITIAL_DRAFT_MANIFEST.json。本稿不覆盖它们。
用户在本聊天明确选择“按最新VISION候选写，保留待板测状态”；先前确认平台/顶部俯拍/置物/遮光可调照明及早期基本画面完成，颜色、尺寸、长稳、帧率/延迟尚未实测。实物确认不是当前bit整机验收。
已登记名称采用用户原文；名称/简介已锁定，本文说明方案演进而不替换登记内容。
全量已读取源码/报告的提交、路径、SHA-256见SOURCE_EVIDENCE_MANIFEST.json；原日志和bit继续位于候选归档。

## 本轮证据边界

本轮只做拉取、源码与归档核对、撰稿、版式渲染及文档检查；没有重新仿真/综合/P&R/生成bit/上板。文中的17帧PASS与WNS均为固定候选已有归档证据，不能记作本轮新实验。
