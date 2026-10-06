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
