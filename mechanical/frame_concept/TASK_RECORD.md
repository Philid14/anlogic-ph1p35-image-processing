# FRAME_CONCEPT_V1 任务与验证记录

- 日期：2026-10-22（Asia/Shanghai）。
- Role：MAIN；人类确认来源：本聊天关于桌面一体式俯视暗箱参数化模型的直接任务。
- Base：`origin/main`，`c42168e26026425660f2a6f51eec76b04c85eea0`。
- Task branch：`codex/main/frame-concept-v1`。
- 允许修改范围：仅 `mechanical/frame_concept/`；使用独立工作树保留原工作区已有修改。
- 接口：无 RTL/引脚/时序/传感器配置变更；尺寸、孔位及光学都是待确认输入。
- 交付：模块化 SCAD、集中参数、场景预设、预览、README、实测清单、重建脚本。
- 软件验证：OpenSCAD 2021.01；脚本输出 `previews/validation.txt`，逐场景 CSG 编译、PNG 预览、四个单件 STL 导出及异常参数断言检查。
- 实际结果：3 种场景编译、4 个单件导出、8 张预览、350 mm 高度及单灯变体、越界高度断言均通过；总装、闭帘、光学布局、载板和标定预览已人工检查。单件网格为可重建中间产物，未作为加工文件入库。
- 发布前检查：仅新增本目录；未混入原工作区文件；文本凭据模式扫描无匹配；未加入 bit、自动构建目录或第三方二进制。
- 实物状态：未加工；未承载校核；未测光；未标定；未实板验证。
- FPGA bit / BUILD_INFO / Timing / tag：本任务不生成 FPGA 版本，均不适用。
- 审查：按仓库协议提交任务分支与 Draft PR；等待 Philid14 审查，不合并。
- 当前 GitHub 身份为 Philid14，不能向同一账号请求 GitHub 自审；Draft PR 留待人类负责人检查最新提交。

外部技术说明仅使用 OpenSCAD/OpenCV 官方文档和光学厂商的照明说明，链接见 README；没有研究或复制 GitHub 外部代码，不更改全局 GitHub 参考日志。
