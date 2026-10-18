# TARGET 接入摘要（2026-10-18）

本页列出当前可交付内容和接入前置条件。完整端口见 [INTERFACE.md](INTERFACE.md)，
系统责任见 [MAIN_CONTRACT_DRAFT.md](integration/MAIN_CONTRACT_DRAFT.md)，
验证统一从 [VERIFICATION.md](VERIFICATION.md) 开始。

当前为独立模块与模拟验证；MAIN 尚未接入 TARGET，没有包含本次修复的整机 bit 或板测。
本页不是可直接复制到顶层的接线批准。生产 TRACK 身份/年龄缺口仍开放。

## 1. 可供选择的检测路径

| 路径 | 组成 | 输入责任与结果时刻 |
|---|---|---|
| 既有检测 | color_classify + color_target_detect | 消费带坐标/SOF/EOF 的 4PPC 观察流；不校验完整固定光栅；EOF 采样沿后发布 |
| 独立流封装 | color_target_detect_stream + color_classify + color_target_support3 + color_target_mask_stats | 额外检查固定光栅与身份；默认 FILTER_ENABLE=0；旁路 EOF+1，过滤 EOF+WIDTH/4+3 |

上述拍号以输入 EOF 采样沿为 0；同步下游 track 在结果发布后的下一沿消费。
过滤 1280 宽时结果为 EOF+323 拍。CDC、排队、文字准备与显示调度耗时另计，不能混用不同域的拍数。
两种检测器不应同时作为同一观测源发布。具体采用哪个接口由 MAIN 确认，按实际实例列出 TD 输入，
不要把整个 rtl 目录通配加入主工程来代替依赖审查。

两路径均为并接观察者，无 ready，不阻塞视频。保持 RGB888/96bit/4PPC，lane0=[95:72]，
每 lane 为 {R,G,B}。观察点应在风格化之前；AWB 彩色输出是候选，实际 RGB/坐标/标记须逐拍核实。

## 2. 必须先解决的系统接口

1. **SOF 规范化。** RAW uial2axis 的 user 与该处首有效拍对齐，但编译的根 awb.v:303–307 保留提前 user，
   RGB/valid 另有延迟。不能把 awb_O_tuser 直接接 I_sof，也不能破坏 video_in 依赖的原提前通知。
   AWB last 来自 valid 包络；行内有空洞时不能据此认定 EOL。MAIN 需提供同拍 RGB、x0/y、SOF/EOL/EOF。
2. **错误与恢复。** 真实帧末、包长度/FIFO 错误、abort 和截断恢复须有来源；当前顶层 video_in 错误口接 0。
   流封装截断后需显式复位和新 session，复位取消所有未发布尾部。无 lane_valid 的 V1 不支持非完整 4 像素尾拍。
3. **身份与缓存。** 当前 MAIN 尚无交付的 session/frame/槽代次链。必须从采集事务到 DDR 完整提交、
   读预取、显示选择和 HDMI 保留身份及写入代次；槽号不能充当帧号。读扫描期间还需保证所选像素不被覆盖。
4. **CDC。** 观察、DDR、显示不在同一域。整包握手或异步 FIFO 由 MAIN 实现，证明突发/服务率/最大停顿/容量，
   并覆盖任一端复位及在途请求。每帧一次的平均速率不足以证明单邮箱可用。满时动作须批准且计数。
5. **显示提交。** 跨域后的结果按所选显示帧匹配，框、十字、文字、count、state 在边界一次提交且全帧稳定。
   仅把“最新 track”寄存一级无法证明同帧。严格同帧或显式历史 HOLD 的策略、年龄上限仍待确认。

## 3. TRACK 与文字的当前限制

TRACK 原功能回归 21/21；新增特征测试复现 6 项缺口：重复观测确认、乱序接受、无效帧列不老化、
停止输入不老化、无效新 session 不清旧状态、旧 session 有效包可回切。见
[责任提案](integration/TRACK_ADMISSION_PROPOSAL.md)，尚未修改生产 TRACK。

因此 O_show 与 TRACK 状态不是新鲜度证明；显示结果仍带上次被接受的身份，HOLD 不得改标当前帧。
有效无目标、无效、观测超时分别处理；ACQ/LOST 不能代替真实时间年龄。

文字每次对 count/x/y/state/show 整组快照，70 拍内发布，稳定新值最多 140 拍可见；允许合并中间值。
该模块当前无观测 ID/转换完成口，需 MAIN 在足够的消隐窗口完成准备，或另提交 shadow/commit 方案。
不能让外框先切换、文字稍后切换。两个覆盖模块只使用显示域已匹配、已整组提交的字段，
不直接跨域读取 track。字库/区域/Logo 优先级仍由 MAIN 统一安排。

## 4. 配置与预算

现有默认：TARGET_CLASS=0、HUE_HALF_WIDTH_DEG=30、C_MIN=24、V_MIN=32、MIN_COUNT=64；
TRACK 的 ACQ_FRAMES=3、LOST_FRAMES=15、MAX_JUMP=0。它们是当前实现默认值，不是实拍验收参数。
A1 将分类与结果标签统一为 1=绿、2=蓝、其他配置回退红且标签 0；无目标/无效字段仍清零。
中心是包含两端包围框的中点，非质心。同色区域目前合为一个框，不声称多个独立目标。
现有文字模板固定 RED；绿/蓝检测标签验证不能替代相应文字类别适配，当前演示仍使用默认红色。

support3 保持关闭。实拍素材、最小目标与同色目标选择按用户意见保留；不因合成测试通过调生产门限。

独立 RGB gate 测试架（源码 5565545）旁路为 918 LUT/579 reg/0 ERAM/0 DSP，过滤为 1224/950/1/0；
人工 10 ns，SWNS/HWNS 1.170/0.502 与 1.140/0.292 ns。含输入影子寄存器和输出选择器，74 未绑定 I/O。
文字 gate（172815e）为 282 LUT/194 reg。不得相加当整机增量、作为 A1 后新综合或推导 routed Fmax。
历史 MAIN 完整 P&R 不含 TARGET，真实接入预算与新时钟/约束/路由报告仍待 MAIN 提供。
完整出处和口径见 [验证入口 §5](VERIFICATION.md#5-资源与板测证据分开引用)。

## 5. 推荐推进顺序

先做现有完整视频的 [基线板测](board/OBSERVATION_GUIDE.md)，收集冻结/撕裂/明暗恢复及实拍资料；
同时审阅 MAIN 契约与 A2 责任分配。获批后先规范化与身份闭环，再做 CDC/缓存/整组显示仿真，
最后实际顶层 P&R、bit 归档和 TARGET 板测。每一步以可追溯输入和失败条件验收。
