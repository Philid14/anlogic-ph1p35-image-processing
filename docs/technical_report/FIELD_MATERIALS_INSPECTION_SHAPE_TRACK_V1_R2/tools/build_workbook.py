from pathlib import Path
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT,WD_ROW_HEIGHT_RULE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import json,hashlib

R=Path(__file__).resolve().parent.parent
OUT=R/'AnlogicTrack2_现场拍摄与测量记录册_R2.docx'
d=Document();s=d.sections[0]
s.page_width=Cm(21);s.page_height=Cm(29.7)
s.top_margin=s.bottom_margin=Cm(1.7);s.left_margin=s.right_margin=Cm(1.8)
s.header_distance=s.footer_distance=Cm(.75)
for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3']:
 st=d.styles[name];st.font.name='Calibri';st.font.color.rgb=RGBColor(0,0,0)
 st.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'微软雅黑')
 st.paragraph_format.space_before=Pt(0);st.paragraph_format.space_after=Pt(3)
for name in ['Title','Subtitle','Heading 1','Heading 2','Heading 3']:
 pr=d.styles[name].element.get_or_add_pPr()
 for n in ['w:pBdr','w:shd']:
  for old in list(pr.findall(qn(n))):pr.remove(old)
d.styles['Normal'].font.size=Pt(10.5)
d.styles['Normal'].paragraph_format.line_spacing=1.10
d.styles['Title'].font.size=Pt(23);d.styles['Title'].font.bold=True
d.styles['Heading 1'].font.size=Pt(17);d.styles['Heading 1'].font.bold=True
d.styles['Heading 2'].font.size=Pt(11);d.styles['Heading 2'].font.bold=True
d.styles['Heading 2'].paragraph_format.space_before=Pt(6)
d.core_properties.title='AnlogicTrack2现场拍摄与测量记录册'
d.core_properties.subject='INSPECTION_SHAPE_TRACK_V1现场记录与技术报告材料收集 R2'
d.core_properties.author='项目组';d.core_properties.last_modified_by='项目组'
header=s.header.paragraphs[0];header.text='AnlogicTrack2  材料采集R2  INSPECTION_SHAPE_TRACK_V1'
header.paragraph_format.space_after=Pt(0)
for r in header.runs:r.font.size=Pt(8);r.font.color.rgb=RGBColor(0,0,0)
f=s.footer.paragraphs[0];f.alignment=WD_ALIGN_PARAGRAPH.RIGHT
f.add_run('现场记录  第 ')
def field(p,code):
 x=OxmlElement('w:fldSimple');x.set(qn('w:instr'),code);r=OxmlElement('w:r');t=OxmlElement('w:t');t.text='1';r.append(t);x.append(r);p._p.append(x)
field(f,'PAGE');f.add_run(' 页 / 共 ');field(f,'NUMPAGES');f.add_run(' 页')
for r in f.runs:r.font.size=Pt(8)
md=[];page_titles=[]

def p(text='',bold=False,small=False):
 pp=d.add_paragraph();rr=pp.add_run(text);rr.bold=bold
 if small:rr.font.size=Pt(9)
 pp.paragraph_format.widow_control=True
 md.append(text+'\n');return pp

def title(text,first=False):
 if page_titles:d.add_page_break()
 q=d.add_paragraph(text,'Title' if first else 'Heading 1');q.paragraph_format.keep_with_next=True
 md.append('# '+text+'\n');page_titles.append(text)

def h(text):
 q=d.add_paragraph(text,'Heading 2');q.paragraph_format.keep_with_next=True;md.append('## '+text+'\n')

def check(text):p('[ ] '+text)
def step(n,text):p(str(n)+'. '+text)
def line(label,lines=1):
 width=sum(1 if ord(c)>127 else .52 for c in label)
 blanks=max(14,min(50,int((87-width*2)/1.0)))
 p(label+'  '+'_'*blanks)
 for _ in range(lines-1):p('_'*64)

def table(headers,rows,widths,minheight=.72):
 t=d.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
 for c,w in zip(t.columns,widths):c.width=Cm(w)
 borders=OxmlElement('w:tblBorders')
 for side in ['top','left','bottom','right','insideH','insideV']:
  x=OxmlElement('w:'+side);x.set(qn('w:val'),'single');x.set(qn('w:sz'),'4');x.set(qn('w:color'),'D9D9D9');borders.append(x)
 t._tbl.tblPr.append(borders)
 mar=OxmlElement('w:tblCellMar')
 for side,val in [('top',90),('bottom',90),('left',100),('right',100)]:
  x=OxmlElement('w:'+side);x.set(qn('w:w'),str(val));x.set(qn('w:type'),'dxa');mar.append(x)
 t._tbl.tblPr.append(mar)
 for i,x in enumerate(headers):t.rows[0].cells[i].text=x
 rep=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(rep)
 for row in rows:
  cs=t.add_row().cells
  for i,x in enumerate(row):cs[i].text=str(x)
 for ri,row in enumerate(t.rows):
  row.height=Cm(minheight if ri else .65);row.height_rule=WD_ROW_HEIGHT_RULE.AT_LEAST
  row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
  for ci,c in enumerate(row.cells):
   c.width=Cm(widths[ci]);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   if ri==0:
    sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'EEEEEE');c._tc.get_or_add_tcPr().append(sh)
   for pp in c.paragraphs:
    pp.paragraph_format.space_before=Pt(0);pp.paragraph_format.space_after=Pt(1);pp.paragraph_format.line_spacing=1.1
    pp.paragraph_format.keep_with_next=(ri==0)
    for rr in pp.runs:rr.font.size=Pt(9.5);rr.bold=(ri==0)
 md.append('| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |')
 for row in rows:md.append('| '+' | '.join(str(x).replace('\n',' / ') for x in row)+' |')
 md.append('');sp=d.add_paragraph();sp.paragraph_format.space_before=Pt(0);sp.paragraph_format.space_after=Pt(0);sp.paragraph_format.line_spacing=Pt(2);sp.add_run(' ').font.size=Pt(1)
 return t

