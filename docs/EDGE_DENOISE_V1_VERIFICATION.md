# EDGE_DENOISE_V1 验证记录

本记录区分合成模型、RTL、完整TD构建和真实上板。参考基线为edge-control-v1-candidate；MAIN任务分支codex/main/edge-denoise-v1，TEAM_PROTOCOL_V1。完整构建源码和资源以归档BUILD_INFO为准。

## 1. 软件模型先于正式RTL

研究提交a3796fe在正式RTL变更之前保留了13个合成场景、三算法各13阈值扫描，共507行CSV。NumPy2.3.5、Matplotlib3.11.2；无真实RAW/RGB采集帧，参考图不是实拍。原Sobel整数灰度/像素对平均/边界/核与既有二维参考70组结果相同。细节和指标定义见EDGE_DENOISE_RESEARCH.md；不根据同一固定阈值宣称算法优劣。

## 2. 联合RTL与旁路回归

复用实际edge_control_stream、edge_detect_96、edge_status_osd、冻结osd_char_lib、真实96→128打包器和isp_top；仅demosaic/AWB边界用既有stub与force注入，不模型化厂商MIPI/DDR/HDMI PHY。独立图像模型用二维空间切片，未照搬流水或RAM地址状态机。

- Gaussian独立双样本测试：四完整64×16帧与截断/黑帧恢复，共1282有效拍；输入覆盖全255、全0、完整0..255随机值与斜坡，验证12bit加权总和/一次截断、4拍data/valid/user/last/threshold、提前及同拍SOF、有效拍气泡、行末及旧行残留屏蔽。
- 新联合测试：黑/白/均匀、亮点、随机/固定行列/混合噪声、强/弱阶跃、水平/垂直/斜边、细线/纹理及独立RGB随机，阈值10/20/40/60/80/100/120/160/250；ORIGIN与EDGE连续切换、帧内快速请求、提前60拍/同拍SOF、消隐变化及旧帧尚在11拍流水内就收到新SOF、错误提前tlast、截断帧后新帧恢复。
- 逐拍比较7拍旁路或11拍Gaussian路径的data/valid/user/last；实际打包后的每个128bit字和SOF再延迟1拍。1280×720另比对实际isp_top运行时分支及打包后行尾补偿。
- OSD独立生成MODE及三位十进制字符串，字体作为冻结数据读入，逐像素核对两行/底色/位置/全部采样值；Original区域外逐字节一致。按键、CDC和Sensor隔离逻辑未改，重跑原control完整测试：200快速CDC请求逐包一致、116次初始化写入后50组按键无新增Sensor写入（I2C握手stub，不是实板寄存器读回）、全256个十进制值。

运行命令：

```text
python tests/edge_denoise_model.py
python tests/run_edge_control_v1.py --full
python tests/run_edge_denoise_v1.py --full
```

Python依赖见tests/requirements-edge-denoise.txt，RTL需Icarus Verilog。运行结果和实际拍数在build_evidence/rtl_*.txt中保留；不能以测试脚本存在替代实际PASS。

### 本次实际结果

`run_edge_control_v1.py --full`退出0：1293320有效拍、969990打包字，含四完整720p旁路帧。`run_edge_denoise_v1.py --full`退出0：下表所有case通过，总1764876有效拍、1323657打包字（含小尺寸旁路case）；独立Gaussian另1282拍。

| DENOISE_ENABLE | 尺寸 | 有效拍 | 128bit字 | 检查结果 |
|---:|---|---:|---:|---|
| 0 | 64×16 | 6916 | 5187 | 26帧及截断/恢复PASS |
| 1 | 64×16 | 6916 | 5187 | 26帧及截断/恢复PASS |
| 1 | 1280×96 | 829444 | 622083 | 26帧及OSD/恢复PASS |
| 1 | 1280×720 | 921600 | 691200 | 四完整帧及实际ISP/打包PASS |

保留原始full输出的`frames=4+recovery`是打印标签错误，完整帧case实际只有上述四帧；截断恢复属于其他case。脚本在构建前仅修正此打印标签，不更改激励、比较或RTL。

## 3. 已定义时空行为

