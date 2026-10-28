# 基础彩色视频画质调试记录

主工程：`in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd`。本表记录**实际修改和上板结果**；未测试内容写“待测”，不把静态推断当成实测。每版只改变一个主要因素，保留可回退的原始工程和配置。2026-10-08 用户反馈 AWB_V1 已上板，颜色仅轻微改善，画面仍有明显灰雾感；具体黑场数值待测。

| Version | 修改内容 | 原值 | 新值 | 测试环境 | 结果 | 是否保留 |
|---|---|---|---|---|---|---|
| Baseline V0 | 实际上板的当前 A 工程；未改本轮 RTL | 实际编译 AWB 每拍仅统计 1/4 像素、帧内更新，增益近 0～约 16×；初始化曝光编码 1990，手动模块默认 3000 | 无 | 2026-10-05，同一室内环境，白/蓝/绿/红物体；四张显示器照片见下 | 用户实测：白明显青蓝/青绿；蓝与绿区分差；红成分严重不足；暗部较差；安路 Logo、黄色文字基本正常。基础颜色测试**不通过**。无寄存器读回和数值色度数据 | 保留作对照 |
| Candidate AWB_V1 | 仅修改实际编译的 `user_source/hdl_source/awb.v`：四像素全帧统一统计，过滤近黑/近饱和样本，帧末计算、次帧固定增益，除零保护、限幅和限步；保留下游所需的提前帧标记 | 每拍只统计 1 像素；`R+G+B<720`；逐拍除法/帧内更新；增益可近 0～约 16× | 每拍统计 4 像素；像素最大通道 `24..239`；≥1024 有效样本；Q4.16 增益 0.75～3.00×；每帧最多变化 0.125× | 用户 2026-10-08 反馈已上板；同场景数值、照片、遮光测试尚未提供 | **颜色仅轻微改善**；仍明显偏色且有灰雾感、黑位抬高、对比度低。无黑场数值，不能定量归因 | 保留作 BLC_V1 对照 |
| Candidate AWB_V2 | 仅在 BLC_V1 基础上改变 AWB 统计样本：加入低色度判定；样本不足保持上一增益 | 最大通道 `24..239` 的所有像素均参与统计 | 原亮度窗口不变，且 `max-min<32`；仍需 ≥1024 样本 | 待上板：白纸、中性灰、正常综合色彩和中性背景中占 20–30% 的红/绿/蓝目标 | **仅模型及完整构建通过，画质待验证** | 保留作候选 |
| 旧建议，延期 | 将 `ae_set.v` 默认曝光 3000 对齐初始化 1990 | 3000 | 暂不修改 | 本轮只处理基础颜色异常，不测 K3/K4 | 未执行 | 延期 |

## Baseline V0：真实上板证据

- 证据照片：`C:/Users/Lenovo/Downloads/vivo办公套件/IMG_20261005_210044.jpg`、`IMG_20261005_210045.jpg`、`IMG_20261005_210201.jpg`、`IMG_20261005_210203.jpg`。照片显示青蓝/青绿占主导、场景辨识度低，同时黄色“安路 CNT”文字可见。四张照片与具体颜色物体的一一对应未在文件名中标注，以用户现场描述为准。
- 静态复核发现实际编译源为 `user_source/hdl_source/awb.v`，此前分析的 `isp/awb/awb.v` 是未参与本工程综合的副本。V0 有效源码已保存到 `docs/baseline/awb_v0_compiled.v`，SHA-256 为 `B6D9D83A6B48952CC9531DAF39BC6C6B94C4E45DDEFE603908E9CB275533E50A`。
- OSD 颜色正常支持将故障范围优先放在相机到 RGB 流，但不能单凭 OSD 证明 Bayer 或 AWB 哪一个正确。`0x3221` 复位读回、相机 RAW 样本、HDMI 原始帧和精确色度值均缺失。

## Candidate AWB_V1：单因素修改记录

- 修改文件：`in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/awb.v`。模块接口、像素延迟 RAM、安路除法器 IP、四像素乘法/输出格式保留；输出 `O_tuser` 继续使用原始提前帧标记，让 `video_in` 在有效像素到达前完成 FIFO 复位；AWB 内部用延迟帧标记切换增益。未改摄像头寄存器、曝光/增益控制、MIPI/DDR/OSD/HDMI、Gamma 或 CCM。
- 算法：RGB888 的 4 像素每拍共同统计全帧 `R_sum/G_sum/B_sum`；仅将最大通道在 `[24,239]` 的像素计入；至少 1024 个有效像素且 R/G/B 和均非零才启动两次 `G/R`、`G/B` 除法；增益限制在 0.75～3.00×，每帧最多调整 0.125×；输出帧内不变。
- 定点：R/G/B 累加 32 位无符号；样本计数 21 位；除法分子为 `{G_sum,16'b0}` 的 48 位，商取 Q4.16 并限幅至 20 位；R/B 乘法 20×8→28 位，右移 16 后超过 255 饱和；G 为 8 位直通。
- GitHub 思路来源及许可边界见 `GITHUB_REFERENCE_RESEARCH.md` 第 4 节；没有直接复制外部代码。
- 预期：抑制纯色画面被逐拍 Gray World 过度拉成青色、减少暗部/高光对统计的影响，使白更接近中性且红绿蓝可分。实际变化待上板；若原始 Bayer 相位/传感器数据异常，单改 AWB 不能根治。

### 2026-10-05 AWB_V1 编译与交付

- 实际编译源：`user_source/hdl_source/awb.v`，SHA-256 `F952339EC4F19C61947B98C041CF9801021A6763B6CF103D32A46D89D6B47AD3`；综合日志 `td_project/camera_to_dsi_display_Runs/syn_1/td_20261005_220717.log` 明确分析并展开该模块。`isp/awb/awb.v` 仍是未参与 A 工程综合的副本，未改动。
- Tang Dynasty 6.2.168116：综合成功；Physical Design 成功；路由后时序报告生成于 22:17:17；最终 `td_project/camera_to_dsi_display_Runs/phy_1/camera_to_dsi_display.bit` 生成于 **22:17:28**，大小 1,789,539 字节，SHA-256 `6512B12C1F231DED42A7809766273CA58D677472FFB08BBE009B839512C729A3`。该文件是本轮供 `PROGRAM_SRAM` 使用的唯一交付 bit。

| 路由后指标 | Baseline V0（20:21 构建日志） | AWB_V1（22:17 最终构建） | 变化 |
|---|---:|---:|---:|
| LUT6 | 13,107 | 13,561 | +454 |
| Slice FF | 13,402 | 13,609 | +207 |
| ERAM20K | 40 | 40 | 0 |
| DSP | 9 | 9 | 0 |
| Setup WNS | +0.109 ns | +0.101 ns | −0.008 ns |
| Hold WNS | +0.020 ns | +0.020 ns | 0 |

- 新增 AWB 统计路径出现在 MIPI 59.995 MHz 时钟域，最差 setup slack **+6.934 ns**；全局最差 +0.101 ns 来自 HDMI 时钟域，仍为正。Setup/Hold TNS 均为 0，路由报告没有违例端点。+0.101 ns 全局裕量较窄，后续任何 RTL 改动都应重跑实现。
- 最终 `phy_1/td_20261005_221212.log` 中有 3 条关键告警：两条 `PHY-5060`（既有 I²C/camera 时钟与控制混合扇出）和一条 `PHY-5079`（一条时钟网用本地布线）；V0 `phy_1/run.log` 具有相同 3 条告警。本轮未改时钟、SDC 或约束。未见编译 Error。综合中 AWB 两个除法器的未使用 `remainder` 端口提示不影响商输出。
- 编译与静态时序通过不等于颜色或连续运行实测通过。候选效果维持“待上板验证”。

### 本次仅做的六场景上板复测

1. 白色物体：在相同光照和机位下看白是否从青色转为接近中性，记录是否跨帧突变。
2. 红色物体：看红色是否明显恢复，并与蓝色分开；若仍严重缺红，记录原图供 Bayer/RAW 通道复核。
3. 绿色物体：看绿色与蓝色是否可分、是否出现规律性四色条纹。
4. 蓝色物体：看蓝色是否仍把整幅画面拉向青色、背景是否发生明显色漂。
5. 正常室内场景：同时观察人/物轮廓、白色区域、安路 Logo、黄色 OSD、画面连续性。
6. 较暗场景：观察暗部噪声/色斑和突然变色；当前没有 AE 自动调节，不把亮度未恢复算作 AWB 结果。

