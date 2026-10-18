# EDGE_STABILITY_PROBE_V1 验证与失败记录

角色MAIN，源码基线8b3b9853cb900ca2305872b4ad9e129274efdbdf；不调用真实硬件。

## 验证方法

- `run_edge_stability_probe.py`用独立NumPy条件图定义固定源，对真实输入用不同随机RGB逐帧替换，检查注入前边界选择、Original保真、软件QUALITY最终输出、两级字库OSD、valid/user/last、实际96→128打包；全720p另强制实际isp_top的AWB后输出，比较真实集成接线。
- 6帧依次EDGE80/ORIGIN80/EDGE80/EDGE60/ORIGIN60/EDGE60，early SOF提前61个消费边沿与同拍SOF交替，变行/帧消隐。帧内请求持续改变，验证配置只在SOF生效。面板的每次320bit原子发布与独立字段/CRC模型比较；每个有效像素包括诊断字符/背景逐拍对照。
- `tb_probe_monitor`：合法帧、行内1+15气泡、缺失tlast、10行截断帧、恢复、相邻同TH完整帧CRC翻转、FIFO sticky上报、N/A首位置和V/W。延迟25/27拍流与实际packer，不只测试计数函数。
- `tb_probe_fifo_events`：实际video_in/out中的full/empty接线、源域sticky、初始化屏蔽、armed可读及复位，FIFO旗标为行为驱动，不模拟真实IP物理失效。
- `run_probe_regression.py`运行原QUALITY关闭路径、分类所有241门限、四层所有生产地址/部分字长度、按键/异步邮箱/116初始化后无写入及256十进制。旧frozen清单用当前明确七文件例外的新604文件核对替代，其余断言、向量和算法未改。
- 算法、Sensor、AWB、SDC、PLL、pack、HDMI mixer、15个历史bit以及队友当前跟踪文件由基线内容核对保护。TD新增两个诊断模块，不改旧算法。

## 可复现入口

```text
python -m pip install -r tests/requirements-edge-quality.txt
python -X utf8 tests/probe_reference.py
python -X utf8 tests/run_edge_stability_probe.py --full
python -X utf8 tests/run_probe_regression.py
```

Python3.12.14、NumPy2.3.5、Pillow12.3.0、Matplotlib3.11.2、Icarus12.0。
正常图期望签名：TH40=417312EE、TH60=2B018224、TH80=6B6DB7D0。全部25个合法门限的软件CRC与白点数另归档，不宣称全25门限都已物理验证。

## 已执行检查点

- 256×160新探针6帧：61440有效拍、46080打包字、6次面板发布点检查，67903步，PASS。
- 监测异常单元9帧：气泡/phase/pack关联、缺失tlast、截断、CRC改变、FIFO观察标志，PASS。
- FIFO事件实际接线和复位/arming单元，PASS。两独立单调HDMI旗标的CDC源/目的接线另由代码检查；Icarus不模拟亚稳态。
- 旧QUALITY0/1各64×32共28676有效拍/21507字，分类2892采样、四跳168500拍/1348000采样-层对照，按键/200异步配置包/116初始化+50按键无Sensor写入/0..255字符，PASS。初次从命令执行等价序列，之后提供独立可复现脚本。
- 完整1280×720新探针6帧：1382400有效拍、1036800打包字、6次面板发布点检查、1409023步，实际isp_top/packer逐项通过；与小尺寸、独立单元一起在完整入口退出0。FIFO最后增加启动屏蔽断言后单独重跑通过，日志另附，未更改被测RTL。
- TD路由结果完成后以归档原始结果和BUILD_INFO补录，不以RTL仿真冒充完整构建。

## 失败及修正