def result():
 p('执行：[ ]已执行  [ ]部分执行  [ ]未执行    观察：[ ]符合预期  [ ]异常  [ ]不确定',small=True)
 line('异常或未测原因');line('原文件名或录像时间段')

def page_run():p('本次 RUN_ID：________________  操作者：____________  记录时间：____________',small=True)

# 01
TITLE='AnlogicTrack2 现场拍摄与测量记录册 R2'
title(TITLE,True)
p('按顺序操作  当场填写  保留成功与失败原件',bold=True)
p('按官方模板已知写作缺口补全的采集表，可打印或在Word填写。第2—14页现场操作，第15—17页样品/数据/图片附件，第18—20页主控确认和收齐核对。所有实测结果待填；建议次数/时长非官方门槛。未测不填0。')
line('现场日期及人员');line('本次 RUN_ID（自定且唯一）')
h('先核对实际加载版本')
p('本册操作依据：INSPECTION_SHAPE_TRACK_V1；工程4d0f779，TD源码517697c。候选原状态为待板测。')
p('归档bit：artifacts/bitstreams/INSPECTION_SHAPE_TRACK_V1/camera_to_dsi_display.bit',small=True)
bit='5d93f2ec5b80ee288455bc942a654de84166ecb202cda7b139b7a4f701b13f9a'
p('对应SHA256：'+bit,small=True)
p('PowerShell核对文件：Get-FileHash -Algorithm SHA256 -LiteralPath <实际bit完整路径>',small=True)
line('实际bit文件路径');line('实际SHA256',2)
p('[ ] 与上述SHA一致   [ ] 不一致   [ ] 尚未核对。不同版本另开RUN，应用操作先按该版本说明确认；不要用相同界面代替SHA核验。',small=True)
h('现场推荐顺序')
p('①整机与尺寸（第2页）→②基础/画质（第3页）→③厘米标定（第4页）→④空台面学习（第5页）→⑤尺寸/圆片（第6—7页）→⑥颜色（第8页）→⑦动态/恢复（第9—10页）→⑧长稳（第11页）→⑨实时性（第12页）→⑩核对回传（第13页）。')
p('标定→移走尺和工件→学习空台面→放入工件，是尺寸测量的连续证据链。第14页可复制记尺寸；完成后按第20页核对能否离场，缺项注明原因及对最终表述的限制。',bold=True)
h('带到现场')
p('[ ] 手机与固定支架/充电  [ ] 公制尺（至少5条清楚厘米长线）  [ ] 独立量具\n[ ] 哑光薄片与反光工件  [ ] 完整圆片/瓶盖  [ ] 同色/异色色样  [ ] 单红卡\n[ ] 纸笔/可编辑Word  [ ] 原文件存储空间  [ ] 已有PROGRAM_SRAM下载工具')

# 02
title('02 实物照片与现场配置 E00');page_run()
p('先拍完整系统，再拍关键局部。照片需清楚反映实际成品；屏幕与现场动作同场录像，便于证明画面实时更新。')
h('照片逐项勾选')
for text in ['正面全景：框架、相机、平台、光源、板卡与显示器尽量同场。','斜45°全景：看清空间关系与连接。','顶部相机和支架：镜头朝向、固定方式、相机丝印。','照明与遮光：光源位置、照明档位、遮光结构。','置物平台：空台面、测量区域与样品平面。','板卡全貌和丝印；供电、MIPI、HDMI连接局部。','用尺量相机高度/框架尺寸的照片；独立量具测样品的照片。']:
 check(text)
h('现场配置填写')
line('板卡型号/丝印/版本');line('相机丝印/镜头规格');line('显示器型号及自报分辨率/刷新')
line('框架长×宽×高（mm）');line('镜头参考位置到样品面距离（mm；写明起止点）')
line('测量面可视范围宽×高（mm）');line('照明布置/档位/有无环境光或遮光')
line('电源标称值、MIPI线与HDMI线实际长度')
p('电路资料后补：请核对实物HX1P35A与仓库HX1P35B_FT_40P_2/3/8图纸版次关系，再提供匹配的MIPI、DDR、HDMI、供电/时钟页及关键网络。现场拍丝印，不凭相似外观认定版次。',small=True)
result()

