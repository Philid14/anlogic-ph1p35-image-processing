# 最终技术文档 V1

2026-11-04。依据最终代码 `final-submission-v1.2` / main `6055a560b020373e77328e7518d200e358401363`，纳入用户提供的最终展示视频。已登记作品名称保持“基于安路FPGA的实时图像处理与颜色目标检测系统”；没有修改官网已锁定的名称或简介。

- [正式 Word 定稿：38页](技术文档_最终定稿_V1.docx)
- [同内容在线正文](TECHNICAL_REPORT.md)
- [主控提交前核对及证据边界](FINAL_DELIVERY_REVIEW.md)
- [最终展示视频的十主题索引](MEDIA_INDEX.md)
- [官方模板对照及本次变动](TEMPLATE_COMPARISON.md)
- [验证命令、结果及适用范围](VERIFICATION_LOG.md)

报告沿用官方五部分结构，包含19个编号图组、32幅嵌图、15张表及20条参考文献；加入T/L同时标注、改进运动提示、真实内部计时设计、最终资源优化与独立重建结果。赛题全部基础、扩展和进阶方向逐项对应；方案演进解释从原单一颜色框选到固定工位颜色筛查与薄工件尺寸的变化。

最终源码、可烧录文件、展示视频是三个独立身份：

| 对象 | 固定身份 |
|---|---|
| 最终交付代码 | `final-submission-v1.2` / `6055a56` |
| 独立TD重建源码 | `6432c918fea3b8ea25d65f5c5fe3816400b0cbfe` |
| bit | `artifacts/bitstreams/FINAL_SUBMISSION_REBUILD_V1/camera_to_dsi_display.bit` |
| bit SHA-256 | `ce6d17efe38297709ff71f24fd57f260270e16ff1bb6ed7031f5a03adc866515` |
| 展示文件F01 | `11月3日(1).mp4`，171.20秒；SHA见MEDIA_INVENTORY.json |

用户确认工程完成、GitHub最新代码为最终版。视频含剪辑与历史片段，没有记录下载bit哈希，故不把各镜头全部绑定到独立重建bit。归档的精确版本板测字段仍为NOT_RUN；本次未代改该事实。报告作为最终文稿交付，独立尺寸精度、连续长稳和真实毫秒延迟保留未量化说明。

特别注意：视频运动段仍可见DEMO，延迟主题未证明有效样本N持续增长。真实计时功能的源码/仿真/整机构建完成与DEMO录像是不同证据，DEMO数值不能作为性能。详见主控核对表。

本目录独立新增，V7及更早文稿和证据保持原样。原始视频370MB不入Git，保留哈希、时间索引及两幅完整变光抽帧；渲染QA文件只在本机保存。正式报告以Word为准，Markdown用于在线审阅，原生公式在Markdown以文字说明。

在仓库根目录运行 `python docs/technical_report/FINAL_REPORT_V1/verify_package.py --check-git` 可只读复核文档包、固定源码对象和bit。需要核对本机视频时追加 `--video "视频完整路径"`。检查PASS仅表示所列包装/对象复核通过，不表示实板性能全部通过。
