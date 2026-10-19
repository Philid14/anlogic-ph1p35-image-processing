# EDGE_STYLE_FILL_V1 交付报告

## 结论与实际功能

完成一个可独立切换的 **STYLE：局部同色区域均值填色 + 64色块化 + RGB边界描黑**。
这符合本轮允许的有界区域风格化路线；**不是全物体分割、闭合轮廓灌色或洞填充**。
新效果覆盖区域内部，不只是白色Edge；也不只是给BINARY换色。
三通道RGB决定局部资格，均值抑制小扰动、粗调色板统一色块、强颜色跨度输出黑边。
具体数学定义、路线比较、因果位置和失败边界见 [DESIGN](EDGE_STYLE_FILL_V1_DESIGN.md)。

## 版本与依赖

- Role：MAIN；人类授权为本轮EDGE_STYLE_FILL_V1附件。
- Baseline：`edge-multi-mode-v1-candidate` → `ed5526930247dccded1bc01f089419f793f4f0b8`。
- 四模式实际TD源码：`4ea67f194941c6717fc1d28889c687a4fb78533f`；用户反馈整体可接受。
- 新分支：`codex/main/edge-style-fill-v1`；**实际TD输入源码commit：`042345cb0e92a1cc5ea0a74fed1be352cf338f2c`**。
- Candidate tag：`edge-style-fill-v1-candidate`，归档commit由该tag唯一解析，不混同源码commit。
- 新Draft PR以`codex/main/edge-multi-mode-v1`为base，依赖未合并#11→#10→#6→#4→#3；不推main、不自动合并。
- 推送与Draft PR地址见本报告末尾交付状态；只有实际成功才填已上传。

## 软件与RTL验证

1. 独立NumPy模型和可视化：`scripts/research_style_fill_v1.py`，
   [比较图](edge_style_fill_v1_evidence/scenes.png)、[统计](edge_style_fill_v1_evidence/model_results.json)。
   图从左到右为RGB、仅调色板、最终STYLE；均为合成数据，不能代替真实画质。
2. 实心/空心矩形、实心/空心圆、缺口、开放线、多目标、嵌套、边界、小目标、
   低对比噪声均经过模型与RTL逐像素对照。常量2×2内部填色错误为0；
   单点扰动仅影响其4个邻域输出，没有扫描线传播。缺一个右交点的奇偶扫描线反例
   会改变行尾33点，其中32点在物体右侧，因此未选择无约束奇偶填充。
3. 单元回归：5种尺寸，每尺寸34组图像/序列；
   宽4/8/68/128/1280，包含valid间隙、行bank交替、提前/同拍SOF、
   未完成帧后复位、0/255与16/64量化边界、移动/消失、未知RAM启动。
   总计738752个有效像素逐像素通过。
4. GRAY/BINARY旧公式9288像素边界/随机回归通过；K3五模式循环、K4
   短/长按、独立阈值端点、STYLE忽略K4、19位CDC整包/忙合并/复位通过。
5. 小尺寸11帧混合模式：5632有效96位拍、3872打包字通过，覆盖帧内请求改变。
   既有packer遇行中valid气泡会重置部分字；此测试按其原语义检查，未改变该硬件。
6. **完整1280×720×5帧**：STYLE→EDGE→ORIGIN→GRAY→BINARY，
   **1152000个有效96位拍、864000个128位字**逐字节通过。
   真实`isp_top`在AWB边界强制输入，与独立模块+packer逐拍对照；
   MODE/THRESHOLD/B:S的字形像素、valid/user/last、提前SOF均比较。
   EDGE在STYLE显示期间继续处理，其下一帧历史输出与独立原模型一致。
7. 冻结审计：59个原TD输入逐文件一致；
   仅6个模式集成输入改变、增加1个STYLE源文件，共66个TD输入。
   TD syn/phy选项与四模式归档完全一致；Sensor、BLC/AWB/Demosaic、
   Gaussian/Sobel/NMS/四跳/Temporal、DDR/HDMI、Logo/CNT、IP、引脚和SDC不变。

本轮没有用手机拍摄的EDGE图充当RGB，没有声称已取得真实STYLE画质验收。

## 实际构建、资源与时序

完整Synthesis → Physical Design → final Timing Check → bitgen通过。
原始日志、源码/约束SHA、TD选项、最终STA、忽略约束、路由资源、历史bit校验均随归档保存。

| 资源 | 新版本 / 设备总量 | 相对EDGE_MULTI_MODE_V1 |
|---|---:|---:|
| LUT6 | 16592 / 21216 | -350 |
| FF | 16972 / 42432 | +1163 |
| Slice | 17792 / 21216 | -527 |
| ERAM20K | 85 / 108 | +10 |
| DSP | 21 / 40 | +0 |

Slice占用 **83.86%**。
Setup WNS **+0.104ns**，Hold WNS **+0.020ns**；
Setup/Hold TNS均0，违例端点均0；STA覆盖 **95.99%**。
关键warning类型 ['PHY-5060', 'PHY-5079']，新增关键类型 []。
关键路径与RAM映射详细复核见本报告附录以及原始报告；不把“无新增类型”当成既有风险消失。

新STYLE局部流水5拍，复用ORIGIN第22拍输入，最终仍为27拍分支窗口；
OSD2拍、打包1拍，总窗口30拍，**相对四模式增加0拍端到端算法流水**。
一拍处理4个原始RGB像素，不降采样、不新增整帧等待/反压/气泡；
两行交替缓存不承担图像历史功能，无跨帧历史混色。
2×2描边为因果锚定，右/下最多1px局部扩展，不叠加旧EDGE的x−14/y−7移位。
实际帧率/显示延迟仍由原Sensor/DDR/HDMI决定，未把仿真时钟冒充实测帧率。