# 03
title('03 基础显示与画质 E01 E09');page_run()
step(1,'按既有PROGRAM_SRAM流程下载已核对bit。记录首次出图时间，启动后观察约1分钟；让明显物体移动，镜头同时拍到动作与屏幕。')
step(2,'屏幕逻辑SW先置0000。K3循环EDGE→ORIGIN→GRAY→BINARY→STYLE→TRACK→MOTION→EDGE；建议完整3轮。每次按下/释放动作拍清。')
step(3,'同一固定场景依次拍五个基础模式；每图保留模式名与Logo。照明变化单独成组，注明手机自动曝光/美化情况。')
line('下载结果/首次出图耗时（s）')
table(['模式','几何/效果与Logo观察','照片或录像编号'],[[x,'',''] for x in ['ORIGIN 原图','GRAY 灰度','BINARY 二值','EDGE 边缘','STYLE 风格化','TRACK','MOTION']],[3.2,8.4,5.8],.75)
h('阈值与控制')
p('EDGE/BINARY：K4短按−10、长按+10；记录实际默认值与变化。TRACK/MOTION中K4不调颜色/运动阈值。实体拨码路序以屏幕SW核对，不猜左右编号。')
line('EDGE：前值/短按后/长按后；BINARY：前值/短按后/长按后')
line('循环次数/多跳或不切次数；黑屏/错行/冻结/回跳及持续时间')
line('变光或色温条件/恢复到稳定画面耗时；暗线、饱和、闪烁现象',2)
p('要看：图像随动作持续更新；算法几何关系无明显错位；Logo可见。既有AWB不等于新自动曝光，本版AE请求关闭。',small=True)
result()

# 04
title('04 厘米长线标定 E04');page_run()
p('需要：已知公制尺、至少5条清晰黑色厘米长线、干净浅色背景；尺和工件同平面、相机正俯视。记录真实刻线照片，算法不识别数字或单位。')
step(1,'K3切ORIGIN，开启DIM与CAL。屏幕逻辑SW通常为0101，AREA应显示1CM RULER LONG TICKS；不要按物理拨码左右猜映射。')
step(2,'将厘米长线水平放入搜索框，覆盖至少5条长线，保持清晰、静止；短按并释放K4一次。录像保留按键到R状态变化全过程。')
step(3,'等待完整搜索。预计约54个采集帧加分析等待；现场用秒表/录像记耗时，不连续重按K4。')
step(4,'R3/CAL:OK后关闭CAL、保留DIM，通常SW0100。先移走尺和工件，再去第5页学习空台面，最后用独立真值工件复核X/Y。')
h('R状态速查')
p('R0未标定；R1等待采样；R2分析；R3成功发布粗尺度；R4对比度不足；R5间距未通过；R6帧几何错误；R7取消。R3不证明单位和双轴精度，R5也不等于链路帧错误。',small=True)
line('标尺型号/单位、可见长线数、位置/角度/光照')
line('本次标定ID（自定，后续尺寸表引用）')
table(['次序/位置','开始→终止时刻','R状态序列/最终状态','耗时s / S100若可见'],[['1','','',''],['2','','',''],['3','','','']],[2.6,4.0,6.2,4.6],1.0)
line('请求数/成功数/取消数；失败条件和文件编号')
p('独立复核：水平与垂直真值都测；若读数约差2倍、5倍，保留原屏/刻线，先标为尺度疑似错误。0.1mm显示位数不能当作0.1mm精度。S100不可见填不可见，勿猜。',small=True)
result()

# 05
title('05 空台面学习与反光 E11');page_run()
p('前提：第4页已标定，ORIGIN测量RUN，CAL关、DIM开，通常SW0100。相机/台面/照明固定，先把尺和工件全部移走。',bold=True)
step(1,'拍一张真正空台面的原图。短按并释放K4，录像保留BG:NEED/WAIT/OK/FAIL的实际变化。短按学习，约1秒长按会切W/H与D/R。')
step(2,'等参照就绪后放入工件，记录AUTO12或CUT、外框/尺寸及丢失区域；先用哑光薄片，再用反光金属、相对背景亮/暗的样品。')
step(3,'单独改变光照或产生阴影，记录旧参照下现象；再移走工件、重新学习空台面、放回同件。各组保留原始照片，写明改了什么。')
step(4,'移动相机、桌面、照明或进入CAL/复位后重新检查参照。不要把BINARY预览当AUTO12分割图；BINARY仍是固定阈值预览。')
line('背景ID/对应标定ID');line('空台面材质、纹理、颜色与光照条件')
line('学习开始/结束时间；BG变化；放件后AUTO12或CUT')
table(['样品/条件','外廓完整或缺失位置','BG/方法/有效状态','证据编号'],[['哑光/亮/暗','','',''],['反光金属','','',''],['变光或阴影','','',''],['重新学习后','','','']],[3.0,6.1,4.9,3.4],1.0)
p('要看：空台面无持续假工件；放件后端点是否贴外廓；变光后是否异常、重学后是否恢复。背景差需要平滑固定背景；过曝或无对比边缘仍可能丢失，保留失败。换旧bit对照须另开RUN，注明其他版本差异。',small=True)
result()

