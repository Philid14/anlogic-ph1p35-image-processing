# INSPECTION_UI_DIMENSION_V1 交付报告

2026-10-30 / MAIN。基于COLOR_COMPARE_V1（1cc0501，PR #17），按用户要求先改颜色显隐与文字，再增加薄工件二维尺寸测量。用户的金属T片、矩形片、角码、合页和塑料件照片用于确定使用边界，不作为FPGA原始RGB或尺寸真值。

## 已完成

- SWITCH第1路（SW0/A4）：统一显示/隐藏两只颜色框与底部全部颜色参数。原RGB均值、九类颜色判定、ABS/L1/MAX、LIM12规则保持。
- 颜色参数和MODE/THRESHOLD/B/S空白字点透明，不再覆盖黑底矩形；字母数字统一为原创等宽5×7字形。保留安路中文位图和Logo ROM、CNT功能。
- 第2路（SW1/B4）：切到尺寸显示；两应用同时开启时尺寸优先，避免面板相互遮挡。关掉两应用即可查看原五模式效果。
- 第3路（SW2/E11）：运行时选深/浅色工件极性；第4路（SW3/D11）：进入/确认两轴尺子标定。标定时先切ORIGIN，第3路选择X/Y，原有K4短按减4像素、长按重复加4像素。正常K3/K4模式/阈值语义不变。
- 使用现有45cm丁字尺的100mm刻度段，两轴分别对齐屏幕端点。未标定只显示PX；确认后显示MM，一位小数是显示分辨率，不是已证实精度。
- 全1280源采样统计工作区内一个薄工件的轴对齐外包宽高；十字线穿过孔/槽时显示GAPX/Y截线间隙。空区、过小/触边轮廓或无效帧显示横线/无有效工件。

## 边界与实际操作

首轮请用薄T形连接片或矩形片，单件平放在纯色哑光对比背景，物体边尽量与画面X/Y平行。木纹、阴影、镜面反光、多个物体会影响分割。尺寸来自原彩色亮度分支，切EDGE/STYLE不会把风格化图像拿去测尺寸。

SIZE W/H不是任意旋转工件的真实长宽；T形片只测整体外包尺寸，不自动分解所有支臂。GAPX/Y不是自动圆拟合：只有圆孔居中、平面正对时才可解释为内径截线；槽孔、缺口、反光也可能形成间隙。完整平圆片的外包W/H可用于外径对照。未实现高度、自动寻孔、多件独立测量或任意CAD参数提取。

3像素连续段、每行8个有效像素的抑噪门槛会忽略非常窄的细节/尖端；整像素边界、4像素标定步进、阈值、尺子对齐、镜头畸变和工件高度均会影响误差。需要实板与独立已知尺寸对照，不能宣称0.1mm准确度。移动物体的结果有一采集帧年龄和原DDR延迟，不是同帧追踪。

详细步骤：[BOARD_TEST](INSPECTION_UI_DIMENSION_V1_BOARD_TEST.md)。模型预览：[颜色显隐](evidence/INSPECTION_UI_DIMENSION_V1/COLOR_ON.png)、[尺寸](evidence/INSPECTION_UI_DIMENSION_V1/DIMENSION_MM.png)、[尺子标定](evidence/INSPECTION_UI_DIMENSION_V1/CALIBRATE_X.png)。这些是合成软件画面，不是实板照片，不是用户工件真实尺寸；Logo/CNT在单独mixer逐周期验证中检查。

## 必要的引脚及时序纠正

详细原理图复核发现K1和K2均上拉1.5V，早期提出的A9/K2被撤销，未生成或烧录bit。最终只增加四个已确认3.3V开关输入，标定复用原有C7/K4。

r1布局通过但Setup -1.276ns、TNS -23.998ns，阻止bitgen；最差路径在原HDMI mixer Logo地址乘加→异步ROM→输出。r2利用已有前一级坐标/DE计算并寄存Logo地址，保持所有外部像素、读使能、同步和输出延迟不变。旧/新mixer逐周期等价通过；没有放宽SDC或改变PLL/视频规格。失败r0（ADC注释语法）、撤销r1和最终r2证据全部保留。

## 验证

