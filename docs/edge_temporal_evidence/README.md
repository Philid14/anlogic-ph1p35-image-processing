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

缺失数据、时间、标注不补0。数据量、错误处理及CRC定义见研究报告/BOARD_TEST；最终资源只看新真实RGB诊断bit最终路由归档。
