# STYLE_V2_TARGET_V1 黑底图启动诊断

2026-10-28 / MAIN。用户确认：旧EDGE_STYLE_FILL_V2同接线正常；新候选重复烧录仍只有安路Logo/CNT，没有MODE/THRESHOLD及底部TARGET诊断；照片中的人物/环境是屏幕反光。

## 已确认与未确认

- 归档原候选bit SHA256仍为2172E53406AF5D67BD2A167C8935F6C9870CC0AC6E79382217F13024DF7888FF。
- HDMI光栅、mixer、Logo/CNT至少在当前观测下工作；照片不能证明DDR已校准或摄像头配置成功。
- MODE/B/S位于DDR前的ISP输出；底部原TARGET面板依赖真实显示metadata。因此缺少这些信息支持“尚无首个可显示帧”，尚不能认定是哪一准入条件失败。
- 未证明是Sensor、lane error、803-halfword envelope、AWB、DDR校准或时序单一根因；不通过关闭错误判定让候选表面恢复。
- 原final18明确采用合成RAW/post-AWB及有界DDR，没有验证真实MIPI PHY、实际包络或整套Sensor初始化。
- 定向front_boundary_01：真实Demosaic、原生RAM、AWB行缓存/valid/user/last、observer两帧通过：460800 AWB拍、1440行、raw_good2/observer_good2/abort0/epoch0。divider算术为固定1×测试替身，仅支持时序边界结论，非完整AWB数值或实板证明。

## 独立诊断版本

Version STYLE_V2_TARGET_BOOT_DIAG_V1，分支codex/main/style-v2-target-boot-diag-v1，从5cbb1de建立。
仅增加无首帧时可见的boot telemetry。原帧准入、错误源、超时、取消、DDR、算法、Sensor、按键、时钟/SDC不改。
新增两个单向整包邮箱传递CSI sticky位与DDR快照；不同于真实FrameRef metadata，不生成伪造的可显示帧。
显示底部两行：C:hhhh D:hhhh R:hhhh / D:hhhh C:hhhh Q:hhhh。

第一行C=CSI累计出现位（低位到高位）：0 RAWvalid，1 capture_start，2 nativeEOF，3 RAWgood，4 AWBuser，5 AWBvalid，6 observer_good，7 detector_valid，8 包络monitor error，9 lane error，10 packedvalid，11 grant_matches，12 camera_we，13 RAWbad，14 observer_bad，15 terminal_bad。
第一行D=DDR累计出现位：0 calib_ready，1 time_valid，2 ledger_ready，3 allocated，4 MCwriteaccept，5 committed，6 scan_request，7 scan_selected，8 camera_epoch_fault，9 grantoverflow，10 displayoverflow，11 cancelled，12 terminal_receive，13 terminalgood，14 terminalbad，15 pendingwrites。
第一行R=DDR当前快照：bit0原metadata邮箱online，[3:1]recovery，4calibready，5timevalid，6ledgerready，7writeactive，8writeidle，9readidle，10pendingwrites为0；[15:11]保留0。
第二行D/C/Q分别是原drop/cancel/metadatafault饱和16位计数。
上述CSI/DDR位是累计观测，不能将曾出现错误等同于持续错误；结合第二行增量和当前R判断。

## 上板后最小回报

从新归档bit烧录，在约5秒和30秒各拍一张完整面板；仍保持当前原接线与Sensor配置。
先看C是否有RAW/AWB输入，再看D的calib/ready/allocation/write/commit/read链是否推进；若C的包络或lane错误出现，需结合计数/阶段进一步确认语义，不能据sticky独断每帧坏。
当前用户黑屏反馈属于原candidate实板FAIL，新增诊断bit状态在完整构建成功前为NOT_GENERATED，构建与新上板结果另行记录。
