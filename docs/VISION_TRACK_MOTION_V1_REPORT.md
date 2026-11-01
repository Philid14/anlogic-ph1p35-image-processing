# VISION_TRACK_MOTION_V1：进阶2/4候选与资源优化

MAIN / 2026-11-01。准确基线43ff61b4 / INSPECTION_USABILITY_V4 / Draft PR #23，未合并。
本轮已完成数字验证、完整TD SYN→PHY→最终STA→bitgen及本地归档；**Board Test NOT_RUN**。
远程推送与Draft PR发布状态见本报告末尾和REMOTE_RECEIPT，不将本地归档称为已上传。

## 实现结果

- K3增加TRACK、MOTION；循环EDGE→ORIGIN→GRAY→BINARY→STYLE→TRACK→MOTION→EDGE。K4原阈值语义、原有应用开关不变。
- TRACK直接引用队友PR #2固定源码的分类、统计、跟踪和年龄保护；MAIN增加SOF适配。当前红色像素绿青标记，最近完整帧包围框中心/像素数明确LAST/HEX；不是同帧完整框，不是质心或多目标识别。
- MOTION全像素32×16块均值帧差，双银行4096×8 ERAM，固定差阈12；显示当前变化块末拍洋红标记，以及LAST变化块数/帧号/状态。计数单位是块，不是物体。大范围变化单列GLOBAL。
- 两者观察真实post-AWB输入，标记/统计烧入源像素后经过原DDR，不新增宽元数据CDC或整帧RGB缓存。不复用历史黑屏集成的DDR/ledger路径。
- 像素流水线仍31拍；所有旧算法、颜色/尺寸应用、Sensor参数、视频格式、引脚、PLL与SDC保留。两个旧RTL只前移精确线网声明以兼容原生仿真器，表达式不变。
- HDMI新增采集完成心跳超时VIDEO STALE；这只检测采集停顿，不证明DDR最新帧，也不构成进阶3延迟测量。

## 最终真实资源与时序

| 布局布线指标 | V4 | 本候选 | 增量 |
|---|---:|---:|---:|
| Slice /21216 |20994|20694 (97.54%)|-300|
| LUT6 |19863|19497|-366|
| FF |19116|20285|+1169|
| ERAM20K /108 |90|102 (94.44%)|+12|
| DSP /40 |27|27|+0|
| Setup WNS(ns) |+0.146|+0.106|-0.040|
| Hold WNS(ns) |+0.020|+0.020|0|

**增加两项功能后Slice减少300、LUT6减少366；代价是FF增加1169、ERAM增加12，DSP不增加。**
仅余522 Slice、6 ERAM，仍属于高密度设计，不是资源宽裕。不能把它宣传成所有资源均减少。
Setup/Hold TNS均0，原SDC未放宽；STA coverage95.68%（V4 95.84%），不是100%约束证明。
最差Setup路径在CSI域original_p→目标统计center_x使能；HDMI域WNS+0.190ns。
关键warning仍PHY-5060/PHY-5079（I2C混合时钟、cam24m本地时钟布线），高密度PHY-7022保留。
FIFO稳态溢出、Gray指针物理约束覆盖、实际长期/温度/光照稳定性尚未排除；不因STA通过而宣称已经解决。

资源优化证据：
1. Logo无损ERAM字典独立检查点使综合估算Slice21761→19849，ERAM90→100；全部32768地址/1857588周期逐像素等价，不增加HDMI延迟。
2. 首轮新增功能把运动历史推断为分布式RAM，综合22456（超容量）故未进入P&R/bit；改显式安路双口ERAM后21767/ERAM102。
3. 宽像素负载移除复位、保留valid/同步/配置复位，FF再降91，综合Slice未变；不夸大该独立改动的面积收益。
4. 本轮只有最终r4进行完整P&R/bitgen，未生成中间候选bit；所有综合检查点/失败工程输入及r3原生回归证据保留在build_evidence/attempts。

## 验证

| 范围 | 结果 | 限制 |
|---|---|---|
| 实际ISP旧功能9帧720p |2073600有效拍/1555200打包字逐像素一致，含500px/100mm标定|post-AWB及同步UI为明确测试边界，不替代真实Sensor/板测|
| 实际ISP新增8帧720p |1843200有效拍/1382400打包字逐像素一致；移动/静置/移出、全部文字/帧号/标记|合成数字场景，不是实拍画质收益|
| 原生ERAM/GSR |两组完整ISP均直接使用实际厂商模型，非行为RAM替身|本地TD仿真模型路径和hash随证据记录|
| observer独立 |14帧检查/37679周期：移动、缺失、取消、错误行尾、超时、重现|不能证明现场噪声和光照误报率|
| 按键/CDC/告警 |七模式循环、去抖/长按、K4保存阈值、原子配置、心跳/过期/恢复/字形|实体按键/时钟风险待上板|
| 负载链复位 |701周期/575有效拍；立即有效、行中复位、内联/提前SOF、valid间隙|仅有效拍内容有意义，不要求无效拍RGB复位值|
| 冻结/追溯 |84个实际TD输入；九个队友RTL原git blob；历史bit hash未变|未合并PR，未冒充队友审批|

相同独立参考模型先用于Icarus开发回归，再用于原生ModelSim整机验证；最终候选门禁只采用当前源码+真实ERAM模型的17帧结果。
预览是合成模型输出，见归档frame_4_expected.png/frame_5_expected.png，不是摄像头证据。
具体算法与取舍见[VISION_TRACK_MOTION_V1_DESIGN](VISION_TRACK_MOTION_V1_DESIGN.md)，实板步骤见[BOARD_TEST](VISION_TRACK_MOTION_V1_BOARD_TEST.md)。

## 交付与剩余条件

- Version：VISION_TRACK_MOTION_V1
- Branch：codex/main/vision-track-motion-v1
- 实际TD源码commit：c3bdf9240647d9f98a2ff68c416693ad1e20f4b9
- Tag：vision-track-motion-v1-candidate（归档提交后建立）
- Bit：[camera_to_dsi_display.bit](../artifacts/bitstreams/VISION_TRACK_MOTION_V1/camera_to_dsi_display.bit)
- Bit SHA256：f3dfd9f1ad42bbca95199ac128b9d4808327d4482a1465019ce85a678c0b63a0
- 构建信息：[BUILD_INFO](../artifacts/bitstreams/VISION_TRACK_MOTION_V1/BUILD_INFO.md)，完整资源/时序/失败尝试/原生验证一并归档。
- Git Status：仅显式提交本任务；用户原有GITHUB_REFERENCE_RESEARCH修改及未跟踪录像/机械/原理图资料保留，不宣称全工作区clean。
- Remote：https://github.com/Philid14/anlogic-ph1p35-image-processing.git，Private。
- Push Status / Draft PR：待本地归档提交后发布并记录回执；不合并。
- Board Test Status：NOT_RUN；进阶2/4只能标为“已集成候选，待实板”，不是正式达标。

最小联合验收：先旧V4再新版确认旧模式；SW=0000；红卡移动/消失重现；MOTION静置/移动/停下/移出及灯光变化；记录FRAME、ERR与B/S在5s/30s/120s和30分钟稳态表现。
本轮到此候选为止，等待用户上板，不自行开展下一版。历史V4 bit/tag直接可回滚，SHA2562655fd65ebb245279b684fbdc5f3065dab8f654b387c7c61cfca3bdbadc64f39。