1. 新监测单元首次期望“一个气泡对应一个phase事件”，实际1+15拆分连续段两端都mod4非0，因此得到2次，打包器288→287字。根据真实计数定义修正测试期望为2；没有改监测RTL掩盖失败。原始观察：IN00000180、PACK0000011F、ERR00000002、首位置行4/拍1。
2. 面板字段审查发现last_line需和其他input影子寄存器同帧锁存，已在完整集成验证前加入s_last_line，避免拿下一帧末行填入旧SEQ。正常与异常行数测试验证一致；没有以帧间跳动当作测量结果。
3. FIFO未armed状态若只显示sticky=0会造成未测误解，完整候选前增加两路独立armed位及其实际接线/启动屏蔽测试。未armed不标正常。
4. 首次TD CLI启动时Python的Windows反斜杠脚本路径被TD按Tcl转义，提示无法读取DefaultFlow；进程退出0但缺少Flow Statistics，构建守卫正确拒绝。统一传入正斜杠路径后重新完整运行。此前未真正综合、未生成bit，日志保留；不是RTL或时序失败。
5. 源码faf3262已综合完成，物理实现过程中复核启动语义发现“只等两个HDMI vsync”不足以屏蔽Sensor初始化前的正常空读。主动停止该轮物理实现，未运行新bitgen（Runs bit仍为2026-10-17旧文件，不能归档冒充新bit）。旧源码commit、综合/部分物理stdout和prebuild信息保留。增加实际packed capture的连续三完整帧ready，经两级同步后再等两次HDMI vsync；独立actual capture_arm/FIFO单元验证未就绪多次刷新不误报、短帧重新等待、三完整帧armed和复位。只改变诊断启用时机，不门控视频请求。原完整720p数据通路测试仍对应未变化的注入/算法/OSD/packer；更改的启动模块另补单元和小尺寸联合回归，再重新完整TD。
6. 源码667eff7完整生成R0 bit，但最终Setup−0.051ns/TNS−0.454ns/15端点违例，Hold+0.020ns。归档EDGE_STABILITY_PROBE_V1_R0，不作为candidate。最差HDMI_PIXEL_CLK路径mult0_syn_59→O_hdmi_data_reg[17]，slow_m40c，数据12.995ns/14级；MIPI域+3.120ns。LUT16076/FF16478/Slice17111(80.65%)/ERAM47/DSP9。说明新增诊断触发重新物理映射后旧HDMI裕量不稳，不能把它作为实板抖动原因已证实。保留全报告与bit，不放宽SDC，继续缩减纯诊断资源后再构建。
7. 首次归档脚本未接受area字段的行首缩进，未成功创建归档目录；修正提取器后原样复制原始报告，未修改资源数字或RTL。
8. R0之后仅将内部诊断SEQ从32bit缩为16bit、面板仍零扩展8位十六进制显示；其余观察字段与数据通路不变。增加3bit参数跨回绕13帧单元，再跑小尺寸联合验证。目的是减少诊断开销/物理干扰，不声称逻辑上修复了未改动的HDMI路径；须重新完整TD判断。

## 最终候选构建（2026-10-18，Asia/Shanghai）

源码`131afb0a745c62f119e1ae2f869788f45944f4a2`经完整Synthesis、Physical Design、final Timing Check、bitgen通过。最终路由LUT6 15415、FF 16334、Slice 16872/21216（79.52%）、ERAM20K 47/108、DSP 9/40；Setup +0.102ns、Hold +0.020ns，两个TNS均0、两个违例端点均0。STA coverage 95.98%，slow/fast及max/min均检查。

最差Setup仍是HDMI_PIXEL_CLK：`u_hdmi_mixer/mult0_syn_59.clk → u_hdmi_mixer/O_hdmi_data_reg[20]_syn_2.id`，15级，周期13.333ns。MIPI域Setup +3.711ns、DDR user域+2.341ns。本轮未改HDMI逻辑、时钟、SDC，正裕量是本次物理实现的结果，不代表已经证明此前抖动由时序造成或已经修好。

与QUALITY全设计相比LUT6 −747、FF +911、Slice −1022、ERAM/DSP均0增量。固定图输入可使综合常量传播，整体重映射也改变资源，因此这些净差不能作为通用实时RGB Edge算法的资源优化收益。

关键warning类型仍PHY-5060/PHY-5079，无新增类型：I²C scl_clk及O_cam_24m混合时钟/数据扇出、局部时钟路由警告保留。两组Gray max_delay 14.700ns/13.033ns仍各18条被set_clock_groups忽略；STA覆盖问题未修复，不将通过报告等同完整CDC验证。

最终bit `artifacts/bitstreams/EDGE_STABILITY_PROBE_V1/camera_to_dsi_display.bit`，1789539 bytes，SHA-256 `7A78AFBC6126CDA8860E70241DA7AA934C68B0C98D1DB02E7FD2F7790A061980`。归档包含63项输入manifest、构建前16份bit不变清单、完整原始日志/报告、关键warning和失败/中断记录。旧R0负裕量bit保留为失败检查点，最终candidate仅指本次正裕量版本。

最后的16bit序号版本执行小尺寸联合测试与13帧跨回绕单元，启动屏蔽模块执行实际接线单元；完整720p六帧测试覆盖的是未变化的注入/算法/OSD/打包通路，不能声称所有物理IP或最后一版再次完整720p仿真通过。实板状态仍待用户烧录反馈。

## 证据局限（最终适用）

无真实AWB后控制采样、无真实连续RGB、未在本机烧录。没有厂商MIPI/DDR/HDMI PHY、带SDF门级或完整CDC MTBF仿真。新OSD和监测与用户上板现象无实测对应，全部结果是数字测试。
新面板显示的历史CRC取两个二值代表位，不能替代全部RGB/DDR读回逐点比较；重复显示/丢帧没有session/frame身份，未实现端到端延迟统计。
时序合格不等于长期显示稳定，Gray指针约束覆盖问题仍需独立修复评估。待上板记录按BOARD_TEST执行。