六场景均用同一光源、物距、显示器与拍照设置；本轮不测试 K3/K4，也不宣称尚未测得的改善。

## Candidate BLC_V1（2026-10-08）：仅检验 RAW10 黑位扣除假设

**上板前证据与不确定性。** A 工程 `td_project/camera_to_dsi_display_Runs/syn_1/camera_to_dsi_display.prj` 未编译 `isp/BLC/BLC.v`；`isp/raw10_unpacket_2lane.v` 中使用 `I_camera_black_level` 的四路扣除代码被整段注释，顶层也未连接该端口。实际数据为 RAW10 解包后直接送 `uial2axis → demosaic`；`mipi_to_raw_converter.v` 取每像素 `[9:2]`，没有 FPGA 端 BLC。SC500CS 当前初始化写 `0x4000–0x4009`，但缺少该型号的公开逐位寄存器说明与实测 RAW 黑场，**传感器内部 BLC 是否已把输出校到零，以及实际黑电平是多少，目前无法确定**。

- 唯一修改假设：RAW10 输出含有未消除的非零 pedestal，造成黑位抬高，并削弱 AWB_V1 的颜色比例校正。本轮仅增加 RAW10 Bayer 域统一饱和减法；AWB_V1、sensor 寄存器、曝光/增益、Gamma、CCM、DDR、OSD、HDMI 均不改。
- 修改文件：`in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/isp_top.v`。输入四个 RAW10 像素各自执行 `max(raw - BLACK_LEVEL_RAW10, 0)`，组合逻辑连接到现有 demosaic 输入；valid、ready、frame、line 信号直接沿用原连线，未增加延迟。
- `BLACK_LEVEL_RAW10 = 15` 的**唯一数值来源**是随工程提供但未接入 A 工程的 `isp/BLC/BLC.v`，其四路默认 offset 均为 10-bit 的 15。该值不是 SC500CS 规格值或本板测量值，只是有源码出处的首次对照参数；若镜头遮光实测接近 0，或出现黑位压死，应判定本假设不成立并回滚。
- RAW10→RAW8：原映射 `raw8 = floor(raw10/4)`，若真实黑位 `BL_raw10`，则其 8-bit 对应约为 `floor(BL_raw10/4)`；现在 `raw8 = floor(max(raw10-15,0)/4)`。`[9:2]` 本身仍完整映射 0–1023 到 0–255，只降低 2 bit 精度；它不自动把非零黑位搬到 0，也不把不足满量程的白位扩展到 255。15 RAW10 约相当于 3.75 RAW8 级，不能据此承诺能消除强烈灰雾。
- Demosaic 主要是非负 8-bit 采样的加法和右移平均，输出有 8-bit 饱和，不会主动减黑位。近似均匀黑场 RAW8 值 `p` 会得到近似 `R=G=B=p`（边界及截断除外）；AWB_V1 的 G 直通，R/B 乘以 0.75–3.00 并饱和，可能保留或放大色偏。若每通道信号为 `S_c+P`，AWB 比值 `(S_G+P)/(S_R+P)` 随共同 pedestal 增大趋向 1，能解释“改善有限”的一种机制，但尚无实测 `P`。
- HDMI 路径：`video_out` 输出连续 RGB888，`hdmi_mixer` 对摄像头数据直接透传，并以常量生成 OSD；HDMI TX 配置为 `VIDEO_FORMAT="RGB"`。未找到摄像头 RGB 的 16–235 偏移/缩放。HDMI IP 内部量化信息与显示器配置尚无读回，但 OSD 黄色和背景正常，整链路 range mismatch 优先级较低。本轮不修改 HDMI。
- Gamma：**现在不加入**。若黑位已抬高，Gamma 不会恢复真实黑位，部分曲线反会继续抬亮暗部。先看遮光场景与黑/白物体，再决定是否研究 Gamma 或 CCM。

| 指标（路由后） | AWB_V1 | BLC_V1 | 变化 |
|---|---:|---:|---:|
| LUT6 | 13,561 | 13,474 | −87 |
| Slice FF | 13,609 | 13,627 | +18 |
| ERAM20K | 40 | 40 | 0 |
| DSP | 9 | 9 | 0 |
| Setup WNS | +0.101 ns | +0.137 ns | +0.036 ns |
| Hold WNS | +0.020 ns | +0.020 ns | 0 |

TD 6.2.168116 综合、Physical Design、Timing Check、bitgen 全部成功，Setup/Hold TNS 均为 0。`final_timing.rpt` 生成于 2026-10-08 18:22:32；原始 bit 于 18:22:41 重新生成，SHA-256 为 `2B9E427DEE8304106F5E75A686899D189E4B61EB3514A4AE33C51EA536FB133D`。MIPI 时钟域最差 setup 余量 +5.763 ns；全局 WNS +0.137 ns。关键告警仍为既有 `PHY-5060` 两条和 `PHY-5079` 一条，无新增关键告警或 Error。**Board Test Result：待上板。**

下次仅按顺序比较 AWB_V1 与 BLC_V1：①完全不透光遮镜头（画面黑度、灰雾、色偏、固定噪声、AWB 跨帧变化）；②黑色物体；③白纸；④灰色物体；⑤正常综合色彩场景；⑥红；⑦绿；⑧蓝；⑨较暗场景。若 BLC_V1 的遮光/黑物体更接近中性黑且白、灰、彩色细节不被压死，同时 OSD/连续性保持，则支持 pedestal 假设；若两版无差异，优先寻求 RAW 黑场统计；若暗部被压死、颜色更差或出现显示错位，回滚到已归档 AWB_V1 bit。手机拍屏需锁定曝光和白平衡，不能用自动调节照片直接量化黑位。

### BLC_V1 上板反馈（用户报告，2026-10-08）

- Version / Git Tag / bit：`BLC_V1` / `blc-v1-candidate` / SHA-256 `2B9E427DEE8304106F5E75A686899D189E4B61EB3514A4AE33C51EA536FB133D`；源码提交 `347dff76d67f8072fc3f0c7a4e78bd01bfae7dbc`，归档提交 `02b27b114bf20ecd6ee176a90ded6863a2a0385c`。
- 修改假设与唯一变量：在 RAW10 Bayer 域扣除可能存在的公共 pedestal；原先旁路，现统一饱和减去 15。构建成功，路由后 Setup WNS +0.137 ns、Hold WNS +0.020 ns，无新增关键告警。
- 实测场景：白色和绿色较此前有所改善；白色仍偏青绿。蓝色目标能识别为蓝色、红色目标能识别为红/暖色，但两者都明显偏暗。完全遮光时摄像头区域为较好的黑色，没有明显灰白 pedestal。较暗真实场景仍明显偏暗、色彩弱。用户目前未观察到大面积黑位压死、HDMI/OSD 颜色异常、花屏或明显时序问题。
- 结论：保留 BLC_V1，`BLACK_LEVEL_RAW10=15` 暂时冻结。上述正向现象支持继续使用本候选 bit，但尚无 RAW 数值、定量色卡或长时间运行证据，不能证明 15 是准确的 sensor 校准值。下一个独立变量为 AWB 样本选择；低照度亮度不足留待以后单独研究 sensor exposure / gain / AE。

## Candidate AWB_V2（2026-10-08）：只改 Gray World 样本选择

