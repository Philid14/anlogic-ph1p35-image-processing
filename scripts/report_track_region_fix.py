"""Generate synthetic comparison and a report from actual archived build facts."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
from run_track_region import scenes,region,legacy
def visual():
 from PIL import Image,ImageDraw,ImageFont
 out=ROOT/'docs/evidence/TRACK_REGION_FIX_V1';out.mkdir(parents=True,exist_ok=True)
 font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',18)
 canvas=Image.new('RGB',(1020,1300),'#17212b');draw=ImageDraw.Draw(canvas)
 draw.text((22,15),'Synthetic RGB evidence (NOT camera/photo RGB)',font=font,fill='white')
 seq=scenes(160,120)
 for j,f in enumerate((0,1,4)):
  for i,fn in enumerate((legacy,region)):
   im=Image.new('RGB',(160,120));im.putdata([p for row in seq[f] for p in row]);im=im.resize((480,360),Image.Resampling.NEAREST)
   l,r,t,b,n=fn(seq[f]);d=ImageDraw.Draw(im)
   if n:d.rectangle((l*3,t*3,r*3+2,b*3+2),outline='#00ff80',width=4)
   x=20+i*500;y=80+j*405;canvas.paste(im,(x,y))
   title=('Old global bbox' if i==0 else 'New selected region')+f' | scene{f} N={n}'
   draw.text((x,y-28),title,font=font,fill='white')
 canvas.save(out/'synthetic_comparison.png')
def main():
 visual();d=json.loads((ROOT/'artifacts/bitstreams/TRACK_REGION_FIX_V1/BUILD_INFO.json').read_text())
 old=json.loads((ROOT/'artifacts/bitstreams/INSPECTION_SHAPE_TRACK_V1/BUILD_INFO.json').read_text())
 rows='\n'.join(f"|{k}|{old['resources'][k]}|{v}|{v-old['resources'][k]:+d}|" for k,v in d['resources'].items())
 text=f'''# TRACK_REGION_FIX_V1 诊断与修复报告

本轮 MAIN 基于 PR28 的真实上板失败，修复“无物品也有巨大跳框、红物体不能被框住”。
未修改其他功能。**数字回归与完整TD通过；本bit尚待用户真实上板，不宣称已经实板修好。**

## 根因与证据等级

- **代码确认**：旧检测统计全画面红点的极值，64点即可有目标；没有空间主体选择。
  所以远处杂点也能把框扩到四边。X/Y是框中心而非质心，巨大框因此常停在639/359。
- **模型+旧RTL复现**：160x120无目标、644散点时，旧框0..159/0..119；同数据新N=0。
  加入24x24红目标与远处散点，旧框仍全屏，新框40..63/32..55，支持面积576。
- **代码/合成输入确认**：RGB208/192/176偏暖中性也满足旧色相/绝对彩度判据。
  新相对红通道优势判定拒绝它。不能据此宣称已测得现场AWB/照明各自贡献率。
- **坐标接线验证**：现有bbox44位打包/解包、1280源坐标、每帧锁存及2像素绿线
  在独立及实际31拍路径中正确；没有发现导致本次整屏框的接线错误。
  拍屏不作为相机原始RGB，不虚构现场精确误检率。

## 本版变化与边界

只修改 `vision_source_observer.v`：保持原红色判据，并要求G/B<=R-floor(R/4)；固定红色/30度的硬件表达经过全部16777216种RGB等价检查，
4像素中至少3红点才构成支持块；每行保留最长连续段，至少8px；相邻行段接续形成
至少4行、64支持像素的区域，选支持面积最大者。不是通用连通域或多物体识别。
内部去掉重复结果寄存器，LAST仍由MAIN原子发布。无新增图像RAM、DSP或反压。
共同像素流水线仍31拍；结果在EOF后一拍发布，保持LAST语义。

X为4像素分组边界，Y为原始行，X/Y显示框中心。N改为选中连续区域的支持面积，
不是全画面命中总数，也不是精密面积。FRAME/VALID/ERR、按键、开关和阈值UI保留。
极浅粉、红细线、空心红环、反光切断、多件相近大小红物体仍可能漏检或换选。
本版以非红背景上的单个哑光实心红瓶盖为验收对象。

![独立合成输入新旧对照](evidence/TRACK_REGION_FIX_V1/synthetic_comparison.png)

## 验证与资源

15组native ModelSim回归通过，使用真实厂商ERAM/GSR模型：独立模型16帧与7帧720p
（含末行末拍目标、921600全红支持计数）、旧RTL同数据失败复现、实际MAIN TRACK
31拍逐像素对照、无目标/移动/消失/圆形/暗红/散点/小干扰、提前和同行SOF、valid间隙、
异常帧；旧/新V5共18帧720p ISP/DDR打包验证4147200有效拍/3110400打包字。
背景、尺寸绘图/格式、配置RAM、复位、长按选择、字库回归亦重跑通过。
这是post-AWB/同步UI边界验证，不冒充真实MIPI/DDR控制器/HDMI物理验证。

|资源|旧候选|本版|差值|
|---|---:|---:|---:|
{rows}

- 最终布局布线 Setup WNS {d['setup_wns_ns']:+.3f}ns / Hold {d['hold_wns_ns']:+.3f}ns，TNS均0。
- STA覆盖{d['sta_coverage_percent']}%；Slice余量{21216-d['resources']['slice']}，ERAM余量{108-d['resources']['eram']}。
- 完整SYN→PHY→最终STA→bitgen通过。SDC、PLL、Sensor/AWB与TARGET文件冻结。
- 关键warning {d['critical_warning_types']}；新增类型{d['new_critical_warning_types']}。
  既有FIFO稳态溢出、Gray覆盖、热/长期可靠性尚未由本轮实板排除。
- 前两轮打包21312/21226>21216；保留失败证据，没有生成或发布失败bit。

## 交付与上板

- Version `{d['version']}`；Branch `{d['branch']}`。
- 实际TD源码commit `{d['source_commit']}`；Tag `{d['tag']}`。
- bit `artifacts/bitstreams/TRACK_REGION_FIX_V1/camera_to_dsi_display.bit`。
- SHA256 `{d['bit_sha256']}`。
- Board Test `{d['board_test']}`。归档commit/PR/远程实推以REMOTE_RECEIPT为准。
- [简明上板流程](TRACK_REGION_FIX_V1_BOARD_TEST.md)：SW0000/TRACK，空台面→单红瓶盖
  →左右上下移动→取走，各观察10秒；再抽查颜色比对、尺寸、模式与B/S稳态。
- 回退 `inspection-shape-track-v1-candidate`，全部旧bit/tag保留。新Draft依赖未合并PR28，
  不自动合并、不改main，完成候选后等待上板。
'''
 (ROOT/'docs/TRACK_REGION_FIX_V1_REPORT.md').write_text(text,encoding='utf-8')
 log=ROOT/'docs/IMAGE_TUNING_LOG.md';s=log.read_text(encoding='utf-8');marker='## 2026-11-02 TRACK_REGION_FIX_V1 candidate / MAIN'
 assert marker not in s
 s+=f'''

{marker}

- 上一版INSPECTION_SHAPE_TRACK_V1实板补记：用户报告空台面与红瓶盖均出现近全屏跳框，TRACK未验收通过；照片未核验实际烧录SHA，不能作原始RGB。本轮不改历史归档。
- 基线{d['baseline_commit']} / Draft PR28；唯一主要变量：全局红点包围框 → MAIN相对红优势+连续主要区域选择。TARGET、Sensor/ISP、其他模式/尺寸/颜色、DDR/HDMI/PLL/SDC冻结。
- 实际TD源码{d['source_commit']}，branch {d['branch']}，tag {d['tag']}。
- 模型与旧RTL同输入复现误框，新RTL独立16帧+7帧720p及完整15组native回归通过；不是实板验证。N语义改为选中连续区域支持面积。
- 最终资源{d['resources']}，差值{d['resource_delta_vs_INSPECTION_SHAPE_TRACK']}；Setup/Hold{d['setup_wns_ns']:+.3f}/{d['hold_wns_ns']:+.3f}ns，TNS0；完整SYN/PHY/STA/bitgen PASS。首轮打包失败保留证据。
- Bit artifacts/bitstreams/TRACK_REGION_FIX_V1/camera_to_dsi_display.bit；SHA256 {d['bit_sha256']}；Board Test NOT_RUN。FIFO/Gray/长期/热稳定风险未排除。
- 保留本候选与全部历史，按BOARD_TEST完成空台面/单实心红目标/移动/消失验证；不自动合并，不自行下一版。
'''
 log.write_text(s,encoding='utf-8')
if __name__=='__main__':main()