Gaussian4拍+Sobel5拍=9拍分支，Original/config同样9拍；OSD2拍、打包1拍，总12拍，比旧版增加4个MIPI接收时钟周期。增加的是寄存时钟延迟，空间核仍有因果依赖；不把额外历史行误称为额外整帧延迟。

640×720样本、每拍两个样本、96bit输入每行320有效拍；每完整帧230400有效输入拍，172800个128bit字。Gaussian需要两历史行10240bit，Sobel原两行10240bit，合计四行20480bit；实际映射以综合报告为准。

最终中心约为原(x−4,y−2)，首4行/首8原像素置黑；右/下不补额外样本，因此保留有效因果输出和总拍数。编译DENOISE_ENABLE=0恢复旧中心(x−2,y−1)、首2行/首4像素及5拍Sobel。帧通知与配置同流水，SOF后的边界屏蔽阻止旧RAM参与有效输出。

## 4. 冻结、构建与实板边界

194个主工程冻结文件、68个只读参考文件、3份原理图SHA检查；包括按键/CDC、OSD字库/布局、Sensor初始化及控制、AWB、demosaic、DDR、HDMI、ADC/SDC、PLL。主要变更仅Edge滤波及局部延迟/参数/输入清单；不改TARGET/LATENCY内容，也不宣称已实现其帧身份接口。

完整TD日志、资源、时序、warning和新bit以BUILD_INFO及build_evidence为证据；实际生成时间和SHA同时校验，TD进程退出0不能单独作为成功依据。首轮独立Gaussian测试曾因无效拍阈值复位值的测试预期不一致而失败；修正为在valid/SOF检查阈值后通过，未因此更改算法。

真实实板降噪效果、20次模式切换、Logo/CNT/HDMI连续性、光照变化和至少30分钟运行仍待用户测试。软件/RTL没有模拟实际SC500CS噪声特性；当前DDR整体是否撕裂/溢出不由此测试证明。candidate完成即停止，按EDGE_DENOISE_V1_BOARD_TEST.md做同场景双bit及各自阈值扫描。

## 5. 实际完整构建结果（2026-10-16）

实际源码`b78dd6b43730c69896bf99753c6b961c3f44a9ae`，Synthesis日志`td_20261016_212319.log`，Physical日志`td_20261016_212757.log`；两个进程退出0，均无ERROR且完整流程已完成，21:32:42生成新bit。最终路由LUT6 15163（71.47%）、FF14667（34.57%）、Slice16859（79.46%）、ERAM20K39、DSP9；Setup/Hold WNS +0.112/+0.020ns、TNS0、违例端点0。

相对EDGE_CONTROL_V1增加439 LUT6、250 FF、386 Slice，ERAM/DSP不变，位于预先提出的800/1000/1400增量预算内。全设计DRAM LUT808（原552，增加256），shifter LUT168（原160），F7MUX64（原32）。Gaussian层级路由报告：logic LUT258、FF250、DRAM LUT256、F7MUX32、ERAM0、DSP0；门级综合前期373 logic LUT/261FF只是阶段值，最终以路由报告为准。总设计差额包含重新优化，不能将其简单全视为Gaussian模块资源。

最差setup在冻结的HDMI_PIXEL_CLK：`u_hdmi_mixer/mult0_syn_59.clk`→`u_hdmi_mixer/O_hdmi_data_reg[10]_syn_2.imf`，slack0.112ns，数据路径12.925ns，12级逻辑；关键路径摘录随bit归档。MIPI_RX_BYTE_CLK本域Setup WNS+4.366ns。STA覆盖96.16%，SDC/PLL/时钟均未改；既有异步分组不等同于所有异步行为获得STA证明。

没有新增关键warning类型，既有PHY-5060/5079保留；Gaussian两行RAM新增两条SYN-5041（与旧Sobel相同类型），说明ram_style=block提示未采用、按AUTO推断为上述DRAM，不宣称映射ERAM。新增算法无锁存/多驱动告警。

最终59项TD输入及syn/phy清单与构建提交一致，194/68/3冻结检查通过，11个旧归档bit与origin/main逐字节一致。新bit大小1789539bytes，SHA256 `224D4BE2F53B807137E19D095DCF6132BAA9CFC023C3C59BCE17ABDE3332B84A`。详见归档BUILD_INFO及SOURCE_MANIFEST；仍未真实上板。