# 06
title('06 宽高与中心间隙 E05');page_run()
p('前提：标定和空台面学习完成。单个薄、平、轴对齐工件放在ROI内，不触边；相机、照明和物体平面保持。尺/工件不在同平面或厚件离面会改变尺度。')
step(1,'用独立量具测成品真值并拍照。注明工具、分辨率和量法；设计图标称尺寸不替代成品量测。')
step(2,'工件静置后拍全屏，必须看清外框、W/H/GAP、MM或PX、CAL、BG、方法和有效状态。记录原值，无法读清填不可读。')
step(3,'测中心、左上、右下等位置，重新拿起/放下才算一次独立摆放。可按3样品×3位置×5次安排45次摆放；先做小批也可，如实写实际次数。')
step(4,'间隙单独取独立真值，确保固定中心截面x640/y352确实穿过待测间隙。没有合适试件填未测，不以反光空洞当真实孔。')
line('标定ID/背景ID；仪器名称/分辨率/量法')
line('样品ID/材质/厚度（mm）/位置/角度')
table(['项目','独立真值mm','显示原值','单位/有效状态'],[['W 外接宽','','',''],['H 外接高','','',''],['GAPX 中心间隙','','',''],['GAPY 中心间隙','','','']],[4.1,3.7,4.1,5.5],.9)
line('量具照片/全屏读数照片/本次重复编号（附页14）')
line('触边、空场、双物体、反光、斜放的失效或错误现象',2)
p('复制第14页记逐次数据；分X/Y、位置汇总有符号误差（显示−真值）、最大/平均绝对误差及重复性范围。PX不与mm直接相减，失败/无效单列；斜放的轴对齐外接宽不等于工件真实边长。',small=True)
result()

# 07
title('07 圆片直径与半径 E12');page_run()
p('适用对象：操作者已知的完整圆片/瓶盖，正俯视、平放、单个、不触ROI。先完成第4—5页，保持尺度与背景。此档为手动选择，不是自动识圆。',bold=True)
step(1,'量具测实际外径D并拍照；记录样品厚度。独立R真值为量具外径/2，不能用屏幕D/2来证明真实精度。')
step(2,'ORIGIN测量RUN中长按K4约1秒，确认K4 HOLD: D/R；保持此档，圆片左/中/右各3次并按第16页采样，拍清圆片、尺寸线与半径线。')
step(3,'完成D/R采样后，再长按回W/H，核对单位与水平跨度；一次长按应只切一次。短按仍学习背景，记录长按是否误触发。')
line('仪器/分辨率；标定ID/背景ID')
table(['样品/位置/重复','真值D mm','屏幕D / 单位','屏幕R / 单位','状态/证据'],[['1','','','',''],['2','','','',''],['3','','','','']],[4.0,2.7,3.6,3.6,3.5],1.15)
h('操作与边界观察')
p('[ ] 一次长按一次切换  [ ] 长按不误学习  [ ] 半径线从中心到右外边界\n[ ] 未标定为PX、已标定为MM（记录实际验证条件，未试项不勾）')
line('长按次数/切换次数/异常')
line('斜放、方片/异形、部分圆弧、双物体或反光的现象',2)
p('D是水平外框跨度，R=D/2；方片也能被手选到D/R，因此出现D/R不证明识圆。圆片倾斜、局部圆弧或厚件不作为有效几何前提；不宣称任意圆弧拟合、内径或厚度测量。',small=True)
result()

# 08
title('08 双区域颜色比对 E03');page_run()
p('在ORIGIN开启既有颜色面板，核对屏幕SW并记录，不猜物理开关编号。样品覆盖两个32×32采样框：参考x304…335/y304…335，测试x944…975/y304…335。')
step(1,'同材质同色样品分别放左右，记录后交换；每次重新放置。')
step(2,'换成明显异色样品；另组仅改变一侧照明。暗、近饱和、反光和背景混入分别记录，保持其他条件。')
step(3,'建议每组10次独立放置，可分批做；每次拍出两区位置、RGB与完整状态。请全部保留，不只选择MATCH图片。')
line('样品ID/材质/预期同色或异色；SW/照明条件')
table(['组别','计划/实际次数','MATCH/LIGHT/DIFF','CHECK/WAIT/异常','证据编号'],[['同色+左右交换','','','',''],['明显异色','','','',''],['单侧变光','','','',''],['暗/饱和/反光','','','','']],[3.6,2.8,4.0,3.8,3.2],1.05)
h('单次原始记录  可复制此区域')
line('组别/重复编号/左右样品身份')
line('REF RGB；TEST RGB')
line('ABS/L1/MAX；CHR/DV（不可见注明）')
line('显示状态/预期/是否异常；原图和全屏文件名')
p('MATCH表示当前原始RGB接近；LIGHT只提示比例接近、可能有亮度因素，不直接证明同色。暗/饱和的CHECK须保留；本项目不是标准色差ΔE计量。左右差异的原因需单变量对照。',small=True)
result()

