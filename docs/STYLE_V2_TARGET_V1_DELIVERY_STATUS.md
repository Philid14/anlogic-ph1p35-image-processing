# STYLE_V2_TARGET_V1 candidate交付状态

2026-10-22构建通过；2026-10-28 / MAIN补记：**真实上板FAIL：Logo/CNT正常，但无摄像头底图、无MODE/B/S及TARGET底部面板；旧STYLE V2同接线正常。** 原bit/tag保持不变，故障定位见STYLE_V2_TARGET_V1_BLACK_SCREEN_DIAG.md。

## 版本追溯

- Version：STYLE_V2_TARGET_V1。
- Branch：`codex/main/style-v2-target-v1`。
- 实际TD源码commit：`7c7e5ee7d6c52260bcf557d9dabd4014f84e2687`；其后验收/归档提交不改变85项TD输入。
- Candidate归档commit：`24dbb6b7611c3f71aa90021807b27dfd3e425500`（tag固定指向此提交）；后续仅补推送回执，不移动tag。
- 验证commit：`a745b073abca71f48d397bedbd578c55b84fdf89`。
- Candidate tag：`style-v2-target-v1-candidate`；归档commit由该tag唯一恢复，已有tag不移动。
- Draft PR：[PR #14](https://github.com/Philid14/anlogic-ph1p35-image-processing/pull/14)，base=`codex/main/edge-style-fill-v2` /89093f4，依赖PR13；保持Draft、不合并。
- Remote：origin=`https://github.com/Philid14/anlogic-ph1p35-image-processing.git`，API核实Private。
- Push Status：**SUCCESS**；candidate归档提交及tag已push，远程refs逐项核实；回执见`docs/evidence/STYLE_V2_TARGET_V1/candidate_push_20261022/`。
- Git Status：本任务变更单独暂存；无关研究文档、用户参考工程/PDF/录像/进度文件保持原样未提交。
- Bit：[camera_to_dsi_display.bit](../artifacts/bitstreams/STYLE_V2_TARGET_V1/camera_to_dsi_display.bit)，1789539 bytes。
- SHA256：`2172E53406AF5D67BD2A167C8935F6C9870CC0AC6E79382217F13024DF7888FF`。
- [BUILD_INFO](../artifacts/bitstreams/STYLE_V2_TARGET_V1/BUILD_INFO.md)、源码manifest、初始化数据、设置及原生构建证据位于同一归档。

## 最终物理结果

| 指标 | 最终route20 | 说明 |
|---|---:|---|
| Slice | 19952 /21216，94.04% | 比最初21825少1873，余1264 |
| LUT6 | 18063 | 与gate原生LUT24255口径不同 |
| FF | 21649 /42432，51.02% | 保留64位时间/16位诊断 |
| ERAM20K | 99 /108，91.67% | 余9；显式Logo映射共10ERAM |
| DSP | 21 /40 | 未增加图像算法 |
| Setup WNS | +0.165ns | Routed Slow/Fast |
| Hold WNS | +0.020ns | Routed Slow/Fast |
| Setup/Hold TNS | 0 /0 | 无违例 |

## 改动与完整回归

无损Logo字典映射官方ERAM、脉冲消费邮箱去重复目的副本且消费后ACK、台账latest索引、共享字形流水、固定延迟payload的等价无复位存储。
联合验证还发现并修正TARGET事务读RGB/控制两拍不齐；该修复与资源优化分别有证据和负对照。
TARGET原算法目录与49641eef逐字一致；STYLE V2/五模式算法、Sensor/ISP参数、按键、Logo像素、视频规格、PLL/SDC均保留。

- 原生ERAM/GSR、像素/命令FIFO及实际MAIN/MC路径：final18完整210ms、52405117检查、8次172800字提交，最终HDMI逐像素比对通过。
- fault19：29904827检查，MC停顿/溢出/packet error/校准恢复，写排空；active21另在pending=1且leased=1时注入epoch，24648825检查通过。
- 720p五模式/K3/K4/OSD/packer、台账晚到/乱序/取消/租约、506位CDC复位/停钟/原子性及提前ACK负对照、显示14场景/真实首输出年龄均通过。
- 官方Logo模型32768地址及1237512光栅周期与旧版完全等价；TARGET独立handoff16任务通过，不改写其历史integration_ready:false。
- 全部源/证据SHA由FINAL_VERIFICATION与bitgen前后门禁核对；失败实验和中止route10保留。

## 尚需实板与独立风险

7类邮箱1706端点以及36位FIFO Gray路径在本次Routed DB独立检查通过。
旧全局async造成原Gray约束覆盖缺口未修复；未来重建仍须重审。相机/I2C原有PHY-5079/5088告警存在，未以STA通过抹除。
STA coverage95.73%，本轮没有证明MTBF、真实MIPI/DDR PHY或长期无溢出。
资源仍紧；保持候选范围，停止下一阶段。详见[CDC审查](STYLE_V2_TARGET_V1_CDC_REVIEW.md)。

按[实板步骤](STYLE_V2_TARGET_V1_BOARD_TEST.md)执行3次冷启动、五模式及红目标出现/移动/消失、明暗变化、30分钟B/S与诊断增量。
稳态S增长或花屏/错位/混帧均阻断验收。原STYLE V2回退tag/bit/SHA全部保留。

设计选择、各轮物理面积和失败证据见[优化记录](STYLE_V2_TARGET_V1_OPTIMIZATION.md)；完整验证范围见[VERIFICATION](STYLE_V2_TARGET_V1_VERIFICATION.md)。