- 静态推导：AWB_V1 对所有最大通道 `24..239` 的像素取 `G_sum/R_sum`、`G_sum/B_sum`。近乎全屏 `(R,G,B)=(200,30,30)` 时 R 目标增益为 `0.15`，经原有 clamp 变成 `0.75`；首个有效帧边界经 `0.125/frame` 限步从 1.0 降到 0.875，再降到 0.75。全屏蓝色同理会压低 B，绿色则使 R/B 目标上升。故纯色目标的亮暗并不能单独判定通道增益是否足够。
- 唯一修改假设：大面积彩色物体污染 Gray World 统计。只在实际编译的 `user_source/hdl_source/awb.v` 中把有效样本改为原亮度窗口 **且** `max(R,G,B)-min(R,G,B)<32`。32 是 RGB888 的实验初值，不是传感器规格或外部代码参数。原 `MIN_SAMPLES=1024`、全帧四像素统计、帧边界更新、增益 clamp `0.75..3.00`、每帧限步 `0.125` 均保持。
- Fallback：低色度样本少于 1024 或任一累加通道为零时，原 `frame_ready` 保持 0，不启动两路除法；`target_r/b` 和实际 `gain_r/b` 保留上一有效值，不回退到整帧彩色 Gray World。上电初值仍为 1.0。现有 `O_tuser` 提前脉冲和 50 时钟像素延迟不改。
- 用 `tests/awb_v2_selection_model.py` 的 RGB888/Q4.16 离线模型检查：全屏红/绿/蓝在 V2 均无候选样本并维持 1.0；灰、白可采样；`(160,185,180)` 偏色白可采样并推动 R 增益；25% 红物体加 75% 中性灰时，V1 首帧 R 增益降至 0.875，V2 保持 1.0。此模型不是 RTL 时序仿真，也不证明实拍场景的像素分布。
- 风险：若真实偏青白纸在输入 RGB 的通道跨度已经大于等于 32，它也会被拒绝，可能导致长期不更新增益；若背景没有足够中性色，同样会保持旧增益。需在上板比较中判定，而不能宣称此阈值已最佳。BLC 15 和 SC500CS exposure/analog gain/digital gain/VTS 均不改；暗场亮度不足另立实验。
- 构建：TD 6.2.168116 于 22:35–22:43 完成 Synthesis、Physical Design、Timing Check 和 bitgen；路由后 LUT6 13,708（较 BLC_V1 +234）、Slice FF 13,627（不变）、ERAM20K 40、DSP 9、Setup WNS +0.101 ns、Hold WNS +0.020 ns，TNS 均 0。MIPI 时钟域 Setup slack +3.823 ns（BLC_V1 +5.763 ns）；既有 `PHY-5060` ×2、`PHY-5079` ×1，无新增关键告警。归档 bit SHA-256 `D6AA67BB303D661E9ABEADCDE456AB27F6828CA948D89029F89F23028D5AA111`；**Board Test Result：待上板**。
- 下一次只比较 BLC_V1 与 AWB_V2：同照明、机位和显示设置，依次看白纸、中性灰、正常室内综合色彩，再让红/绿/蓝目标各占画面约 20–30%，其余留白/灰背景；最后记录暗场现象但不作为本次 AWB 成败指标。观察白/灰中性、彩色物体进出时背景白平衡与帧间闪色、OSD“安路”、HDMI 连续性。若白/灰更偏、长期不调整、色温漂移或闪色，回滚已归档的 BLC_V1 bit。

## AWB_V2 上板反馈与阶段冻结（用户报告，2026-10-09）

- Version：`AWB_V2`；源码提交 `529e5245e386e1f459a4074d01275326571a3d4b`；候选归档提交 `1563153`；候选 tag `awb-v2-candidate`；bit SHA-256 `D6AA67BB303D661E9ABEADCDE456AB27F6828CA948D89029F89F23028D5AA111`。Build Result：综合、实现、时序、bitgen 通过，Setup/Hold WNS +0.101/+0.020 ns。
- 假设/唯一主要变量：在原亮度窗口外增加 Gray World 低色度样本条件，`CHROMA_THRESHOLD` 从无限制改为 32；BLC `BLACK_LEVEL_RAW10=15` 及其余 ISP、sensor 参数不变。
- Board Test Result：用户报告白/绿相较早期明显改善，红/蓝相较 AWB_V2 前改善，中性灰基本保持灰色，RGB 主色可区分；遮光黑场较好。当前主要缺陷为正常室内和低照度场景整体偏暗，OSD 黄色文字与“安路”Logo 亮度正常。无锁定拍照参数的同场景定量测量、sensor 寄存器读回或连续 30 分钟记录，不将相对改善写成量化结论。
- 是否保留：保留 AWB_V2 作为 Gain Sweep 基线；`CHROMA_THRESHOLD=32` 和 BLC 15 本阶段冻结。下一步仅审计 SC500CS 曝光与模拟增益，固定参数做单变量测试，不在本轮修改 AWB 或实现 AE。

## Fixed Gain Sweep candidate（2026-10-09，待上板）

- 修改假设：整体偏暗可能与 SC500CS 固定模拟增益有关；三版唯一功能变量是实际编译初始化表的 `0x3e08` 粗增益字节。Exposure `0x3e00/01/02=00/7c/60`（1990 半行）、VTS 1000、HTS 1600、`0x3e09=20`、数字增益、BLC 15、AWB_V2 色度阈值 32 及其余 ISP/视频链均不变。相对 B，A 另将旧的“约 4 倍”源码注释改为中性说明；相对 A，C 仅修改该字节。完整审计见 `SC500CS_EXPOSURE_GAIN_AUDIT.md`。
- 预期：同场景锁定手机曝光/白平衡，A(1×)→B(4×)→C(8×) 逐级变亮；噪声与过曝可能增加。此为预期，不是上板结果。测试时不要按增益键，因为 `ae_set` 会同时写超出当前 VTS 上限的 3000 半行曝光。

| Version | 源码提交 | Candidate tag | `3e08/09` | 目标模拟增益 | Bit SHA-256 | Build Result | Board Test Result / 是否保留 |
|---|---|---|---|---:|---|---|---|
| GAIN_TEST_A | `5f73df1c0fb4569c312ea33894e89b08df66becc` | `gain-test-a-candidate` | `03/20` | 1× | `DDE2589CC0CD74E89D4198C4AD937AB946FF4D1DBC65241A1F425A7E3D551AF6` | 完整综合/实现/时序/bit 通过；Setup/Hold WNS +0.101/+0.020 ns | **待上板**；是否保留待比较 |
| GAIN_TEST_B | `16be9c4378fd5a94c467315a0a9e9e45e54b5965` | `gain-test-b-candidate` | `0f/20` | 4× | `A34131C7F2E991F3C9C59627DADBE797CCE7A33E4EB0A0F9A272A5BD9C8CB37E` | 完整综合/实现/时序/bit 通过；Setup/Hold WNS +0.107/+0.020 ns | **待上板**；是否保留待比较 |
| GAIN_TEST_C | `1e3a601cfb8074aa30d81f83600ef5a7a8c42712` | `gain-test-c-candidate` | `1f/20` | 8× | `A7CDBFADF6E10FB68C0B79FE8786AFFBA142D8F4509B48D449C4289ACE32FC66` | 完整综合/实现/时序/bit 通过；Setup/Hold WNS +0.104/+0.020 ns | **待上板**；是否保留待比较 |

逐版原始参数、构建报告、bit 完整路径和证据见 `artifacts/bitstreams/GAIN_TEST_A`、`GAIN_TEST_B`、`GAIN_TEST_C`。本阶段没有硬件 I²C ACK、寄存器读回或定量亮度记录；不可填写“控制已验证”。下一步仅执行固定机位/灯光/显示器/目标的 A→B→C 烧录比较，每版等待 3–5 秒并记录亮度、暗部、白/灰/RGB、噪声、过曝、彩色噪点、OSD“安路”和 HDMI 连续性；测试完成后再建立各版结果提交和正式 tag。本轮不实现 AE。

### A/B/C 上板反馈（用户报告，2026-10-10）

- 测试条件：用户确认 GAIN_TEST_A=1×、B=4×、C=8× 已在**完全相同场景**下上板比较。没有逐像素亮度、照度、噪声、锁定拍照参数或 I²C 读回数值，本记录不补造这些结果。
- 修改假设与唯一变量：依次改变 SC500CS 模拟增益档位；Exposure 始终 1990 half-lines、VTS 1000、HTS 1600，BLC 15 和 AWB_V2 参数不变。三版 bit/源码提交/tag/SHA-256 与构建结果见上表，参数变更为 `03/20`→`0f/20`→`1f/20`。
- Board Test Result：A→B→C 画面亮度**稳定、明显、单调增加**。因此固定模拟增益写入控制链可判为**基本有效**，仍不等同于逐字节 I²C ACK 或寄存器读回证明。C=8× 相比此前明显改善，但正常室内亮度仍略低；用户尚未报告高增益噪声、彩色噪点、高光过曝、灰/白/RGB 定量变化或长时间稳定性结果。
- 是否保留：A、B 保留为已测试对照版本；C 保留为上限档位扩展的起点，不预设最终固定增益。下一步只做 `3e08/09=1f/30`（12×）和 `1f/3f`（15.75×）的单变量候选，比较亮度与噪声；不修改曝光/VTS、数字增益、ISP 或按键，也不实现 AE。

## Analog Gain Upper Range Test candidate（2026-10-10）

