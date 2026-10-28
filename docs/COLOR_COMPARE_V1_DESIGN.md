# COLOR_COMPARE_V1：固定平台双区颜色比对

Role MAIN；用户2026-10-28明确停止STYLE_V2_TARGET黑屏修复，要求从已正常上板的EDGE_STYLE_FILL_V2推进最终作品的颜色比对功能。本轮不继续TARGET缓存/启动诊断，也不实现尺寸测量。

## 基线与范围

- 精确基线：edge-style-fill-v2-candidate，实际原构建源码694559fd76676093e134229d435161ecb44ab00c；原bit SHA256 CFB7435648ED50310F053AFE138702F2094B0061B6A7DD68B3B064B6B3D88F51。
- 新分支codex/main/color-compare-v1；本轮人类指令优先于协议默认从main建分支；Draft PR以STYLE_V2分支为依赖，不自动合并。
- 参考用户本地说明“最终作品实现/关于最终作品实现.txt”：固定高度俯视、遮光框架、受控内置光源，一侧标准色卡、一侧待测物。该本地文件不作为修改Sensor/ISP或开发测尺寸的授权。
- 保留ORIGIN/GRAY/BINARY/EDGE/STYLE、EDGE_TEMPORAL、K3/K4、安路Logo/CNT、原MODE/THRESHOLD/B/S、RAW10/BLC15/AWB、曝光1990、VTS1000/HTS1600、15.75×模拟增益，以及原MIPI/DDR/HDMI/PLL/SDC。
- 不修改features/color_target或features/latency_view。新增的是MAIN固定区域测量应用，不复制队友的目标跟踪/框检测工程。

## 画面与参数

1280×720坐标，左上原点：REF绿色外框，内部x256..383、y256..383；TEST青色外框，内部x896..1023、y256..383。每区128×128=16384像素，四lane全部累加，不下采样。物体应完全覆盖对应框的内部，边框绘制在取样区外。

从AWB输出、灰度/边缘/STYLE之前并接统计；五种显示模式下都测同一真实彩色输入。每区RGB各22位和、15位计数；均值采用四舍五入(sum+8192)>>14。除法是定值移位，不用整帧缓存、通用除法器或新DSP。

屏幕底部x32..1247、y544..671共四行：

```
REF  R:nnn G:nnn B:nnn C:GREEN
TEST R:nnn G:nnn B:nnn C:GREEN
ABS  R:nnn G:nnn B:nnn
L1:nnn MAX:nnn LIM:012 MATCH LAST:hhhh
```

ABS为TEST与REF各通道绝对差；L1为三差之和0..765；MAX为最大通道差0..255。MATCH仅表示三个相机RGB通道差均≤12，否则DIFF。12为本版演示容差，需用户真实材料/光源验证，不等同于行业验收容差；不挪用K4改变已有阈值语义。

九类粗颜色名称：BLACK、WHITE、GRAY、RED、GREEN、BLUE、YELLOW、CYAN、MAGENTA。max<32为BLACK；max-min≤24时min≥224为WHITE否则GRAY；其余按RGB色相的主/次通道分类。它不区分材质、肤色、棕色等精细色名。

这些指标是经过现有ISP的相机RGB码值差，**不是CIE Lab/ΔE或校准色差仪的测量**；饱和、光照不均、反光、AWB、暗噪声及曲面均会影响结果。不能恢复被剪裁的高光。标准色卡提供同画面参照，不能自动获得其印刷标称色度。

## 帧、无效数据与延迟

统计由提前SOF重新开始，valid驱动坐标，不将SOF当成首个像素。支持SOF提前与SOF伴随首有效拍、行内valid间断；验证每行last、总230400拍、两个ROI完整计数及帧终点。缺行/多拍/异常last/复位导致该次测量无效，但**绝不控制视频读写使能或阻止画面显示**。

完整帧结果在下一输入SOF发布；经过原27拍算法对齐后，在比较OSD的SOF锁存同一组结果。LAST是最近完成的统计帧16位循环编号，明确是前一完整采样帧，不能当作DDR读出帧身份或延迟测量。两个ROI来自同一帧；无效时显示WAIT FOR FULL FRAME，不把无效数值当成有效比对。

比较OSD新增两拍（约33.34ns@60MHz标称CSI时钟），valid/user/last/config一起延迟；所有原算法分支延迟仍一致。用一份原字库查询覆盖四个像素，十进制由共享逐位转换器在帧前段完成，底部面板出现前已完成。原状态OSD在其后保持优先级，Logo/CNT仍由原HDMI mixer输出。

编译参数COLOR_COMPARE_ENABLE默认0，可精确回退原算法链路；本候选顶层仅把该参数设为1。未增加时钟域、CDC邮箱或帧缓存。历史FIFO sticky和Gray约束覆盖局限继承STYLE_V2，不能宣称已修复；需真实长时间、光照变化及模式切换上板验收。

## 验证与构建门槛

- 独立NumPy均值、颜色、绝对差/距离和OSD模型；80帧小尺寸统计，含纯色、噪声、末尾像素、提前/同步SOF、间断valid、缺行、多拍、错误last、中途复位。
- 原五模式/K3/K4/配置CDC/灰度二值/STYLE及打包回归；完整720p五帧、1152000有效四像素拍、864000个128位字逐像素/逐字比较。显式Demosaic/AWB测试替身仅提供已知post-AWB输入，不冒充真实Sensor/PHY/DDR实板验证。
- 68个直接TD输入中原66个的63个提交内容不变（允许Windows检出换行差异），另三个只做接线/使能；IP、Sensor、MIPI、DDR、HDMI及约束冻结；原字库不改。
- 所有实际TD输入必须先commit。SYN、place/route、最终STA通过后才允许bitgen，禁止旧Runs bit充当新版本；归档完整源码清单、资源、时序、SHA256和上板状态。

实际结果、资源和bit以交付报告及BUILD_INFO为准，本设计说明不代表已上板。
