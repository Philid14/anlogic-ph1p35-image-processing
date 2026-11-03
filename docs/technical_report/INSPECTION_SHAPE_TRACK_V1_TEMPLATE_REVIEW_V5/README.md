# 技术文档第五稿 主控审阅入口

以最新INSPECTION_SHAPE_TRACK_V1候选为准：工程`4d0f779cefd680363b8a3f0d4d5c33a42d81197f`，TD`517697c7f3ad3328ed62a976867b5185fbcb7df0`，板测**NOT_RUN**。本次仅文档，不改MAIN/RTL/阈值/约束/bit，不合并PR。

- [正文Markdown](TECHNICAL_REPORT.md)
- [Word第五稿](技术文档_形状与跟随框候选_官方模板第五稿.docx) / [PDF第五稿](技术文档_形状与跟随框候选_官方模板第五稿.pdf)
- [主控实验清单E00…E12](MAIN_EXPERIMENT_LIST.md) / [已有与缺少现象](EXPERIMENT_STATUS.md)
- [原版与现版及演进](APPLICATION_EVOLUTION.md) / [空白记录表](EXPERIMENT_RECORD_TEMPLATE.csv)
- [合理借鉴的出处与实际采纳](AWARD_REPORT_REFERENCES.md) / [模板调整](TEMPLATE_COMPARISON.md)

先审：新背景学习、手选D/R、LAST外框的真实语义；基础及新流程仍待板测。先测E00/E01/E02和E04→E11→E05，再补E12/E06，颜色/运动/恢复分组进行。重点保留成功与失败，不以合成140px例或旧CAL:OK冒充新实测。

相对第四稿：应用流程先行、增加实际方案取舍和成组图/数据计划；按最新候选修正旧“完整框未接入”、资源/STA及数字覆盖；新增背景/D/R实验，明确B/S为FIFO-full事件帧HEX计数。登记名称/简介、官方五部分不变，原版本资料完整保留。

## 构建来源核验的保留项

89个TD输入在固定源码提交、归档与候选HEAD中Git内容一致；归档原始字节SHA中28项直接匹配、56项转换Windows换行后匹配、5项未能在本机复现。不能把未复现直接说成RTL变化，也不声称全部原始字节均独立匹配。请构建方为5项提供LF规范化内容哈希或保留原始源文件；列表见[TD_INPUT_HASH_CHECK.json](TD_INPUT_HASH_CHECK.json)。bit自身SHA已独立匹配。