- 修改假设：在已实测 8× 且仍略暗的条件下，提高唯一变量 SC500CS 模拟增益细档，检验 12× 是否适合作固定基准，并以 15.75× 观察上限效果。Exposure 1990 half-lines、VTS 1000、HTS 1600、数字增益、BLC 15、AWB_V2、MIPI/Demosaic/DDR/OSD/HDMI 和按键逻辑全部冻结；没有实现 AE。用户提供的 A→B→C 单调增亮属于已有上板证据，D/E 尚未上板。

| Version | 构建时源码提交 | Candidate tag | `3e08/09` | 理论模拟增益 | Bit SHA-256 | Build Result | Board Test Result / 是否保留 |
|---|---|---|---|---:|---|---|---|
| GAIN_TEST_D | `1a3e549fb2ebef29412c90098ccae3c44681f021` | `gain-test-d-candidate` | `1f/30` | 12× | `78E20726747B65B7CC6B5A1149698824B0AA83157E6A8A4DD3BB5DEAEA00C80A` | 全流程完成；LUT6 13,841、FF 13,631、ERAM20K 40、DSP 9；Setup/Hold WNS +0.106/+0.020 ns | **待上板**；保留作候选 |
| GAIN_TEST_E | `b2301a228050458051d4425484fef4c0c523a931` | `gain-test-e-candidate` | `1f/3f` | 15.75× | `EE477E5BAC6D3A315408D2935F80D9DFD85240D45060BA6C434AC421BFE900E2` | 全流程完成；LUT6 13,757、FF 13,625、ERAM20K 40、DSP 9；Setup/Hold WNS 0.000/+0.020 ns，零 setup 裕量、无违反端点 | **待上板**；保留作上限候选 |

两版归档 bit、详细构建证据与源码指纹见 `artifacts/bitstreams/GAIN_TEST_D`、`GAIN_TEST_E`。逐版固定机位、场景、灯光、显示器及手机曝光/白平衡，按 **C=8× → D=12× → E=15.75×** 比较整体亮度、暗部、普通/彩色噪点、白灰 RGB、高光过曝、AWB 稳定性，并观察 OSD“安路”、HDMI 连续性。若 D 亮度合适且噪声可接受，考虑以 12× 为后续固定基准；若 D 仍暗，再看 E；若 E 亮度合适但噪声明显恶化，下阶段研究 VTS/曝光与帧率折中，不直接加数字增益。本轮在 candidate 归档后停止，等待实测。

### GAIN_TEST_E 上板选择（用户 2026-10-10 算法集成任务反馈）

- Version / Git Commit / Git Tag：`GAIN_TEST_E` / 构建源码 `b2301a228050458051d4425484fef4c0c523a931`，归档 `c1e3002bcf895ce1902d517b184cfeaca79ae74b` / `gain-test-e`（本结果提交），原 `gain-test-e-candidate` 保留。
- 唯一变量：模拟细增益 `3e09=30→3f`，粗增益 `3e08=1f`，12×→15.75×；Exposure 1990 half-lines、VTS1000、HTS1600、BLC15、AWB_V2固定。
- Bit SHA-256：`EE477E5BAC6D3A315408D2935F80D9DFD85240D45060BA6C434AC421BFE900E2`；Build Result：完整构建完成、零违例端点，Setup/Hold WNS 0.000/+0.020 ns，setup零裕量。
- Board Test Result：用户确认15.75×亮度基本满意，并决定暂时保持。没有提供D/E同场景定量比较、噪声/高光测量、I²C读回或长稳结果，不补造这些数据。
- 是否保留/下一步：保留E为算法集成临时基线；Stage1只新增Sobel，冻结所有ISP和传感器参数。D继续保留候选对照，未补报上板结论。

## EDGE_V1 Stage 1 candidate（2026-10-10）

- Version / Git Commit / Git Tag：`EDGE_V1` / 实际完整构建源码 `dd42086963eec1b1dbf8284048335502139da069` / `edge-v1-candidate`（归档提交SHA由该tag唯一恢复）。E用户反馈正式tag `gain-test-e` 保留，未移动原candidate tag。
- 修改假设：在用户已认可亮度的E固定基线上，在AWB后、DDR前增加FPGA Sobel流水，维持1280×720连续输入输出与原Logo/CNT。唯一主要变量是Original→固定Edge；修改前AWB输出直接打包，修改后5级两像素对Sobel、阈值80，再打包。编译参数 `EDGE_ENABLE=1`；0分支保留原链路用于接线回归，不实现运行时切换。
- 冻结值：Exposure1990 half-lines、VTS1000、HTS1600、模拟增益1f/3f=15.75×、Digital Gain、BLC15、AWB_V2 CHROMA32及全部参数、MIPI/demosaic/DDR/HDMI/OSD、按键、PLL/ADC/SDC。192个冻结主工程文件SHA一致；B/C只读参考68文件SHA一致。
- Bit SHA-256：`268EAEE8830AF99C6275EAB45AC1C1CDE231127B91DC3B4729754C6FD581D1D6`；归档 `artifacts/bitstreams/EDGE_V1/camera_to_dsi_display.bit`，大小1789539bytes。
- Build Result：完整Synthesis/Physical Design/Timing Check/bitgen通过；LUT6 14174（66.81%）、FF13656（32.18%）、Slice16031（75.56%）、ERAM20K34（31.48%）、DSP9（22.50%）；Setup/Hold WNS +0.107/+0.020 ns，TNS0、违例端点0，无新增关键warning类型。独立空间参考RTL测试7组、512024有效拍通过，含两完整1280×720帧及实际isp_top边界/真实打包器。
- 算法边界：640点水平边缘采样、结果复制两像素，前两行/首4像素黑边，因果窗口约右移2像素/下移1行；不能称为全宽逐像素Sobel。两行RAM实际映射256分布式RAM LUT，不新增ERAM/DSP；总ERAM下降源于黑白输出的FIFO优化。
- Board Test Result：**待上板**。暂未确认新增算法的轮廓质量、噪声假边、HDMI连续性、Logo可见或长期稳定性。完整流程及量化填写项见 `docs/EDGE_V1_BOARD_TEST.md`。
- 是否保留/下一步：保留candidate；PROGRAM_SRAM以E对照固定Edge，观察竖/横/斜界、室内轮廓、移动、光照变化和至少30分钟运行。等待用户实拍后再决定Stage2共享灰度/Binary及Stage3四模式；本轮停止，不自行加AE/Gamma/CCM/VTS或阈值调节。

### EDGE_V1 上板观察（用户2026-10-10 EDGE_CONTROL任务反馈）

- Version / Git Commit / Git Tag：EDGE_V1 / 归档 `08d2a0d39991d29b410235645e769b642246d97d` / `edge-v1-candidate`；构建源码、唯一变量及参数见上节，原tag不移动。
- Bit SHA-256：`268EAEE8830AF99C6275EAB45AC1C1CDE231127B91DC3B4729754C6FD581D1D6`，完整构建通过，Setup/Hold +0.107/+0.020 ns。
- Board Test Result：用户确认可以输出边缘检测画面，但弱光时许多弱边缘不明显或检测不到；没有报告30分钟稳定性验收或量化边缘/噪声数据。
- 是否保留/下一步：保留作为有效Sobel对照。下一版只做ORIGIN/EDGE切换、10–250阈值控制及对应OSD；保持sensor/ISP参数，不通过提高增益/曝光补偿。
- 按键补充：用户说明旧两个“增益按键”输入此前未使用并允许修改；用户提供的原理图证明N2/J14为扩展GPIO，板载K3/K4应为B9/C7。本轮按该只读原理图修正，详见EDGE_CONTROL_V1_PLAN。

## EDGE_CONTROL_V1 candidate（2026-10-10）