# 09
title('09 红色LAST外框 E06');page_run()
p('屏幕逻辑SW0000，K3进入TRACK。用单红卡、无大片红背景开始；录像同时拍物理动作和HDMI，完整保存移动→停止→移出→放回。')
step(1,'慢移左→中→右、上→下，停住后看外框、X/Y/N与FRAME；再做一次快移，保留可见滞后。')
step(2,'红卡移出后，新无目标结果应框消失、N=0、VALID=0；放回看重建。再加入第二个红物体、小红块或红背景，分组记录。')
step(3,'应看到2像素绿色外框、框内仍为原红色。框/中心/数量/帧号应成组更新；多红区域可能合并，不期待独立多ID。')
h('字段速查')
p('X/Y是最近完整观测的包围框中心，N是红色匹配像素数，FRAME是采集结果帧号，均按屏幕HEX原样抄。ERR是协议sticky错误，非置信度。右移X增、下移Y增；例27F/167/028BB为639/359/10427，仅是解释例，不填作测量。',small=True)
table(['动作/时刻','X/Y/N/FRAME原HEX','VALID/状态/ERR','框/本体/证据'],[['慢移/静止','','',''],['快速移动','','',''],['移出/重现','','',''],['第二红物体','','','']],[3.0,6.4,4.0,3.8],1.15)
line('肉眼或录像可见滞后；若计录像帧，写拍摄fps与原帧索引')
line('框与文字不一致/旧绿填充/空场仍框等异常',2)
p('框来自上一完整采集结果，快移可有帧级滞后，不能按严格同显示帧描述。源停止时DDR可连旧框重复，需结合SOURCE STALE；不要把HDMI重复刷新算成新观测或把尺寸外框当颜色框。蓝色尚未集成。',small=True)
result()

# 10
title('10 运动检测与恢复 E07 E08');page_run()
h('运动检测 E07')
step(1,'SW0000，K3进入MOTION，固定相机和照明。先静置，再明显移动→停止→移出；小/慢目标和单独灯变分组。')
step(2,'拍清WARMUP/INVALID/STILL/MOTION/GLOBAL、LAST CHANGED、源FRAME与洋红提示位置；记录停止后回落耗时。')
table(['输入/持续时间','状态/CHANGED原HEX','现象/恢复/证据'],[['静置','',''],['明显移动→停止','',''],['小慢目标','',''],['仅灯变','','']],[4.0,5.4,8.0],.85)
p('CHANGED是变化块数；STILL允许1—2块变化，≥3为MOTION，>75%块变化为GLOBAL。洋红色只标块末拍4像素；GLOBAL不能唯一判断是灯变。',small=True)
h('复位与停顿 E08')
step(1,'只用既有受控复位流程；采集停顿仅用已有且获准的注入入口。没有入口填未测，不能用遮镜头代替断流。')
step(2,'录像保留复位/停顿前、STALE、恢复后首个可信结果；注意是否重复旧DDR画面。复位后重新标定与学习背景，运动先重建历史。')
line('复位/停顿方式、操作时刻、源FRAME前后值')
line('SOURCE STALE是否出现/旧图旧框是否仍在/恢复耗时s')
line('恢复后TRACK/MOTION状态；是否需重新下载')
p('guard名义约100ms、采集心跳告警名义约200ms是源码门槛口径，手机录像不证明周期级精度。遮镜头仍在出帧；心跳有更新也不能证明DDR显示最新帧。',small=True)
result()

# 11
title('11 连续运行与异常 E02');page_run()
p('建议单独做一段30分钟起步的连续观察，可延长。先固定条件，再在明确时间点切模式、移动或变光；所有变化写入事件表。分别记录运行时长与录像/人工实际覆盖时长，未覆盖区间保留；不能据此声称全程零异常。')
line('开始/结束时刻；连续运行时长/实际观察覆盖时长')
line('固定模式/SW/样品/光照；录像方式及中断情况')
table(['启动后时间','FRAME原HEX','ERR原值','B原HEX','S原HEX','画面/文件'],[['5秒','','','','',''],['30秒','','','','',''],['120秒','','','','',''],['5分钟','','','','',''],['10分钟','','','','',''],['30分钟/末尾','','','','','']],[2.5,3.5,2.3,2.2,2.2,4.7],.8)
p('B/S为HEX、饱和FFFF：B统计前600采集帧中含write-valid且FIFO-full事件的帧数，S统计之后同类帧数。不是亮度/饱和度或像素数；启动B非零不等于稳态丢帧，S持续增长优先检查缓存/吞吐。',small=True)
h('事件与异常  需要时续页')
table(['时刻','操作或异常','持续s/计数变化','恢复方式/证据'],[['','','',''],['','','',''],['','','','']],[2.5,5.4,4.0,5.5],.9)
line('花屏__次/冻结__次/回跳__次/错位__次/异常重启__次；未观察时勿填0')
line('计数清零/饱和/不可见情况；稳态S增长区间与恢复')
p('看到异常先记录完整画面、操作、计数和恢复，再继续。未知内部欠读/溢出填不可观测，不从“画面正常”推断为0。手机录像丢帧与FPGA异常分别描述。',small=True)
result()

