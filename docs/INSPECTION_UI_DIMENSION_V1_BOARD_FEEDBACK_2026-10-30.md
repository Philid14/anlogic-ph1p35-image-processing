# INSPECTION_UI_DIMENSION_V1 首次界面反馈

日期：2026-10-30。角色：MAIN。范围：解释实板开关行为、修正操作文档；不改RTL、引脚、bit或既有tag。

## 版本与证据

- 用户当前测试版本：INSPECTION_UI_DIMENSION_V1，candidate tag `inspection-ui-dimension-v1-candidate`。
- 实际TD源码：`d26a591a399f70259944671956c7a801d9674b6d`；归档commit：`dfbec5818de58925852e06554c1d8fa0c8bf1d31`。
- Bit：`artifacts/bitstreams/INSPECTION_UI_DIMENSION_V1/camera_to_dsi_display.bit`。
- SHA256：`2003bbcc9f205b488ba566d7606e16416335b28dec738810827e296d62b62adc`；本次未由实板回读确认烧录文件。
- 原始证据是本对话四张用户拍屏，顺序为全部OFF、仅第一路ON、仅第二路ON、仅第三路ON。
  用户确认每次其余路均恢复；追加测试为仅第二路ON时再将第四路ON，界面不变。
- 原图文件在用户Temp目录，未复制上传包含人物反光的照片；这里保存可核对的文字转录。

## 确认的界面现象

| 状态（沿用用户物理路数及OFF/ON称呼） | 画面转录 |
|---|---|
| 全部OFF | CAL Y 100.0 MM，SPAN0256，竖直导线 |
| 仅第一路ON | CAL X 100.0 MM，SPAN0256，水平导线 |
| 仅第二路ON | 两只颜色框和REF/TEST/ABS面板；REF约22/20/19，TEST约20/18/17，BLACK/BLACK |
| 仅第三路ON | 大黄色工作区和十字；W/H、GAP横线；CUT130 BRIGHT CAL:OK；NO VALID OBJECT |
| 第二路ON，再开启第四路 | 用户反馈界面完全不变，颜色显隐未得到验证 |

原说明将SW0～3逻辑向量编号直接等同实板第1～4路，缺少硬件验证；现在撤回该物理顺序说明。
第一路行为对应轴/极性、第二路对应关闭尺寸、第三路对应退出标定。不能据排除法指定第四路为颜色控制。
对应是由界面推断，未直接测量GPIO；不能把用户称OFF等同逻辑低电平。

源码inspection_control直接同步输入，高电平为启用；inspection_calibration以SW1&&SW3进入CAL，SW2为X0/Y1。
实际路由IO报告列出SW0/A4、SW1/B4、SW2/E11、SW3/D11，与归档约束一致。
这证明构建绑定，不证明板卡物理控制对应。未发现足以断言第四开关损坏、A4恒高或硬件型号错误的证据。
下一步可核对实板SWITCH区丝印/型号与原理图；若仍不能确认，再单独设计原始IO状态诊断，不盲改引脚。

## 标定与尺寸判断

CAL:OK只检查本次访问过X和Y并在尺寸启用时退出CAL，不检查尺子是否在场、刻度是否对齐。
用户此次开关测试本身足以满足该条件。照片中两个SPAN0256是默认值，尚无实际100mm对齐证据。
所以CAL:OK不能作为尺寸精度通过。黄色大框是固定工作区，NO VALID OBJECT和横线表明该帧没有有效工件测量。

按[更新后的实板步骤](INSPECTION_UI_DIMENSION_V1_BOARD_TEST.md)先确认实际摄像头图像、RUN下调好BINARY分割，
再在ORIGIN完成同平面100mm水平/竖直手动标定。使用独立参考尺寸、10次读数、旋转和位置复测评价误差。
孔/槽仅输出固定中心截线；实心片GAP无值不代表故障。

## 尚未得到的证据

- 反光很强，不能由照片确认实时图像全黑或摄像头链路故障，也不能据此宣称原图显示验收通过。
- 色框均值约20仅描述该两ROI，不代表整个尺寸工作区的亮度。
- B/S照片未见非零不能替代重置后的长时间观测，FIFO/Gray约束风险未排除。
- 尺寸准确度、重复性、光照稳定性、30分钟运行、颜色开关完整显隐均尚未通过验收。

结论：Board Test PARTIAL，保留candidate，不建立正式通过tag，不生成新bit，不合并PR。
