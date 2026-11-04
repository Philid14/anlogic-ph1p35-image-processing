# 技术文档文字结构与图组优化稿

2026-11-04，依据用户批准完成不依赖新增实验的优化。本稿对应最终代码final-submission-v1.2 / main6055a56；本次只改文档，生产RTL、阈值、约束、bit及测试结论沿用原归档。

- [正式Word优化稿](技术文档_优化定稿_V2.docx)
- [同内容在线正文](TECHNICAL_REPORT.md)
- [文字和结构修订说明](REVISION_NOTES.md)
- [图组重排及裁剪索引](MEDIA_INDEX.md)
- [官方模板对照](TEMPLATE_COMPARISON.md)
- [检查命令和适用范围](VERIFICATION_LOG.md)

本机Word原生导出32页，较前稿38页减少6页。保留五部分、原页眉页脚、原生公式和20条参考文献；正文为15个编号图组、28幅嵌图（24幅完整图及4处Word原生局部）、20张表（含图4原生关系表）。32份原图文件及原Word图像部件字节全部保留，裁剪只改变Word内的显示区域。

本次澄清16×16像素单元与48×24格、亮度有效条件与统计置信、LAST上一采集帧与同帧内部计量的差别。成果先呈现操作和现象，尺寸误差、真实延迟、长稳、背景对照、T/L实物及拍摄bit身份等状态集中在3.3.4，防止重复说明淹没已有结果。

DEMO仍明确为模拟界面数值，没有新增真实毫秒值。独立重建bit的板测NOT_RUN在3.3.5说明为缺少该精确bit身份绑定的归档记录，并不抹去已有实物录像。原始哈希审查184/191匹配、7项原始字节未闭合等细节继续保留SOURCE_EVIDENCE.json及前稿验证记录。

原[38页定稿](../FINAL_REPORT_V1/README.md)及更早版本保持原样；完整[主控补充记录说明](../FINAL_REPORT_V1/FINAL_DELIVERY_REVIEW.md)仍可使用。本轮没有补拍、修改实验数字或转录为新测量。原始视频与内部QA导出不入Git。

在仓库根目录运行：`python docs/technical_report/FINAL_REPORT_V2/verify_package.py --check-git`。需要核对本机展示视频时追加`--video "视频完整路径"`。PASS适用于文档及证据包装检查。