# 12
title('12 刷新率与延迟 E10');page_run()
p('有合适设备再测；没有设备就填未测。三种数值分别记录：显示器刷新、独立采集新帧率、包含曝光与显示器的光学延迟。')
h('显示刷新')
step(1,'拍显示器信息页或采集/测量设备读数；注明来源是显示器自报还是仪器量测。显示器标称60Hz不证明相机独立新帧60fps。')
line('来源/设备/显示分辨率/刷新读数Hz/证据')
h('独立采集新帧率')
step(2,'在可见源FRAME的模式（如TRACK/MOTION）记录真实时间窗t、起止原HEX与录像。无身份重启/回绕时，先转十进制，再用帧号增量/t；这是源采集计数速率，不是实际显示独立新帧率。')
line('t起__ s / FRAME起HEX________；t止__ s / FRAME止HEX________')
line('十进制增量__ / 时长__s = __fps；重启/回绕/跳变/漏读说明')
h('光学端到端延迟')
step(3,'用高速录像同时拍物理变化与屏幕相应变化；采用原始采集视频，核实拍摄fps，不用慢放导出fps代替。定义统一起止判据，重复若干次。')
line('相机/录像设备、真实拍摄fps f；物理事件与屏幕判据')
table(['重复','物理事件帧a','屏幕响应帧b','(b−a)×1000/f ms','证据文件'],[['1','','','',''],['2','','','',''],['3','','','','']],[1.7,3.4,3.4,5.0,3.9],1.0)
p('记录逐帧判读误差：若起止各最多偏1帧，保守量化边界约±2000/f ms，还需说明滚动快门、显示扫描和人工判读影响。帧率不恒定时应用原始时间戳，勿直接套恒定f公式。',small=True)
line('误差边界/局限；最小、最大、平均值（有真实样本后再算）')
p('内部同帧采集到HDMI计时链路尚未集成；本册不要求凭31拍、两个帧号或STALE门槛推算内部延迟。配置约60.61Hz也不是本次实测值。',small=True)
result()

# 13
title('13 回传与资料核对');page_run()
p('现场操作结束先在本页汇总，再按第15—20页查样品、原始数据、图组和主控资料。未测与失败同样回传。每个RUN只使用一种bit身份；改版本、复位重标定或重新学背景时注明新ID。')
table(['项目/所在页','已/部分/未执行','观察/缺少内容','文件名或目录'],[['E00 实物/第2页','','',''],['E01/E09 基础/第3页','','',''],['E04 厘米/第4页','','',''],['E11 背景/第5页','','',''],['E05 尺寸/第6及14页','','',''],['E12 圆片/第7页','','',''],['E03 颜色/第8页','','',''],['E06 外框/第9页','','',''],['E07/E08 运动恢复/第10页','','',''],['E02 长稳/第11页','','',''],['E10 实时性/第12页','','','']],[4.0,3.0,5.5,4.9],.8)
h('交回的文件')
check('填写后的本册，以及原始照片/录像。文件名建议 RUN_ID_E04_01 等，与记录页一致。')
check('整机正面/45°；基础模式同场组图；标定→空台面→放件连续录像；量具真值照片。')
check('颜色/圆片/红卡/运动的成功和失败样本；长稳起末屏、异常时间点与恢复片段。')
check('原始视频保留；若另裁剪展示版，标明其对应原文件时间段。')
line('尚缺的材料/器材，及预计补测安排',2)
p('资料依据：技术文档第五稿470f6d9中的MAIN_EXPERIMENT_LIST.md，及工程4d0f779的INSPECTION_SHAPE_TRACK_V1_BOARD_TEST.md。本文改成现场顺序和填写表，不更改生产参数，也不替代官方技术报告五部分。',small=True)
p('编制日期：2026年11月2日。现场结果由实际记录决定；未经记录的现象保持未测。',small=True)

# 14
title('14 尺寸逐次原始记录附页');page_run()
p('此页可复制。每次重新拿起并放置工件后记录一组；一次摆放的W/H/GAP可各占一行。按标定ID、背景ID和单位分组；PX与mm不混算。')
line('标定ID/背景ID；样品ID/材质/厚度')
line('独立量具名称/分辨率/测量方法')
p('项目填写W、H、GAPX、GAPY、D或R；真值与读数按同一单位填写。显示无效仍保留一行，真值不确定注明，勿填假数。',small=True)
table(['摆放号/位置','项目','真值\nmm','屏幕\n原值','单位/\n有效状态','照片/备注'],[['','','','','',''] for _ in range(12)],[3.1,1.5,2.6,2.6,3.1,4.5],.95)
line('本页缺测/异常/重复条件说明',2)
p('后续计算：误差=显示−真值；平均绝对误差=Σ|误差|/有效样本数；最大绝对误差=max|误差|；同条件重复性范围=max读数−min读数。无效/失败数另报，不从分母静默删除。',small=True)

# 15
title('15 样品与量具台账');page_run()
p('给每件实物、量具和现场配置命名，后续照片与数据都引用同一ID。此页可复制。写实际型号与实测值，不用购物链接名称或设计标称值代替成品信息。')
h('样品台账')
table(['样品ID/用途','材质/颜色/表面','独立真值及单位','厚度/摆放面','真值照片'],[['','','','',''] for _ in range(5)],[3.2,4.0,4.5,2.6,3.1],1.0)
p('尺寸样品包括哑光薄片、反光件、完整圆片、有条件的已知间隙件；颜色需同色同材质及明显异色；跟踪用单红卡。真值W/H/D/GAP按实际测量项目注明，圆片R的真值由独立量具D/2得到。',small=True)
h('量具与记录设备')
table(['仪器ID/型号','用途/单位','分辨率或采样率','校零/方法/证据'],[['','','',''],['','','',''],['','','','']],[4.0,3.8,4.5,5.1],.95)
line('重复测真值的方法、次数、读数范围或不确定因素')
line('布光位置/距离/档位与环境光；配置照片ID')
p('有照度计/温度计就附仪器读数与单位；没有则写灯的型号、位置、档位与照片，不虚构lux或温度。手机曝光/白平衡尽量固定；不能固定的注明自动状态，避免手机变化被误当系统效果。',small=True)
line('镜头/视场/工作距离和平台平整度的测量方法')
line('现场BOM补充：最终器件、线长、供电与已有图纸对应')

