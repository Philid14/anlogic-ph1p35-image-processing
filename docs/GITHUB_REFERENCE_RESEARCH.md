# 基础画质 GitHub 源码调研记录

日期：2026-10-05。范围：SC500CS、RAW→RGB、AWB/AE 及后续可选 ISP；本轮只做静态研究，未复制第三方代码，未修改视频 RTL，也未声称完成上板画质验证。主工程为 `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd`。检索和以下源码读取均经已连接的 GitHub MCP 完成；链接固定到读取时的 commit，便于复核。仓库活跃度和许可信息是读取时状态。

> 2026-10-05 AWB_V1 更新：上一轮“未修改视频 RTL”的说明只适用于上一轮研究。TD 工程 `camera_to_dsi_display_Runs/syn_1/camera_to_dsi_display.prj` 实际编译的是 `user_source/hdl_source/awb.v`，**不是**同目录树内的 `user_source/hdl_source/isp/awb/awb.v`。此前四组独立增益的分析对应后者；实际基线只统计每拍四像素中的第一个，并用一组 R/B 增益处理全部四像素。实际编译源还有帧内更新和未延迟帧起始输出。本轮 AWB_V1 仅修改实际编译的文件；旧版保存于 `docs/baseline/awb_v0_compiled.v`。

## 1. 同传感器配置的逐项对照

本地依据：`user_source/hdl_source/uics500_cfg/uics500reg_720p60.v`、`uics500regAE.v`、`SC500GainTbl.v`，以及 `uiisp_beta/ae_set.v`。下表仅比较写入值；外部工程的时钟、分辨率和板级条件不同，**不能把寄存器值直接搬入本地工程**。

| 项目 | 本地 720p 表 | Cirbug/sc500cs | Allwinner 驱动 | 判断 |
|---|---|---|---|---|
| 输出宽高 `3208–320b` | `0x0500 × 0x02d0` = 1280×720 | `0x0a20 × 0x0798` = 2592×1944 | 本次读取的片段未覆盖宽高 | 场景不同，不能直接对比曝光亮度。 |
| HTS `320c/d` | `0x0640` = 1600 | `0x0b24` = 2852 | `0x0640` = 1600 | 只能结合像素时钟推帧率。 |
| VTS `320e/f` | `0x03e8` = 1000 | `0x0bb8` = 3000 | 驱动会在长曝光时更新 VTS | 不能把较长曝光值孤立移植。 |
| 曝光 `3e00–02` | `00 7c 60`，寄存器编码 `0x07c6` = 1990 | `3e01/02 = 8c/60`，编码低位为 `0x08c6`；此处未确认 `3e00` | 通过 `shutter` 拆为三寄存器；长曝光时按 `2×VTS−10` 判定是否加长 VTS | 本地 `ae_set` 默认 3000 与初始化 1990 不一致。 |
| 模拟增益 `3e08/09` | `0f 20` | `08 5f` | 根据增益档位写 `03/07/0f/1f` 和细增益 | 本地值属于高档位编码；确切倍率应以传感器资料/实测确认。 |
| 数字增益 `3e06/07` | 初始化表和手动写表均未写 | 本次读取的表未见 | 驱动显式写 `3e06/07` | 本地数字增益的上电默认值未知，不能称为 1×。 |
| `4000–4009` | `00 04 aa aa aa 00 07 a5 00 c8` | `00 04 b0 00 00 00 07 ae 00 c8` | `00 04 aa aa aa 00 07 a5 00 c8` | 可能涉及黑电平，但公开片段不能逐位确定功能。 |
| MIPI `4837` | `42` | `21` | `21` | 与链路速率/模式耦合，不能直接替换。 |
| `5000` | `4e` | `0e` | `0e` | 可能涉及 sensor 内部处理开关；缺寄存器定义，不推断具体功能。 |

本地 `uics500regAE.v` 把 16 位 `I_AE` 分拆到 `3e00/01/02`；因此上述 1990、3000 是**寄存器编码量**，不直接等于微秒或行数。Allwinner 驱动把其上层 `exp_val` 先右移 3 位得到 `shutter`，再用同样的寄存器拆分；单位不能直接混用。该驱动在 `shutter > 2×VTS−10` 时延长帧长，而本地后续写表没有更新 VTS。这支持“默认 3000 需优先核查”的判断，但本地实测帧率仍是必要证据。

