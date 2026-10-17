# EDGE_QUALITY_V1 验证与失败记录

MAIN任务，基线712fbb33cfc5ba8436b96306e1fe443553aa6591。研究提交46c8f18先于正式RTL。所有实际构建资源/bit/SHA以归档BUILD_INFO和原始报告为准；真实画质、物理I2C、厂商PHY与长期运行不能用离线测试替代。

## 独立参考与测试边界

- 研究模型比较13方法×29场景×8门限共3016项，空间算子不模拟RTL RAM/时钟。共同ROI补偿偏移后，因果逐层模型与直接邻接迭代一致。
- tb_edge_quality_class：直接观察实际S5分类寄存器，241个high=10..250（包括奇数）、low=floor(high/2)边界−1/相等/+1、high边界、keep掩码和14bit端点0/16383，共2892采样检查；不是只测复制的分类函数。
- tb_edge_link_pair：四个真实窗口串联，逐层比weak/active和valid/user/last；全空/全弱/全强、八个邻居、拍内/跨拍奇偶、长弱链、零屏障、无锚弱链、孤立强点、随机标签、行间气泡、提前/同拍SOF、截断帧/错误tlast及黑帧恢复，共6916拍/55328采样-层检查。边界初始0，逐层递增2；正式初始6另在全链验证。
- tb_edge_quality_stream：原Gx/Gy、幅值/轴逐点仍检查；由RGB独立模型计算最终输出，再逐拍核对Original/Edge/config/OSD/data/valid/user/last，逐字检查实际96→128打包。小尺寸QUALITY=0/1，宽1280状态区、完整720p实际isp_top接线。TH10..250及30/50/70，帧内高频请求、旧帧仍在流水时新SOF、提前60拍/同拍SOF、错误行尾/截断恢复保留。
- 旧tests/run_edge_nms_v1.py --full使用默认QUALITY=0，验证恢复完整旧算法及旧15拍含OSD；旧模块/激励不修改。旧按键/CDC/Sensor握手/decimal单元另执行；Sensor使用握手stub，不代表实板ACK或寄存器读回。
- 195主工程冻结文件、68参考、3原理图以及新增保护的NMS模块SHA保持；旧归档文件不修改。Top只开启QUALITY和四跳，Sensor请求仍解除，原按键语义与外部约束不变。

## 可复现入口

```text
python -m pip install -r tests/requirements-edge-quality.txt
python tests/edge_quality_model.py
python tests/run_edge_quality_v1.py --full
python tests/run_edge_nms_v1.py --full
```

原始日志随candidate归档。新测试的golden由独立空间模型产生；每个完整帧230400拍/172800字，边界清黑不减少计数。实际厂商MIPI/AWB/DDR/HDMI PHY未进行全系统仿真。

实际软件环境Python3.12.14、NumPy2.3.5、Matplotlib3.11.2、Pillow12.3.0；单独锁定本轮直接依赖，不改历史requirements。Pillow自带默认字体可能随版本变化，复现文字图和汇总指标时应使用锁定版本。Icarus执行RTL，TD6.2.168116执行正式构建。

## 开发失败及修正（保留事实）

1. 首次软件绘图因运行时更新后缺matplotlib中断，按既有requirements安装后完整重跑成功；没有以部分CSV冒充完成。
2. 集成脚本在发现isp_top实际有两处NMS参数接线时触发数量断言，按源码核对后为两处均传QUALITY，未运行TD或生成bit。
3. 首次分类单元在TH10/j1失败：Icarus对procedural force的拼接表达式仅求值一次，测试夹具没有随a/b更新。改为持续赋值wire后force该wire；未为消除该失败改分类RTL，随后241门限/全链通过。初次原始输出随归档保留。该测试夹具失败不隐瞒为“全部首轮通过”。

小尺寸检查点：QUALITY0/1各28676拍/21507字，分别含OSD15/27拍，通过。完整RTL及TD结果完成后在后文补录；失败bit若产生需另外保留，不覆盖历史归档。

## 完整RTL执行结果

实际源码检查点`acf7d444f19ae0dbb8a36a854edc7627f7f8b2ec`。两个完整脚本均退出0；以下只统计联合RGB流，不重复累加独立单元的采样层数。

| QUALITY_ENABLE | 输入尺寸 | 有效96bit拍 | 128bit字 | 结果 |
|---:|---|---:|---:|---|
|0|64×32|28676|21507|旧NMS输出/控制/OSD旁路PASS|
|1|64×32|28676|21507|新质量链/异常恢复PASS|
|1|1280×96|1720324|1290243|宽幅状态OSD/中间梯度/打包PASS|
|1|1280×720|921600|691200|四完整帧/实际ISP/打包PASS|
|合计||2699276|2024457|PASS|

完整720p包括EDGE60眼镜、ORIGIN80独立随机RGB、EDGE50纸张、EDGE40黑帧。每帧230400拍/172800字；新流含OSD27拍，打包后28拍。其余尺寸包含55组完整场景/参数模式再截断及恢复，恢复追加完整帧，不能把有效边界变黑算丢帧。

