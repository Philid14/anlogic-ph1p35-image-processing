# 作品简介 V2 与实测补证：请 MAIN 审核

2026-10-31 / TARGET / 仅文档交付。

用户要求：“上传至github，让主控审核，同时重点强调说明之前所需的实测现象等，让主控进行说明，解释它们可以如何提高简介的水平”。本目录是该请求的独立审阅包。

**请主控优先回答：每项实测要观察什么、现象意味着什么、能支持或推翻简介中的哪句话、取得证据后应怎样改写。仅回复‘效果不错/可以’不足以完成这次材料审核。**

## 阅读入口

1. [名称与418字符简介](INTRODUCTION_V2.md)：建议名称“色尺—安路FPGA视觉检测系统”，15字符。
2. **[实测现象、记录方法及如何提升简介](MEASUREMENT_PLAN.md)**：本次重点。
3. [主控逐项回复模板](MAIN_REPLY_TEMPLATE.md)：要求给出证据、解释与建议措辞。
4. [板测记录空模板](BOARD_RUN_TEMPLATE.md)：尚未产生实测数据，不能把模板当实验结果。
5. [赛题逐项完成度](REQUIREMENTS_STATUS.md)、[公开获奖介绍参考与官网限制](REFERENCE_RESEARCH.md)、[用户初版原文](INITIAL_SUBMISSION.md)、[来源索引](EVIDENCE_INDEX.json)。

## 两个基线必须分开

| 内容 | 版本 |
|---|---|
| 本文档分支起点 | origin/main `c42168e26026425660f2a6f51eec76b04c85eea0` |
| 文档分支 | codex/target/submission-intro-review-v2 |
| 当前展示候选（用户确认口径） | INSPECTION_UI_DIMENSION_V1 |
| 展示候选参考文档/源码提交 | `7cffe56c384340f59a526da80a2ac3f3018bf209` |
| 真正TD构建输入 | `d26a591a399f70259944671956c7a801d9674b6d` |
| candidate tag | inspection-ui-dimension-v1-candidate |
| 归档bit SHA256 | 2003bbcc9f205b488ba566d7606e16416335b28dec738810827e296d62b62adc |

文档从最新main起步，**不表示当前展示候选、旧TARGET或LATENCY已经合入main**。主控审核功能应使用表中候选及下列固定提交来源，不能只看本分支的旧main生产代码。

- [候选交付报告](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/7cffe56c384340f59a526da80a2ac3f3018bf209/docs/INSPECTION_UI_DIMENSION_V1_REPORT.md)
- [候选设计与标定边界](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/7cffe56c384340f59a526da80a2ac3f3018bf209/docs/INSPECTION_UI_DIMENSION_V1_DESIGN.md)
- [候选板测步骤](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/7cffe56c384340f59a526da80a2ac3f3018bf209/docs/INSPECTION_UI_DIMENSION_V1_BOARD_TEST.md)
- [BUILD_INFO](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/7cffe56c384340f59a526da80a2ac3f3018bf209/artifacts/bitstreams/INSPECTION_UI_DIMENSION_V1/BUILD_INFO.md)

## 当前状态

用户确认实物框架、顶部俯拍、置物面、遮光、可调照明及基本视频/五模式/Logo/显隐开关完成。颜色实际效果、尺寸误差、长稳/明暗/缓存、实测FPS/延迟仍未测。10月30日旧显隐反馈与BUILD_INFO的历史NOT_RUN/PARTIAL原样保留；本次口头更新不能倒写成历史测试通过。

红蓝动态框选是否保留继续按用户要求暂缓。主控可核对措辞与当前候选一致性，本PR没有新增跟踪、MAIN接线、阈值调整或固件任务。

## 请主控交回

- 在PR对当前文档提交审核，确认名称/主线/功能边界及15/500字符限制。
- 按MAIN_REPLY_TEMPLATE说明每项实测如何提高简介的可信度与辨识度，确认测试样本和判断准则；缺数据写未测，不代填结果。
- 如已有本轮未知的真实数据，提供实际版本、原始日志/照片/视频和测量条件；由此提出不超过500字符的更新句或替换稿。
- 只确认已审阅的SHA；后续追加文案或实测结果需重新审核。GitHub审阅不自动等于人类最终验收。

本交付只有文字、来源和空记录模板；无RTL/约束/bit变化，无新增综合、P&R或上板结论。