| 项目 | 结果及口径 |
|---|---|
| 几何/异常帧 | 160帧、91459周期；独立NumPy模型；四lane、连续段、空区/触边、孔/槽、明暗极性、valid间断、提前/同步SOF、缺行/错误last/多拍、复位PASS |
| 两轴标定/换算 | 两轴确认、上下限、K4短按/长按重复/松开停止、复位；240组像素/mm换算与快照隔离PASS |
| 颜色原规则 | 218组、2398个字段、九类颜色及容差边界PASS；统计RTL和分类函数保持 |
| 透明显隐 | 三帧720p、691200四像素拍，帧内请求不撕裂，OFF/ON/OFF逐像素PASS |
| 最终完整720p | 六帧、1382400四像素拍、1036800个128位打包字；五模式、颜色/尺寸/标定、实际ISP接线与直接流逐项PASS |
| mixer等价 | 1857588周期、1851484有效像素；两完整720p帧及不规则/复位；RGB、DE/HS/VS、读使能逐周期PASS |
| 原功能回归 | K3五模式/K4阈值、200次配置CDC、STYLE五种宽度独立像素回归PASS |
| 源码隔离 | 原Sensor/AWB/BLC、Edge/STYLE算法、MIPI/DDR、PLL/SDC、Logo ROM不变，队友目录未修改；仅mixer Logo地址做等价重定时 |

完整ISP仿真使用显式post-AWB RGB及已同步控制/标定边界，控制RTL另行独立测试；mixer测试位于DDR后的数字边界。不能把这些当作真实Sensor/DDR PHY/HDMI电气或长期实板证明。

复现入口：tests/run_planar_measure_v1.py、tests/run_inspection_ui_v1.py、tests/run_color_compare_formatter.py、tests/run_inspection_stream_v1.py --full、tests/run_mixer_logo_retime.py、tests/run_style_fill_v2_unit.py、scripts/check_inspection_source_scope.py。重新构建应从下列实际源码commit独立检出、生成TD运行配置，不覆盖既有归档或复用旧Runs bit。

## 最终实际布局布线与bit

Synthesis → Physical Design → final Timing Check → bitgen全部完成。最终采用r2原始成功路由，没有进行额外post-route polish；资源以路由报告为准。

| 项目 | 本版 | 相比COLOR_COMPARE_V1 |
|---|---:|---:|
| Slice | 20042 / 21216（94.47%） | +706 |
| LUT6 | 18668 | +564 |
| FF | 18560 / 42432 | +954 |
| ERAM20K | 85 / 108 | +0 |
| DSP | 23 / 40 | +2 |
| Setup WNS / TNS | +0.152ns / 0 | 原版+0.000ns |
| Hold WNS / TNS | +0.020ns / 0 | 原版+0.020ns |

Setup/Hold违例端点0。最差路径现位于CSI域尺寸统计minx的使能逻辑。Slice余量有限，+0.152ns是当前约束下STA通过，不替代温度/供电/长期实板验收。关键warning类型仍为PHY-5060/PHY-5079，无新增类型。保留原FIFO B/S及Gray指针约束覆盖风险，本轮没有宣称修复；若实板S增长，停止尺寸精度验收并先定位视频完整性。

相对COLOR_COMPARE_V1没有新增公共像素流水延迟（仍31拍统一对齐）；没有新帧缓存或额外ERAM。两块新增DSP为定值比例换算的实际TD映射。Logo地址重定时不增加HDMI外部延迟。

- Version：INSPECTION_UI_DIMENSION_V1
- Git Branch：codex/main/inspection-ui-dimension-v1
- 实际TD源码Git Commit：d26a591a399f70259944671956c7a801d9674b6d
- Git Tag：inspection-ui-dimension-v1-candidate，指向归档commit dfbec5818de58925852e06554c1d8fa0c8bf1d31；已push，不移动历史tag。
- Draft PR：[#18](https://github.com/Philid14/anlogic-ph1p35-image-processing/pull/18)，依赖#17→#13→#12；不合并。
- Bit：[camera_to_dsi_display.bit](../artifacts/bitstreams/INSPECTION_UI_DIMENSION_V1/camera_to_dsi_display.bit)
- SHA-256：`2003bbcc9f205b488ba566d7606e16416335b28dec738810827e296d62b62adc`
- 构建信息：[BUILD_INFO](../artifacts/bitstreams/INSPECTION_UI_DIMENSION_V1/BUILD_INFO.md)及JSON；完整资源/时序、源码清单和各轮验证在同目录build_evidence。
- Remote：Private origin https://github.com/Philid14/anlogic-ph1p35-image-processing.git
- 源码、bit归档、分支与candidate tag已实际push；远程引用和tag内bit的SHA256已核对，见[evidence/REMOTE_RECEIPT](evidence/INSPECTION_UI_DIMENSION_V1/REMOTE_RECEIPT.json)。
- Git Status：本轮内容独立提交；原docs/GITHUB_REFERENCE_RESEARCH.md修改与用户未跟踪资料保留，不混入提交。
- Board Test Status：**NOT_RUN**。候选等待用户上板；本轮不自行进入下一版。
