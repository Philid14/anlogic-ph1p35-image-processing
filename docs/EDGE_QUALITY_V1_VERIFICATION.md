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
python -m pip install -r tests/requirements-edge-denoise.txt
python tests/edge_quality_model.py
python tests/run_edge_quality_v1.py --full
python tests/run_edge_nms_v1.py --full
```

原始日志随candidate归档。新测试的golden由独立空间模型产生；每个完整帧230400拍/172800字，边界清黑不减少计数。实际厂商MIPI/AWB/DDR/HDMI PHY未进行全系统仿真。

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
