# EDGE_NMS_V1 验证记录

MAIN任务；基线08ea909febf2dd0952e7221a0ce2bf34b24e3b44，依赖PR #3的降噪分支；研究提交7620c16先于正式RTL。实际构建源码、完整TD资源/时序及bit以归档BUILD_INFO为准。独立软件与RTL结果不替代实际夜间画质/30分钟稳定性。

## 软件与实现对应

19个梯度场和133个二值结果与此前已RTL验证的Gaussian/Sobel整数模型相同；研究四方法、六阈值、456行CSV。保留真实gray逐分量截断、两像素floor平均、Gaussian总和一次>>4、Gx/Gy符号、L1幅值、640点采样与复制。NMS参考直接切片二维幅值/中心方向和邻居，没有复刻RTL的RAM地址/寄存状态机。Gy正向上，方向比较阈值1/2及2，相等平台按固定侧选择。

完整8邻接BFS和单邻域一跳软件对照：27点强锚弱链完整保留27点，一跳2点，无锚弱分量0点。硬件没有加入强弱分类、队列或传播；不称本bit为完整Canny。

## 单元与逐采样点检查

- tb_nms_axis：调用实际Sobel模块中的gradient_axis函数，25组人工定义期望，包括零梯度、横纵、同/异号对角、恰好1/2边界和相邻值、符号反转、13bit负极限−4096，检查移位宽度和Gy向上约定。
- tb_nms_gradient_pair：输入完整14bit幅值（含16383及随机0..16383）、四轴和随机方向、全零/常值平台、同拍/跨拍相等双峰；比对真正中心幅值、中心方向、严格/非严格两个14bit邻居、keep和抑制后幅值。两个平台奇偶位置各确保每有效行只保留一个峰；不因梯度正负改变比较轴。9完整输入帧及截断/黑帧恢复，共2564拍，4200有效中心采样点；带气泡、早SOF/同拍SOF和14bit门限元数据同4拍。
- tb_edge_nms_stream：逐输入拍附独立空间Gx/Gy、幅值、方向，分别在S3(含Gaussian共7拍)、S4(共8拍)检查实际内部值；不只比二值图。输出同时比较15拍data/valid/user/last（旁路11拍）、原字库OSD、实际打包器每一个128bit字、SOF再1拍和完整720p真实isp_top行尾补偿。
- 输入包含黑/白/灰、点、随机点、横/竖/原像素45°/内部采样网格45°/任意斜边、强/低对比阶跃、模糊阶跃、双边、细线、曲线、文字、编织、随机/固定/混合噪声及独立RGB随机。覆盖42个模式/阈值/场景组合再截断/恢复，包含行首/行尾、帧末、提前60拍及同拍SOF、消隐变化、帧内高频请求、新SOF时旧帧尚在流水、错误提前tlast、无反压持续吞吐。

## 旁路、控制与冻结

NMS_ENABLE=0在小尺寸新中间量测试和原tests/run_edge_denoise_v1.py --full的四完整720p回归中核对，恢复原降噪算法9拍分支、11拍含OSD。DENOISE_ENABLE=0原Sobel小尺寸回归也保留；NMS候选只使用DENOISE_ENABLE=1/NMS_ENABLE=1。

另外实际执行旧按键/CDC/Sensor/decimal单元：按键抖动/一次事件/短长互斥/饱和；200异步快速请求逐包原子性/顺序；116次初始化写入后50组按键无新增Sensor写入（I2C只用握手stub）；三位十进制全256值。Top中ae_set继续解除，Sensor请求保持0。

195主工程冻结文件（新增保护Gaussian）、68只读参考、3原理图SHA一致；原按键、CDC、OSD字库/布局、Sensor、AWB/demosaic、MIPI/DDR/HDMI/PLL/ADC/SDC未改。只改变NMS、局部参数/延迟与新增输入文件。不修改PR #3分支、TARGET/LATENCY目录或外部帧身份接口。

## 运行与证据

```text
python tests/edge_nms_model.py
python tests/run_edge_nms_v1.py --full
python tests/run_edge_denoise_v1.py --full
```

Python依赖沿用tests/requirements-edge-denoise.txt，Icarus执行RTL；原始输出随candidate存build_evidence。完整帧应各230400个96bit拍/172800个128bit字，不能因新边界黑区而减少计数。

## 时空边界与实板限制

Gaussian4+Sobel前四级4+NMS4+原阈值S5=13拍Edge；Original/9bit配置同13拍，OSD2+打包1，总16拍，比旧版多4个接收周期。实际空间中心约(x−6原像素,y−3行)，首6行/左12原像素置黑；右/下不补额外数据，分辨率仍1280×720。tuser仍提前通知，tlast仍行尾，状态仍随DDR前图像缓存。阈值为帧常量，邻域有效时中心/邻居均属本帧。

未模拟厂商MIPI/AWB/DDR/HDMI PHY，未进行实板寄存器读回或长期测试；Sensor握手stub不能证明物理I2C ACK。软件真值/厚度是合成模型口径，不能冒充真实目标识别率。旧降噪上板反馈按用户描述记录，新NMS真实细化、弱轮廓断裂和稳定性等待上板，详见EDGE_NMS_V1_BOARD_TEST.md。失败构建如有须保留并明确，不以退出码0或旧bit作为成功证据。

## 本次实际RTL执行结果

源码检查点5e4c3d97de8fd591febc4dc4754e2040ed539151，两个完整测试脚本均退出0。NMS新联合测试如下，总2264588有效拍/1698441打包字；NMS单元另2564拍/4200有效中心采样检查，方向函数25组。