# 16
title('16 定时观测与对照原始记录');page_run()
p('对照围绕一个问题做：如同件反光表面的外廓与尺寸。先写bit、标定、背景、相机/光照与真值；换bit另开RUN。其他改动不能归因给一个算法。',bold=True)
line('对照目的/样品ID/真值；条件A与条件B')
line('A的RUN/bit SHA/标定ID/背景ID；B对应记录位置')
h('10秒固定时点观察')
p('连续录像至少10秒，从约定起点按t=0…9秒各抽一个时点，共10次，记录W/H或D与状态。N是实际抽取次数，n是其中读数有效次数，n/N叫“定时采样读数可用比例”。若有可信独立源帧ID，才能另按独立帧统计；HDMI重复画面不算新帧。',small=True)
table(['t秒','W或D原值/单位','H或R原值/单位','有效/状态/源帧若可见','文件/视频时刻'],[[str(i),'','','',''] for i in range(10)],[1.3,4.0,4.0,4.5,3.6],.7)
line('N__ / n__ / 比例__；最小__ / 最大__ / 单位__')
line('失败/无效/不可读次数与原因；是否出现冻结或重复旧图')
p('同条件重复摆放的尺寸误差按第14页统计，与本页时间采样分开。未标定PX不算mm误差；无效、取消、失败均保留分母和原因。R3成功率应写成功/实际请求数并注明取消数。',small=True)
line('对照结论及能支持的表述；不确定因素')

# 17
title('17 照片录像索引与图组检查');page_run()
p('每件材料给一个ASSET_ID，登记原文件、RUN、样品、条件和所支持的结论。可复制本页。清晰图组比大量无对应关系的截图更有用；原视频与裁剪展示版分开。')
h('每组照片先检查')
p('[ ] 原图/原视频保留，未美化或重绘结果  [ ] 模式、状态、单位与整幅OSD清楚\n[ ] 无切掉边界、强反光或拍屏条纹遮住数字  [ ] 说明手机自动曝光或HDMI采集条件\n[ ] 单张成功有对应操作/原始数据  [ ] 失败图有输入条件与原因记录，不只选成功')
table(['ASSET_ID/组别','原文件/视频起止','RUN/样品/条件','用途/数据行'],[['A01 整机正面/45°','','',''],['A02 安装/线材/光源','','',''],['A03 模式/Logo/按键','','',''],['A04 尺子→R3','','',''],['A05 空台面→BG','','',''],['A06 工件+量具真值','','',''],['A07 反光/重学/失败','','',''],['A08 圆片D/R/负例','','',''],['A09 同色/异色/变光','','',''],['A10 红卡移动/移出','','',''],['A11 运动/静止/灯变','','',''],['A12 长稳/异常/恢复','','',''],['A13 刷新/延迟仪器','','','']],[3.8,4.9,4.6,4.1],.75)
p('需要精确像素坐标/框偏差时，优先保存有原始分辨率的HDMI采集帧并记录尺度；斜拍拍屏的坐标不能直接当1280×720像素真值。只做定性观察就注明，不额外声称定位精度。',small=True)
line('原始素材目录/备份位置；公开使用副本的整理情况')

# 18
title('18 主控工程资料一次交付');page_run()
p('本页由主控补文件位置或作确认，不要求现场人员另做RTL实验。已有资料引用固定提交和原始日志即可；新的构建或测试另记版本，不能拼接不同bit的结论。')
table(['需交付的资料','最低可写内容','文件/提交/负责人确认'],[['最终工程与bit','分支/commit/tag、TD入口、BUILD_INFO、实际SHA、展示版本确认',''],['系统与模块图','视频/缓存/时钟域关系；顶层到模块输入输出、格式/同步/流水深度',''],['真实机械图','总体尺寸、支架、相机高度与样品面；用第2/15页实测对应',''],['匹配电路资料','板卡版次、MIPI/DDR/HDMI/电源时钟页、关键I/O；厂商/自研范围',''],['参数与复位配置','相机模式、2-lane/RAW10、曝光/增益/AWB及默认阈值；配置与读回分开',''],['整机资源与STA','最终SYN/PHY/STA/bit日志、工具/器件版本、时钟/约束、WNS/TNS/覆盖及warning',''],['数字模型与回归','测试命令、输入/独立预期、结果JSON/日志、原生primitive、覆盖边界',''],['演进与参考出处','关键失败→修改依据→代价；引用/图纸来源；保留独立综合与失败构建边界','']],[3.5,7.5,6.4],1.0)
h('仍需主控补证的来源项')
p('89个TD输入在517697c、归档8fe9dbb和4d0f779的Git内容一致；归档字节SHA中5项本机未复现。请给原始源文件或LF规范化内容哈希：mc_to_user_interface.v、ph1p35_324_ddr_wrapper.v、hdmi_tx.v、measure_background.v、camera_to_dsi_display.sdc。不可仅凭SHA差异认定RTL变化。详见第五稿TD_INPUT_HASH_CHECK.json。',small=True)
line('以上5项的补证位置或仍保留的来源限制')
line('哪些资料可直接引用既有仓库；哪些尚缺/谁补')
p('资源与时序用最终整机P&R；独立架综合、阶段报告或中止布线另列。STA正裕量不替代CDC/板测。内部同帧延迟尚未集成，缺少这一路时保留未完成，不为文档改MAIN。',small=True)

