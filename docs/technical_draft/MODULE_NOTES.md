# 模块注意事项与代码对应

基于固定提交 7cffe56c384340f59a526da80a2ac3f3018bf209，本页是技术文档的实现索引，不改变RTL。

| 部分 | 活动源码 | 注意事项 |
|---|---|---|
| 顶层和工程入口 | [design_top_wrapper.v](../../in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/design_top_wrapper.v) | 以TD实际入口为准；不把独立目录视为已接入 |
| 应用接线 | [edge_control_stream.v](../../in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/edge_control_stream.v) | 颜色和尺寸在效果前取样，统计不能门控视频写入；帧结果带LAST年龄 |
| 颜色统计 | [color_compare_stats.v](../../in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/color_compare_stats.v) | 两ROI各16384像素；RGB差不是ΔE；阈值12是演示值 |
| 颜色及测量OSD | [color_compare_osd.v](../../in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/color_compare_osd.v) | 文字/几何快照统一；透明空字点不等于显隐已实板验证 |
| 平面统计 | [planar_measure_stats.v](../../in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/planar_measure_stats.v) | 单件薄片、ROI不触边；W/H轴对齐；GAP只是固定中心截线 |
| 标定 | [inspection_calibration.v](../../in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/inspection_calibration.v) | 100mm两轴手动标定；默认SPAN256和CAL:OK不是刻度对齐证据 |
| 人机控制 | [inspection_control.v](../../in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/inspection_control.v) | SW逻辑编号不等于实板位置；第四物理开关显隐尚未通过 |
| 风格化 | [style_fill_96.v](../../in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/style_fill_96.v) | 局部同色均值、共享明度和暗侧描边；不能拿渲染像素做计量 |
| Gaussian | [gaussian_pair_3x3.v](../../in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/gaussian_pair_3x3.v) | 像素对灰度结构；抑噪会弱化细节 |
| Sobel | [edge_detect_96.v](../../in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/edge_detect_96.v) | 内部像素对处理；不宣称全1280点独立Sobel |
| NMS | [nms_gradient_pair_3x3.v](../../in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/nms_gradient_pair_3x3.v) | 有空间窗口偏移和边界屏蔽，注意元数据对齐 |
| 弱边连接 | [edge_link_pair_3x3.v](../../in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/edge_link_pair_3x3.v) | 文件存在性由manifest核验；有界传播不是全递归Canny |
| 时间保持 | [edge_temporal_hold.v](../../in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/edge_temporal_hold.v) | 历史仅限定义的单帧支持，不能宣传任意运动追踪 |
| 采集与缓存 | [video_in.v](../../in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/video_in.v) | 提前帧通知需保留，FIFO溢出/Gray约束风险未关闭 |
| 读出与拆包 | [video_out.v](../../in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/video_out.v) | CNT不证明相机活性；本应用LAST不是DDR同帧身份 |
| HDMI显示 | [hdmi_mixer.v](../../in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/hdmi_mixer.v) | Logo地址重定时须保持外部时序；Logo/安路不得被覆盖 |

## 证据和验收口径

- 代码存在、仿真通过、P&R通过、bit已归档、实板局部可见、精度验收通过分开记录。
- 当前最新板测结论见[10月30日反馈](../INSPECTION_UI_DIMENSION_V1_BOARD_FEEDBACK_2026-10-30.md)，为PARTIAL；不能直接引用旧BUILD_INFO的NOT_RUN覆盖新反馈，也不能改写构建时历史。
- GPIO映射与极性按最新BOARD_TEST核实；未知时先只读诊断，不盲改引脚。K1/K2电压不兼容问题有历史记录，不擅自使用。
- 颜色应用只做相机RGB码值差；未建立CIE色度溯源、标准ΔE或材质分类能力。
- 尺寸0.1mm为显示步长，准确度/重复性待独立工件真值试验；没有高度、畸变/透视修正、任意CAD重建或自动圆拟合。
- 当前颜色/尺寸是固定ROI应用，不是将队友TARGET/LATENCY全部整机接入的证据；不要复用旧整合计划当成完成证明。
- 保留用户关于STYLE V2效果不错的定性反馈，不扩写成全部赛题验收完成。
- 实物照片、原始图像、拍屏、合成图分别标注；反光人物照片不自动发布。
- 商业IM-X1000样本只借鉴应用/展示，性能不移植，原PDF未纳入本次上传。

## 后续文档补齐

1. 机械装配CAD、尺寸/平面度和光照布局；实物正面、45度、相机和载物面照片。
2. 当前板卡型号、外设与电源清单、物理开关与逻辑输入的逐项对应。
3. 同平面100mm尺子两轴对齐记录、不同位置/旋转与10次重复读数、误差统计。
4. 固定颜色样品重复性、光照变化和饱和/暗区失效示例，不只展示MATCH成功样本。
5. 30分钟稳定性、B/S计数、冷启动和异常恢复证据；缺少仪器时填未测。
6. 最终bit及源码输入manifest、git tag、真实资源和STA覆盖；不移动旧tag。
