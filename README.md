# 安路PH1P35固定工位视觉检测系统

全国大学生嵌入式芯片与系统设计竞赛2026 FPGA创新设计赛道，上海安路选题二。以HX1P35A/PH1P35MDG324实现MIPI摄像头采集、FPGA并行图像处理、DDR缓存、含安路Logo的OSD和720p HDMI显示，面向固定俯视工作台的颜色比对与薄工件二维尺寸标注。

**最终代码交付入口：[submission/README.md](submission/README.md)**。GitHub保持Private；主分支main，固定提交tag `final-submission-v1.2`。RAR由dist目录提供，全部代码/配置齐全，大小低于200MB。

## 当前有效版本

当前交付bit为 **FINAL_SUBMISSION_REBUILD_V1**（逻辑与LATENCY_FRAME_FIX_V1同源），真实测量源码`6432c918fea3b8ea25d65f5c5fe3816400b0cbfe`。本次从压缩包独立解压实际完成SYN/PHY/STA/bitgen，95项直接输入、96项IP支持和.al构建前后保持不变。随机延迟模拟版本不进入最终代码和提交包。

- [可烧录bit](artifacts/bitstreams/FINAL_SUBMISSION_REBUILD_V1/camera_to_dsi_display.bit) / [BUILD_INFO](artifacts/bitstreams/FINAL_SUBMISSION_REBUILD_V1/BUILD_INFO.md)
- Setup/Hold：+0.137/+0.020ns；Slice19177、LUT6 18498、FF16374、ERAM105/108、DSP25/40。
- SHA256：`ce6d17efe38297709ff71f24fd57f260270e16ff1bb6ed7031f5a03adc866515`。
- 状态：完整TD构建通过；该修复bit的真实延迟及整机长稳仍待实板。合并与代码交付不表示这些项目已通过。

## 已集成功能

七模式ORIGIN/GRAY/BINARY/EDGE/STYLE/TRACK/MOTION；双ROI颜色比较与光照/占比提示；厘米尺一键近似标定；工程制图式W/H、D/R和T/L分段标注；主红区域跟随框；密集运动点阵；真实同帧延迟面板。Sensor曝光1990 half-lines、VTS1000、HTS1600、模拟增益15.75×、BLC15、AWB_V2数值配置沿用。

[控件和重建](submission/README.md) · [实板验收](submission/ACCEPTANCE.md) · [集成记录](submission/INTEGRATION.md) · [第六稿技术文档](docs/technical_report/REAL_MEDIA_REVIEW_V6/README.md) · [版本更新说明](submission/TECHNICAL_REPORT_ADDENDUM.md)

## 目录

| 路径 | 用途 |
|---|---|
| submission/ | 最终代码入口、源清单、验收及整合记录 |
| in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/ | 正式TD工程；.al/RTL/IP/引脚/SDC/ROM保持原路径 |
| features/color_target/、features/latency_view/ | 队友独立模块及交付；是否进入正式工程以.al和INTEGRATION为准 |
| tests/、scripts/ | 软件模型、原生RTL回归、构建/归档及提交包校验工具 |
| docs/ | 赛题、团队协议、历史研究、构建和技术文档 |
| mechanical/frame_concept/ | 机械参考设计；不冒充已制造成品 |
| 3_原理图/、最终作品实现/ | 板级资料索引和用户作品需求；商业参考/未核验Sensor PDF不随包提交 |
| artifacts/bitstreams/ | Git历史候选和完整构建证据；当前bit见上方唯一链接 |
| edge_example/ | 官方边缘参考基线，保留对照 |
| local_assets/、2026-10-05/ | 本地录像/厂家参考资料，不入库、不打包 |
| dist/ | 生成的RAR与校验结果，不入Git历史 |

## 验证与提交

```powershell
python scripts/submission_package.py verify
python scripts/submission_package.py rar
```

RAR使用WinRAR原生RAR5格式，先进行完整性测试和解压后文件哈希校验，再交付。Git历史/旧bit可由固定tag恢复，不通过删除历史或改写tag整理版本。原始录制数据和用户未提交研究笔记单独保留。

工程/验收基准见[AGENTS.md](AGENTS.md)、[团队协议](docs/TEAM_AI_WORK_PROTOCOL.md)和[原始赛题](docs/赛题/上海安路信息科技股份有限公司_2026FPGA创新设计赛道选题指南.pdf)第16–18页。