# 19
title('19 最终展示与性能声明确认');page_run()
p('主控结合本次实测决定最终展示范围。每项填“已展示且有证据 / 部分 / 未测 / 未实现”，并写证据位置。源码已接入不自动等于现场验证通过。')
table(['功能或指标','当前已知边界','本次结论/证据/允许表述'],[['MIPI→HDMI及Logo','基础链路/Logo已实现；本SHA基础与长稳待测',''],['五基础模式与七模式切换','实际按键/阈值/切换连续性由第3页记录',''],['颜色一致性筛查','RGB码值/比例状态；非标准ΔE测量',''],['厘米/背景/平面尺寸','X/Y共尺度；粗测；须独立误差与失效记录',''],['圆片D/R','操作者手选；D水平外径、R=D/2；非自动识圆',''],['红色跟随框','LAST结果有滞后/合并；蓝色未集成，非多ID',''],['运动与图像调节','块均值帧差；沿用AWB，AE关闭；GLOBAL非唯一原因',''],['实时性与延迟','分刷新/源计数/光学；内部同帧计时未集成',''],['稳定/资源与时序','有限条件下的现场统计；余113 Slice/3 ERAM及约束覆盖风险','']],[3.2,7.0,7.2],1.0)
h('已登记简介与现作品的差异说明')
p('名称/简介锁定，文档据实解释：YCbCr改HSV红色；蓝色尚缺；控制改K3循环；LAST完整框已接入但待本版实测；新增颜色比对、厘米/背景尺寸、手选D/R及运动观察。新增项不能替代原承诺未完成项的说明。',small=True)
line('最终保留的演示顺序/模式与样品；删去的未验收能力')
line('可写进性能表的实测结论及条件；未测项目如何说明')
line('负责人/确认日期；本次最终展示bit SHA记录位置')

# 20
title('20 技术报告材料收齐核对');page_run()
p('按官方五部分逐项核对。覆盖当前已知缺口的目标是减少反复补拍；若更换bit/硬件/参数，或异常仍需查明，后续可能需要定向补测。')
table(['官方模板位置','对应材料与入口','已齐/缺项/文件'],[['摘要/第一部分','第19页最终能力、应用场景、真实性能与创新依据；限字由撰稿检查',''],['2.1 系统整体','第18页系统框图、模块/数据/时钟关系及固定来源',''],['2.2 硬件/机械/电路','第2/15页实物和量测；第18页总体/局部设计图及关键I/O',''],['2.3 软件总体/模块','第18页层次流程、接口、位宽、同步/延迟、PC工具角色',''],['3.1/3.2 成果','A01正面/45°及机械/电路局部；同bit基础/应用UI组图',''],['3.3 功能性能','E00—E12原始记录、真值/仪器、对照/失败/误差/长稳/实时性',''],['第四/第五部分','第18/19页演进/局限/改进方向与可核实参考出处；引用≤20','']],[3.7,8.7,5.0],1.05)
h('离场前确认')
check('每个拟写的功能/指标都有输入条件、操作、原始数据/图片和结论，且能追溯同一bit。')
check('尺→R3→空台面BG→放件是完整过程；真值、样品、标定/背景ID和单位可互相对应。')
check('成功、失败、无效、取消、未测分开；有样本数/分母/真实观察窗，未用重复刷新充新样本。')
check('原件可打开、数字清晰、图组齐全；完整运行与实际观察覆盖分开，记录缺口已说明。')
check('不能取得的仪器/内部计数/功能写限制并由主控确认；不以估算或0填补实测。')
check('公开提交副本按官方模板不出现学校名称等身份信息；原始私有证据保留。')
h('本次收集结果')
p('[ ] 已足以撰写当前版本且各声明有据  [ ] 有缺项但按限制/未测写入  [ ] 仍需补拍补测')
line('必须再补的最小事项/原因/负责人/时间',2)
line('门户最新格式/大小/截止要求的核对日期与来源')
line('复核人员与日期；填写版/原件/工程资料的统一目录')


# Avoid orphan headings and reset inherited blue hyperlink styles.
for pp in d.paragraphs:
 if pp.style.name.startswith('Heading'):pp.paragraph_format.keep_with_next=True
for name in ['Hyperlink','FollowedHyperlink']:
 if name in d.styles:
  d.styles[name].font.color.rgb=RGBColor(0,0,0)
d.save(OUT)
(R/'FIELD_WORKBOOK.md').write_text('\n'.join(md),encoding='utf-8')
(R/'BUILD_INFO.json').write_text(json.dumps({'date':'2026-11-02','docx':OUT.name,'intended_pages':20,'page_titles':page_titles,'candidate':'INSPECTION_SHAPE_TRACK_V1','engineering_head':'4d0f779cefd680363b8a3f0d4d5c33a42d81197f','bit_sha256':bit,'source_document_commit':'470f6d97ae9692b4b08b839f760f4ba85086936b','purpose':'Blank on-site collection workbook; no measurements invented; no RTL changes','sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'path':str(OUT),'planned_pages':20,'tables':len(d.tables)},ensure_ascii=False))
