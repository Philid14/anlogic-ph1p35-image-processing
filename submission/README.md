# FINAL_SUBMISSION_V1 最终代码交付入口

仓库：https://github.com/Philid14/anlogic-ph1p35-image-processing （Private，main为整合主线）。固定代码版本使用tag `final-submission-v1.1`。本目录是提交资料入口，正式RTL仍在原TD工程目录，避免移动路径破坏IP和约束。

## 可烧录文件

`artifacts/bitstreams/LATENCY_FRAME_FIX_V1/camera_to_dsi_display.bit`。SHA256：`d516c1d81ec30999d3510ac82e32e354dd31e1e40dd374ad376e2b572a1f2c16`。

真实测量源码 `ebbd3cd7b41bde86c06bdd5bc436dcb3195990d8`；原归档tag `latency-frame-fix-v1-candidate`。Setup/Hold +0.137/+0.020ns；Slice19177、LUT6 18498、FF16374、ERAM105、DSP25。当前交付未改变95项实际构建输入，沿用这个已完整构建的bit，不伪造一次新硬件构建。完整构建证据仍在同目录build_evidence；RAR保留BUILD_INFO和源清单，Git中保留全部证据。

仅PROGRAM_SRAM先做验收；FLASH只保存固件，标尺和空背景等运行状态仍需重新学习。此前随机延迟DEMO已撤下，当前无模拟延迟，BAD或N0如实显示。

## 工程与重建

TD入口：`in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display.al`。推荐已验证Tang Dynasty6.2，PH1P35MDG324 speed3及相应安路IP环境。保持原PLL、引脚、SDC和ROM初始化文件。

1. 解压整个RAR，保留目录层次；TD打开上述.al。
2. 完整Synthesis → Physical Design → Timing Check → bitgen；必须确认最终Setup/Hold非负。
3. 新构建是新实验，按AGENTS归档源码commit、bit和哈希，不能覆盖原归档。
4. Python3执行 `python scripts/submission_package.py verify`，核对95项正式输入及当前bit哈希。
5. 可选原生ModelSim：`python tests/run_latency_frame_fix.py`。需对应安路ERAM/GSR库；工具路径适配见tests/vision_sim.py。仿真不代替实板。

本RAR精简为正式.al的全部有效RTL、IP内部依赖、约束、ROM、当前bit和三个构建/校验工具；排除独立未使用模块、历史算法/测试/报告、录像和旧bit。历史版本在仓库tag恢复。Windows需解压到普通路径，尽量避免额外过深嵌套。

## 功能、控件与展示

- K3循环EDGE、ORIGIN、GRAY、BINARY、STYLE、TRACK、MOTION。
- BINARY/EDGE下K4短按减10，长按加10；尺寸CAL下短按K4读厘米尺；尺寸RUN下短按K4学空背景，长按切W/H与D/R。
- 按屏幕SW逻辑四位判断：1000颜色比较，0101尺寸CAL，0100尺寸RUN/DARK，0110尺寸RUN/BRIGHT，0000关闭应用叠加。不是实体左右顺序；SW5/6不是新增用户GPIO。
- 颜色两小ROI显示RGB、差值、CHR/DV及MATCH/LIGHT/CHECK/DIFF，均匀漫射光下使用；不是标准色差仪或ΔE。
- 尺寸是正俯视、同平面、单件薄工件：厘米尺近似标尺，W/H、手选D/R及轴对齐T/L的S/T/A/B/V；不是任意圆弧/CAD拟合，不测高度，显示小数位不等于物理精度。
- TRACK是单一主红色连续区域的LAST框，MOTION是32×16块帧差/橙红点阵；均不是神经网络识别或物体独立计数，可滞后一采集帧。
- 延迟常显真实LAT/MIN/MAX/AGE和F/N/E、C/W/D。未匹配或异常帧拒绝统计；不能用零或BAD说明延迟已通过。

具体流程和限制见 [验收清单](ACCEPTANCE.md)、[集成记录](INTEGRATION.md) 及 [文档更新说明](TECHNICAL_REPORT_ADDENDUM.md)。
