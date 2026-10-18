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

## 本机解码与分析

在项目根目录，用独立Python环境安装`tests/requirements-edge-temporal.txt`，不要随意改现有工具运行时包版本。

```powershell
python -m pip install -r tests/requirements-edge-temporal.txt
python -X utf8 tests/temporal_transport.py 'D:/captures/static_glasses.mp4' --output 'D:/captures/static_glasses_decoded'
python -X utf8 tests/temporal_roi_analysis.py 'D:/captures/static_glasses_decoded/capture.npz' --threshold 80 --output 'D:/captures/static_glasses_analysis.json'
```

每个通过CRC的页面会保存为pages/*.bin。缺页会明确报编号，不生成有效capture.npz；补录**相同冻结burst**后以同一output目录再运行，可保留已有页。不同复位/不同场景必须用新output目录。镜像、反光、过模糊或滚动快门可能无法识别；CRC拒绝错误而不修复错误。

成功必须满足全部101页、header/payload CRC、完整burst及每帧原RGB CRC、实际gain重建后CRC、连续采集序号和输入/行/ROI/pack数量。未armed、ROI内gain变动或burst出现新FIFO sticky先报错，不进行算法排名。相同历史sticky仍会记录，不等于从未发生异常或能检测重复同类事件。

研究工具输出RGB差异、增益、统计、各级变化、候选静态指标；未标注真实轮廓/平坦区时完整度/误检/拖影为null，不会把缺失数据当0。首帧固定gain回放不是已收敛硬件冻结，真实AWB未改动。

## 后续重复场景（首份可解码后）

- 眼镜框/人脸局部、纸边/文字、平坦墙面；每次ROI兼有真实轮廓与平坦区。
- 同机位静态室内正常灯光/更亮灯光；已知稳定光源与现有灯光对照，避免手遮镜头模拟“纯噪声”。
- 慢速移动纸边/眼镜，另做出现和消失；固定曝光/增益，不因画质调整相机配置。
- 每条件多次burst，记录是否真正静止、光源、重置时间、TH、模式、异常；8帧仅是短窗口，不能声称长期稳定性已经量化。

反馈：bit SHA、场景说明、原视频路径、解码结果/缺页号、是否新异常；不需要把巨大编码视频提交GitHub，保留原文件及SHA即可。

## 回滚

- 实时原算法：重新PROGRAM_SRAM烧录`artifacts/bitstreams/EDGE_QUALITY_V1/camera_to_dsi_display.bit`；SHA `629ACAA828EF8151DED0261779ED8B91F0FA618EED66DD46C72D6E799ADCC9D5`。
- 固定源对照：`artifacts/bitstreams/EDGE_STABILITY_PROBE_V1/camera_to_dsi_display.bit`；SHA `7A78AFBC6126CDA8860E70241DA7AA934C68B0C98D1DB02E7FD2F7790A061980`。

若花屏/失锁或数据数量报错，先记录并回滚，不增加时域滤波。当前诊断没有修复Gray约束覆盖，也没有未经确认集成新算法。
