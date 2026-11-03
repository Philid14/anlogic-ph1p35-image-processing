# LATENCY_PERFORMANCE_V1：同帧延迟可视化与资源优化

2026-11-03，MAIN。状态：数字验证、SYN、PHY、最终STA、bitgen通过；**Board Test NOT_RUN**。完成candidate后停止，等待用户验收，不合并PR。

## 结果与赛题对应

进阶三：实现MIPI解码后RAW首有效像素至**同一采集帧**进入HDMI发送器首有效像素的延迟测量与透明显示，包含ISP、缓存等待和读出；不包含曝光、摄像头内部及显示器内部延迟。普通帧号相减没有冒充同帧延迟。

扩展四：加入测量功能后减少111个Slice，ERAM/DSP总量不增加，未降低720p规格、放宽SDC或删除原功能。没有宣称实际端到端延迟已经降低。进阶三RTL集成及构建完成，稳定显示、测量数值与长期运行仍须实板验收。

## 实现与屏幕参数

RAW起点记录session/frame/tick；87位身份、时间及完整性标签与128位像素使用**同一个FIFO字**跨域。DDR四槽按写入代次记录，只有同身份、连续完整的172800个打包字才提交；实际读槽选择锁存该代次，通过握手传到HDMI域。首DE打点，完整921600像素及帧边界校验后发布统计。覆盖、溢出、异常读出、过期和无关联样本不参与数值统计；参考时钟运行后中断保持失效直到全局复位。

透明面板位于x256..639/y16..79，采用原有5×7字形系列，复用原mixer流水，无新增公共视频延迟。

| 字段 | 含义 |
|---|---|
| LAT / MIN / MAX | 最近有效首次显示样本及复位以来极值，ms，两位小数 |
| AGE | 最近有效显示样本的图像年龄；重复显示时可增加 |
| NEW / REP | 新采集身份 / 重复显示同帧；REP不重复累计LAT统计 |
| BAD / WAIT | 当前关联无效 / 尚无完整发布；BAD保留旧数字，不能当当前有效测量 |
| F / N / E | RAW帧号 / 不同帧有效样本数 / 无效测量数，十六进制；N/E到FFFF饱和 |
| 10US HEX | 时间戳量化10us；F/N/E使用十六进制 |

时基来自原配置75MHz，未做物理校准，10us不是已证明的绝对精度。DDR用户时钟实际66.667MHz。F/LAT属于最近完成的合格帧；F与TRACK LAST计数观察点不同，不应相减。各算法仍采用相同固定流水延迟，切换模式后LAT接近是合理现象。

## 资源优化与最终布局结果

四跳连接共享原生双端口行RAM；Gaussian/NMS首行读提前一级并在原窗口级对齐，使两行共享物理RAM；短配置延迟改为等价移位链。窗口、边界、valid/SOF/tlast、复位恢复及拍数保持原语义。宽字SP延迟实验资源不划算，未进入正式工程。

| 项目 | TRACK_REGION_FIX_V1基线 | 本candidate | 增量 |
|---|---:|---:|---:|
| Slice | 20942 | 20831 / 21216（98.19%） | -111 |
| LUT6 | 19498 | 19532 | +34 |
| FF | 20368 | 21337 / 42432 | +969 |
| ERAM20K | 105 | 105 / 108 | 0 |
| DSP | 25 | 25 / 40 | 0 |
| Setup WNS | +0.137ns | +0.175ns | +0.038ns |
| Hold WNS | +0.020ns | +0.020ns | 0 |

Setup/Hold TNS均0，最终STA覆盖95.33%。公共post-AWB流水仍31拍，增量0，每拍4像素。测量新增存储由行缓存/配置优化抵消；并非模块独立面积简单加总。

剩余385 Slice、3 ERAM，仍是高密度设计。保留既有PHY-5060（时钟混合扇出）和PHY-5079（局部时钟布线）关键告警；本轮无新增关键告警类型，不代表旧告警解决。

## 验证

bit目录build_evidence内保存完整证据，REGRESSION_GATE绑定45份结果/原生源码清单哈希。

