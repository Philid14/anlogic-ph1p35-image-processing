# EDGE_TEMPORAL_RESEARCH_V1 首次实板录像解码报告

日期：2026-10-18。角色：MAIN。结果：**传输恢复不完整，85/101页；缺54–69（协议编号从0开始），不进行真实ROI时间稳定性研究。**

## 1. 输入与版本

| 项目 | 实际值 |
|---|---|
| 原录像 | 仓库根目录 `video_20261018_171946.mp4`，65404067字节；保留原件，不提交Git |
| 原录像SHA-256 | `0C53F9B65B2B910E1EBA180B7978D1BBA9DBA49ACA0C72A067868291373FAD7A` |
| 视频 | 1920×1080、HEVC；视频轨118.658189秒，容器118.692秒；平均29.87573fps，不能视作严格恒定帧率 |
| 手机图像解码帧数 | OpenCV4.13.0与FFprobe实际count_frames均为3544；容器nb_frames标注3545，差1单列记录 |
| candidate tag / 归档commit | `edge-temporal-research-v1-candidate` / `e3a6943857116b0a037aa1776a94e4b9f3602180` |
| 实际TD构建源码 | `84299d42fb88842b837794bdf43b61a88f1e2049` |
| 既有诊断bit SHA-256 | `5D01156E08E69DDAA51AB41A3E3C2DFB1BC8B60436E97FBAE6555754AE6EB27D` |
| 本轮分支 / PR | `codex/main/edge-temporal-research-v1` / Draft [#9](https://github.com/Philid14/anlogic-ph1p35-image-processing/pull/9) |

开工时tracked文件干净，HEAD与远程研究分支均为e3a6943；用户录像和历史本地参考资料未跟踪。本轮继续同一研究任务/PR，未从main重建或假设功能已经合并。联网核对#9→#8→#7→#6→#4→#3均为open Draft、未合并；各head/base SHA见证据目录pr_snapshot.json。

## 2. 执行方法与结果

1. 记录原文件SHA及视频参数，保留原件；读取BOARD_TEST、既有解码器及数据校验协议。
2. 执行原`temporal_transport.py`，stride=3，自动寻找白框四角，透视到1040×528，取8192个单元中心，执行原header/payload CRC及padding检查。得到85页，缺54–69。
3. 对约44–64秒区间599个连续手机帧以stride=1复查，没有新增合格页面。
4. 使用PC审计工具`temporal_video_audit.py`，对全部3544个可解码手机帧逐一执行相同光学解码器和CRC门槛，记录每帧实际视频PTS、有效页号及重复页一致性。结果仍85页。
5. 对名义46秒临界画面手工指定/小范围调整白框外沿四角，7个几何尝试中5个成功读回已有第53页，未补出54–69。没有推测填充丢失位或放宽CRC。逐帧主结果与stride=3所得85个页面逐字节相同。

| 校验/输出 | 结果 |
|---|---|
| 返回CRC合格页的手机帧 | 2641帧 |
| 没有返回CRC合格页的手机帧 | 903帧；包括未定位/裁切/切页/模糊等可能情形，**不是903次已判定CRC错误** |
| 去重有效页 | 85/101：0–53、70–100 |
| 缺失页，0起算 | **54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69** |
| 页header/payload CRC、bounds、末页padding | 保存的全部85页通过，含有效载荷20字的第100页 |
| 合格重复页冲突 / identity种类 | 0 / 1 |
| 包头声明总字数 / 页数 / burst identity | 24720 / 101 / `897350F6`；该identity尚未由完整burst RGB CRC复验 |
| 已恢复有效载荷字数 | 20768/24720；缺3952字、15808字节，不能补0当原数据 |
| 全101页assemble | 拒绝：missing pages [54…69] |
| 整批pre RGB及8帧pre/post CRC、实际gain重建 | **未执行到此门槛，不能报告通过** |
| 8帧连续SOF / IN / LINE / ROI / PACK / FIFO完整性 | **未完成整批验证，状态未知** |
| capture.npz / temporal_roi_analysis.py | 未生成真实capture.npz；**未运行真实数据算法分析** |

原审计脚本先把手机容器帧数差1作为保守阻断，原结果与脚本快照均保留。FFprobe独立扫描同样读出3544帧后，PC最终化逻辑将手机容器计数差异单列提示，仍完整执行页面assemble；真正缺页阻断保持不变。没有放宽FPGA帧数量、ROI、CRC或FIFO校验。最终化复用了同一全片扫描得到的页面与逐帧记录，没有声称再扫描一次或读取不存在的第3545个图像帧。decode_audit.json分别记录扫描脚本与最终化脚本SHA。

## 3. 失败定位与证据边界

**已证实：录像中段取景移动，编码框上沿/左上区域及部分数据格超出手机画面。** 约47、60、62秒的代表画面可直接看到顶端格子被画面边缘截断；正常时段能稳定通过CRC。透视可以校正可见四角，不能恢复画面之外的未知数据格。

逐帧CRC时间戳的两个边界：

- 第53页最后一次合格：视频frame1355，PTS **45.680611秒**。
- 第70页第一次合格：视频frame1872，PTS **62.911033秒**。

二者间没有任何可校验页面；缺页54–69与该时段一致。缺失页没有通过header CRC，因此不能把推算的逐页时刻冒充已经解码的页号。名义46秒静帧允许外推四角读回53，说明仅白边略被切掉时仍有恢复机会；后续数据格本身越界，人工四角无法补足未知内容。录像录到页100→0回绕，但该批缺页没有在其余录像中再次成功出现。

这支持**当前文件的光学导出完整性失败**。不能据此认定板内8帧存储坏、AWB异常、实际RGB静止或不静止，也不能据此归因Sensor噪声、频闪、运动、NMS或四跳连接。页CRC合格不等于完整capture已合格，手机图像亮度也不作为真实RGB码值使用。

## 4. 已保存资料与复现

证据目录：`docs/edge_temporal_evidence/board_20261018_first_recording/`。

- `valid_pages.zip`：85个1024字节合格原始包；`pages_manifest.json`记录各页SHA、identity、缺页及有效载荷量。ZIP保持原页面命名，可解压到新的解码output/pages后补录。
- `decode_audit.json`：最终传输审计；`frame_ledger.csv`：3544帧的0起算视频frame/实际PTS/合格页号。
- `video_info.json`、`ffprobe.json`：原视频SHA和两种工具的参数/计数。
- `boundary_scan.json`、`interval_probe.json`、`manual_boundary.json`：边界加密扫描与人工四角尝试。
- `decode_audit_initial.json`、`audit_tool_sources.zip`：初次保守手机计数门槛及实际扫描/最终化/光学解码器的原字节快照；ZIP保留行尾及源码SHA，没有覆盖失败记录。
- `audit_tool_tests.json`：**合成**无损视频完整恢复/重复页一致性、缺单页拒绝且不输出capture.npz的回归。它不是实板ROI恢复成功证据。
- `page_coverage.png`：页面覆盖图，红色为缺页，不是算法质量曲线。
- `pr_snapshot.json`：开工时PR依赖与SHA。
- `verification.json`：归档包CRC/SHA、源码快照SHA和逐帧计数一致性检查结果；完整capture仍被拒绝。

在安装requirements-edge-temporal.txt的独立Python环境中，从根目录可复现：

```powershell
python -X utf8 tests/temporal_video_audit.py video_20261018_171946.mp4 --output tmp/first_video_audit_fresh
python -X utf8 tests/test_temporal_video_audit.py
```

审计输出目录必须为新目录，避免混入其他录像；本次本地全扫描目录是`tmp/edge_temporal_real_20261018/full_audit`。现有原解码器的可续录目录是`tmp/edge_temporal_real_20261018/decoded`，其中pages已保留85页。OpenCV只安装在隔离的tmp/temporal_deps中，没有改工具全局依赖。原始手机录像与带房间背景的检查帧未加入Git。

## 5. 最少补录步骤

1. **如果FPGA仍保留原来这批编码页面：不要断电、复位或重新PROGRAM_SRAM。** 手机退后、固定，完整白框四角及四周余量始终入镜，建议整个显示器入镜，锁定对焦。无需调整相机、Sensor或算法。
2. 按原协议再录约4分钟、不移动取景，保存原始文件到根目录。页面循环，不要求人工读页号；只要缺少的54–69被完整拍到即可。也可提供这16页的完整清晰照片，但逐页人工定位更麻烦。
3. 我会向同一解码output补页，保持原header/payload CRC、重复页一致性、完整burst及每帧RGB/post重建和视频数量门槛，全部合格后才运行temporal_roi_analysis.py。
4. **若已断电/复位/重新烧录：重新录完整新一批101页**，另用新output目录，不能与旧85页混拼。即便场景看似相同也不混用；数据identity仅为32位内容CRC，不能代替现场是否复位的记录。

## 6. 本轮交付边界

仅增加PC逐帧审计/合成回归和报告，正式RTL、AWB/Sensor参数、PLL/SDC、按键、OSD、视频接口、旧bit及历史BUILD_INFO没有修改；未运行TD、未生成新bit、未移动candidate tag、未合并PR。继续在既有Draft #9提交本次解码证据，等待补录后再做真实数据分析。
