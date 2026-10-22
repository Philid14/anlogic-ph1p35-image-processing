# STYLE_V2_TARGET_V1 路由后时序与CDC审查

2026-10-22 / MAIN。实际源码 `7c7e5ee7d6c52260bcf557d9dabd4014f84e2687`；TD V6.2.168116，PH1P35MDG324 speed3。

## 1. 正式实现

- SYN20 → place20 → route20完成；最终Slice19952/21216、LUT6 18063、FF21649、ERAM99/108、DSP21/40。
- 原SDC SHA256 `457379c949a59da39579d996bea3c56f066f85be422cec9a3b320d558e8f5c0d`，PLL/SDC/引脚均未放宽或修改。
- Routed、Slow/Fast corners均检查：Setup +0.165ns / Hold +0.020ns，Setup/Hold TNS均0。
- CSI59.995MHz：Setup+3.247/Hold+0.020ns；DDR用户66.667MHz：+0.227/+0.020ns；HDMI75.002MHz：+0.165/+0.021ns。
- 最差Setup在HDMI mixer x_2d到O_hdmi_data，12级逻辑，数据12.927ns（cell3.461/net9.466）；原TARGET字库跨模块长组合链已拆开。
- STA coverage95.73%，不是100%设计安全证明。路由DRC无多驱动、无异常时序路径，bound检查通过。
- 实际route.db SHA256 `9a4d9b04ada337c6142db88d054cf76c316f640297abb809b03f6e2a0dcfd248`。

## 2. 元数据邮箱

实现SDC有全局异步时钟组，不能据普通STA通过认定整包安全。
在独立工程载入同一Routed DB，清理约束后加载审查专用SDC；禁止export、place、route或bitgen。
覆盖begin/control/display/grant/terminal/time_csi/time_ddr共7类，1706端点全部分析；40ns datapath界限下WNS+25.799ns，TNS0，最大报告数据14.137ns。
保守最早注册邮箱接收窗口5×13.333=66.665ns，脉冲消费6×13.333=79.998ns；源payload在ACK前保持不变，ACK晚于消费者采样。
快源慢目的、单侧复位、停钟/恢复及提前ACK负对照详见VERIFICATION。

## 3. FIFO Gray覆盖

原IP max_delay被async组屏蔽的历史缺口仍存在，未修改全局SDC。
本次对已实现物理路径另施严格13.033ns界限（最短13.333ns周期减0.3ns），四组0..8共36位逻辑Gray网络全部出现。
物理双FF打包会把部分Gray/同步FF命名为相邻寄存器，因此只按cell名字匹配会漏2位；失败选择器22/23保留，不删除。
最终按逻辑net审查305端点（包括额外同域扇出），全部严格13.033ns，WNS+3.232ns、TNS0、最大数据9.737ns；36位逐组逐位校验，不将305当作指针位数。
这确认当前as-built路由满足此界限，**没有修复未来重新实现时的SDC覆盖机制**。后续应单独制定每跨域指针的约束优先级/覆盖门禁，复建重新审查。
不据此声称完整CDC形式证明、MTBF或硬件长时间验证。

## 4. 告警与未消除的风险

- PHY-5079相机24m区域时钟有3段local wire，47 clock/48 fanout；I2C scl_clk为逻辑派生，13段local wire。STYLE V2旧构建已有相同类型（其相机3段/I2C12段），数量/布局变化如实保留。
- PHY-5088：clock buffer驱动数据或其他clock net；原相机/I2C结构未改，不宣称已根治。最终时钟报告及日志保留，须冷启动、Sensor配置与明暗变化实板验收。
- 既有No ports matched clkw/clkr及重复CompileOrder告警存在；实际Gray路径已另审，不将未命中约束当作有效覆盖。
- MIPI packet monitor查wordcount/HS/lane error，并非完整CSI ECC/CRC检查；本轮未扩大该功能。
- 资源余量Slice1264（5.96%）、ERAM9（8.33%）仍有限；+165ps比原负裕量显著改善，但不预报板卡电气或长期稳定性。
- FIFO故障仿真故意注入一次满帧，验证坏帧不提交及物理排空；真实稳态S增长仍为正式验收阻断项。

## 5. 证据与发布隔离

`docs/evidence/STYLE_V2_TARGET_V1/route_explicit_logo_20`保存正式实现报告；`routed_cdc_24`保存审查SDC/脚本/summary及原始报告zip。
审查始终不导出数据库；最终bit只能从原route20 DB、原settings生成，另由release/finalize脚本检查DB、SDC、源码及全部证据SHA。
当前硬件状态NOT_RUN，见BOARD_TEST。
