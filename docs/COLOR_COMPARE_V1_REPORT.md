# COLOR_COMPARE_V1 交付报告

2026-10-28 / MAIN。本轮按用户明确指令停止旧集成版黑屏修复，从已正常上板的EDGE_STYLE_FILL_V2构建固定平台双区域颜色比对应用。未继承TARGET事务缓存、启动面板或101页采样资源。

## 已实现

- 原ORIGIN、GRAY、BINARY、EDGE、STYLE五模式及K3/K4语义保留。
- 左REF绿色框x256..383、右TEST青色框x896..1023，均y256..383。每区128×128，物品完全覆盖框内部；统计取自同一完整post-AWB彩色帧，位于灰度/边缘/STYLE之前。
- 实时RGB均值、九类粗颜色名称、逐通道ABS差、L1和MAX差值；MAX≤12显示MATCH，否则DIFF。12为本版演示容差，与EDGE/BINARY阈值无关。
- LAST标明前一完成采样帧，两个ROI是同一帧；启动/无效测量显示WAIT，不控制原有视频读写使能。新增公共像素流水两拍，数据/config/valid/提前SOF/last同时对齐。
- 没有增加帧缓存、ERAM、DSP或时钟域；不修改Sensor/BLC/AWB、曝光、增益、MIPI、DDR、HDMI、PLL、引脚及SDC，不改队友目录。

## 功能证据

- NumPy独立patch统计与OSD模型，80帧统计用例、4464次检查，包括纯色/噪声、四lane求和、最后拍、提前/同步SOF、valid间断、缺行/多拍/错误last、中途复位。
- 218组格式/颜色/极值/容差边界快照，2398个十进制字段检查；转换期间输入变化不会混入已锁存字段。
- 完整1280×720五模式：1152000个有效四像素拍（4608000像素）、864000个128位打包字逐项对比通过，直接流与生产ISP集成路径一起验证。比较关闭的小尺寸旧版、按键、200次配置CDC、灰度二值RGB和STYLE独立回归通过。
- 主完整回归使用**未改写的实际生产RTL**。Demosaic/AWB在此边界测试中是显式替身；不能把它当作真实Sensor/PHY/DDR/HDMI或长期实板验证。
- 可选ModelSim加速尝试有编译器前向声明限制，后续重复仿真在原始Icarus已经PASS后终止；其日志保留但不计为PASS。生产Edge RTL没有因此修改。
- 数值预览：[SOFTWARE_PREVIEW.png](evidence/COLOR_COMPARE_V1/SOFTWARE_PREVIEW.png)仅为合成哑光色块软件画面，不是实板照片或采集RGB证据。

## 实际TD结果

完整Synthesis→Physical Design→final Timing Check→bitgen完成。原生布局后优化再尝试一次，未提高Setup，未选用；最终bit来自首个通过STA的原路由数据库。源码和约束未调整。

| 项目 | 本版 | 相比STYLE_V2 |
|---|---:|---:|
| Slice | 19336 / 21216（91.14%） | +1196 |
| LUT6 | 18104 / 21216 | +934 |
| FF | 17606 / 42432 | +792 |
| ERAM20K | 85 / 108 | +0 |
| DSP | 21 / 40 | +0 |
| Setup WNS / TNS | +0.000ns / 0 | 裕量很紧 |
| Hold WNS / TNS | +0.020ns / 0 | 通过 |

Setup/Hold违例数为0；STA通过**不等于时序裕量充足或已上板稳定**。新增关键warning类型无；仍有旧PHY-5060/PHY-5079，原始上下文保留。继承的FIFO sticky/Gray指针约束覆盖风险没有在本轮修复，需实板长时间与光照变化测试。

## 归档与版本

- Version：COLOR_COMPARE_V1
- Branch：codex/main/color-compare-v1
- 实际TD输入源码commit：06e70a0d5d1676ed7991c475facd533b2b804aad
- Bit：[camera_to_dsi_display.bit](../artifacts/bitstreams/COLOR_COMPARE_V1/camera_to_dsi_display.bit)
- SHA256：`b3dd03799924184d73bbd805caaa57c245a498030376d24ca75205ce06e91d27`
- Build info：[BUILD_INFO.md](../artifacts/bitstreams/COLOR_COMPARE_V1/BUILD_INFO.md)，包含源码清单、工具流程/原始资源/时序、SYN及route数据库SHA、验证证据及历史bit不变清单。
- Candidate tag：color-compare-v1-candidate，待归档提交审查后创建；PR/实际push状态另记，不移动旧tag。
- Board Test Status：**NOT_RUN**，用户负责真实验收。

## 上板与使用限制

按[BOARD_TEST](COLOR_COMPARE_V1_BOARD_TEST.md)烧录后K3一次进入ORIGIN；标准色卡覆盖左绿框，待测物覆盖右青框。先用同色均匀哑光纸检查左右照明，再比较近色/异色并交换两侧，拍清四行结果；随后遍历五模式和30分钟稳定性。

本版是相机RGB相对比较，非CIE Lab/ΔE或校准色差仪。粗颜色类别不等同于材质/精细颜色识别。框内背景、反光、饱和、左右照明差、镜头阴影和AWB均会影响结果；MATCH不是物品存在或工业合格结论。没有自动分割物体，需操作时填满取样框。

下一步先等待本候选真实上板反馈，再决定光源/颜色标定与容差设定。本轮不做二维尺寸、目标跟踪或下一版算法，不自动合并PR。旧STYLE_V2归档bit可直接回滚，SHA已核对未变。
