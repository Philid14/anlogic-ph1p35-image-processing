# EDGE_MULTI_MODE_V1 candidate 交付报告

日期：2026-10-18；角色：MAIN；状态：**构建通过的四模式候选，实板待验收，不自动合并**。

## 1. 完成内容

在`EDGE_TEMPORAL_V1`基础上增加GRAY和BINARY，形成：

| 编码 | 模式 | 输出 |
|---|---|---|
| `00` | ORIGIN | AWB后RGB888原图 |
| `01` | GRAY | `(Y,Y,Y)` |
| `10` | BINARY | `Y>=T_binary`时纯白，否则纯黑 |
| `11` | EDGE | 原Gaussian/Sobel/NMS/四跳/单帧时间保持 |

其中`Y=(77R+150G+29B+128)>>8`。复位默认`EDGE/080/130`。K3按`EDGE→ORIGIN→GRAY→BINARY→EDGE`循环；K4短按减10、长按约0.7秒加10，只修改当前BINARY或EDGE阈值，ORIGIN/GRAY忽略，10..250饱和。两个阈值独立保存。

## 2. 实际修改模块

- `design_top_wrapper.v`、`isp/isp_top.v`：配置由9位扩为18位。
- `edge_key_control.v`：K3四态循环、双阈值编辑和默认值。
- `edge_config_cdc.v`：18位整包保持+toggle/ack邮箱。
- `isp/edge_control_stream.v`：SOF整帧锁存、四分支同深度对齐、末端整拍选择、Edge历史持续运行。
- `isp/rgb_effects_96.v`：新增4像素并行灰度/二值模块。
- `edge_status_osd.v`：四模式名称和当前有效阈值显示；复用既有字库。
- `td_project/camera_to_dsi_display.al`：加入新RTL文件，工程输入由64项变为65项。
- `tests/tb_edge_multi_mode_*.v`、`tests/run_edge_multi_mode_v1.py`：新增定向与完整流回归。
- 构建、归档脚本及本版文档。

未修改Sensor Exposure/VTS/HTS/Gain、BLC、AWB_V2、Demosaic、FIFO/DDR/HDMI结构、PLL、引脚或SDC。与V1对比的18个算法/ISP/DDR/HDMI/Logo/引脚/SDC文件SHA完全一致。

## 3. 配置、时序与数据对齐

配置总线：

```text
[17:16] mode
[15:8]  EDGE threshold
[7:0]   BINARY threshold
```

24 MHz按键域只产生完整18位请求；CDC在目标域一次捕获数据并返回ack。视频域在原AWB提前`tuser`处提交配置，帧内总线变化不会进入当前帧。配置、RGB、`valid/user/last`共同经过27拍分支窗口，随后进入原OSD2拍和96→128打包1拍。

四分支均使用同一AWB后RGB源。Edge时间历史在ORIGIN/GRAY/BINARY下仍按真实采集帧更新，因此切回EDGE不丢失上帧历史。没有新增帧缓存、气泡、反压、图像中心偏移或等待整帧。相对TEMPORAL_V1没有增加流水拍数；每帧仍为230400有效拍，打包仍为172800字。

## 4. 验证结果

| 检查 | 结果 |
|---|---|
| 灰度/二值逐像素 | 2322拍/9288像素，黑、白、中性灰、RGB三原色、随机RGB、T=10/130/250及`Y=T`边界通过 |
| K3/K4 | 四态循环、首次按K3进ORIGIN、按住不重复、短/长按互斥、ORIGIN/GRAY不改阈值、两个阈值独立保留及10/250饱和通过 |
| CDC | 200个快速18位请求，所有交付包顺序/内容完全一致；busy期间无半包变化；复位恢复通过 |
| 混合视频流 | 64×32九帧，覆盖四模式、提前/同拍SOF、valid间隙、帧内请求变化、帧首/行尾，4608拍/3168打包字通过 |
| 完整720p | 两帧460800有效拍/345600打包字逐字节通过 |
| ISP集成 | 完整720p下实际`isp_top`与独立生产数据通路逐拍、逐128位字一致 |
| OSD | 四模式文字、BINARY/EDGE阈值、ORIGIN/GRAY空白阈值及既有B/S第三行逐像素匹配；Logo/CNT模块未改 |
| 旧功能 | Edge算法源文件及AWB/BLC相关配置、DDR/HDMI、引脚/SDC哈希与V1一致 |