- 原生Anlogic ERAM/GSR：64/68/72/76/1280宽度四跳、Gaussian/NMS方向及等峰、气泡、提前SOF、中断恢复与独立模型一致。
- 最终缓存结构完整720p对照18帧，4147200有效拍、3110400打包字逐像素/标记一致；TRACK31拍、颜色、尺寸、背景、字体、控制和复位回归通过。
- 标签FIFO与原FIFO异步时钟、复位、满空压力下5575次读取逐字一致；源标签、session回绕、槽覆盖、引用过期、重复帧、参考时钟停/恢复异常测试通过。
- 实际video_in、命令FIFO、video_out/解包、mixer的1280×4链路：12次完整提交、14幅合格显示、60424校验像素、4次重复、10个不同帧样本；独立仿真时间差在±2.1tick内。不是物理DDR/MIPI/HDMI PHY验证。
- OSD与原字库参考对照24576像素；单位、BCD、透明混合和旧字体验证通过。
- 最终95项TD输入冻结，与实际源码commit绑定；SYN→PHY→最终STA→bitgen通过。

R0时序通过但108ERAM、未生成bit。R1进一步共享行RAM至105ERAM，重新完整构建，未借用R0时序。早期PHY中止、资源失败实验保留在attempts，没有签发为候选。

## FIFO、CDC与限制

DDR仲裁、帧缓存策略、官方FIFO指针逻辑不变。异常会使测量失效，不代表历史溢出已修复；启动累计B/S与稳态增长仍需上板分开记录。

最终**同一route DB**只读CDC审计通过：时间Gray20位、保持元数据85位、选槽toggle、心跳、读坏标志、新FIFO Gray18条首级路径。最大路由net delay分别1.542/2.010/0.636/0.466/0.357/1.263ns，符合记录包络；20位时间同步级均存活，SDC未改。

这不是全设计CDC签核、MTBF或PVT长期稳定性证明；既有Gray约束覆盖缺口未擅自全局修改。真实长时稳定、热稳定、光照变化仍须验证。

## 功能保持与上板

Sensor曝光1990 half-lines、15.75×增益、VTS1000/HTS1600、BLC15/AWB、七模式算法、颜色对比、厘米读尺、W/H/D/R尺寸、TRACK/MOTION、K3/K4/开关语义、Logo/CNT及原OSD保持。MIPI/DDR/HDMI接口/调度、PLL、引脚、SDC保持；FIFO字内部增加标签，不增加DDR视频数据量。

首次PROGRAM_SRAM烧录；5s/30s/120s记录NEW/REP、F/N推进、LAT及稳态E/B/S。切换七模式及颜色/尺寸功能，再运行30min移动工件、改变光照；异常回滚旧candidate同接线对照。详见[LATENCY_PERFORMANCE_V1_BOARD_TEST.md](LATENCY_PERFORMANCE_V1_BOARD_TEST.md)。拍屏不能校验10us物理精度。

## 版本与归档

- Version：LATENCY_PERFORMANCE_V1；Branch：codex/main/latency-performance-v1。
- 精确基线：072bc0f8858ceb3009659f8df7cb02b9da05ed36 / PR29，不假设main包含未合并依赖。
- 实际构建源码：69521d7932c2fec94dd67c03a7362b4d6b0ceb8f。
- Tag：latency-performance-v1-candidate；归档commit由tag唯一指定，输入与tag闭环核验。
- Bit：artifacts/bitstreams/LATENCY_PERFORMANCE_V1/camera_to_dsi_display.bit，1789539bytes。
- SHA256：062b48ec7c002b56b4a025cd36a0e0f5e9138178f5706d6390a7f91eef3a27a4。
- BUILD_INFO.md/json及build_evidence在同目录。
- [Draft PR30](https://github.com/Philid14/anlogic-ph1p35-image-processing/pull/30)依赖未合并PR29；LATENCY PR5未合并/未搬入，不修改队友文件。
- Private origin：https://github.com/Philid14/anlogic-ph1p35-image-processing.git。
- Push及归档commit以docs/evidence/LATENCY_PERFORMANCE_V1/REMOTE_RECEIPT.json实际回执为准。
- Git Status：仅保留原有docs/GITHUB_REFERENCE_RESEARCH.md修改和用户未跟踪资料；本任务提交，不混入用户资料或自动构建数据库。
- Board Test：NOT_RUN。停止候选开发，等待上板，不自动合并。