- Version / Git Commit / Git Tag：`EDGE_CONTROL_V1` / 实际TD构建源码 `dff499a75cf0a348aaf2167548b4fe34bf4a78a9` / `edge-control-v1-candidate`，归档提交SHA可由该tag唯一恢复；原EDGE/E及其他版本保留。
- 修改假设/唯一主要变量：为同一Sobel增加运行时控制能力及帧关联状态。修改前固定EDGE/80；修改后默认EDGE/80，K3(B9)切换ORIGIN/EDGE，K4(C7)短按−10/长按约0.7s+10，阈值10–250饱和。输入同步、消抖、CDC整体邮箱、AWB提前SOF帧边界提交；Original增加5拍对齐，Sobel始终运行。状态文字在DDR前叠加，原DDR后Logo/CNT保持。
- Sensor隔离与冻结：旧ae_set实例解除、I_ae_req固定0，按键不能触发Exposure/Gain写入。Exposure1990、VTS1000、HTS1600、Gain1f/3f=15.75×、Digital Gain、BLC15、AWB_V2及MIPI/demosaic/DDR配置/HDMI/PLL/SDC不变。用户允许修改旧未使用输入，按用户原理图修正N2/J14扩展GPIO为K3/K4真实B9/C7。190冻结主工程、68只读参考、3原理图SHA一致；58个实际TD输入与构建源码一致。
- Bit SHA-256：`05E05B153800E38982D7D1C2981A347B3616EAFA6EABA91A43443468FAF5DCF6`；`artifacts/bitstreams/EDGE_CONTROL_V1/camera_to_dsi_display.bit`，1789539bytes。
- Build Result：完整Synthesis/Physical/Timing/bitgen通过；LUT6 14724、FF14417、Slice16473（77.64%）、ERAM20K39、DSP9；Setup/Hold +0.100/+0.020ns，TNS0、违例端点0，无新增关键warning类型。首轮纯输入ADC的DRIVESTRENGTH入口失败已修正并重新完整构建，保留失败日志。RTL检查点A–D通过，共1293320有效拍/969990打包字，四完整720p帧；异步CDC200快速请求、116次sensor初始化写入后50组按键无新增写入（I2C握手stub）。
- Board Test Result：**待用户上板**，没有新版本实拍或30分钟结果。步骤见EDGE_CONTROL_V1_BOARD_TEST；固定场景比较80/60/40/20及100/120/160，记录真实轮廓和噪声假边，至少20次模式切换与30分钟稳定性。
- 是否保留/下一步：保留candidate，停止并等待用户反馈。640点Sobel/两像素复制与既有核偏移保持，降低阈值不等于增加采集信息；不自行进入Gray/Binary/AE或曝光/VTS调整。

### EDGE_CONTROL_V1 上板观察（用户2026-10-16反馈）

- Version / Git Commit / Git Tag：EDGE_CONTROL_V1 / 归档`467df3cee53218f4bc9eab7b29bfbc9df084dd97` / `edge-control-v1-candidate`；原bit和tag保持，SHA256 `05E05B153800E38982D7D1C2981A347B3616EAFA6EABA91A43443468FAF5DCF6`，原构建+0.100/+0.020ns。
- Board Test Result：ORIGIN彩色正常，无肉眼明显雪花，亮度基本满意；弱光EDGE在80漏弱边，降阈值增加真边也增加大量白色假边；增照明明显减少雪花；部分遮挡噪点相对稳定并小幅波动；全遮光几乎全黑。尚无定量数据、20次切换或30分钟稳定性结果。
- 是否保留/下一步：保留未降噪对照。只验证Edge分支Gaussian滤波，先对照原Sobel/Gaussian/Median合成模型，不改变Sensor/ISP画质；现象支持低照噪声梯度重叠，但不能排除其他硬件因素。

## EDGE_DENOISE_V1 candidate（2026-10-16）

- Version / Git Commit / Git Tag：EDGE_DENOISE_V1 / 实际构建源码`b78dd6b43730c69896bf99753c6b961c3f44a9ae` / `edge-denoise-v1-candidate`（归档提交由tag唯一恢复）；MAIN分支codex/main/edge-denoise-v1，基线c42168e，协议TEAM_PROTOCOL_V1；PR等待Philid14审查，未自动合并main。
- 修改假设/唯一主要变量：Edge在原灰度/两像素平均后新增3×3Gaussian，再保持原Sobel/阈值；降低噪声梯度同时保留足够真实轮廓。原DENOISE_ENABLE=0，无滤波5拍；候选=1，Gaussian4拍+Sobel5拍，原图/配置同9拍，OSD2+打包1总12拍。K3/K4语义、默认EDGE080/10–250、OSD内容/位置不变。
- 冻结参数：Exposure1990、VTS1000、HTS1600、Gain1f/3f=15.75×、Digital Gain、BLC15、AWB_V2、demosaic/MIPI/DDR/HDMI/PLL/ADC/SDC与旧版一致。194主工程/68只读参考/3原理图SHA一致；59实际TD输入与构建提交匹配；旧11个bit均未改。
- 模型：研究提交a3796fe先于RTL，13合成场景/三方案/13阈值=507行CSV；无实际传感器RAW/RGB帧。低对比阶跃选点原TH70/GaussianTH40/MedianTH40误检0.2634%/0.0718%/0.0399%、召回均100%；细线保留下降、椒盐Median更好。不能把合成收益当作实板结论。
- Bit SHA-256：`224D4BE2F53B807137E19D095DCF6132BAA9CFC023C3C59BCE17ABDE3332B84A`，归档artifacts/bitstreams/EDGE_DENOISE_V1/camera_to_dsi_display.bit，1789539bytes。
- Build Result：完整Synthesis/Physical/Timing/bitgen通过；LUT6 15163、FF14667、Slice16859（79.46%）、ERAM39、DSP9；Setup/Hold +0.112/+0.020ns、TNS0、违例0，既有关键类型PHY-5060/5079，无新增关键类型。Gaussian新增两条SYN-5041，实际额外256 DRAM LUT、0ERAM/0DSP。独立Gaussian1282拍、新联合1764876拍/1323657字（四完整720p帧）、旧旁路回归1293320拍全部PASS。
- Board Test Result：**待用户上板**；实际雪花减少幅度、真实弱边/细线是否保留、HDMI连续性及30分钟长稳尚未测试。新旧核中心约偏移4像素/2行与2像素/1行；候选首4行/首8像素置黑，整帧172800个DDR字不变。
- 是否保留/下一步：保留候选和原控制版bit，按EDGE_DENOISE_V1_BOARD_TEST同机位/照明分别扫描阈值，重点弱光ROI/细线/遮挡/运动、20次切换与30分钟。完成候选即停止，不直接集成Median/Canny/AE或改变曝光/VTS。

### EDGE_DENOISE_V1 上板观察（用户EDGE_NMS任务反馈）

- Version / Git Commit / Git Tag：EDGE_DENOISE_V1 / candidate归档08ea909febf2dd0952e7221a0ce2bf34b24e3b44，构建b78dd6b / edge-denoise-v1-candidate。bit SHA256 `224D4BE2F53B807137E19D095DCF6132BAA9CFC023C3C59BCE17ABDE3332B84A`，原完整构建+0.112/+0.020ns。
- Board Test Result：用户描述夜间弱光020/040/060/080四档实拍：020碎纹理密集且局部成片；040轮廓和纹理丰富但碎边多；060主要轮廓相对明显而弱细节减少；080较干净但丢弱边。不能将所有白纹理判断为噪声。未得到本轮可用ORIGIN RGB输入或30分钟结果，不补造定量结论。
- 是否保留/下一步：保留未NMS对照，下一版只加二值化前NMS，研究双阈值仅限软件。PR #3尚未合并，不自动合并或改其分支，新增依赖分支codex/main/edge-nms-v1。

### EDGE_NMS_V1 用户上板观察（2026-10-17，EDGE_QUALITY任务补录）

- Version / Git Commit / Git Tag：EDGE_NMS_V1 / 归档712fbb33cfc5ba8436b96306e1fe443553aa6591，实际构建8ae2fd6 / edge-nms-v1-candidate；SHA256 `734F5D97C429D086FBE8518514B8547CF0C2FBC485B44D35BD218F0F7FA2A448`。历史归档文件/tag保持原样，本条只追加新反馈。
- 修改假设/唯一主要变量/原值/新值：前轮在Gaussian+Sobel单门限前加入NMS；完整TD原结果LUT6 15206、FF15018、Slice16598、ERAM39、DSP9，Setup/Hold+0.101/+0.020ns。
- Board Test Result：用户确认边缘明显变细，弱边仍易断裂；TH40眼镜/脸/头发轮廓较丰富但杂线多，TH60较干净同时缺真实轮廓，TH80大量弱边消失。本轮3张拍屏能观察到对应类型现象，但右侧OSD裁切，不能自行逐张认定TH数字或计算真实原图召回率。没有可用摄像头ORIGIN RGB，也未提供30分钟稳定性/溢出测量。
- 是否保留/下一步：保留NMS作为准确可回退对照；EDGE_QUALITY只研究Edge内部质量，先模型比较再实现，Sensor/原图内容/外部链路冻结。待用户评价连续性与杂边的真实折中，不自动合并#3/#4。

## 每次测试填写项