## 效果边界与演示

优先演示彩色几何图/日常物体、纸张边缘、多个分离目标与运动移出。
空心轮廓不会自动补洞；开放线不会定义全局内部，缺口不会触发远处传播。
同色相接物体不能分成独立对象；低对比边界可能不描黑；小目标可能被黑边占据。
渐变会色带化，高增益纹理可能描黑，量化门限仍会闪烁；本轮不是新的时间稳定算法。
无历史状态意味着消失后没有算法性跨帧残留，但原DDR显示延迟依然存在。

K3：`EDGE→ORIGIN→GRAY→BINARY→STYLE→EDGE`。
K4仅EDGE/BINARY短−10、长+10、独立保存；STYLE阈值数字留空。
按 [BOARD_TEST](EDGE_STYLE_FILL_V1_BOARD_TEST.md) 检查正常效果、限制和失败判定，
特别比较是否出现远处填充、4像素周期接缝、行错位、运动后残留、模式/OSD不一致。

## FIFO/CDC与系统风险

原B/S计数与OSD保留。仿真证明新分支不增加有效拍/打包字，不证明实板FIFO绝不溢出。
既有write-full历史sticky及Gray指针max-delay被全局异步组覆盖的缺口未修复；
STA通过不等同于电气链路/长期运行通过。若S在稳态增长，应阻断正式验收，
优先保存触发条件并查FIFO/DDR，不用视觉效果掩盖。新模式30分钟、光照变化、
HDMI连续、Logo/CNT与B/S均待实板，不能填写为已排除。

## 构建复核附录

最差Setup路径仍在HDMI mixer：`u_hdmi_mixer/mult0_syn_59.clk` →
`u_hdmi_mixer/O_hdmi_data_reg[9]_syn_2.ib`，+0.104ns；
MIPI处理域的时钟组Setup WNS为+3.542ns。没有改变PLL/SDC，
HDMI全局裕量仍较小，必须做长期实板验收，不称为充分宽裕。

STYLE在路由面积表中为449 LUT6、888 FF、10 ERAM、0 DSP；
综合表为476 LUT6、869 FF、10 ERAM。全设计净LUT/Slice下降包含TD
重新优化/打包的影响，不能宣称新算法没有资源成本，也不能保证后续构建重复相同净下降。
两个320×96行bank各分为5个20位ERAM，逻辑容量61440bit，存在宽深度映射开销。
实际门级导出确认DP20K、20bit端口、A端READBEFOREWRITE、B端NORMAL；
源码选择上一行bank读，写另一个bank，因此不依赖选中bank的同址读写结果。
这是配置核对，不是门级/SDF仿真；见归档`RAM_MAPPING.json`。

与四模式比较，所有warning代码计数完全一致，新STYLE源文件无warning。
PHY-5060的O_cam_24m混合扇出上下文随重新映射变化，仍为既有风险；
PHY-5079本地时钟路由警告仍在。原始日志和`BUILD_REVIEW.json`均保留。
STA覆盖从96.16%变为95.99%，未宣称100%覆盖；Gray的14.700/13.033ns
max-delay各18条仍全部被忽略。本轮不修改全局异步组，未排除该CDC风险。

## Bit与回滚

- [候选bit](../artifacts/bitstreams/EDGE_STYLE_FILL_V1/camera_to_dsi_display.bit)
- SHA-256：`B4FBB61FABD6A510B26EEC6DAD4D950FF8A3D2B6F561753D5611B334274B336E`；1789539 bytes。
- [BUILD_INFO](../artifacts/bitstreams/EDGE_STYLE_FILL_V1/BUILD_INFO.md)
- [构建与验证证据](../artifacts/bitstreams/EDGE_STYLE_FILL_V1/build_evidence/FINAL_CHECKS.json)
- 回滚：`artifacts/bitstreams/EDGE_MULTI_MODE_V1/camera_to_dsi_display.bit`，
  SHA `8C62195DA8A2F8748CE9D6CFD7D9703BCB81E6F6CDA09AEDF4BBB0DE0FE0BBE9`。
- Board Test：**等待用户上板**。到candidate为止，不自动合并，不进入下一功能。

## Git交付状态

- 归档/candidate commit：`e17a1af3e8e53b3e704f069db178d4b93f2a04cf`。
- Draft PR：[ #12 ](https://github.com/Philid14/anlogic-ph1p35-image-processing/pull/12)，base为四模式分支，未合并；创建后GitHub报告mergeable=true、clean。
- Remote：`origin` → `https://github.com/Philid14/anlogic-ph1p35-image-processing.git`。
- 分支与candidate tag均已实际push成功，远程tag剥离后指向上述归档commit。
- 实际TD输入仍为`042345cb0e92a1cc5ea0a74fed1be352cf338f2c`；本次PR状态补充只改文档，不重建bit、不移动tag。
- 预推送检查通过：61个任务相关变更，无队友目录、视频、未跟踪参考资料或Runs临时库；文件大小与凭据模式扫描通过；66项构建输入/bit SHA/历史bit一致。
- Git跟踪文件在提交后干净；用户已有未跟踪原理图、参考目录和录像保留。等待Philid14对最新文档tip与candidate审查及上板反馈。
