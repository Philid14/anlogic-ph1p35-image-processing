# STYLE_V2_TARGET_V1 集成工作记录

日期：2026-10-21。角色 MAIN。人类授权：本轮 MAIN_STYLE_V2_TARGET_INTEGRATION_PROMPT。

## 固定基线与范围

- MAIN：`89093f428878b918036c8a30a0d1afe7764946b8`，STYLE V2 PR #13，未合并。
- TARGET：`49641eefc8bab37de3cd1b9d7f95a0051a0f0d1e`，PR #2；2026-10-21 fetch 与 API 确认头相同。
- TARGET 九份生产 RTL：`e9958669a3ce04b544f012b29bf80a1f9025384f`，按交付 JSON 核验 blob 与 LF SHA256。
- 分支 `codex/main/style-v2-target-v1`，从固定 MAIN HEAD 新建。直接导入原目录，不合并队友分支、不复制算法。
- STYLE V2 用户反馈“效果不错，仍有提升空间”只作为定性意见；30分钟、零溢出、冷启动未据此认定通过。
- 不接入 LATENCY，不修改 Sensor/ISP 算法、按键、五模式、PLL/引脚/原 SDC，不覆盖既有归档。
- 开工 tracked clean；根录像、PDF、参考工程及未跟踪 `docs/PROGRESS_REPORT_2026-10-21.md` 为用户资料，排除本任务提交。

## 已核实的接口缺口

原 `video_in` 在提前 SOF 轮转写槽并设置读指针，没有完整提交和读租约。
`I_mipi_rx_error` 目前常零。相机 FIFO 每帧复位，复位源跨域；写突发/命令 FIFO 在途并不由该复位终结。
原 `video_out` 在 VSYNC 设地址、复位像素 FIFO，没有总读字数界限或在途返回排空屏障。
`mc_to_user_interface` 的 user ready 表示命令 FIFO 余量，实际 MC 接受点是 `O_mc_app_en` 与读/写命令。
这些是代码事实，不表示已证明实板正在持续丢帧。

观察点是 `isp_top.awb_O_tdata/valid`，CSI 域、96bit/4PPC。
AWB user 是提前通知；last 是 valid 下降沿，均不能直接作为 TARGET 同有效拍 SOF/EOL。
生产 TD 引用 `isp/csi_unpacket_2lane.v`，其没有 CRC/ECC 错误输出。不能将计数正确冒充已经验证 MIPI CRC。

## 设计检查点

1. 固定来源、复跑 TARGET 独立交接与工具失败注入，保存真实退出码。
2. 有界台账先独立 RTL 验证：真实写接受计数、取消/代次、读租约、排空屏障。
3. 最小多时钟固定标注，证明整包传输、像素身份、文字准备、首像素年龄和共同遮罩。
4. 实际 TARGET/guard 进入生产路径；启用64位时间与16位诊断，整体 SYN 资源预检。
5. 全尺寸像素/元数据/五模式回归，完整 TD 后才签发 bit、tag 与板测交接。

当前生产入口尚未接 TARGET。独立测试/新适配器检查点不得描述为整机完成。
年龄数值仍未决，保留配置工具 UNKNOWN/exit2，实际时基/服务/扫描预算确认后再填写。
75 MHz HDMI、1650×750 时序不变；完整扫描 1,237,500 显示时钟、16.5ms（配置计算值，非实测）。
先核对真实 DDR 最坏服务和排空行为，不用无限等待或随意年龄值掩盖异常。

## 原有风险

STYLE V2：LUT6 17170、FF16814、Slice18140/21216、ERAM85/108、DSP21/40，WNS +0.100/+0.020ns。
两组 Gray max_delay 被全局异步时钟组忽略；FIFO 稳态、I²C 跨区 clock warning 未关闭。
新增 CDC 不能凭异步例外宣称覆盖，须另列握手保持、复位屏障、服务界和物理路径检查证据。

## 当前交付状态

研究/独立验证进行中；无本版本 bit、candidate tag 或上板结论。
回滚继续使用 `edge-style-fill-v2-candidate` 原归档，SHA256 见来源清单。