| NMS_ENABLE | 输入尺寸 | 有效96bit拍 | 128bit字 | 结果 |
|---:|---|---:|---:|---|
| 0 | 64×16 | 11012 | 8259 | 42组合及截断/恢复PASS |
| 1 | 64×16 | 11012 | 8259 | 42组合及截断/恢复PASS |
| 1 | 1280×96 | 1320964 | 990723 | 宽幅OSD及中间量PASS |
| 1 | 1280×720 | 921600 | 691200 | 四完整帧及实际ISP/打包PASS |

原降噪脚本NMS=0完整旁路另1764876拍/1323657字通过，包括四完整720p帧，保证恢复旧行为；Gaussian独立1282拍通过。按键/CDC/Sensor/decimal独立回归也执行通过。原始输出存build_evidence，不修改PASS日志中的计数或时间。本轮迄今未出现功能性RTL仿真失败；综合/实现结果将在完成后另补录。

首轮5e4c3d9综合完整完成，但出现3条HDL-5373（nms_valid_d/user_d/last_d先使用后声明）。随后仅把该reg声明移到首次使用前，always/assign/运算均未改变；增加--small选项，重跑25方向、2564拍NMS单元及两种小尺寸联合回归通过。此为声明顺序清理，不是算法更改或失败bit。首轮日志和门级area单独保留，最终源码由BUILD_INFO记录，重新完整综合和实现，不直接沿用首轮数据库。

## 最终TD构建补录（2026-10-16）

实际源码/配置提交 `8ae2fd6c38416095e1232783a0e63b2eb2d1e9f3`，研究提交7620c16、完整RTL测试检查点5e4c3d9和声明清理后small回归的证据均保留。最终综合日志td_20261016_232120.log，完整物理/时序/bitgen日志td_20261016_232756.log，最终两进程退出0、无ERROR、无HDL-5373。

| 路由后 | EDGE_DENOISE_V1 | EDGE_NMS_V1 | 增量 |
|---|---:|---:|---:|
| LUT6 |15163|15206|+43|
| FF |14667|15018|+351|
| Slice |16859 (79.46%)|16598 (78.23%)|-261|
| ERAM20K |39|39|+0|
| DSP |9|9|+0|
| Setup WNS(ns) |+0.112|+0.101| |
| Hold WNS(ns) |+0.020|+0.020| |

全设计DRAM LUT 1256（旧808，增量+448），shifter LUT 168（旧168），F7MUX 112（旧64）。实际NMS层级行（顺序logic LUT/ripple/seq/ERAM/DSP/DRAM/shifter/F7MUX等，详见area表头）：

```text
|        g_nms$u_nms                                              |nms_gradient_pair_3x3                          |283       |0       |325     |0       |0       |448      |0           |48      |0       |0       |0       |
```

两行逻辑容量19200bit保留14bit幅值和中心2bit方向；实际AUTO映射以该层级行及报告为准，不把逻辑bit数直接当ERAM数量。新RAM无强制block提示；既有Gaussian/Sobel/FIFO的SYN-5041仍在，未通过修改其RTL消除。关键warning类型仍为PHY-5060/PHY-5079，无新增关键类型；不是无warning。Setup/Hold TNS与违例端点均0；STA覆盖96.37%，未放宽SDC、PLL或异步分组。

归档bit SHA256 `734F5D97C429D086FBE8518514B8547CF0C2FBC485B44D35BD218F0F7FA2A448`；全部60个实际TD源码/IP/约束输入与构建提交内容匹配（只归一Git文本换行），195冻结主工程/68参考/3原理图一致；12个旧归档bit与基线08ea909逐字节相同。SOURCE_MANIFEST、PREVIOUS_BITS_UNCHANGED、FINAL_CHECKS、完整flow日志、核心area/qor/ts/exception及测试原始输出随bit归档。完整逐路径报告在忽略的Runs，摘要和关键路径另存build_evidence。

本轮没有功能性RTL失败或失败bit；首轮仅综合完成并发现3条声明顺序warning，无物理构建/bit。清理后重新完整构建，首轮日志/area保留。candidate尚未真实上板：MIPI采集、连续HDMI、细化收益、20次切换和30分钟稳定性均不能用离线仿真替代。完成candidate后停止，等待人类审查与实板反馈。

### 路径、预算与warning说明

最差setup仍在HDMI_PIXEL_CLK：u_hdmi_mixer/mult0_syn_59.clk → u_hdmi_mixer/O_hdmi_data_reg[17]_syn_2.ib，数据路径12.838ns、slack+0.101ns；MIPI_RX_BYTE_CLK本域Setup WNS+4.154ns。约束/时钟均未修改。PHY-5060涉及既有I2C scl_clk和O_cam_24m混合扇出，PHY-5079涉及既有局部时钟路由；DDR加密厂商IP中既有HDL-5369 latch warning与基线同位置，未引入NMS锁存或多驱动告警。

最终Slice78.23%低于约85%目标；全设计LUT6+43、FF+351、Slice−261是本次完整工具重映射/打包后的净变化，不代表NMS本身不花资源或占负资源。新增NMS层级实际283逻辑LUT、325FF、448 DRAM LUT、48F7MUX、0ERAM/0DSP；含方向量化、对齐及其他全设计映射变化后的净值须与该局部成本分开解释。Gaussian源码冻结但工具层级映射可变化，未为满足预算修改冻结模块。
