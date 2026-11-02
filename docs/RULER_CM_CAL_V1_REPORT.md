# RULER_CM_CAL_V1：厘米刻线平均粗标定候选

MAIN / 2026-11-02。基线123186a9/VISION_TRACK_MOTION_V1/Draft PR24，未合并。
用户当前拍屏CAL FAIL/R5；烧录bit SHA未独立核验，不能把该照片精确归到某历史tag或认定单一光学根因。
本轮按用户要求只改厘米粗标定和标题，不再要求可靠识别密集毫米刻度。

## 交付效果及操作

**1CM RULER LONG TICKS → 短按K4 → 保持尺子不动等待CAL:OK → 关闭CAL、保留尺寸测量，换同平面工件。**
相邻厘米线有d像素，则10mm=d像素；先平均四个以上相邻间隔，再平均两条相邻有效行。
在全部27带中优先较大稳定间距，降低先读到半厘米行的风险；不是OCR或能自动识别任意尺子的单位。
沿用大框768×288、原十二行缓存和“像素/100mm”接口，尺寸W/H等工程制图式标注继续使用该比例。
至少五条厘米长线清楚可见；保持水平、白色干净背景、摄像头正俯视、尺和工件同平面。
约54个采集帧完成整框搜索，期间不要连续点K4重启。看到1MM标题说明仍是旧bit。

这是大致比例，不承诺精密准确度；细线/反光/规律背景、尺度范围或高度差仍会误读。
**CAL:OK不等于精密校准或绝无倍数误认。** 成功后用尺量过的独立工件复核；若约差两倍/五倍，不能接受。
详细算法见[DESIGN](RULER_CM_CAL_V1_DESIGN.md)，操作见[BOARD_TEST](RULER_CM_CAL_V1_BOARD_TEST.md)。

## 验证证据

- 19项原生RTL检查、3992831周期：12..120px/cm、非整数33.4px、毫米/半厘米/厘米混合、边界、五线条件、抖动、平坦/无长线、错误帧/重试/取消/复位。
- 模型另对构造真值span=10×厘米像素距作断言，防止仅模型与RTL相互一致却采用错误单位。
- 默认1280×720/768×288全区域读尺实例：框上/下放置、完整27带搜索，27443319周期，通过500px/100mm。
- 9帧720p整机ISP/原生ERAM/GSR/工程字形/测量换算/DDR打包逐像素通过：2073600有效拍、1555200打包字，得到500px/100mm。
- 该9帧测试只有读尺搜索高度限定为12以缩短调度，其余视频/算法/OSD/打包均实际720p；全部288高度已经由上述默认读尺独立实例覆盖，不将缩小调度冒充全区域整机测试。
- 8帧TRACK/MOTION原生回归1843200拍/1382400字、原按键/CDC/复位回归通过。
- 两个正式HDL文件变化，其余82个TD输入、工程入口、Sensor/ISP参数、五算法、颜色、跟踪、运动、视频/DDR、PLL/引脚/SDC及队友源码保持基线。公共像素延迟仍31拍，无新增视频延迟。

仿真/综合/时序不是新实物读尺成功或精度证据；**Board Test NOT_RUN**，等待用户上板。

## 最终布局布线

| 指标 | VISION基线 | 本版 | 增量 |
|---|---:|---:|---:|
| Slice /21216 |20694|20726 (97.69%)|+32|
| LUT6 |19497|19445|-52|
| FF |20285|20230|-55|
| ERAM20K /108 |102|102|0|
| DSP /40 |27|25|-2|

仅剩490 Slice与6 ERAM，仍高密度。本版不是所有资源都下降：Slice小增32，换来厘米平均读尺；没有增加缓存，DSP少2。
完整TD Synthesis→Physical Design→最终Timing Check→bitgen PASS，一次完整构建，无放宽SDC。
Setup/Hold WNS **+0.145/+0.020ns**、TNS均0；STA coverage95.66%。
关键warning类型仍PHY-5060/5079和高密度告警；FIFO稳态、Gray约束覆盖、长期/光照/温度稳定性风险未因此消失。

## 版本追溯

- Version：RULER_CM_CAL_V1
- Branch：codex/main/ruler-cm-cal-v1
- 实际TD源码commit：9d1eff3e1e88861bfac317c6064c51062282aa4d
- Tag：ruler-cm-cal-v1-candidate（归档提交后创建）
- Bit：[camera_to_dsi_display.bit](../artifacts/bitstreams/RULER_CM_CAL_V1/camera_to_dsi_display.bit)
- SHA-256：6372f765f61ec31d8a18923596c8326ce84a0fd7637850847d5ac364cc3aebc2
- [BUILD_INFO](../artifacts/bitstreams/RULER_CM_CAL_V1/BUILD_INFO.md)与完整构建/资源/STA/原生回归证据已归档。
- Git Status：显式提交本任务；用户原有GITHUB_REFERENCE_RESEARCH修改和未跟踪资料保留，不宣称全工作区clean。
- Remote：https://github.com/Philid14/anlogic-ph1p35-image-processing.git（Private）。
- Push Status / Draft PR：待本地归档提交后发布，尚不把本地bit称为已上传；不合并。
- Board Test：NOT_RUN。完成本候选即停止，不自行开发下一版。

回滚VISION_TRACK_MOTION_V1 / vision-track-motion-v1-candidate；SHA256 f3dfd9f1ad42bbca95199ac128b9d4808327d4482a1465019ce85a678c0b63a0。历史bit/tag未改变。
