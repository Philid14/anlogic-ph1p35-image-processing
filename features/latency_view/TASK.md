# TASK - LATENCY / 同帧延迟与性能可视化

```text
Role: LATENCY
来源: 2026-10-16 审查意见 + TEAM_PROTOCOL_V1 §2.3
目标: L1 帧计数/帧率；L2 模拟事件下同帧计时与异常；性能信息可视化
不含: DDR 调度、主线时钟/顶层接线、共享 OSD、曝光/显示器内部延迟
Base: origin/main c42168e
Branch: codex/latency/same-frame-association-v2
范围: features/latency_view/ 内全部文件
接口: TEAM_PROTOCOL_V1 / 接口草案（待 MAIN 确认）
交付: RTL、模型、18 场景、面板测试、INTERFACE/VERIFICATION/INTEGRATION/DEMO
验收: 18/18 通过；面板 80 字符一致；坐标对齐通过；不声称整机完成
```
