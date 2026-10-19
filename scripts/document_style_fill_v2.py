"""Write V2 delivery evidence from a passing routed archive and model results."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'artifacts/bitstreams/EDGE_STYLE_FILL_V2'
def main():
    ev=DEST/'build_evidence'
    c=json.loads((ev/'FINAL_CHECKS.json').read_text())
    review=json.loads((ev/'BUILD_REVIEW.json').read_text())
    rtl=json.loads((ev/'rtl_results.json').read_text())
    units=json.loads((ev/'unit_results.json').read_text())
    m=json.loads((ROOT/'docs/edge_style_fill_v2_evidence/model_results.json').read_text())
    full=next(x for x in rtl['streams'] if x['full'])
    assert c['candidate_eligible'] and c['timing_passed']
    assert full['beats']==1152000 and full['packed_words']==864000
    labels=dict(lut='LUT6',ff='FF',slice='Slice',eram='ERAM20K',dsp='DSP')
    base=dict(lut=16592,ff=16972,slice=17792,eram=85,dsp=21)
    total=dict(lut=21216,ff=42432,slice=21216,eram=108,dsp=40)
    resource='\n'.join(f'| {labels[k]} | {c[k]} / {total[k]} | {c[k]-base[k]:+d} |' for k in labels)
    metric=lambda case,method,key:m[case][method][key]
    p=review['critical_setup_path']
    report=f'''# EDGE_STYLE_FILL_V2：实板问题归因与候选交付

## 结论

已形成仅优化STYLE分支的V2候选，保留五模式系统与5拍局部流水。
修正V1**独立RGB粗量化放大小色差**及**2×2极差描黑吞亮细线**两种可复现机制。
实际采用：保守同色均值、9档共享明度/低色度中性保护、一致亮度梯度的暗侧描边。
**尚未完成V2上板画质验收**；不能把模型结果称为现场改善率。

## 1. 实板问题的原因与证据等级

| 现象 | 已有事实/实验 | 尚待证实 |
|---|---|---|
| 白灰底绿青斑 | 用户反馈与[V1拍屏](edge_style_fill_v2_evidence/v1_board_photo.jpg)可见；常量(191,192,191)经V1变(170,255,170)，经V2变(192,192,192)，无须缓存故障即可复现 | 实际输入色差的Sensor/AWB/照明/打印/手机占比未知 |
| 细线/星中心/小字损失 | V1将亮线周围高极差窗口全部描黑；数字星和亮细线可复现 | 实际印刷、失焦、采样先前已丢失的细节不能恢复 |
| 纹理过度描黑 | V1不区分亮度/色度或边界极性，等亮度色扰动也可触发；新模型隔离验证 | 强亮度噪声仍可能描黑，实际误检率待实板 |
| 彩块偏色 | 通道独立台阶会改变混合颜色，纯绿(0,128,0)也被V1抬到(0,170,0)；V2保留(0,128,0) | 缺同场景摄像头ORIGIN，无法校准实际颜色/打印色域 |
| 高光白化 | V1把输入192..255合为255；V2对此区间保留192/224/255三个档 | 原始255已经截断的信息无法恢复 |

重点RGB核对：AWB的R/G/B分别为每24位高/中/低8位，`awb.v`第295..310行及
STYLE输出顺序一致；原色像素与lane回归通过，未发现STYLE内通道交换。
这不等于已经验证Sensor Bayer顺序、前级色彩校准、打印或显示器颜色准确。
原四模式与前级65个TD输入不变；本轮不改变Sensor/曝光/增益、BLC/AWB/Demosaic。

用户提供的是STYLE拍屏和数字测试卡，**没有摄像头ORIGIN帧**。
[数字卡](edge_style_fill_v2_evidence/digital_test_chart.png)可作数字算法输入；
拍屏仅作定性问题证据，未把其RGB当作FPGA输入。
压力模型为`0.76×RGB+[0,2,-1]+N(0,2)`（seed132），是显式边界测试，
不是拟合现场参数或证明现场贡献率。

## 2. 实际算法与选择理由

1. 四点RGB高4位均相同才平均；其他点保留当前像素。比V1更少混合细节，未增加大范围模糊。
2. 局部亮度两侧差达到48才考虑描边，只把当前暗侧像素描黑；色噪声不直接作黑边。
3. RGB最小/最大值给出共同明度L，以32为档距四舍五入（末档255）。
   对RGB施加同一`Q−L`偏移，避免三个通道各自跳档。
4. 色度≤12的近中性基色输出相同RGB，抑制白灰底低色度杂斑；其余保留未截断通道差。

完整方程与五级硬件结构见[DESIGN](EDGE_STYLE_FILL_V2_DESIGN.md)。
比较了V1、8级RGB+旧描边、共享明度+旧描边、完整V2。
单独增加RGB级数仍会形成独立跨阈值彩斑，旧描边仍吞亮线；
只换调色板也没有修复细线侵蚀，因此选择协调的色彩/轮廓渲染策略。
没有新增高斯、中值、时域滤波、全帧缓存或自适应ISP。

## 3. V1/V2客观模型对照

| 受控测试与指标 | V1 | V2 |
|---|---:|---:|
| 192附近中性噪声区域：彩斑比例 | {100*metric('gray_threshold','V1','neutral_colored_fraction'):.2f}% | {100*metric('gray_threshold','V2','neutral_colored_fraction'):.2f}% |
| 同场景：RGB平均绝对误差 | {metric('gray_threshold','V1','rgb_mae'):.3f} | {metric('gray_threshold','V2','rgb_mae'):.3f} |
| 0..255灰度渐变：平均绝对误差 | {metric('gray_ramp','V1','rgb_mae'):.3f} | {metric('gray_ramp','V2','rgb_mae'):.3f} |
| 数字西门子星：黑白结构错分率 | {100*metric('siemens_star','V1','binary_mismatch_fraction'):.3f}% | {100*metric('siemens_star','V2','binary_mismatch_fraction'):.3f}% |
| 数字亮细线：黑白结构错分率 | {100*metric('thin_bright','V1','binary_mismatch_fraction'):.3f}% | {100*metric('thin_bright','V2','binary_mismatch_fraction'):.3f}% |
| 无黑像素的等亮度色扰动：输出黑像素率 | {100*metric('chroma_texture','V1','black_fraction'):.3f}% | {100*metric('chroma_texture','V2','black_fraction'):.3f}% |
| 输入192..255的高光输出档数 | {len(m['highlight_levels']['V1'])} | {len(m['highlight_levels']['V2'])} |

8级独立RGB候选在同一中性门限样本的彩斑比例仍为
{100*metric('gray_threshold','RGB8_old_ink','neutral_colored_fraction'):.2f}%，未选用。
共享明度但旧描边的星结构错分率仍为
{100*metric('siemens_star','joint_old_ink','binary_mismatch_fraction'):.3f}%，也未选用。
均匀246附近的白色两版都可能白化，不能声称所有白色样本改善。
V2对12416个随机纯黑白像素恒等保留；这证明数字亮线不被描黑侵蚀，
不是已经恢复实际摄像头缺失的高频细节。
彩色几何仍有{m['motion']['geometry_ink_pixels']}个描边点，灰度仍有9档：
新模式保留STYLE特点，没有通过取消描边/分层退回ORIGIN。

- [数字测试卡原输入 / V1 / V2](edge_style_fill_v2_evidence/digital_chart.png)
- [受控偏色噪声输入 / V1 / V2](edge_style_fill_v2_evidence/modeled_cast_noise.png)
- [全部场景与四候选对照](edge_style_fill_v2_evidence/comparison.png)
- [完整指标与反例](edge_style_fill_v2_evidence/model_results.json)

这些图均为软件模型结果，**不是V2实板照片**。

## 4. 细节、颜色与运动代价

- 浅淡色度≤12的颜色会去饱和；这是固定STYLE策略，不是AWB。
- 明度9档仍有色带及门限附近亮度闪烁；等亮度异色边界不保证描黑。
- 低对比小字仍可能被分级/局部均值弱化，失焦、欠采样、输入过曝不可恢复。
- V2更接近输入明度；前级偏暗的纸白可能呈灰色，不在STYLE中自动抬曝光。
- 没有帧历史，慢移/快速消失的独立模型无残留；同帧邻域仍可能有1px局部形态变化。
- DDR原延迟保留，未把仿真无残留等同于真实显示无延迟。

## 5. RTL与数据完整性验证

独立NumPy参考，不读取RTL中间值。5种宽度（4/8/68/128/1280），
每种{units[0]['frames']}组图像/序列逐像素对照，包含几何/星/细线/不同字号/
复杂彩纹、色度12/13、梯度95/96、灰阶/饱和/有符号偏移边界、
未知RAM启动、复位、未完成帧后复位、提前/同拍SOF、valid间隙。
GRAY/BINARY原公式、K3/K4五模式、19位CDC/复位、11帧混合流均通过。
完整720p×5帧 **{full['beats']}个96位有效拍 / {full['packed_words']}个128位字**
逐字节通过，包含实际`isp_top`的AWB后边界、OSD和旧EDGE历史连续。
65个冻结TD输入及TD选项与V1相同；**正式RTL仅修改`isp/style_fill_96.v`**。
原图、阈值、OSD/Logo/CNT/B:S、视频接口、时钟约束未改。
局部仍5拍，对齐27拍、OSD2拍、打包1拍；新增端到端流水0拍。
没有新增视频气泡、反压或分辨率降低。物理MIPI/DDR/HDMI电气链路不在仿真内。

## 6. 完整TD、实际资源与时序

实际TD源码commit：`{c['source_commit']}`。完整Synthesis→Physical Design→
final Timing Check→bitgen通过；源清单、选项、原始日志、路由报告与全部历史bit校验已归档。

| 资源 | V2 / 总量 | 相对V1 |
|---|---:|---:|
{resource}

Slice占用{100*c['slice']/21216:.2f}%；Setup WNS **{c['setup_wns_ns']:+.3f}ns**，
Hold WNS **{c['hold_wns_ns']:+.3f}ns**；TNS均0、违例端点均0。
STA覆盖{c['sta_coverage']}；V1为95.99%，不宣称全部路径100%覆盖。
最差Setup：`{p['Begin Point']}` → `{p['End Point']}`。
新增关键warning类型：{c['new_critical_warning_types']}；所有代码计数增量：{review['warning_count_delta']}。
STYLE本身告警：{review['new_style_warning_contexts']}。
新增上下文与既有风险原文见`BUILD_REVIEW.json`，不隐藏既有PHY/CDC警告。
普通warning增量为HDL-5001命名提示+1、PHY-5088+2记录；后者在place/route各出现一次。
`analyze_clock -detail`定位跨区缓存为既有I²C SCL时钟缓存
`u_uicfgcs500/u_i2c/scl_clk_created_gclkinst`（驱动TOP、缓存BOTTOM），
详细原文保存在`clock_review.log`。I²C/时钟源码不变，但该物理风险仍需至少3次冷启动检查，
未通过则暂停验收；没有修改PLL/SDC掩盖它。HDL-5001是匿名实例/网未重命名提示，
本次没有新增STYLE源文件的锁存器、端口宽度或未驱动告警。
局部模块路由面积行：

```text
{review['style_routed_area_row']}
```

两bank行RAM仍为10 ERAM（5+5），逻辑61440bit；DP20K配置导出核对通过。
这不是门级/SDF仿真。全设计净面积差还包含TD重新映射/打包影响。

## 7. 上板、未解决问题与下一阶段边界

按[BOARD_TEST](EDGE_STYLE_FILL_V2_BOARD_TEST.md)，固定同一卡片/灯光/机位，
锁定手机曝光白平衡，记录ORIGIN/V1/V2静态和移动/消失短片。
优先检查白灰底彩斑、星中心/文字、彩块、明度分层与暗侧轮廓。
B/S和30分钟、光照变化、五模式/Logo/CNT/HDMI仍待用户验收。
历史FIFO溢出与Gray max-delay各18条被忽略的缺口未修复；S稳态增长阻断正式验收。

需要后续ISP阶段处理/研究：真实白平衡偏移、输入动态范围/过曝、传感器高增益噪声、
颜色矩阵/色彩校准与照明影响；对焦、打印和显示器也需分开确认。
本轮只记录这些边界，没有提前开发自动调节，也没有修改队友目标检测工程。

## 8. Bit与Git

- Version：EDGE_STYLE_FILL_V2；MAIN；branch `codex/main/edge-style-fill-v2`。
- [候选bit](../artifacts/bitstreams/EDGE_STYLE_FILL_V2/camera_to_dsi_display.bit)，{c['bit_size']} bytes。
- SHA256：`{c['bit_sha256']}`。
- [BUILD_INFO](../artifacts/bitstreams/EDGE_STYLE_FILL_V2/BUILD_INFO.md)，
  candidate tag `edge-style-fill-v2-candidate`，归档commit由tag唯一解析。
- 新Draft PR以STYLE_V1为base，依赖#12及其既有链，不自动合并。
- Remote/push/PR实际结果在交付状态附记中填写；Board Test：**待用户上板**。
- V1回滚SHA `B4FBB61FABD6A510B26EEC6DAD4D950FF8A3D2B6F561753D5611B334274B336E`，历史源/bit/tag完整保留。
- 完成候选即停止，不进入进阶五或其他功能。
'''
    (ROOT/'docs/EDGE_STYLE_FILL_V2_REPORT.md').write_text(report,encoding='utf-8')
    log=ROOT/'docs/IMAGE_TUNING_LOG.md'
    if '## EDGE_STYLE_FILL_V2 candidate' not in log.read_text(encoding='utf-8'):
        with log.open('a',encoding='utf-8')as f:
            f.write(f'''
## EDGE_STYLE_FILL_V2 candidate（2026-10-19，MAIN）

- 基线：V1/e17a1af，用户已上板，功能基本正常但有绿青斑/细线与星中心损失/过描黑/偏色/高光白化；本轮拍屏和数字卡证据见EDGE_STYLE_FILL_V2_DESIGN.md，无摄像头ORIGIN帧。
- Git：codex/main/edge-style-fill-v2；实际TD源码`{c['source_commit']}`；tag edge-style-fill-v2-candidate；Draft PR依赖STYLE_V1/#12，不合并。
- 唯一主要变量：STYLE渲染策略；V1独立4级RGB+极差黑边→V2保守均值+9档共享明度/中性保护+亮度暗侧描边。仅1个RTL文件变化，其余65个TD输入不变；原四模式/ISP/Sensor/按键/OSD/视频/PLL/SDC冻结。新增流水0拍、ERAM增量{c['eram']-85:+d}。
- Bit：artifacts/bitstreams/EDGE_STYLE_FILL_V2/camera_to_dsi_display.bit；SHA `{c['bit_sha256']}`。
- Build：完整TD PASS；LUT{c['lut']} / FF{c['ff']} / Slice{c['slice']} / ERAM{c['eram']} / DSP{c['dsp']}；Setup/Hold {c['setup_wns_ns']:+.3f}/{c['hold_wns_ns']:+.3f}ns；TNS0、违例0。
- 模型/RTL：中性门限彩斑47.31%→0，数字星/亮线结构误差→0；这些不是实板改善率。5尺寸×{units[0]['frames']}序列、完整720p五帧1152000拍/864000打包字通过。
- Board：待用户上板；按BOARD_TEST比较ORIGIN/V1/V2；浅色去饱和/明度色带/输入饱和不可恢复等代价已记录。B/S稳态、30分钟/光照变化待验收，S增长阻断正式验收。
- 保留候选与V1全部历史；停止本轮，不开发进阶五或队友目标检测。
''')
    print('Wrote V2 report and tuning record')
if __name__=='__main__':main()
