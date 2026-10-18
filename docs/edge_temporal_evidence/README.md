# 证据边界

- `probe_board_observation.json`：用户真实固定PROBE截图/持续观察，含原附件SHA，未上传带房间背景的原照片。
- `rtl_full.json`：新增AWB/OSD/capture/packet数字测试，初始完整检查点。
- `rtl_capture_final.json`：最终带SOF周期时间戳的完整8帧ROI复测，合成RGB。
- `regression_summary.json`：旧完整PROBE及QUALITY/控制回归已执行结果。
- `probe_regression_full.json`：旧PROBE完整回归原始返回日志与摘要。
- `isp_integration.txt`：实际ISP边界强制后的采样接线/CRC/pack检查日志，非真实PHY仿真。
- `transport_tests.json`、`synthetic_transport_preview.jpg`：软件光学失真测试，预览不是板上采样数据。
- `research_tool_tests.json`：移动细线合成反例，不是现场算法排名。
- `packet_singleport.json`及`build_r0_aborted/`：页面RAM单写口修正对照和过量资源首轮中断证据，首轮未生成新bit。

`board_20261018_first_recording/`保存首次真实手机录像的逐帧传输审计和85个CRC合格页面。完整101页尚缺54–69（0起算），没有生成可用于算法研究的8帧ROI；详见`../EDGE_TEMPORAL_RESEARCH_V1_FIRST_DECODE.md`。该目录的页面是实际数字传输数据，不能与上述合成测试混称。

后续`board_20261018_complete/`已由新增录像**独立恢复101/101页、全部8帧真实RGB及AWB元数据**，原缺页补齐，旧85页逐字节相同。首份失败记录保持历史原状。完整数据验证通过并已执行TH40/60/80模型；ROI为较平坦暗部、有效区无门限边缘，不能据零翻转排名时间算法。见`../EDGE_TEMPORAL_RESEARCH_V1_REAL_DATA_EVALUATION.md`、完整数据目录中的NPZ/原始包/分析JSON/图表。

`board_20261018_181941/`来自用户明确指定的新文件video_20261018_181941.mp4：3653帧全扫描，101/101页全部CRC/capture检查通过；**101个页面及pre/post/meta/global全部与前一批逐字节相同**，没有取得新的含边缘ROI。保存独立解码证据和对照图，详见`../EDGE_TEMPORAL_RESEARCH_V1_RECORDING_181941.md`。不能把新录像次数当成独立采样次数。

缺失数据、时间、标注不补0。数据量、错误处理及CRC定义见研究报告/BOARD_TEST；最终资源只看新真实RGB诊断bit最终路由归档。

`board_20261018_184242/`为**新采样6A23858A**：全3332帧扫描、101页齐全、8帧RGB/AWB校验通过。TH40/60有临界响应，TH80为空；阈值/NMS及四跳的模型重放证实局部输出敏感性，AWB有小影响但非唯一来源。用户目标手持、未看到绿框，ROI未辨认出清晰黑白分界；不能量化真实纸边完整度或纯噪声贡献。写侧FIFO sticky均1，发生时刻与复发未知。详见`../EDGE_TEMPORAL_RESEARCH_V1_RECORDING_184242.md`；该目录保留原页、NPZ、SHA、模型中间结果、图表、现场说明及PC源快照，不含原手机录像或新bit。
