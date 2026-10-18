# 真实ROI诊断上板与手机导出

这是独立诊断bit，不是时间滤波优化版；实际SHA与源码见同版本BUILD_INFO。历史QUALITY/PROBE均可直接回滚。

## 一次最小采样

1. 机位、供电、灯光、曝光/增益不变，先把一段眼镜框/纸边与少量平坦背景放到画面正中心。不是把整张脸塞进ROI。
2. PROGRAM_SRAM烧录`artifacts/bitstreams/EDGE_TEMPORAL_RESEARCH_V1/camera_to_dsi_display.bit`。本版EDGE是真实摄像头边缘，不是固定PROBE图；左下暂显示REAL ROI诊断信息。K3仍ORIGIN/EDGE，K4仍短减10/长加10。
3. 立刻K3切ORIGIN，绿色框内是采样范围X576..703、Y344..375。保持目标与相机静止；第601个SOF开始采8个连续帧（600帧预热）。若没来得及定位，定位好后重新PROGRAM_SRAM/真正复位，重新计预热。不修改曝光或AWB参数。
4. 采完自动出现大块黑白编码图，旧MODE/THRESHOLD、安路Logo、CNT仍在。数据已经冻结，之后移动物体不会改变这一批采样。编码覆盖区外仍实时；当前模式不影响采样数据。
5. 手机横屏固定，拍清**整个白色矩形框及四角**，尽量正对、避免反光、对焦锁定。1080p或更高、30/60fps均可；保留原视频，不经聊天软件压缩。不要只拍数据框的一部分。
6. 编码共101页、每60个采集SOF一页并循环。若采集60/30fps一轮约101/202秒，实际采集率未实测。初次建议录约4分钟；缺页可继续录同一个冻结burst或补照片，不要复位后混拼。
7. 把原视频保存在本机并在当前聊天发完整路径；也可直接上传。先只做这一份静态采样，确认手机链路能恢复全部页后再扩大实验。

第一次采样关注“能否无损导出”，不能凭编码图闪动评价Edge稳定性。页面切换、CNT和SEQ变化是预期；白色框需要完整入镜。

本版预览是真实Edge，所以仍可能出现白线闪烁；CRC不再是固定图的6B6DB7D0，COUNT低16位（相邻同TH CRC改变）累加和FLAG bit24置位是预期，不直接判控制流故障。控制错误看ERR、COUNT高16位、IN/PACK/LINE及后续采样元数据。新诊断没有宣称修复抖动。

## 本机解码与分析

在项目根目录，用独立Python环境安装`tests/requirements-edge-temporal.txt`，不要随意改现有工具运行时包版本。

```powershell
python -m pip install -r tests/requirements-edge-temporal.txt
python -X utf8 tests/temporal_transport.py 'D:/captures/static_glasses.mp4' --output 'D:/captures/static_glasses_decoded'
python -X utf8 tests/temporal_roi_analysis.py 'D:/captures/static_glasses_decoded/capture.npz' --threshold 80 --output 'D:/captures/static_glasses_analysis.json'
```