旧NMS完整回归另2264588拍/1698441字，包括原来的四完整720p帧，NMS_ENABLE=0/1与实际Gx/Gy/幅值/方向/邻居单元均PASS。按键、异步200包配置、116次初始化后50组按键无Sensor后续写入、全256十进制显示亦PASS。原始日志不修改数值/计数；分类force夹具修复后没有出现功能性RTL失败。实际PHY/DDR长稳仍待实板。

绘图QA后仅将研究对照图的二值结果按实际HDMI横向复制两像素显示，使RGB与算法图具有相同物理纵横比；指标及RTL参考仍在原640采样坐标计算。只改research绘图分支并重新生成图/研究输出，不改变算法、RTL或完整回归的激励/期望。

## 首轮完整TD检查点 R0（资源目标未达）

源码acf7d444f19ae0dbb8a36a854edc7627f7f8b2ec；日志td_20261017_220454.log/td_20261017_220918.log。Synthesis/Physical/Timing/bitgen完整成功，退出0；LUT6 16888、FF15402、Slice18263(86.08%)、ERAM39、DSP9，Setup/Hold+0.102/+0.020ns、TNS0/违例0。未新增关键类型，但资源超过实现前目标，不作为最终上板candidate。

bit SHA256 `27FDB0B07DD1AE9196164D209DA54CF48E3867BD6F9357549AEE3100ECD0126B`，保存artifacts/bitstreams/EDGE_QUALITY_V1_R0；tag edge-quality-v1-r0-build唯一解析归档提交。未上板、不推荐烧录。后续只优化存储布局，算法、阈值和延迟不变，重新验证/完整构建。R0并非时序失败；资源未达目标的记录及bit均保留。

## R0后等价缓存优化

先验证两拍合并原型，通过64/68行宽单元和小尺寸整链，未生成该原型bit。最终采用四拍16bit word并把最上历史行缩为8个active位，逻辑缓存10240→7680bit；期望减少窄深RAM映射开销，实际资源仍以新完整路由为准。未改A4算法、高低门限、中心选择、三拍/跳或对外格式/时序。

优化后独立窗口单元已通过64/68/72/76像素行宽，覆盖全部4种打包尾数；分别6916/7348/7780/8212拍、55328/58784/62240/65696采样层检查，共30256拍/242048采样层。分类2892采样和QUALITY0/1小尺寸整链通过。接下来重新完整RGB回归和TD。旧NMS完整回归的acf7d44检查点仍有效：此次只改QUALITY生成分支内的独立缓存模块，该模块未进入旧runner编译/旧默认路径；关闭QUALITY路径源码与R0完全相同，不把旧完整日志冒称为优化后重跑。

随后将存储地址明确为clog2(WORDS)位（正式80word为7位），增加1280行宽逐层单元以覆盖全部80word及高端地址。61f7ebe较宽地址版本的完整回归在尚未完成宽幅用例时主动中断，保留日志，未判定功能失败、未生成bit；以最终源码重新统一执行完整回归，避免混合不同源码检查点。计数归纳保证x只在0..GROUPS−1，地址收窄不改变可达帧数据，最终仍以实际测试为证。

## 最终源码97858d5的完整回归与映射核对

实际源码`97858d51c7599a504a733b2302db797207c1ac0e`，完整runner退出0。联合RGB四组计数与上表完全相同，合计2699276拍/2024457字；四完整720p帧/实际ISP/打包通过。新增1280行宽单元138244拍/1105952采样层检查，连同四种尾数合计**168500拍/1348000采样层检查**；分类2892采样通过。由此对最终源码重新统一确认，不依赖中断的61f7ebe回归。

最终源码完成全量独立模块、实际生产行宽及小尺寸整链后，综合与余下宽幅/720p回归并行；布局布线等待完整回归通过后开始。综合日志td_20261017_223119.log，无ERROR/声明顺序警告，四层AUTO实际映射8ERAM/0DRAM LUT，尚须看最终路由的整机资源。

针对新ERAM同地址读写风险，另从该实际gate.db导出网表并逐个核对8个新缓存primitive：四个row1为单口READBEFOREWRITE，匹配RTL在最后一拍读旧字同时写新字；四个row2分离读写端口NORMAL，稳态读新word时写前一个word。中断帧边界即使发生同地址冲突，前14行/左28像素拒绝其数据。检查保存ERAM_MAPPING_CHECK.json和QUALITY_ERAM_MAPPING.v.txt，包含导出网表SHA与模式/连接摘录，不提交32MB完整网表。此项是网表配置核对，不冒称门级功能仿真或实际ERAM上板测试。

## 最终TD结果补录（2026-10-17）

实际构建源码`97858d51c7599a504a733b2302db797207c1ac0e`，研究检查点46c8f18；最终综合日志td_20261017_223119.log，物理/最终时序/bitgen日志td_20261017_224134.log。两个进程退出0、无ERROR、无新增声明顺序警告。源码提交后只修改文档，不修改硬件输入。