未覆盖：真实MIPI PHY、摄像头I²C、DDR控制器和HDMI电气链路的联合仿真；真实光照、镜头、面板和长期运行。模拟通过不等于实板通过。

## 5. 资源与时序

首次R0使用移位加法，虽然时序零违例，但Setup WNS仅`+0.002ns`；已将bit和全部证据归档为`EDGE_MULTI_MODE_V1_R0`，tag `edge-multi-mode-v1-r0-build`，明确拒绝上板。最终版把亮度常数乘法映射到DSP并完整重建。

| 项目 | TEMPORAL_V1 | MULTI_MODE R0 | MULTI_MODE candidate |
|---|---:|---:|---:|
| LUT6 | 16119 | 17040 | **16942** |
| FF | 15657 | 15801 | **15809** |
| Slice | 17684（83.35%） | 18483（87.12%） | **18319（86.35%）** |
| ERAM20K | 75 | 75 | **75** |
| DSP | 9 | 9 | **21 / 40** |
| Setup WNS | +0.133ns | +0.002ns | **+0.107ns** |
| Hold WNS | +0.020ns | +0.020ns | **+0.020ns** |
| Setup/Hold TNS | 0/0 | 0/0 | **0/0** |
| STA coverage | 96.05% | 96.22% | **96.16%** |

最终相对TEMPORAL_V1：LUT +823、FF +152、Slice +635、ERAM 0、DSP +12，Setup WNS少26ps但仍保留107ps。关键warning仅保留原有`PHY-5060`、`PHY-5079`，无新增类型。既有FIFO Gray指针`Set Max Delay (Ignored)`覆盖缺口未修复，不把STA零违例解释为全部异步CDC已覆盖。

## 6. Bit 与追溯

- Version：`EDGE_MULTI_MODE_V1`
- Branch：`codex/main/edge-multi-mode-v1`
- 实际TD输入源码commit：`4ea67f194941c6717fc1d28889c687a4fb78533f`
- Bit：[camera_to_dsi_display.bit](../artifacts/bitstreams/EDGE_MULTI_MODE_V1/camera_to_dsi_display.bit)，1,789,539 bytes
- SHA-256：`8C62195DA8A2F8748CE9D6CFD7D9703BCB81E6F6CDA09AEDF4BBB0DE0FE0BBE9`
- Build evidence：[BUILD_INFO](../artifacts/bitstreams/EDGE_MULTI_MODE_V1/BUILD_INFO.md)
- Candidate tag：`edge-multi-mode-v1-candidate`，在归档commit上创建
- PR：[Draft #11](https://github.com/Philid14/anlogic-ph1p35-image-processing/pull/11)，base为`codex/main/edge-temporal-v1`；不自动合并，不修改旧candidate bit/tag
- Remote：`origin` = `https://github.com/Philid14/anlogic-ph1p35-image-processing.git`；开发分支、R0 tag和candidate tag均已推送
- Push Status：`codex/main/edge-multi-mode-v1`、`edge-multi-mode-v1-r0-build`、`edge-multi-mode-v1-candidate` 推送成功

## 7. 实板状态与回退

Board Test Status：**待用户烧录**。必须验证默认EDGE、K3四模式、GRAY灰阶、BINARY严格黑白、两侧阈值独立保留、OSD/Logo/CNT、B/S计数以及30分钟稳定性。

详细步骤见[EDGE_MULTI_MODE_V1_BOARD_TEST.md](EDGE_MULTI_MODE_V1_BOARD_TEST.md)。出现黑屏、失锁、花屏、错行或模式/阈值异常时，先断电重新烧录；持续异常回退：

`artifacts/bitstreams/EDGE_TEMPORAL_V1/camera_to_dsi_display.bit`

SHA-256：`14A36D98BC0A1547F84588087D796C14098AD4441CB30B5878D8F81CBADC95C4`
