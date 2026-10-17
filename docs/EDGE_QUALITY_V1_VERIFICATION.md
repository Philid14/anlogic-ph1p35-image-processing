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