| 路由后 | EDGE_NMS_V1 | EDGE_QUALITY_V1 | 增量 |
|---|---:|---:|---:|
| LUT6 |15206|16162|+956|
| FF |15018|15423|+405|
| Slice |16598 (78.23%)|17894 (84.34%)|+1296|
| ERAM20K |39|47|+8|
| DSP |9|9|+0|
| Setup WNS(ns) |+0.101|+0.009| |
| Hold WNS(ns) |+0.020|+0.020| |

全设计DRAM LUT 1256（旧1256，增量+0），shifter LUT 176（旧168），F7MUX 112（旧112）。四个连接层级合计逻辑LUT 232、ripple 0、FF 390、ERAM 8、DSP 0、DRAM LUT 0、shifter 0、F7MUX 0。完整层级行保留：

```text
|        g_quality$g_hop[0]$u_link                                |edge_link_pair_3x3                             |60        |0       |94      |2       |0       |0        |0           |0       |0       |0       |0       |
|        g_quality$g_hop[1]$u_link                                |edge_link_pair_3x3                             |59        |0       |103     |2       |0       |0        |0           |0       |0       |0       |0       |
|        g_quality$g_hop[2]$u_link                                |edge_link_pair_3x3                             |58        |0       |98      |2       |0       |0        |0           |0       |0       |0       |0       |
|        g_quality$g_hop[3]$u_link                                |edge_link_pair_3x3                             |55        |0       |95      |2       |0       |0        |0           |0       |0       |0       |0       |
```

R0完整两位标签数组10240bit、四层512 DRAM LUT；最终四拍打包、顶行只存active，逻辑容量7680bit、地址明确7位。实际RAM LUT必须按报告判断。R0路由LUT6 16888/FF15402/Slice18263(86.08%)，最终相对R0分别-726/+21/-369，四层DRAM变化-512。全设计增量还包括Original/配置12拍对齐及工具重映射，不能仅用四个模块的FF/LUT解释总增量。实现前预算保留在研究文档，不事后改成实测值。

最差Setup在HDMI_PIXEL_CLK，Begin `u_hdmi_mixer/mult0_syn_59.clk (rising edge triggered by clock HDMI_PIXEL_CLK  { rise@0.000000ns  fall@6.666000ns  period=13.333000 })`，End `u_hdmi_mixer/O_hdmi_data_reg[15]_syn_2.id (rising edge triggered by clock HDMI_PIXEL_CLK  { rise@0.000000ns  fall@6.666000ns  period=13.333000 })`，Data Path Delay 12.952ns (cell 5.592ns (43%), net 7.360ns (57%))。Setup/Hold TNS0、违例端点0，STA覆盖96.11%；完整final_timing.rpt已归档，可核对所有时钟域。SDC/PLL/异步分组保持。既有PHY-5060混合扇出、PHY-5079局部时钟路由、旧RAM_STYLE AUTO和厂商加密DDR latch warning仍保留，无新增关键类型，不声称零warning。

bit SHA256 `629ACAA828EF8151DED0261779ED8B91F0FA618EED66DD46C72D6E799ADCC9D5`。全部61实际TD输入与实际源码提交匹配（仅Git文本换行归一）；13个NMS及以前旧bit和本轮R0共14个bit字节一致，全部历史BUILD_INFO/报告未改。SOURCE_MANIFEST、PREVIOUS_BITS_UNCHANGED、FINAL_CHECKS、实际settings、完整flow/STA及RTL原始输出随bit归档。R0时序通过但资源未达目标，bit/报告/tag完整保留；此前分类夹具失败及主动中断回归的原始输出明确标记并保留。用户Edge照片仅保存文件指纹/类型记录，不将其当RGB研究输入。

最终candidate仅等待人类审查和实板验收，实际连续性/噪声折中未确认。合成对照支持受限收益：TH60召回提高、误检也提高；TH40可能沿噪声扩散，不能只宣传优点。公平测试需同门限及相近完整度两种口径，并核对原图/按键/OSD/视频长稳。停止本轮，不自动扩展下一版本。

### 最终预算与时序裕量判断

最终相对NMS LUT6+956、FF+405、Slice+1296，满足实现前约1200/1800/1400增量预算及约85%Slice目标。ERAM增加8块（39→47/108），以空余块RAM换取Slice资源；7680bit是逻辑数据容量，不能用它掩盖实际占用8个ERAM20K块。剩余3322Slice、61ERAM块，不能保证未来任意算法都能放入。

Setup最差+0.009ns比NMS+0.101ns更紧，路径仍是冻结HDMI mixer；MIPI_RX_BYTE_CLK本域Setup+3.353ns。slow/fast setup/hold均检查通过、无端点违例，但不能把9ps余量描述为宽裕或把STA通过当作长期上板稳定。未为提高数字而修改冻结HDMI/PLL/SDC、降低视频规格或忽略违例。该限制列入候选审查和实板验收，先完成当前候选，不自行进入另一版HDMI优化。