- 固件/工程版本、TD 工程路径、综合/时序结果、修改的唯一因素、原始/新寄存器编码；保留 bitstream 的可识别名称。
- 硬件：HX1P35A 与 SC500CS 模组/镜头版本、显示器、线材、供电；若能读回寄存器，记录 `320e/f`、`3e00/01/02`、`3e06/07`、`3e08/09`。读回能力未确认时注明“无法读回”。
- 环境：固定机位、固定色卡/灰卡/红蓝物体和背景；注明照度（无照度计则记录灯具、距离和手机曝光锁定情况）、色温/光源、遮挡方式。拍摄输出屏幕时关闭手机自动曝光和自动白平衡，或在两版中严格锁定同设置。
- 稳态：明亮室内、弱光室内、暖色灯各录至少 30 秒；截同位置灰卡、白纸、红/蓝物体、暗部、高光。记录画面平均亮度（若可导出帧）、灰卡 R/G/B 均值、饱和像素比例、主观噪声和色偏；记录 OSD“安路”Logo 可见。
- 光照阶跃：在固定镜头前从亮切暗、暗切亮，各重复 3 次；记录恢复时间、是否过曝/欠曝、色彩漂移、帧率及是否花屏。当前为手动曝光，自动恢复可能不存在，应如实记录。
- 按键：属于后续曝光/增益专题，本轮 AWB_V1 不测试 K3/K4，也不据此判断色彩修正效果。
- 稳定性：连续运行至少 30 分钟，记录花屏、错位、缓存溢出/丢帧指示、HDMI 中断、异常重启。没有仪器读数时不能填写“0”。
- 决策：列出本版改善/退化、是否达到“连续稳定且色彩自然”的目标、保留或回退依据。下一版仍只改变一个主要因素。

## 待填测试记录模板

| Version | 修改内容 | 原值 | 新值 | 测试环境 | 结果 | 是否保留 |
|---|---|---|---|---|---|---|
| Vx |  |  |  |  |  | 待定 |

截图命名建议：`Vx_场景_按键前后_日期.png`；原始视频与截图可另存证据目录，日志中写路径及时间点，不在文档中压缩或美化图像。

## Git 追溯（2026-10-06 建立仓库时补录）

| Version | Git Commit | Git Tag | 实际编译源码 | 源码 SHA-256 | 归档 bit | Bit SHA-256 | Build Result | Board Test Result | 是否保留 |
|---|---|---|---|---|---|---|---|---|---|
| Baseline V0 | `7466c7f19e8e3f592486b52ba5d9720eb5f176c0` | 无 | `docs/baseline/awb_v0_compiled.v` | `B6D9D83A6B48952CC9531DAF39BC6C6B94C4E45DDEFE603908E9CB275533E50A` | `artifacts/bitstreams/BASELINE_V0/camera_to_dsi_display.bit` | `D42E4AFC8CC6939230DAB332EEBE6E439297F1EA9FC57E6984152B60C673D668` | 综合 / 实现 / bit 全部成功；Setup WNS +0.109 ns、Hold WNS +0.020 ns、TNS 0 | 已上板（2026-10-05 约 21:00）：基础颜色测试不通过 | 保留作对照 |
| Candidate AWB_V1 | `7466c7f19e8e3f592486b52ba5d9720eb5f176c0` | `awb-v1-candidate` | `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/awb.v` | `F952339EC4F19C61947B98C041CF9801021A6763B6CF103D32A46D89D6B47AD3` | `artifacts/bitstreams/AWB_V1/camera_to_dsi_display.bit` | `6512B12C1F231DED42A7809766273CA58D677472FFB08BBE009B839512C729A3` | 综合 / 实现 / bit 全部成功；Setup WNS +0.101 ns、Hold WNS +0.020 ns、TNS 0 | **用户反馈已上板**：相对 V0 色彩轻微改善；仍有明显偏色与灰雾感，缺同场景定量数值 | 保留作 BLC_V1 对照 |
| BLC_V1 | `347dff76d67f8072fc3f0c7a4e78bd01bfae7dbc` | `blc-v1-candidate`；上板记录 `blc-v1` | `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/isp_top.v` | `4F15F8588FA6AA7249CD01D470E943E18B761F95B356AC3F7698E8C01B054DD5` | `artifacts/bitstreams/BLC_V1/camera_to_dsi_display.bit` | `2B9E427DEE8304106F5E75A686899D189E4B61EB3514A4AE33C51EA536FB133D` | 综合 / 实现 / bit 全部成功；Setup WNS +0.137 ns、Hold WNS +0.020 ns、TNS 0；关键告警无新增 | **用户反馈已上板**：遮光黑位较好；白/绿有所改善；白仍偏青绿，红/蓝和低照度偏暗；未观察到显示异常 | 保留；BLC 参数 15 暂时冻结，低照度留作独立问题 |
| Candidate AWB_V2 | `529e5245e386e1f459a4074d01275326571a3d4b` | `awb-v2-candidate` | `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/awb.v` | `5DB871953306D5EDB4F2D9B17E1EC18F0A6D32DE052192F77FDF999ECC336FF0` | `artifacts/bitstreams/AWB_V2/camera_to_dsi_display.bit` | `D6AA67BB303D661E9ABEADCDE456AB27F6828CA948D89029F89F23028D5AA111` | 综合 / 实现 / bit 全部成功；Setup WNS +0.101 ns、Hold WNS +0.020 ns、TNS 0；关键告警无新增 | **已上板（用户 2026-10-09 反馈）**：白/绿、红/蓝改善，中性灰基本为灰；正常室内和低照度整体偏暗；缺量化与长稳记录 | 保留为固定 Gain Sweep 基线，冻结 AWB/BLC |

补充说明：

- 时间线：V0 = 2026-10-05 20:13–20:22 构建，约 21:00 上板；AWB_V1 = 2026-10-05 21:43–22:17 构建，用户于 2026-10-08 反馈已上板；BLC_V1 = 2026-10-08 18:13–18:22 构建，用户同日反馈已上板；AWB_V2 = 2026-10-08 22:35–22:43 构建，用户于 2026-10-09 反馈已上板。
- 资源明细、告警与证据清单见 `artifacts/bitstreams/<VERSION>/BUILD_INFO.md`；两个版本的构建日志已随版本一并归档。
- V0 的 bit 在构建时未记录 SHA-256 与归档路径，原始 `phy_1` 目录随后被 AWB_V1 构建覆盖。本次从 `best_result/` 中恢复出与 V0 构建时间（2026-10-05 20:22:08）及 `phy_run.log` 一致的 bit 并归档；该对应关系以时间戳和构建日志为据，**未做上板复现**。
- 未建立 `baseline-official-osd` / `baseline-official-edge`：归档时 `user_source/hdl_source/awb.v` 已是 AWB_V1，工作目录内不存在可逐字节校验的官方原始副本，不能把已修改工程标记为官方基线。需取回官方原始压缩包校验后单独提交并打 tag。
- 追溯链：`bit 文件 → Git commit → 源码 + 工程配置 + 约束 + 文档 + 构建信息 + 上板测试记录`。

## EDGE_NMS_V1 candidate（2026-10-16，MAIN）

- Version / Git Commit / Git Tag：EDGE_NMS_V1；实际构建源码`8ae2fd6c38416095e1232783a0e63b2eb2d1e9f3`；归档提交通过`git rev-parse edge-nms-v1-candidate^{commit}`唯一解析；tag `edge-nms-v1-candidate`；分支codex/main/edge-nms-v1，base08ea909/PR #3，Draft PR依赖降噪分支，等待Philid14最新提交审查。
- 修改假设/唯一主要变量：只在Gaussian+Sobel幅值与二值阈值间加入方向NMS，压窄粗边；原值Gaussian4+Sobel5共9拍分支，新值Gaussian4+Sobel前4+NMS4+阈值1共13拍，Original/配置/标记同步延迟。逻辑缓存新增19200bit。Exposure1990 half-lines/VTS1000/HTS1600/Gain15.75×/BLC15/AWB_V2/Gaussian/按键/OSD/MIPI/DDR/HDMI/PLL/约束冻结，无双阈值硬件。
- Bit SHA-256：`734F5D97C429D086FBE8518514B8547CF0C2FBC485B44D35BD218F0F7FA2A448`；路径artifacts/bitstreams/EDGE_NMS_V1/camera_to_dsi_display.bit。
- Build Result：完整Synthesis→Physical Design→Timing Check→bitgen通过；LUT6 15206、FF 15018、Slice 16598 (78.23%)、ERAM 39、DSP 9；Setup/Hold +0.101/+0.020ns，TNS0/端点违例0，既有PHY-5060/5079保留无新增关键类型。新联合2264588拍/1698441字、NMS单元2564拍/4200中心、25方向、旧旁路1764876拍/1323657字及控制回归通过。首轮仅有声明顺序warning，修复后完整重建，无失败bit；原始证据保留。
- Board Test Result：**待用户上板**。软件合成TH40直阶跃厚度4→1、模糊阶跃7→1且100%逐行覆盖；不等于真实场景测量。未发现真实ORIGIN RGB帧，未证明物理I2C/厂商PHY或长期整机稳定。
- 是否保留/下一步：保留candidate及旧降噪对照；按EDGE_NMS_V1_BOARD_TEST同条件比较020/040/060/080，优先边缘变细且主要轮廓不过度断裂，纹理仍被检测不直接判失败。至少20次切换/30分钟，等待结果；不自行进入滞后硬件、AE或其他扩展。

