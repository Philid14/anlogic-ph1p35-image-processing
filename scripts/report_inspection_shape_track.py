"""Report only archived, verified candidate values (never intermediate area/STA)."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def main():
 folder=ROOT/'artifacts/bitstreams/INSPECTION_SHAPE_TRACK_V1';i=json.loads((folder/'BUILD_INFO.json').read_text())
 old=json.loads((ROOT/'artifacts/bitstreams/RULER_CM_CAL_V1/BUILD_INFO.json').read_text());r=i['resources'];delta=i['resource_delta_vs_RULER_CM']
 table='\n'.join(f'| {k} | {old["resources"][k]} | {r[k]} | {delta[k]:+d} |' for k in ('slice','lut6','ff','eram','dsp'))
 (ROOT/'docs/INSPECTION_SHAPE_TRACK_V1_REPORT.md').write_text(f'''# INSPECTION_SHAPE_TRACK_V1 candidate

完成反光分割改进、显式圆片D/R测量档和红色LAST跟随框。**不是自动圆弧拟合，也尚未实板验收。**

## 本轮问题与结果

1. 反光漏测：旧固定灰度阈值/单极性会丢掉接近背景的亮面。增加空台面学习后，逐像素绝对差12同时保留亮、暗表面，并以每行左右外廓确定尺寸。4样本/16×16格参照要求平滑背景；完全过曝、无对比、光照/相机变化仍需处理或重新学习，不能声称万能消反光。
2. 瓶盖D/R：自动分类尝试因资源超限未交付。最终在ORIGIN测量RUN下长按K4，明确选择已知圆片的D/R档；D是水平外径、R=D/2，按物体位置画尺寸线和半径线。再长按回W/H。不是仅凭W≈H便自动识圆，不支持任意局部圆弧拟合。
3. TRACK：缓存TARGET已有边界结果，与LAST中心/数量/帧号一同锁定，画绿色外框、保留红色本体。框是上一完整采集结果，快速移动有帧级滞后；目标消失/无效后清框。源暂停时重复DDR画面仍可能保留旧框，需结合SOURCE STALE告警。没有改成独立多目标跟踪。

## 最短上板流程

先PROGRAM_SRAM，确认Logo/CNT、原图正常。使用屏幕逻辑SW值，不猜物理左右编号：

- ORIGIN + SW0101：水平尺子至少5个清楚长厘米线，短按K4等CAL:OK；关闭CAL，SW0100。
- 移走尺子和工件，**空台面短按K4**，等BG:OK/AUTO12，再放工件测W/H。
- 放正俯视完整圆瓶盖，**长按K4约一秒**，看到K4 HOLD: D/R及D/R标注；异形件用W/H。
- SW0000、K3进入TRACK，用单个红色不反光物体慢移/快移/移出/放回，检查框、X/Y/N/VALID。

CAL中短按K4仍是读尺；BINARY/EDGE下K4短-10/长+10不变；TRACK/MOTION不调检测阈值。K3七模式、颜色对比开关和其他开关语义保持。复位后尺子比例与背景参照需要重新获得。

## TRACK参数如何看

| 字段 | 含义 / 移动物体时的预期 |
|---|---|
| X / Y | 最近完整帧的包围框中心，HEX像素；右移X增、下移Y增 |
| N | 匹配红色像素数，HEX；一般靠近变大、远离/遮挡变小，不是物体数量 |
| FRAME | 采集结果帧号，HEX；持续更新，不是端到端延迟 |
| VALID | 当前LAST结果可用；无目标或失效时0 |
| ERR | 视频协议异常sticky；不是检测置信度，新增异常先查链路 |
| SEARCH/ACQUIRE/TRACK/HOLD | 检测确认/丢失状态；HOLD不代表继续假画已消失物体 |
| B / S | 前600采集帧/之后含write-valid且FIFO-full事件的帧数，HEX，非亮度/饱和度 |
| SW / R | 逻辑开关状态 / 读尺状态（R3是CAL成功），与目标X/Y无关 |

用户截图27F/167/028BB对应X639、Y359、N10427；原绿色填充是旧覆盖色，并非摄像头将红色变成绿色。本版保留红色本体，仅绘框。

## 实际布局布线结果

| 项目 | RULER_CM_CAL_V1 | 本候选 | 差值 |
|---|---:|---:|---:|
{table}

- Slice {r['slice']}/21216，余{21216-r['slice']}；ERAM {r['eram']}/108，余{108-r['eram']}。资源非常紧，不能当作后续算法仍有充足余量。
- Setup WNS {i['setup_wns_ns']:+.3f}ns，Hold WNS {i['hold_wns_ns']:+.3f}ns，TNS均0；完整SYN/PHY/final STA/bitgen通过，未放宽SDC。
- 公共视频延迟31时钟，新增0；仅测量统计分支增加2时钟。Sensor/ISP参数、视频分辨率、DDR/HDMI、PLL/引脚/SDC及队友RTL保持。
- 关键warning类型 {i['critical_warning_types']}；新增类型 {i['new_critical_warning_types']}。继承FIFO/Gray覆盖问题、长期/温度/稳态风险仍未通过新实板验证。

## 验证证据

- 旧路径和新路径各9帧完整720p ISP/真实打包器：合计4147200拍、3110400个打包字逐像素/同步通过；边界是post-AWB及已同步UI，非物理MIPI/DDR控制器仿真。
- 完整720p背景：4帧、1152格、分格梯度、双极性反光、±11/12/13边界、同拍SOF/valid间隙、帧中clear；D/R共享标准字库及径向绘图2帧720p。
- 实际MAIN TRACK31拍路径128×96测试：移动/消失/框内红色/同步；完整720p模式验证不冒充真实上板跟踪。
- 独立几何160帧/91459周期、240组数值换算、4096字形行、2000随机配置及RAM回绕/复位、模式选择/失效事件、首拍有效/中途复位等通过。
- 合成反光样例：旧分割外宽70px，新参照140px、真值140px；这是构造模型，不是实板改善率。图见evidence/INSPECTION_SHAPE_TRACK_V1/synthetic_reflection.png。
- 四轮未装入器件的尝试完整保留；另有字体RAM版长时间布线/阶段时序恶化后主动终止，未完成最终STA、未生成bit。最后保留显式圆片档，恢复原字库逻辑；不能把被停止的尝试说成通过或最终STA失败。

## 版本与归档

- Version: {i['version']}
- Branch: {i['branch']}
- 实际TD源码commit: {i['source_commit']}
- Candidate Tag: {i['tag']}（建立于归档commit，不移动旧tag）
- Bit: artifacts/bitstreams/INSPECTION_SHAPE_TRACK_V1/camera_to_dsi_display.bit
- SHA256: {i['bit_sha256']}
- BUILD_INFO、完整资源/时序/构建记录、各轮失败及RTL验证在同目录build_evidence。
- 基线Draft PR27尚未合并；本轮独立Draft PR依赖该分支，不自动合并。实际push/PR结果见本报告末尾发布记录与REMOTE_RECEIPT。
- Board Test Status: NOT_RUN。完成候选后停止，等待用户实板反馈。

详见INSPECTION_SHAPE_TRACK_V1_DESIGN.md、BOARD_TEST.md。回滚使用RULER_CM_CAL_V1归档bit，SHA256 {old['bit_sha256']}，不依赖本轮临时构建目录。
''')
 log=ROOT/'docs/IMAGE_TUNING_LOG.md'
 with log.open('a') as f:f.write(f'''

## 2026-11-02 INSPECTION_SHAPE_TRACK_V1 candidate / MAIN

- 基线8dd67021 / RULER_CM_CAL_V1 / Draft PR27；新分支{i['branch']}，实际TD源码{i['source_commit']}，tag {i['tag']}。
- 用户实板反馈：反光工件漏测、瓶盖无D/R、红色目标只有填充无跟随框。Sensor/ISP/SDC不改；分别保留背景、D/R、框和资源检查点，未把三个问题伪称同一根因。
- 旧固定阈值 → 空台面4样本格参照/逐像素双极性差12；无D/R → ORIGIN测量RUN长K4显式圆片档；绿色实心目标 → 保留红色本体、上一完整结果LAST外框。短K4学背景，CAL/阈值交互保持。
- 自动近圆分类因资源失败放弃正式集成，四轮失败证据归档；最终资源{r}，差值vs厘米版{delta}，Setup/Hold{i['setup_wns_ns']:+.3f}/{i['hold_wns_ns']:+.3f}ns，TNS0，SYN/PHY/final STA/bitgen PASS。
- Bit artifacts/bitstreams/INSPECTION_SHAPE_TRACK_V1/camera_to_dsi_display.bit；SHA256 {i['bit_sha256']}。
- 数字验证：18帧720p ISP/打包器、2帧D/R绘图、4帧背景缓存、MAIN TRACK128×96、160帧几何/240换算、字库/配置RAM/复位/选择等通过；不是实板证据。
- Board Test NOT_RUN，FIFO/Gray、资源紧张和实际反光/测量误差/跟踪滞后待验收。保留候选及全部历史；按BOARD_TEST完成CAL→空背景→工件及TRACK对照，S稳态若增长先查完整性。停止候选开发，不自动合并、不自行下一版。
''')
 print('Wrote report and tuning log')
if __name__=='__main__':main()
