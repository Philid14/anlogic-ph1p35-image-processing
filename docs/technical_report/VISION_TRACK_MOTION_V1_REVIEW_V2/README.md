# VISION候选技术报告第二版

此稿已完成主体撰写，供主控和负责人审阅；最新候选仍为 **Board NOT_RUN**。保留原报名名称，不覆盖PR #19或PR #25初稿，不修改RTL、bit、约束或MAIN接线。

## 阅读入口

- [Word审阅稿](技术报告_VISION候选_第二版审阅稿.docx)
- [PDF审阅稿](技术报告_VISION候选_第二版审阅稿.pdf)
- [可检索正文](TECHNICAL_REPORT.md)
- [证据索引](EVIDENCE_INDEX.md)
- [待补材料与审核清单](REVIEW_CHECKLIST.md)
- [文档检查记录](DOCUMENT_CHECKS.json)

以 `VISION_TRACK_MOTION_V1`、候选审阅HEAD `123186a9d339990b207b846cb15e6a7e309c22a7` 为准；它位于[Draft PR #24](https://github.com/Philid14/anlogic-ph1p35-image-processing/pull/24)，并非已合并main。真实TD输入、归档提交、tag和bit SHA见正文3.6及证据索引。

## 相对初稿的修改

1. 将EDGE_CONTROL_V1旧内容更新为当前七模式、颜色比对、自动标尺、二维尺寸、TRACK/MOTION实际实现；保留五部分结构。
2. 加入视频数据流和时钟边界示意，明确96bit/4PPC、无ready、31拍流水与总延迟的区别。
3. 说明已登记简介与当前实现差异：YCbCr到HSV红色；蓝色未作为本候选完成；TRACK完整颜色框尚未显示；尺寸外框不能代替颜色框。
4. 使用真实完整P&R结果，与独立Logo综合估算及失败尝试分开；保留高密度、STA覆盖和CDC风险。
5. 解释RGB差不是标准ΔE、LIGHT不是颜色相同、1mm刻线对应100mm等效像素跨度、共用X/Y尺度及0.1mm显示不等于精度。
6. 增加赛题逐项对应、实板步骤、数据统计建议和空白实验表，全部缺测项明确标注。

## 审核与后续更新

本稿18页，摘要448字符；沿用初稿章节上限并执行保守逐字符检查。Word用原生Microsoft Word导出PDF，18页逐页目检并保留本地渲染记录；原初稿哈希未变。此轮没有新RTL仿真或TD构建。

最缺的是整机实物照片、当前bit的基本闭环与七模式录像、同色/异色/变光实验、双轴尺寸误差、TRACK/MOTION动态与异常恢复、30分钟以上稳定性记录，以及实测刷新/新帧率/延迟。具体字段见审核清单。补齐时应同步修改Markdown、Word和PDF，并再次导出检查；不能仅将“未测”替换为“完成”。