## EDGE_QUALITY_V1_R0 工程检查点（2026-10-17，未选为上板candidate）

- Version / Git Commit / Git Tag：EDGE_QUALITY_V1_R0，构建acf7d444f19ae0dbb8a36a854edc7627f7f8b2ec；归档commit通过edge-quality-v1-r0-build^{commit}解析；分支codex/main/edge-quality-v1。
- 假设/唯一变量/原值/新值：NMS后加入四跳强锚弱边连接，单阈值→high=TH/low=floor(TH/2)，总16→28拍；Sensor、原图内容及外部控制/链路冻结。
- Bit SHA256：27FDB0B07DD1AE9196164D209DA54CF48E3867BD6F9357549AEE3100ECD0126B；artifacts/bitstreams/EDGE_QUALITY_V1_R0/camera_to_dsi_display.bit。
- Build Result：全流程成功、Setup/Hold+0.102/+0.020ns、TNS0；LUT6 16888/FF15402/Slice18263(86.08%)/ERAM39/DSP9。四层512DRAM LUT高于预算，Slice增量1665超过1400目标。
- Board Test Result：未上板，不推荐烧录。是否保留/下一步：保留bit和全部证据，未选为最终candidate；仅优化等价缓存成对写入，重新验证和构建，不能把R0称作优化后版本。

## EDGE_QUALITY_V1 candidate（2026-10-17，MAIN）

- Version / Git Commit / Git Tag：EDGE_QUALITY_V1；实际构建源码`97858d51c7599a504a733b2302db797207c1ac0e`，归档commit通过`git rev-parse edge-quality-v1-candidate^{commit}`唯一解析；tag edge-quality-v1-candidate，分支codex/main/edge-quality-v1，base712fbb3，PR依赖codex/main/edge-nms-v1/#4/#3，等待Philid14审查。
- 修改假设/唯一主要变量：在冻结Gaussian/Sobel/NMS后四跳8邻接强锚弱边传播。原值单TH逐点二值化/13拍Edge分支，新值high=TH/low=floor(TH/2)、最多4跳/25拍Edge，Original/config等量对齐；OSD+打包总16→28拍。最终逻辑行数组新增7680bit，实际DRAM增量+0LUT。Sensor/ISP画质、NMS/Gaussian、原图内容、按键/OSD/Logo/CNT、外部链路和时钟约束冻结。
- Bit SHA-256：`629ACAA828EF8151DED0261779ED8B91F0FA618EED66DD46C72D6E799ADCC9D5`；路径artifacts/bitstreams/EDGE_QUALITY_V1/camera_to_dsi_display.bit。
- Build Result：完整Synthesis→Physical Design→Timing Check→bitgen成功；LUT6 16162、FF 15423、Slice 17894 (84.34%)、ERAM 47、DSP 9，Setup/Hold +0.009/+0.020ns、TNS0、端点违例0。既有关键类型保留、无新增关键类型；61项源码匹配、13旧bit加R0及旧归档不变。新联合2699276拍/2024457字、旧NMS回归2264588拍/1698441字、四层独立168500拍/1348000采样层、分类2892采样及旧控制单元通过。
- Board Test Result：**待用户上板**。合成TH60平均轮廓召回67.28%→74.20%，平坦误检0.0043%→0.028%；没有真实ORIGIN帧，不等于实际眼镜/脸/文字质量改善已确认。TH40可能扩散噪声，零响应/无强锚弱边仍不能恢复，孤立强点仍保留。
- 是否保留/下一步：保留candidate及原NMS对照，按EDGE_QUALITY_V1_BOARD_TEST同场景分别做同TH及近似相同完整度比较，40/50/60/70/80扫描、至少20次切换/30分钟。R0资源未达目标已保留、未作为最终candidate；首次测试夹具失败已修复，主动中断较宽地址回归后按最终源码统一重跑。停止等待实板，不自动改曝光/VTS、增跳数、换采样密度或合并PR。

## EDGE_TEMPORAL_V1 candidate（2026-10-18，MAIN）

- Version / Git：EDGE_TEMPORAL_V1；分支codex/main/edge-temporal-v1；实际TD源码7aa6beb87d477c01303f44b6d50a0ca66f2c9ac8；candidate tag edge-temporal-v1-candidate（归档commit由tag唯一解析）；Draft PR#10→#6/#4/#3，不自动合并。准确QUALITY基线b64daf3，研究PR#9仅为证据来源，没有继承诊断缓存。
- 修改假设 / 唯一主要算法变量：当前未抑制Sobel梯度仍≥TH/2时，最多保留一采集帧原始QUALITY边缘；不递归保存已保持结果。修改前为Gaussian/Sobel/NMS/四跳，修改后加单帧保持；高低门限、Sensor Exposure1990/VTS1000/HTS1600/Gain15.75×、BLC15/AWB_V2、K3/K4、原OSD/Logo/CNT、视频规格及PLL/SDC不变。
- 独立可靠性观测：只读写FIFO.full计数，前600帧B/之后S；新增第三行十六进制历史计数。FIFO控制未改；没有实板计数反馈前，不宣称启动或稳态根因已定位。原Gray max_delay两组18路径仍Ignored，未改全局约束。
- Bit：artifacts/bitstreams/EDGE_TEMPORAL_V1/camera_to_dsi_display.bit，1789539 bytes；SHA256 `14A36D98BC0A1547F84588087D796C14098AD4441CB30B5878D8F81CBADC95C4`。
- Build Result：完整Synthesis→Physical Design→final Timing Check→bitgen PASS；LUT6 16119、FF15657、Slice17684（83.35%）、ERAM75、DSP9；Setup/Hold +0.133/+0.020ns，TNS0、违例0，STA96.05%，无新增关键warning类型。相对QUALITY全设计净增FF234/ERAM28，LUT−43/Slice−210/DSP0；重映射净值不能当算法负面积。新增2接收时钟周期，无新增整帧等待/空间偏移。
- Verification：最终严格门禁5481周期单元、最终720p×2帧460800拍/345600打包字、10帧小尺寸及状态OSD、旧QUALITY/NMS与link尾数/1280地址回归、FIFO计数独立测试通过；R0正常算法核心另有720p×10帧对照。未进行新候选实板或门级/SDF验证。
- 失败保留：R0时序通过但组合重复/缺EOL能误接纳历史，拒绝上板；归档EDGE_TEMPORAL_V1_R0、tag edge-temporal-v1-r0-build。最终仅增加逐行pending_eol资格检查并完整重建，不移动旧tag/bit。
- 模型结果：TH60弱/强静态边缘翻转约下降49%/46%，参考轮廓容差召回保留，但线会增厚；8px/帧移动未像投票那样完全丢失。真实18:42 ROI TH40翻转16.6667%→14.8667%、平均边缘94.167→126.167，无真值不判定真实画质提升。
- Board Test Result：**待用户烧录**；真实静态稳定、运动增厚/拖影、S计数稳态复发、30分钟及明暗变化均待测。
- 是否保留 / 下一步：保留此candidate及R0全部证据，见EDGE_TEMPORAL_V1_REPORT/BOARD_TEST/DESIGN。先5/30/120秒B/S，再同TH旧新固定目标与移动/消失对照；S增加先阻断正式验收查FIFO。完成本轮即停止，不自动合并或开展下一版。

## EDGE_MULTI_MODE_V1 candidate（2026-10-18，MAIN）

