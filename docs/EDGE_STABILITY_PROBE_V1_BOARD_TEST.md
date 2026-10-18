# EDGE_STABILITY_PROBE_V1 最小上板步骤

状态：待用户实板。最终bit/源commit/哈希见`artifacts/bitstreams/EDGE_STABILITY_PROBE_V1/BUILD_INFO.md`；本页不是已完成上板记录。

## 烧录与最小记录

1. 保持相机、静物、灯光、显示器、线材、供电不变。用原QUALITY候选在EDGE/080记录5–10秒真实输入抖动，保存对照；不改Sensor参数。
2. 校验新bit SHA，选择**PROGRAM_SRAM**烧录PROBE候选，避免混用TD Runs中的临时bit。默认EDGE/080，画面应为固定图的边缘，左下出现`PROBE FIXED V1`。
3. 等至少1秒，确认尾字符从W变V，SEQ持续更新，FLAG低4位为7（两FIFO都armed且完整测量）；W或低位未齐表示相关测量尚不可判正常。
4. 固定TH80，拍一张能读清MODE/THRESHOLD与诊断九行的照片，再录10–30秒。至少再拍一次九行值；记录是否整行/局部抖动、CRC是否变化、FLAG和COUNT是否增加。
5. 用手遮挡/移动相机前静物：EDGE的固定图在相同TH下应不受真实RGB变化影响；不要遮挡数据线或断开摄像头。然后K3切ORIGIN，确认仍是实时真实彩色画面、原Logo/CNT和状态文字可见；再K3返回固定EDGE。
6. K4短按两次，从80到60（每次减10，按已有消抖节奏），等待V/数值更新，重复照片。可再到40。长按仍是约0.7秒加10，不新增诊断键操作。

无须本轮先做AWB冻结、独立时序或RGB导出。以上一份新bit和旧QUALITY对照已经能给出首轮判别证据。

## 应读到的关键值（均为十六进制）

| 字段 | 正常完整流预期 |
|---|---|
|IN|00038400|
|PACK|0002A300|
|LINE|02D00140|
|CRC TH080|6B6DB7D0|
|CRC TH060|2B018224|
|CRC TH040|417312EE|
|GAP|低4位十六进制数字为该帧气泡数，正常0000；高4位为实际SOF间隔，不指定固定值|
|ERR|00000000|
|COUNT|高4位坏帧累计、低4位同TH CRC变化累计；完整测试期间应不增长|
|FLAG|无事件且已armed/有效为00FFFFF7；FFFFF是无首气泡坐标的N/A标志|

序列、模式和门限变化时不要跨配置比较CRC。其它门限参考`docs/edge_stability_probe_evidence/fixed_reference.json`。
FLAG高字节含CRC改变/输入行帧/气泡/pack/phase/Edge计数/FIFO事件，详细位定义见DESIGN。FLAG是sticky，故障曾发生即保留；本页列正常期望不是本机已经量到的结果。
计数结果是约两个采集帧前的历史样本、跟随该画面存入DDR；FIFO及COUNT是累计历史。SEQ不是HDMI CNT、不是延迟值。

## 结果判读

| 观察 | 优先方向 |
|---|---|
|固定EDGE稳定，CRC等于参考，实时原QUALITY EDGE仍抖|真实RGB/ISP变化经过算法放大优先；下一阶段采AWB增益/pre/post ROI，而不是先换硬件算法|
|固定EDGE抖，CRC变化，控制/pack数量也错|先查真实valid/SOF/tlast、异常段和输入源；保留首气泡位置及计数，不加时域滤波|
|固定EDGE抖，CRC变化，完整计数正确且同TH|Edge内部状态、RAM映射、复位或物理时序；需要错误触发/门级或独立合法控制诊断|
|CRC始终相同且等于参考，画面仍抖|算法之后的复制位、OSD、打包内容、DDR/HDMI及显示采集伪影优先；相同CRC不能绝对排除漏检/碰撞|
|phase/气泡非0且PACK不足|已经有真实流触发已知打包限制的证据；下一步做该位置复现和最小链路修复，不能直接把所有抖动归为它|
|FIFO sticky非0且armed有效|实际观察到读空/写满条件；先核对事件时刻、复位屏蔽和流量，不把普通empty当异常|
|CRC稳定但不等于参考|先确认烧录版本、门限、稳定帧、完整计数；仍不符则即使视觉稳定，也不能认定算法正确|
|面板W/停止更新/字符撕裂|诊断不可读，不能使用旧数值证明任何环节正常；回滚检查显示/控制/供电/时钟|

固定图使用真实摄像头控制；固定图稳定并没有证明Sensor逐帧像素稳定，也没有单独证明AWB振荡。固定图异常时不直接进入时间滤波。

## 建议反馈模板

```text
bit SHA / 板卡与摄像头 / 灯光与显示器：
THRESHOLD：
V或W / SEQ是否递增：
IN / PACK / CRC / LINE / GAP / ERR / COUNT / FLAG：
固定图是否闪烁、平移、整行错位：
遮挡摄像头是否改变固定EDGE：
ORIGIN是否正常、Logo/CNT是否可见：
切换及运行时间 / 首次异常触发条件：
照片或录像文件：
```

## 回滚

重新PROGRAM_SRAM烧录`artifacts/bitstreams/EDGE_QUALITY_V1/camera_to_dsi_display.bit`；SHA256：`629ACAA828EF8151DED0261779ED8B91F0FA618EED66DD46C72D6E799ADCC9D5`。
原tag `edge-quality-v1-candidate`完整保留，未改曝光/增益/SDC或历史bit。当前probe关闭参数默认0，但回滚硬件以已归档旧bit为准。
出现花屏、CRC/流错误或失锁先记录并回滚。新候选仅用于故障定位，不是画质优化版本；本轮候选完成即停止，等待反馈。
