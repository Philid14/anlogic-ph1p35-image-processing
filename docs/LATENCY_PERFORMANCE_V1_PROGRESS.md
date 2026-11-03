# LATENCY_PERFORMANCE_V1 暂停检查点

状态：用户于2026-11-03明确恢复工作；以下暂停记录保留作为历史。
角色MAIN；基线072bc0f8 / TRACK_REGION_FIX_V1；分支codex/main/latency-performance-v1。

## 已完成

- 核对AGENTS/TEAM_PROTOCOL、当前正式工程入口、四槽DDR读写/FIFO、HDMI输出和75MHz配置频率。
- 核对LATENCY PR5（未合并），来源87bb9a5375843c4f3e9696eb0dbd028f3e364f47；未导入或修改队友目录。
- 新建独立分支、TASK说明。只修改MAIN的edge_link_pair_3x3.v行缓存调度：对1280等16整数倍宽度，将两行缓存放入一个原生双端口RAM；非整字宽度保留旧路径。
- Native ModelSim/真实Anlogic ERAM+GSR，与现有独立空间参考对照：宽64/68/72/76/1280、四跳逐级标签、valid/SOF/tlast、气泡、边界、跨帧恢复测试通过。结果及源码哈希见evidence/LATENCY_PERFORMANCE_V1/memory。

## 未完成及证据边界

- 没有综合，不能将“每跳目标减少一个RAM”描述为最终实际资源结果。
- 尚未将处理延迟测量、帧身份/时间戳、DDR元数据或新OSD接入正式RTL。
- 尚未完成新检查点的整机旧功能回归、布局布线、时序检查、bitgen。
- 本轮没有新bit、candidate tag或Draft PR。可烧录版本仍是TRACK_REGION_FIX_V1，不能烧录本检查点。
- docs/GITHUB_REFERENCE_RESEARCH.md的原有用户修改及其他未跟踪资料保留。

## 恢复时接续

1. 先检查分支/HEAD/dirty状态；回读本说明和TASK，禁止把暂停检查点当完成版本。
2. 完成行缓存优化的综合/资源检查点，必要时研究等价RGB/灰度延迟存储优化。
3. 延迟方案尚属设计研究：考虑用并行原生FIFO让身份/时间与实际写入数据同行；验证RAW首有效像素起点、源完整性/FIFO错误、DDR整帧提交及实际读选槽代次；对齐最终HDMI首有效像素，重复显示单列，异常不计统计。
4. 按当前资源预算选择实现，不直接搬入通用大模块；新增CDC需仿真与实际布局布线路径检查，不改全局异步时钟约束掩盖问题。
5. 完整模型/RTL/视频链路回归，再SYN→PHY→STA→bitgen、归档、独立Draft PR依赖29；没有合并授权。

当前原有算法、参数、按键/开关、Logo/CNT/OSD、Sensor、MIPI/DDR/HDMI调度、PLL/SDC均未更改。新的行缓存调度只获得独立RTL验证，整机验证待续。

## 2026-11-03恢复后的实际进度

- 行缓存单独综合确认105→101ERAM。单独PHY因拥塞未完成最终STA，已取消并保留partial_physical/STOPPED.json；不能报告时序通过。
- MAIN同帧测量适配器及透明OSD已实现并接入：RAW首valid、同字FIFO标签、完整DDR写入校验、实际读槽代次、HDMI首DE、NEW/REP/BAD及毫秒显示。
- 原生FIFO、源标签/会话回绕、DDR journal异常、HDMI同帧统计、24,576像素字形及小高度真实DDR控制链路仿真通过；这些不等于真实硬件验证。
- SP宽字延迟存储实验虽然逐拍正确，但实际ERAM代价过大，正式工程未采用；原图/灰度/二值payload延迟保持基线实现。
- 新资源方案将Gaussian/NMS旧LUT行缓存等价映射到原生ERAM，配置延迟改为短移位链以释放2ERAM。独立旧模型对照通过；整机综合试验r5为108ERAM，最终布局/时序尚待。
- 当前正在完成新源码的720p旧功能回归与正式TD构建。没有新candidate bit/tag或上板成功结论。
- GitHub核对：PR29仍Draft/open，HEAD072bc0f8；PR5仍open/unmerged，HEAD87bb9a53。没有自动合并。

## 后续已验证检查点

- R0正式源d1eabc5实际完成SYN/PHY/最终STA：Setup+0.127ns、Hold+0.020ns、TNS0；未生成bit。所有18帧720p旧功能/打包和TRACK31拍回归通过。
- 为保留ERAM余量，R1将Gaussian/NMS首行读提前一级，并在原G2/N2对齐，窗口与总延迟不变。两类行缓存6→3ERAM；独立软件参考、复位及18帧整机回归再次通过。
- retime_syn实际确认105ERAM。R1需重新正式构建，禁止引用R0时序冒充R1。
- 校正诊断超时使用DDR实际配置66.667MHz，并让参考时钟中断sticky invalid直到全局复位；新增独立异常测试，视频调度不变。
- Draft PR30已创建，依赖29；尚无最终candidate bit/tag，仍不能宣称实板验收通过。