每个通过CRC的页面会保存为pages/*.bin。缺页会明确报编号，不生成有效capture.npz；补录**相同冻结burst**后以同一output目录再运行，可保留已有页。不同复位/不同场景必须用新output目录。镜像、反光、过模糊或滚动快门可能无法识别；CRC拒绝错误而不修复错误。

若自动定位被Logo、反光或其他白色图形干扰，固定手机机位后可传`--corners "x0,y0,x1,y1,x2,y2,x3,y3"`指定视频像素坐标中白框外沿左上/右上/右下/左下，所有页仍执行相同CRC检查。也可把原视频路径发来由我处理，不要求你先会手工定位。不要用HDMI1280×720坐标替代手机视频坐标。

成功必须满足全部101页、header/payload CRC、完整burst及每帧原RGB CRC、实际gain重建后CRC、连续采集序号和输入/行/ROI/pack数量。未armed、ROI内gain变动或burst出现新FIFO sticky先报错，不进行算法排名。相同历史sticky仍会记录，不等于从未发生异常或能检测重复同类事件。

研究工具输出RGB差异、增益、统计、各级变化、候选静态指标；未标注真实轮廓/平坦区时完整度/误检/拖影为null，不会把缺失数据当0。首帧固定gain回放不是已收敛硬件冻结，真实AWB未改动。

## 后续重复场景（首份可解码后）

### 首次录像反馈（2026-10-18）

`video_20261018_171946.mp4`已完成全片逐帧检查。恢复85/101页，缺54–69（协议编号从0开始）；对应约46–63秒时段编码框上沿/部分数据格越出手机画面。不能重建完整8帧，未执行时间稳定性分析。完整证据见`EDGE_TEMPORAL_RESEARCH_V1_FIRST_DECODE.md`。

补录时把手机退后、固定，建议整个显示器入镜并在白框四周留出余量；不要边录边靠近或移动取景。保持原板上冻结数据、不复位、不重新烧录，补录约4分钟即可与已有合格页合并。若已经断电/复位，则重新录完整101页，不能与这批旧页混拼。原录像保留；缺页不是要求修改Sensor或算法。

### 完整补录反馈（2026-10-18）

新增`video_20261018_174321.mp4`已独立恢复101/101页、8帧真实128×32 ROI及AWB元数据，全CRC/数量/armed/sticky检查通过，与旧录像85页逐字节相同。这是原冻结burst的完整导出，不是第二次独立采样。

已执行TH40/60/80离线模型：真实RGB存在微小帧间变化；AWB动态gain在本ROI未造成额外码值变化；公共有效区为平坦暗部，Gaussian+Sobel最大18，无有效门限轮廓，不能评价白线稳定性或给时间算法排名。完整评估见`EDGE_TEMPORAL_RESEARCH_V1_REAL_DATA_EVALUATION.md`。

**当前旧数据已不缺页面。下一步是重新采样真实边缘：先把纸边/眼镜框确实放在绿色ROI中央，定位好后重新PROGRAM_SRAM同一bit，600 SOF后冻结，再独立录完整页面。** 继续录旧编码页不会产生新RGB。建议附一张绿色框穿过边缘的照片及灯光/静止性说明，仅用于确认位置。

### 18:19录像核对（2026-10-18）

`video_20261018_181941.mp4`独立完整恢复101页，但全部页面、8帧RGB、AWB元数据和SOF周期时间戳与17:43录像导出内容逐字节相同；仍为原平坦暗部burst。详见`EDGE_TEMPORAL_RESEARCH_V1_RECORDING_181941.md`。录制了新视频不表示采样RAM已更新；本程序只有实际复位后重新预热/捕获，K3/K4及采完后移动纸张均不重新采样。

下一次建议明确完成同一bit的PROGRAM_SRAM并在预热阶段定位纸边，编码出现后先提供一张完整清晰编码页进行快速批次身份/载荷检查，再录整圈，减少重复导出旧数据。某个按键是否复位采样模块不能从录像判断；未据此修改按键或RTL。

- 眼镜框/人脸局部、纸边/文字、平坦墙面；每次ROI兼有真实轮廓与平坦区。
- 同机位静态室内正常灯光/更亮灯光；已知稳定光源与现有灯光对照，避免手遮镜头模拟“纯噪声”。
- 慢速移动纸边/眼镜，另做出现和消失；固定曝光/增益，不因画质调整相机配置。
- 每条件多次burst，记录是否真正静止、光源、重置时间、TH、模式、异常；8帧仅是短窗口，不能声称长期稳定性已经量化。

反馈：bit SHA、场景说明、原视频路径、解码结果/缺页号、是否新异常；不需要把巨大编码视频提交GitHub，保留原文件及SHA即可。

## 18:42新采样反馈（2026-10-18）

`video_20261018_184242.mp4`已独立全扫描3332帧，恢复**101/101页、全8帧及AWB元数据**，全部页面/重建CRC通过。identity为新的`6A23858A`，与旧`897350F6`不同，RGB全数组也已变化；本次重新采样确实产生新数据。

新ROI变亮且出现TH40/60临界响应：pre/post RGB相邻MAE5.1392/5.8269，公共区域Gaussian+Sobel最大64，TH40四跳同坐标翻转率16.35%，但未辨认出清晰黑白分界，TH80为空。实际AWB变化有小幅影响，固定gain后仍不稳定。写侧FIFO历史sticky均1，发生时刻/重复事件未知，不能宣称视频流完全正常。

用户补充：目标手持、尽量保持不动；未看见绿框，边界估计位于画面中间。不要把这批当作无运动的理想纸边或纯传感器噪声数据。完整结果与图见`EDGE_TEMPORAL_RESEARCH_V1_RECORDING_184242.md`。

**下一步先核对预热期ROI与异常，再补长录像：** 固定相机和纸边，重新PROGRAM_SRAM后立即切ORIGIN，拍下编码出现前绿框穿过边界的整屏照片/短录像。ROI只有画宽45%–55%、画高47.78%–52.22%；编码出现后中央已被覆盖。若一直看不到框，先提供预热短录像用于核对，不要再盲录整轮。沿用既有bit、无参数改动；暂不开发正式时间算法。复核重置后写FIFO标志首次置位情况；既有sticky不能检测置位后的重复事件。

## 回滚固件

- 实时原算法：重新PROGRAM_SRAM烧录`artifacts/bitstreams/EDGE_QUALITY_V1/camera_to_dsi_display.bit`；SHA `629ACAA828EF8151DED0261779ED8B91F0FA618EED66DD46C72D6E799ADCC9D5`。
- 固定源对照：`artifacts/bitstreams/EDGE_STABILITY_PROBE_V1/camera_to_dsi_display.bit`；SHA `7A78AFBC6126CDA8860E70241DA7AA934C68B0C98D1DB02E7FD2F7790A061980`。

若花屏/失锁或数据数量报错，先记录并回滚，不增加时域滤波。当前诊断没有修复Gray约束覆盖，也没有未经确认集成新算法。
