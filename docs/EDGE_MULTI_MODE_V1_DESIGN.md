# EDGE_MULTI_MODE_V1：四模式实时图像处理设计

## 1. 基线与范围

本版本从`EDGE_TEMPORAL_V1`分支`codex/main/edge-temporal-v1`的文档tip `b47105f`起开发，实际RTL构建基线为`7aa6beb`。不继承PROBE、RESEARCH或QUALITY之外的ROI缓存、绿色采集框、101页编码或研究模块。

唯一主要变量是把原有ORIGIN/EDGE二选一扩展为ORIGIN/GRAY/BINARY/EDGE四选一，并增加两个独立可调阈值。Sensor Exposure/VTS/HTS/Gain、BLC、AWB_V2、Demosaic、MIPI、DDR、HDMI、Logo、CNT、PLL、引脚与SDC均不修改。

## 2. 配置格式

配置总线从9位扩展为18位：

| 位域 | 含义 | 复位值 |
|---|---|---:|
| `[17:16]` | 模式：`00` ORIGIN、`01` GRAY、`10` BINARY、`11` EDGE | `11` |
| `[15:8]` | EDGE阈值 | 80 |
| `[7:0]` | BINARY阈值 | 130 |

复位配置为`18'h35082`。K3在24 MHz现有消抖域内执行2位模4递增，因此从EDGE开始的自然循环是`EDGE→ORIGIN→GRAY→BINARY→EDGE`，第一次按下K3进入ORIGIN。

K4继续使用既有短按释放/长按单次触发结构：

- ORIGIN、GRAY：忽略短按和长按，不改任何阈值。
- BINARY：只编辑`[7:0]`。
- EDGE：只编辑`[15:8]`。
- 短按减10，长按约0.7秒加10；范围10..250，端点饱和。
- 模式切换仅改变`[17:16]`，不会重写两个阈值寄存器。

## 3. CDC与帧锁存

`edge_config_cdc`保留原“整包保持”邮箱：源域保存18位完整配置，toggle请求跨到目的域，目的域同步后一次捕获整个配置并ack；ack返回前源域不改变held数据。忙期间的新请求被合并为最新完整配置，不存在按位跨域或半新半旧总线。

`edge_control_stream`在原AWB提前`tuser`处提交配置。该`tuser`可能与`valid`同拍，也可能提前出现；帧内之后改变`requested_config`只影响下一次SOF。配置随每个有效拍经过与图像相同深度的寄存器数组，所以选择器、Edge阈值、时间保持阈值和OSD状态都属于同一拍对应的配置。

## 4. 数据通路

AWB输出每个96位拍包含4个RGB888像素，低24位为lane0。每像素位序为`{R[23:16],G[15:8],B[7:0]}`。

```text
AWB RGB888 (4 px/beat)
├─ ORIGIN        原96位RGB
├─ GRAY          每lane复制8位Y
├─ BINARY        Y>=binary_threshold ? 白 : 黑
└─ EDGE          Gaussian→Sobel→NMS→四跳→单帧时间保持
        │
        └─ 统一27拍分支窗口
                 ↓
        按本帧mode选择96位拍
                 ↓
        原OSD 2拍（MODE/THRESHOLD/B:S）
                 ↓
        原96→128打包1拍
                 ↓
        原DDR缓存、Logo/CNT、HDMI
```

亮度严格为：

`Y = (77R + 150G + 29B + 128) >> 8`

`rgb_effects_96`使用4路并行常数乘法，16位中间和最高为`255×256+128=65408`，不会溢出。首轮移位加法实现使全设计增加921 LUT，最终Setup WNS仅`+0.002ns`，因此按R0证据保留并拒绝签发；最终实现把12个常数乘法映射到DSP，模块LUT从556降到约227，全设计恢复slice与时序裕量。GRAY和BINARY复用完全相同的亮度结果；BINARY仅做无符号8位比较，输出每个lane只能是`0x000000`或`0xFFFFFF`，不存在彩色残留。

## 5. 对齐与帧一致性

- 原有Edge空间/时间路径保持27拍；ORIGIN、GRAY、BINARY使用同长度数组，不用假设各模块latency相同。
- 模式选择发生在第27拍末端，选择整拍96位数据，4个像素结构不会被拆分。
- `valid/user/last`和18位配置使用同一组移位数组，与本拍RGB同步进入OSD。
- Edge计算在ORIGIN/GRAY/BINARY期间也持续运行，因此切回EDGE仍使用真实上一采集帧历史，不因显示模式中断。
- 无新增帧缓存、视频气泡或反压；每帧仍为230400有效拍，128位输出仍为172800字。
- 新模式没有新增整帧等待，相对TEMPORAL_V1没有增加数据通路拍数。

## 6. OSD

保留原状态框位置、两行布局及第三行`B:hhhh S:hhhh`，只扩展第一行和第二行内容：

| 模式 | 第一行 | 第二行阈值 |
|---|---|---|
| ORIGIN | `MODE: ORIGIN` | `THRESHOLD:` 后留空 |
| GRAY | `MODE: GRAY` | `THRESHOLD:` 后留空 |
| BINARY | `MODE: BINARY` | 当前BINARY阈值 |
| EDGE | `MODE: EDGE` | 当前EDGE阈值 |

`osd_char_lib`已经包含A–Z、0–9和冒号，本轮不新增字形。状态OSD仍在DDR写入之前，因此文字与图像一起缓存；DDR后的“安路”Logo和CNT路径不变。

## 7. 验证边界

独立RTL回归覆盖亮度公式全部边界、随机RGB、二值化Y=T、K3/K4、18位CDC整包顺序、四模式混合帧、提前/同拍SOF、valid间隙、帧内请求变化、帧首/行尾及完整720p打包。实际MIPI PHY、DDR控制器和HDMI电气链路不在RTL仿真内；实板四模式画质和长期稳定性必须由板测确认。