- Version / Git：EDGE_MULTI_MODE_V1；分支`codex/main/edge-multi-mode-v1`；实际TD源码`4ea67f194941c6717fc1d28889c687a4fb78533f`；candidate tag `edge-multi-mode-v1-candidate`；从EDGE_TEMPORAL_V1 `b47105f`起分支，Draft PR以`codex/main/edge-temporal-v1`为base，不自动合并。
- 修改假设 / 唯一主要变量：在原有ORIGIN/EDGE基础上增加GRAY、BINARY及18位帧锁存配置；`Y=(77R+150G+29B+128)>>8`，BINARY按`Y>=T`输出纯黑白。新增分支与Edge共用27拍窗口，Edge历史在所有模式持续运行。Sensor Exposure1990/VTS1000/HTS1600/Gain15.75×、BLC15、AWB_V2、MIPI/DDR/HDMI、Logo/CNT、PLL/引脚/SDC不变。
- 参数/控制：复位`EDGE/EDGE_TH=80/BINARY_TH=130`；K3为`EDGE→ORIGIN→GRAY→BINARY→EDGE`；K4短按-10、长按+10，ORIGIN/GRAY忽略，两个阈值独立保存，10..250饱和。配置整包跨24MHz→MIPI接收域，AWB提前SOF锁存，帧内不以新配置切换数据。
- R0：移位加法实现LUT6 17040、FF15801、Slice18483、ERAM75、DSP9，Setup/Hold +0.002/+0.020ns；虽零违例但2ps裕量不足，拒绝上板，归档`EDGE_MULTI_MODE_V1_R0`及tag `edge-multi-mode-v1-r0-build`。
- 最终Bit：`artifacts/bitstreams/EDGE_MULTI_MODE_V1/camera_to_dsi_display.bit`，1789539 bytes；SHA256 `8C62195DA8A2F8748CE9D6CFD7D9703BCB81E6F6CDA09AEDF4BBB0DE0FE0BBE9`。
- Build Result：完整Synthesis→Physical Design→final Timing Check→bitgen PASS；LUT6 16942、FF15809、Slice18319（86.35%）、ERAM75、DSP21；Setup/Hold +0.107/+0.020ns，TNS0、违例0，STA96.16%，无新增关键warning类型。相对TEMPORAL LUT+823/FF+152/Slice+635/ERAM0/DSP+12；亮度常数乘法映射DSP后，全设计较R0恢复105ps Setup裕量。
- Verification：9288像素灰度/二值边界与随机对照、K3/K4/18位CDC、九帧混合四模式4608拍/3168字、完整720p×2帧460800拍/345600字逐字节通过；18个V1算法/ISP/DDR/HDMI/Logo/引脚/SDC文件SHA保持一致。
- Board Test Result：**待用户烧录**。默认EDGE、四模式切换、GRAY灰阶、BINARY纯黑白、双阈值保留、OSD/Logo/CNT、B/S计数、30分钟及光照变化均待测。
- 是否保留 / 下一步：保留最终candidate及R0全部证据。按`docs/EDGE_MULTI_MODE_V1_BOARD_TEST.md`验收；S计数增长先阻断正式验收并查FIFO/DDR。完成本轮即停止，不自动合并或开始下一阶段。

## EDGE_STYLE_FILL_V1 candidate（2026-10-19，MAIN）

- Branch/Source/Tag：codex/main/edge-style-fill-v1；实际TD源码`042345cb0e92a1cc5ea0a74fed1be352cf338f2c`；edge-style-fill-v1-candidate。基线四模式ed55269，用户已反馈整体可接受；Draft PR依赖#11，不合并main。
- 唯一主要变量：增加独立STYLE有界2×2同色均值/64色填色/RGB描黑；不是全物体或洞填充。原四模式算法、Sensor/ISP、Logo/CNT/B:S、DDR/HDMI、PLL/SDC不变。19位配置；K3加STYLE，K4旧阈值独立保留。
- Bit：artifacts/bitstreams/EDGE_STYLE_FILL_V1/camera_to_dsi_display.bit；SHA `B4FBB61FABD6A510B26EEC6DAD4D950FF8A3D2B6F561753D5611B334274B336E`。
- Build：完整TD PASS；LUT16592 / FF16972 / Slice17792 / ERAM85 / DSP21；Setup/Hold +0.104/+0.020ns；TNS0、违例0。
- 验证：合成几何/缺口/嵌套/运动/复位逐像素，完整720p五帧1152000拍/864000打包字；59个冻结TD输入及构建选项一致。证据见EDGE_STYLE_FILL_V1_REPORT.md。
- Board Test：待用户上板；真实视觉、B/S稳态、30分钟/光照变化未验收。保留候选与全部历史；按BOARD_TEST检查，S增长阻断正式验收。完成candidate后停止。

## EDGE_STYLE_FILL_V2 candidate（2026-10-19，MAIN）

- 基线：V1/e17a1af，用户已上板，功能基本正常但有绿青斑/细线与星中心损失/过描黑/偏色/高光白化；本轮拍屏和数字卡证据见EDGE_STYLE_FILL_V2_DESIGN.md，无摄像头ORIGIN帧。
- Git：codex/main/edge-style-fill-v2；实际TD源码`694559fd76676093e134229d435161ecb44ab00c`；tag edge-style-fill-v2-candidate；Draft PR依赖STYLE_V1/#12，不合并。
- 唯一主要变量：STYLE渲染策略；V1独立4级RGB+极差黑边→V2保守均值+9档共享明度/中性保护+亮度暗侧描边。仅1个RTL文件变化，其余65个TD输入不变；原四模式/ISP/Sensor/按键/OSD/视频/PLL/SDC冻结。新增流水0拍、ERAM增量+0。
- Bit：artifacts/bitstreams/EDGE_STYLE_FILL_V2/camera_to_dsi_display.bit；SHA `CFB7435648ED50310F053AFE138702F2094B0061B6A7DD68B3B064B6B3D88F51`。
- Build：完整TD PASS；LUT17170 / FF16814 / Slice18140 / ERAM85 / DSP21；Setup/Hold +0.100/+0.020ns；TNS0、违例0。
- 模型/RTL：中性门限彩斑47.31%→0，数字星/亮线结构误差→0；这些不是实板改善率。5尺寸×63序列、完整720p五帧1152000拍/864000打包字通过。
- Board：待用户上板；按BOARD_TEST比较ORIGIN/V1/V2；浅色去饱和/明度色带/输入饱和不可恢复等代价已记录。B/S稳态、30分钟/光照变化待验收，S增长阻断正式验收。
- 保留候选与V1全部历史；停止本轮，不开发进阶五或队友目标检测。

### 2026-10-28 / COLOR_COMPARE_V1 candidate / MAIN

- 用户明确停止STYLE_V2_TARGET黑屏修复，改从已正常上板的EDGE_STYLE_FILL_V2推进固定平台颜色比对。
- 基线tag edge-style-fill-v2-candidate（8d26c6e）；新分支codex/main/color-compare-v1；实际TD源码commit 06e70a0d5d1676ed7991c475facd533b2b804aad。
- 唯一主要新增功能：并接于算法前彩色流的左右128×128区域RGB均值/粗颜色分类/差值比对，OSD显示REF/TEST/ABS/L1/MAX与LAST；不引入TARGET事务帧通路、不控制原视频读写。
- 原Sensor/ISP、曝光1990、VTS1000、HTS1600、15.75×增益、BLC15、五模式算法和K3/K4、Logo/CNT、MIPI/DDR/HDMI/PLL/SDC不变。公共像素流水新增2拍，无新增ERAM/DSP。
- 软件/RTL：80帧统计/4464检查、218快照2398字段、完整五模式720p 1152000四像素拍/864000打包字及原键控/CDC/STYLE回归PASS；物理IP和实板不在该仿真证明范围。
- TD SYN→Physical→final Timing→bitgen PASS：Slice19336、LUT6 18104、FF17606、ERAM85、DSP21；Setup +0.000ns，Hold +0.020ns，TNS0。Setup裕量紧，一次布局后优化未改善、未选用。不能报告长期实板稳定。
- Bit：artifacts/bitstreams/COLOR_COMPARE_V1/camera_to_dsi_display.bit；SHA256 b3dd03799924184d73bbd805caaa57c245a498030376d24ca75205ce06e91d27；candidate tag color-compare-v1-candidate（待实际创建/push记录）。
- Board Test：NOT_RUN；相机RGB差非标定ΔE，LIM12为演示容差，空框/背景仍参与均值。保留候选等待上板，暂不进入测尺寸或后续ISP调节。
