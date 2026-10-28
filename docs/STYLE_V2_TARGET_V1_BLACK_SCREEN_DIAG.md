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

## 本轮验证范围与限制

- `verify_style_target_boot_release.py --proof-only` 对原候选实际输入清单逐项比对：算法、Sensor/ISP、DDR、时钟/SDC字节一致；逆向删除新增的诊断端口、接线和显示分支后，顶层、帧控制、显示控制与原候选文本一致。未绕过错误、伪造FrameRef或改变帧准入。
- 原生ModelSim完整1650×750显示旧版等价回归：2,475,309次检查；新增启动面板在metadata缺失/scan_fault状态下逐像素检查1,237,500拍、1532个文字像素，不制造有效显示身份。
- 原生MAIN/MC/FIFO active-epoch回归完成90ms、24,648,825次检查。调用脚本误填了另一个测试的PASS字符串，原summary保留`passed:false`；`RESULT_EVALUATION.json`依据实际正确PASS标记、三个工具退出码0和源码哈希另行确认RTL通过。没有改动期望、掩盖工具退出或将脚本失败改写为成功。
- 两级整包邮箱单元测试PASS；上述front_boundary仅验证真实行缓存及流边界，不验证实际Sensor/PHY。
- 原生默认布线出现一条packed RGB寄存器bit87到写FIFO ERAM的Hold -0.068ns；不得生成该结果的bit。原始报告和后续短物理实验都保留。CPLD专用buffer_opt未生效；默认post-route优化和clock_opt未收敛；移动试验因没有可用slot移动0实例，不能描述为已修复。
- 最后一次有界尝试使用TD原生route effort high，自同一place.db重新布线；不改RTL/SDC/seed。其结果及实际选择另记。诊断版的Hold违例不构成原候选黑屏原因证据。

## 最终状态：诊断固件未发布

- Version：STYLE_V2_TARGET_BOOT_DIAG_V1；Branch：codex/main/style-v2-target-boot-diag-v1。
- 实际构建RTL commit：958e1068a3aae15b5d2c0f93141a9e5cbea83ca2。
- Synthesis/placement完成；最终route_boot_diag_08仍为Setup +0.110ns、Hold -0.068ns，Setup TNS0、Hold TNS -0.068ns、1个Hold违例端点。原生高力度route没有解决该违例。
- 实际布局布线资源：Slice19572/21216（92.25%）、LUT6 17692、FF21352、ERAM20K99/108、DSP21/40。相对原candidate Slice减少380；这不是功能修复或稳定性通过。
- **Timing FAIL；bitgen未执行；Bit Path/SHA256不适用；Board NOT_RUN；未建立candidate tag。** 不烧录 *_Runs 中旧bit，不将SYN/仿真PASS冒充完整构建PASS。
- 失败标签拟使用style-v2-target-boot-diag-v1-hold-fail，指向包含源码和失败证据的提交；不替代或移动历史tag。
- 新增两条诊断邮箱的最终物理CDC复核未执行，因为本诊断构建已被Hold门阻断。原候选的CDC/PHY及首帧实板风险依旧未排除。
- 用户最新照片确认仅Logo/CNT、其余为反光；原STYLE_V2_TARGET_V1上板状态仍为FAIL，尚未修复。
- 当前最安全的可用显示回退仍是已由用户确认正常的edge-style-fill-v2-candidate归档bit。后续应先解决诊断构建这条最小Hold短路径，取得启动C/D/R及drop/cancel/fault增量，再定位首个失败的帧准入条件；不能直接关闭包错误、lane错误或完整帧检查。

### 复现路径

1. 从本诊断分支的实际RTL commit恢复TD输入，执行`build_style_v2_target_v1.py --attempt <独立名称>`完成SYN。
2. `place_style_target_preflight.py`从该SYN完成place；本轮原输入manifest、place结果存于docs/evidence/STYLE_V2_TARGET_V1/syn_boot_diag_01和place_boot_diag_01。
3. route_boot_diag_01完整布线；route_boot_diag_08自同一place.db用`set_param route effort high`重新布线，flow、source chain、原生stdout、压缩timing和最终RESULT均已归档。02–07是短物理命令实验，无新RTL candidate；无效/CPLD专用选项或移动0实例按实际失败记录保留。
4. 未通过Hold前不得调用finalize_style_target_route.py生成bit。脚本仍保留Setup/Hold/TNS、源码哈希、物理CDC及验证门槛。