## 2. 深读项目

### 2.1 [amd/mini-isp](https://github.com/amd/mini-isp)

- Owner：Advanced Micro Devices；License：[MIT](https://github.com/amd/mini-isp/blob/67e752d6bf668179ec45446089a709bbc1ef9736/LICENSES/MIT.txt)；commit：`67e752d6bf668179ec45446089a709bbc1ef9736`。读取时约 138 stars / 26 forks，有仿真、Python 测试及综合入口。许可证细节以仓库文件为准。
- 已读源码：[demosaic.sv](https://github.com/amd/mini-isp/blob/67e752d6bf668179ec45446089a709bbc1ef9736/rtl/demosaic.sv)、[colorgain.sv](https://github.com/amd/mini-isp/blob/67e752d6bf668179ec45446089a709bbc1ef9736/rtl/colorgain.sv)、[gamma.sv](https://github.com/amd/mini-isp/blob/67e752d6bf668179ec45446089a709bbc1ef9736/rtl/gamma.sv)、[ccm.sv](https://github.com/amd/mini-isp/blob/67e752d6bf668179ec45446089a709bbc1ef9736/rtl/ccm.sv)、[histogram_minmax.sv](https://github.com/amd/mini-isp/blob/67e752d6bf668179ec45446089a709bbc1ef9736/rtl/histogram_minmax.sv) 和 [README](https://github.com/amd/mini-isp/blob/67e752d6bf668179ec45446089a709bbc1ef9736/README.md)。
- 技术与关系：流式 Bayer 去马赛克、帧边界锁存的定点数字增益、饱和裁剪、3×3 有符号 CCM、Gamma LUT、亮度统计。相较本地简单双线性去马赛克及帧内变化的 AWB 增益，它提供数据有效对齐、定点截断和帧间更新的设计参照。
- 采用：**帧边界增益锁存和饱和裁剪的思想，已在本地 AWB_V1 独立实现；未复制源码**。该仓库 README 明确标记 **Auto Exposure 和 Auto White Balance 尚未实现**，不能作为其 AE/AWB 成熟实例。AMD 专用 AXI/IP、时钟、MIPI/DDR/HDMI 不适用于 PH1P35；完整 ISP 资源和时序也尚未在本板验证。

### 2.2 [10x-Engineers/Infinite-ISP](https://github.com/10x-Engineers/Infinite-ISP)

- Owner：10x Engineers；License：[Apache-2.0](https://github.com/10x-Engineers/Infinite-ISP/blob/32212079dc13528125df711fed27da332250485e/LICENSE)；commit：`32212079dc13528125df711fed27da332250485e`。读取时约 392 stars / 111 forks。
- 已读源码：[gray_world.py](https://github.com/10x-Engineers/Infinite-ISP/blob/32212079dc13528125df711fed27da332250485e/modules/auto_white_balance/gray_world.py)、[norm_gray_world.py](https://github.com/10x-Engineers/Infinite-ISP/blob/32212079dc13528125df711fed27da332250485e/modules/auto_white_balance/norm_gray_world.py)、[auto_exposure.py](https://github.com/10x-Engineers/Infinite-ISP/blob/32212079dc13528125df711fed27da332250485e/modules/auto_exposure/auto_exposure.py)、[gamma_correction.py](https://github.com/10x-Engineers/Infinite-ISP/blob/32212079dc13528125df711fed27da332250485e/modules/gamma_correction/gamma_correction.py)。
- 技术与关系：普通 Gray World 用通道均值计算 `G/R`、`G/B`；另一版使用二范数，容易更受高亮值影响。AE 片段使用亮度分布偏斜度和数字增益反馈；Gamma 片段从配置生成 LUT。可用来建立本地 AWB/AE 的离线参考模型和对照场景。
- 采用：**思想/算法比较，暂不移植代码**。这是 Python 图像处理管线，并非 FPGA 流式 RTL；其 AE 是数字增益反馈，不能视为 SC500CS 传感器曝光控制，也没有本地 IP、像素时钟或资源证明。

### 2.3 [lanserge/np2hw](https://github.com/lanserge/np2hw)

- Owner：Serge Rabyking；License：[LICENSE 文件为 MIT，附加条款见原文](https://github.com/lanserge/np2hw/blob/4c6d8e261265ea7cddbfc87456a7dcd290ac7248/LICENSE)；GitHub 元数据当时显示 NOASSERTION；commit：`4c6d8e261265ea7cddbfc87456a7dcd290ac7248`。读取时约 6 stars，有运行和像素逐点比对示例。
- 已读源码：[examples/awb.py](https://github.com/lanserge/np2hw/blob/4c6d8e261265ea7cddbfc87456a7dcd290ac7248/examples/awb.py)。示例用 NumPy 计算 Gray World 通道均值，量化为 Q4.4 增益；硬件像素乘增益后右移 4 并饱和，使用软件结果逐点核验。
- 采用：**思想/定点验证方法**。适合验证本地乘法、移位、裁剪和误差界。统计与参数计算运行在主机，不能视为完整 FPGA 自动 AWB；Q4.4 也不是本地 Q16.16 的可替换参数。

### 2.4 [Aurora-520/anlogic-ph1p35-vision](https://github.com/Aurora-520/anlogic-ph1p35-vision)

- Owner：Aurora-520；License：**未找到明确仓库许可**；commit：`3ccd79f97107041dc7d6470521c80ab5be4148cf`。读取时约 6 stars。公开源码包含与本地相近的 SC500CS/安路链路，独立性和板上效果未经确认。
- 已读源码：[auto_white_balance.v](https://github.com/Aurora-520/anlogic-ph1p35-vision/blob/3ccd79f97107041dc7d6470521c80ab5be4148cf/rtl/isp/auto_white_balance.v)、[auto_exposure.v](https://github.com/Aurora-520/anlogic-ph1p35-vision/blob/3ccd79f97107041dc7d6470521c80ab5be4148cf/rtl/isp/auto_exposure.v)。AWB 使用前帧统计、亮度范围筛选、最低样本量、逐帧有限步调整 R/B 定点增益；AE 模块统计亮度并有限步调节数字亮度。读到的是模块实现，**未据此确认已集成并上板稳定运行**。
- 采用：**思路，不复制代码**。对本地帧内逐拍更新、黑像素/高亮像素未排除的问题有直接启发。其额外数字 AE 不是传感器曝光控制，且位于另一处理阶段；若直接串入会改变时序/延迟并叠加本地 AWB。无明确 License，禁止直接复制。

### 2.5 [Cirbug/sc500cs](https://github.com/Cirbug/sc500cs)

- Owner：Cirbug；License：**未找到明确仓库许可**；commit：`cac0204852c12882c558ac19a7b22afaca1841db`。读取时 0 stars；因传感器型号相同而纳入配置对照，不把它当成已验证的高质量画质方案。
- 已读源码：[uics500reg.v](https://github.com/Cirbug/sc500cs/blob/cac0204852c12882c558ac19a7b22afaca1841db/user_source/hdl_source/uics500_cfg/uics500reg.v)。表中输出 2592×1944、HTS 2852、VTS 3000，曝光、模拟增益、`4000–4009`、`4837`、`5000` 与本地表不完全相同。
- 采用：**对照证据，无参数和代码移植**。分辨率/时序不同，且缺独立画质结果与明确 License。其文件版权声明指向米联客，不能据公开托管认定可自由复制。

### 2.6 [shiyouliang/A133_13_1.1_ROM](https://github.com/shiyouliang/A133_13_1.1_ROM)

- Owner：shiyouliang 托管的 Allwinner 平台源码；参考文件头注明 Allwinnertech 版权和 **GPL-2.0**；仓库级 License 未确认；commit：`f99f23494a0b7b2689c9d155a8302a58d71b62af`。
- 已读源码：[sc500cs_mipi.c](https://github.com/shiyouliang/A133_13_1.1_ROM/blob/f99f23494a0b7b2689c9d155a8302a58d71b62af/platfrom_yhk/longan/bsp/drivers/vin/modules/sensor/sc500cs_mipi.c)。`sensor_s_exp` 明确曝光寄存器拆分；`sensor_s_gain` 分别写模拟增益 `3e08/09`、数字增益 `3e06/07`；`sensor_s_exp_gain` 在曝光越过 `2×VTS−10` 时重写 `320e/f` 帧长。
- 采用：**寄存器控制思路/风险判断，不复制代码**。它说明传感器曝光与帧长可能耦合，直接指向本地 3000 默认值的风险。驱动属于不同 SoC/摄像头模式，初始化表、输入单位、I²C 框架和 GPL 代码都不能直接移植。

## 3. 对本地设计判断的实际影响

| 现象/问题 | 本地证据 | GitHub 源码启发 | 最小后续动作与风险 |
|---|---|---|---|
| 增益按键后亮度或帧率可能突变 | 初始化曝光编码 1990；`ae_set.v` 默认 3000；任一增益变化请求会写曝光+增益 | Allwinner 驱动在长曝光时同步处理 VTS | 首先把手动模块的曝光默认/复位值统一为初始化 1990；只消除控制值不一致。须上板确认，勿假设传感器会如何处理越界值。 |
| 暖灯/暗场色偏及单色画面失真 | 实际编译的 AWB 只取每拍一个像素统计、每有效拍启动除法，并在帧内更新增益；只排除 R+G+B≥720 的样本，未排除黑像素，增益允许趋近 0 或约 16 倍 | Aurora 帧间冻结+亮度窗口；Infinite-ISP Gray World 公式；np2hw 定点逐像素验证 | AWB_V1 统一四像素统计、有效样本门限、帧间增益与限幅；须上板测单色目标、白卡、光照阶跃和时序。 |
| 红蓝颠倒或色边 | 本地 `BGGR` 固定，RAW10→RAW8 取 `[9:2]`；目前无 sensor 实际 CFA 实测 | AMD 去马赛克显式 CFA/位宽/裁剪、可仿真 | Level 0 用红蓝色块、单色均匀场及 RAW 探针确认 Bayer/通道，未经排除不可用 AWB 掩盖。 |
| 中间调显暗或颜色虽白点正确但不自然 | 本地可见管线未插入 Gamma/CCM，AWB 只缩放 R/B | AMD `gamma.sv`、`ccm.sv`；Infinite-ISP Gamma LUT | Level 3 才用灰阶卡/色卡判断需否加 LUT 或 3×3 矩阵。需估算 BRAM、乘法器和流水线延迟；不能凭主观感觉一起加入。 |
| 明暗变化无自动恢复 | `ae_set.v` 是按键手动控制，没有由视频统计到 sensor I²C 的反馈 | Aurora 平均亮度数字控制；AMD 亮度统计；Infinite-ISP 直方图指标 | Level 4 可复用像素统计、跨域稳定帧值做低资源 sensor AE。先修手动基线，后估资源/收敛；软件 AE 代码不能当硬件实现。 |

外部项目均未提供对本工程板卡、镜头、SC500CS 修订版和 TD 时序的直接验证。是否改善画质，须按 `IMAGE_TUNING_LOG.md` 做同场景 A/B 测试。

## 4. AWB_V1 前的颜色链复核与新增 GitHub 证据

- 本地 `uics500reg_720p60.v` 写 `0x3220=0x01`，未写 `0x3221`；两份官方例程的 Bayer 设置均为 `BGGR`。`0x3220` 的本地注释为 VBIN+HSUB，不能据此推定镜像/翻转。传感器复位后的 `0x3221` 实测读回尚缺失，所以不能把 Bayer 完全证明正确。
- [LineageOS 的 SC500CS 720p 驱动](https://github.com/LineageOS/android_kernel_xiaomi_earth/blob/d7851c271883170591db1ef71e1eff17b6ddacdb/drivers/misc/mediatek/imgsensor/src/common/v1/sc500cs_truly_front_mipi_raw/sc500cs_truly_front_mipi_raw.c) 源码将输出标记为 `SENSOR_OUTPUT_FORMAT_RAW_B`、默认 `IMAGE_NORMAL`；其 720p 表写 `0x3220=0x01`，镜像函数给出 `0x3221` 的正常/水平/垂直/双向值 `00/06/60/66`，但该函数位于 `#if 0`。Owner：LineageOS；该文件位于 Android kernel 树，许可应按仓库/文件核实；commit：`d7851c271883170591db1ef71e1eff17b6ddacdb`。**采用：思路与对照证据，不复制代码/寄存器值**。它支持当前模式把 `0x3220` 和 mirror/flip 分开看，但不是同模组的板级证明。
- [Samsung A146p 的 SC500CS 驱动](https://github.com/forforksake/android_kernel_samsung_a146p/blob/a53fbf15e526d719ba6f9bac316f5b566451f4b1/drivers/misc/mediatek/imgsensor/src/common/v1/n23_sc500cs_front_txd_mipi_raw/n23_sc500cs_front_txd_mipi_raw_Sensor.c) 也将 `0x3221=0x66` 标注为 mirror and flip，同时 `0x3220=0x01`；它和本地默认方向不同。Owner：forforksake 托管的 kernel 树；许可未在本轮确认；commit：`a53fbf15e526d719ba6f9bac316f5b566451f4b1`。**采用：只作反例对照**，说明同一 `0x3220` 不足以确定 Bayer 相位，不能将 `0x66` 搬进本地表。
- 数据顺序静态追踪：RAW10 解包端和 RAW8 转换端的四像素次序调整互相对应；双线性输出每像素 `{8'b0,R,G,B}`；`data128_96` 取各 24 位后改变四像素排列，但 AWB 位段仍按每像素 `{R,G,B}`；96→128 打包与 `video_out` 24 位顺序保持连续位流。未找到可证明的 R/B 通道交换。RAW10 的 `[9:2]` 截位对三类 Bayer 像素相同，只损失 2 位精度，不能单独解释选择性缺红。
- AWB 实现参考再次核读：[AMD colorgain.sv](https://github.com/amd/mini-isp/blob/67e752d6bf668179ec45446089a709bbc1ef9736/rtl/colorgain.sv) 在帧边界锁存增益并进行输出饱和；[Infinite-ISP gray_world.py](https://github.com/10x-Engineers/Infinite-ISP/blob/32212079dc13528125df711fed27da332250485e/modules/auto_white_balance/gray_world.py) 明确 `G/R`、`G/B`；[np2hw examples/awb.py](https://github.com/lanserge/np2hw/blob/4c6d8e261265ea7cddbfc87456a7dcd290ac7248/examples/awb.py) 验证定点乘法和裁剪；[Aurora AWB 模块](https://github.com/Aurora-520/anlogic-ph1p35-vision/blob/3ccd79f97107041dc7d6470521c80ab5be4148cf/rtl/isp/auto_white_balance.v) 提供黑/亮样本过滤、最低样本数及帧间限步的思路。AWB_V1 只采用**思想/算法/定点验证方法**，未复制第三方 RTL，也未替换安路底层 IP。

## 5. BLC_V1 前的黑电平资料核查（2026-10-08）

| Repository / Owner | 固定 revision、License、参考文件 | 对本轮决策的作用 | 采用范围 |
|---|---|---|---|
| `LineageOS/android_kernel_xiaomi_earth` / LineageOS | [`sc500cs_truly_front_mipi_raw.c`](https://github.com/LineageOS/android_kernel_xiaomi_earth/blob/d7851c271883170591db1ef71e1eff17b6ddacdb/drivers/misc/mediatek/imgsensor/src/common/v1/sc500cs_truly_front_mipi_raw/sc500cs_truly_front_mipi_raw.c)，commit `d7851c271883170591db1ef71e1eff17b6ddacdb`；Android kernel 源码，文件具体许可本轮未逐条确认 | SC500CS 初始化序列同样写 `0x4001=04`、`0x4002/03=aa/aa` 等寄存器；公开驱动没有给出这些位的 black pedestal 单位或本板实际 RAW 输出黑位，不能把 `0xaa` 当 RAW10 offset | 仅对照传感器初始化行为；未复制代码或参数 |
| `Aurora-520/anlogic-ph1p35-vision` / Aurora-520 | [`docs/architecture.md`](https://github.com/Aurora-520/anlogic-ph1p35-vision/blob/3ccd79f97107041dc7d6470521c80ab5be4148cf/docs/architecture.md)，commit `3ccd79f97107041dc7d6470521c80ab5be4148cf`；仓库级 License 未确认（见本文件第 2.4 节） | 文档把 RAW10 BLC 钩子默认旁路，并要求先用遮光实测偏置；说明同平台项目也不把未经实测的常数视为 SC500CS 校准值 | 只采纳“遮光验证和保留可回退实验”的判断；未复制代码 |

SmartSens 官方 [SC500CS 产品简介](https://smartsens.oss-cn-beijing.aliyuncs.com/web/products/SC500CS_V4.0.pdf) 明确支持 10/8-bit、2-lane MIPI RAW，但没有寄存器 `0x4000–0x4009` 的逐位定义或 RAW10 黑电平数值。**本轮无法确定传感器输出的实际 black pedestal，也无法确认其内部 BLC 是否已把黑位校到 0。** 不使用其他型号传感器（例如 OV4689）的 `0x400x` 寄存器说明推断 SC500CS。

本地有效 RTL 证据：A 工程清单没有编译 `isp/BLC/BLC.v`；`raw10_unpacket_2lane.v` 中使用 `I_camera_black_level` 的减法位于整块注释中，而顶层直接把解包 RAW10 送去马赛克。随例程的 `isp/BLC/BLC.v` 给出四个 RAW10 offset 默认值均为 **15**，但未连接到 A 工程，且没有注明是 SC500CS 的测量结果。本轮 BLC_V1 若用 15，只能标为**来自随工程参考模块的试验初值**，不能写成传感器已校准黑电平。新 RTL 独立写为饱和减法，没有复制外部 GitHub 实现。

## 6. AWB_V2 低色度样本选择依据（2026-10-08）

| Repository / Owner | 固定 revision、License、参考文件 | 参考内容与采用范围 |
|---|---|---|
| `10x-Engineers/Infinite-ISP` / 10x Engineers | commit `32212079dc13528125df711fed27da332250485e`；Apache-2.0；[`modules/auto_white_balance/gray_world.py`](https://github.com/10x-Engineers/Infinite-ISP/blob/32212079dc13528125df711fed27da332250485e/modules/auto_white_balance/gray_world.py) | 已有普通 Gray World 的 `G/R`、`G/B` 对照。本地按实际 `awb.v` 推导：单色区域主导均值时会压低对应通道。**采用算法比较思想，不复制源码或参数**。 |
| 学术论文，非 GitHub 仓库 / Kai-Fu Yang、Shao-Bing Gao、Yong-Jie Li | [CVPR 2015《Efficient Illuminant Estimation for Color Constancy Using Grey Pixels》](https://openaccess.thecvf.com/content_cvpr_2015/html/Yang_Efficient_Illuminant_Estimation_2015_CVPR_paper.html)；revision 为 CVPR 2015 正式论文；本文非代码仓库，代码许可不适用，论文文本版权未用于代码复制 | 论文提出从灰色像素估计照明，而非假设整幅场景平均为灰；其检测用对数颜色空间等更复杂方法。**只采用中性候选像素的设计思想**，本地 `max(R,G,B)-min(R,G,B)<32` 是针对 RGB888 资源和上板试验独立设计的简单门槛，并非论文公式或参数。 |

实际决策受本地 BLC_V1 上板反馈和有效 `awb.v` 控制逻辑主导：红/蓝单色可辨但偏暗，符合纯色 Gray World 造成的对应通道目标增益低于 1 的可能性，仍不能仅凭照片定量归因。现有帧末 `sample_count>=1024` 才启动除法，为低色度样本不足时保留上一增益提供已有硬件保护。阈值 32 为 **AWB_V2 单一实验初值**，约为 RGB888 满量程的 12.5%；对明显纯色（如 `200,30,30`）拒绝，对中等偏色的白/灰（如 `160,185,180`）保留。没有本机逐像素采样数据证明 32 最优；若白纸实际色差超过 31，候选样本可能不足，需要在下一轮上板记录中如实报告，不在本轮另扫 bit。

## 7. SC500CS Exposure / Analog Gain 审计（2026-10-09）

| Repository / Owner | 固定 revision、License、参考文件路径与 URL | 参考内容 | 是否采用及边界 |
|---|---|---|---|
| `A133_13_1.1_ROM` / `shiyouliang`（Allwinner 源码镜像） | commit `f99f23494a0b7b2689c9d155a8302a58d71b62af`；文件头标注 Allwinner copyright、GPL-2.0，仓库级许可未确认；[`platfrom_yhk/longan/bsp/drivers/vin/modules/sensor/sc500cs_mipi.c`](https://github.com/shiyouliang/A133_13_1.1_ROM/blob/f99f23494a0b7b2689c9d155a8302a58d71b62af/platfrom_yhk/longan/bsp/drivers/vin/modules/sensor/sc500cs_mipi.c) | `sensor_s_exp` 将曝光拆入 `3e00/01/02`；`sensor_s_gain` 分段写模拟粗/细增益；`sensor_s_exp_gain` 对超出 `2×VTS−10` 的曝光延长帧长 | **采用寄存器解释与长曝光需同步调 VTS 的设计判断**，不复制代码、驱动表或 SoC I²C 实现；本地固定 sweep 不改曝光/VTS。 |
| `Power-Armor-13` / `ulefoneofficial` | commit `de34198b04c5dc11b23c16ffcd121ce978c7bc1e`；文件级/仓库级许可本轮未确认；[`kernel-4.14/drivers/misc/mediatek/imgsensor/src/common/v1/sc500cs_mipi_raw/sc500csmipi_Sensor.c`](https://github.com/ulefoneofficial/Power-Armor-13/blob/de34198b04c5dc11b23c16ffcd121ce978c7bc1e/kernel-4.14/drivers/misc/mediatek/imgsensor/src/common/v1/sc500cs_mipi_raw/sc500csmipi_Sensor.c) | 模拟粗档 `03/07/0f/1f` 对应 1/2/4/8×，细档以 `0x20` 为 1 倍；`write_shutter` 将行数换算为 2 倍寄存器单位 | **采用编码交叉验证思想**，无代码复制；它与本地辅助数据手册摘录及 Allwinner 驱动一致。 |
| `android_kernel_xiaomi_earth` / `LineageOS` | commit `d7851c271883170591db1ef71e1eff17b6ddacdb`；具体文件许可本轮未确认；[`drivers/misc/mediatek/imgsensor/src/common/v1/sc500cs_truly_front_mipi_raw/sc500cs_truly_front_mipi_raw.c`](https://github.com/LineageOS/android_kernel_xiaomi_earth/blob/d7851c271883170591db1ef71e1eff17b6ddacdb/drivers/misc/mediatek/imgsensor/src/common/v1/sc500cs_truly_front_mipi_raw/sc500cs_truly_front_mipi_raw.c) | `set_gain` 以 1/2/4/8× 粗档及细档 `0x20` 基准写 `3e08/09`，另有数字增益路径 | **采用模拟增益档位交叉验证**，不复制代码；数字增益路径不在本轮启用。 |

本地 SC500CS Preliminary 数据手册 V1.8 的文本摘录见未纳入版本控制的研究材料；由于原 PDF 来源未在本仓库核验，仅作辅助，**不把其文字或表格逐项复制进本仓库**。本轮实际候选值 `0320/0f20/1f20` 由三个公开驱动的编码逻辑交叉支持，具体计算、工程接线、限制与上板判据见 `SC500CS_EXPOSURE_GAIN_AUDIT.md`。上述所有外部项目均非 HX1P35A 板级验证，也未替换安路的 MIPI/DDR/HDMI/PLL/IP。

## 8. EDGE_STABILITY_DIAG_V1 外部诊断参考（2026-10-18）

本轮仅采用实验设计/概念核对，无外部代码复制，不替换任何安路IP，不改变Sensor配置。

| Repository / Owner | revision / License / 路径与URL | 参考内容 | 是否采用 / 范围 |
|---|---|---|---|
| opencv / opencv | 4.10.0 tag object `67f3511f2354ebfb5f98045ee6153345f632aadd`指向commit`71d3237a093b60a27601c20e9ee6c3e52154e8b1`；仓库LICENSE Apache-2.0，canny.cpp文件头保留Intel/Itseez许可（三条款BSD风格），不得忽略文件级声明；[modules/imgproc/src/canny.cpp](https://github.com/opencv/opencv/blob/71d3237a093b60a27601c20e9ee6c3e52154e8b1/modules/imgproc/src/canny.cpp)、[LICENSE](https://github.com/opencv/opencv/blob/71d3237a093b60a27601c20e9ee6c3e52154e8b1/LICENSE) | NMS严格/非严格邻居比较、强阈值、栈传播均在单幅图中；无上一帧记忆；L568等、L647–676、L910–930 | 采用“空间hysteresis不等于时间稳定”的检查思路；不复制、不替换本地算法、不以OpenCV输出作本工程位准确参考。固定版本便于复核，不声称最新。 |

GitHub连接实际检索`repo:opencv/opencv is:issue Canny flicker`，total_count=0；这是有限查询结果，不是证明GitHub无同类问题或本地没有bug。一般论坛回答未作为根因证据。

其他一手资料（非GitHub仓库，网页无固定commit；访问2026-10-18）：

- John Canny，1986，IEEE PAMI 8(6):679–698，[原论文](https://cecas.clemson.edu/~stb/ece847/internal/classic_vision_papers/canny_pami1986.pdf)。版权论文，仅理解检测/定位与噪声折中，采用分测梯度幅值/峰位的实验思路；不复制代码或图表，不将论文当实板故障证据。
- Basler官方[Balance White Auto](https://docs.baslerweb.com/balance-white-auto)、[Adjustment Damping](https://docs.baslerweb.com/balance-white-adjustment-damping)、[Auto Function Profile](https://docs.baslerweb.com/auto-function-profile)。厂商文档、未确认可复用代码许可；只采用连续/冻结AWB比率和稳定光源对照的诊断思路。不是SC500CS寄存器依据，不移植其AE或增益参数。
- 安路本地安装文档`D:/TD/doc/SWUG/SWUG200_Timing_Constraints_User_Guide.pdf`，2024.09，§3.14印刷页35/PDF物理页43。厂商版权，仅用于理解set_clock_groups不分析跨组路径；最终覆盖缺口以本项目归档exception.timing实际Ignored条目为证，不因阅读文档就擅改SDC。

本轮诊断与实板待测范围见`EDGE_STABILITY_DIAG_V1.md`和`EDGE_STABILITY_DIAG_V1_BOARD_PLAN.md`。

## 9. EDGE_TEMPORAL_RESEARCH_V1 数据导出参考（2026-10-18）

- Repository/Owner：opencv/opencv；revision 4.13.0 tag object `2e1f8da65e4f9fa1a98423e6ac223187438a4db8` → commit `fe38fc608f6acb8b68953438a62305d8318f4fcd`；仓库LICENSE Apache-2.0。[固定版本](https://github.com/opencv/opencv/tree/fe38fc608f6acb8b68953438a62305d8318f4fcd)。参考API文档[透视变换](https://docs.opencv.org/4.13.0/da/d6e/tutorial_py_geometric_transformations.html)及[视频读取](https://docs.opencv.org/4.13.0/dd/d43/tutorial_py_video_display.html)，对应modules/imgproc/src/imgwarp.cpp、modules/videoio/src/cap.cpp。采用getPerspectiveTransform/warpPerspective/VideoCapture库API做编码位恢复，不复制教程代码、不将OpenCV Canny作为RTL金标准；编解码协议为本项目独立实现。Python绑定依赖opencv-python-headless4.13.0.92，未改安路IP。
- 本地安路SWUG111(v1.0)2024.11，`D:/TD/doc/SWUG/SWUG111_Debug_Tools_User_Guide.pdf`，§2.2/§2.4、印刷页5–6/40/46：ChipWatcher深度128..65536、窗口触发、CSV导出。厂商版权，仅阅读能力边界，没有复制厂商RTL/生成IP。本工程未配置该通道，不把“手册有功能”写成硬件已可用；未验证跨帧数据限定/压缩采样，本轮根据用户无采集卡、可手机录像选择HDMI编码导出。
- 网络搜索所得其他平台/分割模型deflicker仓库、普通论坛没有形成具体实现依据，未复制代码或采用其参数。时间算法不凭外部宣传选型；本轮准备独立软件反例及真实数据入口，待新ROI实板证据。
- 安路本地SWUG106，2024.04，`D:/TD/doc/SWUG/SWUG106_HDL_Coding_Synthesis_User_Guide.pdf`，§4.2.6印刷页29/§5.6.13页88–89：ram_style合法值bram/单写口同步读条件。厂商版权，仅采用受支持综合属性和独立单写端口编码原则，解决本项目页面缓存被当多写口展开的问题；不复制厂商原语/IP代码、不修改SDC。实际是否推断成功由本轮层级area检查，不靠指令名称宣称成功。
