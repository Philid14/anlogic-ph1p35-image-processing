# 模板调整与验证

日期2026-11-03。本轮范围为技术文档及只读实拍审核，不修改生产RTL、约束、Sensor/颜色阈值、bit或MAIN接线。

## 来源与同步

执行fetch全部远端分支和tag成功；对文档分支执行`git merge --ff-only origin/codex/target/technical-report-vision-v2`，结果Already up to date。新增工程分支状态通过固定源码报告、BUILD_INFO与GitHub Draft PR29/30/31交叉核对，详见[SOURCE_EVIDENCE.json](SOURCE_EVIDENCE.json)。

最新已归档延迟候选bit从Git对象独立计算SHA，匹配`062b48ec7c002b56b4a025cd36a0e0f5e9138178f5706d6390a7f91eef3a27a4`。6份本轮来源文件SHA重新匹配。95项输入/45份回归闭环及最终STA数值为该构建的归档证据，本轮没有重做全构建或将其写成硬件验收。

## 实拍审核方法

27项原件逐文件SHA入清单，12张照片总览与精选图核查；15段视频均解码到末尾，0.5秒抽样共979帧，审核每段九帧总览和重点原尺寸帧。视频容器共489.95秒、最长92.65秒，只用来描述资料规模。没有连续逐帧审计、音频转录、系统帧率测量或连续长稳观察；短暂现象可能不被抽样覆盖。

FFmpeg由任务目录内下载的imageio-ffmpeg 0.8.0 wheel解出，未安装/修改全局或托管运行库。原照片/视频未写入。新增20张入稿JPG仅作EXIF方向处理和比例缩放，不调色、不透视矫正、不改数字或算法结果；来源/时点/操作在SELECTED_MEDIA中逐图记录。

用户确认素材为同一个当时最新版bit；未提供精确SHA，独立真值和连续运行指标答“没测”。这些未决状态写入正文和附件，未据界面猜测版本。

## 官方模板与明确调整

保留的官方模板SHA为`d15a2aa186f600cb9c234bffd9deff0c4e9b05c569643d8a81d536f66f424f0c`。回读赛题原PDF物理页16—18；模板第三部分要求整体/机械/电路/界面及功能测试实物照片，因此新增实拍图组放在第三部分。没有自行增加第六部分或改登记名称/简介。

本稿从官方模板派生的V5副本定点编辑：更新摘要、限字章节、跟踪区域选择和配置RAM新实现；添加同帧延迟小节；第三部分添加照片、成组图注、真实现象和量化边界；更新最终P&R表、版本及在研状态。删除一张与要求矩阵重复的状态表，避免空白分页。原图4保留并明确标为SHAPE历史结构，不能替代新区域选择/延迟身份链。

原A4单节尺寸、边距、页眉页脚/PAGE、样式、4幅原结构图和原生OMML公式保持。包级比较只允许document.xml、document.xml.rels、core属性及Content Types变化，其他原部件逐字节保留；新图片为新增部件。正式正文仍使用原12pt和1.5倍行距；新增图注采用原10.5pt角色。未为压页缩小正文。

## 生成 渲染和检查

使用Codex bundled Python、python-docx/lxml/Pillow/pypdf生成并检查；Word只读导出兼容适配器接技能render_docx的PNG流程，以140DPI检查全部35页的对应最终图像。第1—13及15页与已目检版本逐字节一致，其余最终页逐页目检；页码另行核对。修正了末尾引用孤页、实物照片对齐、机械小节多余分页及重复状态表。未发现裁切、缺字、重叠或表格行截断。

任务脚本在本机`outputs/technical-report-2026-11-03/run-01/`：

```powershell
& <bundled-python> -X utf8 inspect_media.py
& <bundled-python> -X utf8 extract_video.py
& <bundled-python> -X utf8 prepare_v6.py
& <bundled-python> -X utf8 build_v6.py
& <bundled-python> -X utf8 <render_with_word.py> <第六稿.docx> --output_dir <qa/release2> --dpi 140 --emit_pdf
& <bundled-python> -X utf8 check_v6.py
& <bundled-python> -X utf8 release_checks.py
```

检查包含官方9个限字槽、20条参考、24幅内嵌图、原生公式和原包部件、文档ZIP/XML、来源SHA、原始素材/精选图SHA、分页/图片链接、文件范围与凭据特征。限字按去空白字符保守计，1.4包含表头/体；结果见DOCUMENT_CHECKS与RELEASE_CHECKS。初次内联修改脚本曾因PowerShell引号失败，随后改用文件补丁修正；失败不涉及原始资料或生产文件。

内部QA PDF/PNG不随本包交付。最终Word为35页、约8.4MB；在线Markdown作为阅读入口。页数和大小不是官方已核定的提交规格，最终入口限制仍需核对。

## 检查结论边界

文档检查通过证明文件、格式和来源关系可检查，不能替代实物精度或可靠性。BG学习改善、真实误差、连续运行、延迟数值及最终bit绑定仍见[FOLLOWUP.md](FOLLOWUP.md)。本轮没有运行RTL回归、TD/P&R或硬件下载。保留V5的历史5项原始TD输入字节哈希未复现项，不把新候选归档门禁用于抹去旧保留项。
