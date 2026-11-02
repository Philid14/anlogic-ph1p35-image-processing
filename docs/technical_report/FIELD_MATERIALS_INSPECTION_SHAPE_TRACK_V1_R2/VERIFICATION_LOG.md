# 记录册验证方法与适用边界

日期：2026-11-02。范围：本目录新增的空白材料采集包；第五稿和原有实测/仿真/构建证据保持原样。

## 同步和依据

```powershell
git -c http.proxy=http://127.0.0.1:7890 -c http.version=HTTP/1.1 fetch origin '+refs/heads/*:refs/remotes/origin/*' --tags
git merge --ff-only origin/codex/target/technical-report-vision-v2
```

fetch成功，文档分支检查结果为Already up to date。main为`c42168e`，最新已核对工程为`4d0f779`、PR #28为OPEN Draft、候选NOT_RUN。三个固定提交来源的Git内容SHA见[SYNC_REPORT.json](SYNC_REPORT.json)，本轮重新核对相同字节；不依赖会移动的分支来解释操作步骤。

读取官方赛题原PDF第16—18页，并对照保留的官方技术文档模板、V5模板提取结果和工程板测说明。没有新增外部方案或性能引用，也没有在本轮核实官网提交入口的新公告；最终提交格式/期限留给主控确认。

## 生成与版式

使用Codex bundled Python、python-docx/lxml及[本包生成器](tools/build_workbook.py)：

```powershell
& <bundled-python> -X utf8 docs/technical_report/FIELD_MATERIALS_INSPECTION_SHAPE_TRACK_V1_R2/tools/build_workbook.py
```

生成Word、在线Markdown和BUILD_INFO。输出不是现场测试结果。原14页初稿保留在本机原目录；本包R2扩充到20页。

通过已配置的Word只读导出适配器重新分页、更新页码域并导出内部QA PDF，再由文档技能的render_docx路径生成140dpi逐页PNG。检查过最终版全部20页的对应图像；最终D/R顺序改动后重渲染，第7页重新目视检查，另19页与已检查版本的PNG逐字节相同。版面未发现文字裁切、重叠、缺字、表格溢页或页码错乱。PDF/PNG仅留本地QA，不上传为参赛材料。

```powershell
& <bundled-python> -X utf8 <render_with_word.py> <R2.docx> --output_dir <qa/release> --dpi 140 --emit_pdf
```

适配器是本机Word导出兼容路径，非新增项目依赖；若其他机器无Word，需改用文档技能支持的渲染器并重新检查，不声称跨软件分页必然一致。记录册使用A4现场表格，与官方正文五部分排版的区别已在README和材料覆盖表说明。

## 独立结构与内容检查

[VERIFICATION.json](VERIFICATION.json)保留可核对的结果及文件哈希。检查项包括：

- DOCX ZIP/XML完整性、20个预期页标题和20个表格、19个显式分页、PAGE/NUMPAGES域。
- Word导出实际20页；各预期标题位于指定页，页脚1—20/20可提取。
- E00—E12和A01—A13齐全；D/R采样在切回W/H之前；独立真值、单位、失败/无效、分母和原文件索引均有填写位置。
- 实验栏保持空白；统计门槛为团队建议；候选NOT_RUN、实际版本待填，不捏造测量值。
- Markdown相对文件链接、官方模板/固定来源哈希、Word哈希及旧版资料保留状态。
- 提交范围仅本目录；不包含RTL、bit、TD生成目录或QA临时图片；文本和DOCX XML做凭据特征检查，不打印疑似敏感值。

本地内部检查命令是本轮输出目录的`verify_r2.py`，调用本包目录及`qa/release`作为输入；它不驱动硬件，也不改生产文件。人工核对负责实验语义和官方对应关系，结构检查不能代替人工判断。

## 测试结果的边界

本轮文档结构/分页/链接等检查通过，不代表算法、整机仿真、时序或板测重新通过。没有运行RTL仿真、TD综合/P&R、硬件下载、误差测量或长稳测试。资源和STA数据仅引用固定工程归档，不能据此得出无缓存问题、CDC已证明或实物长稳通过。

实测待补项见[MATERIALS_COVERAGE.md](MATERIALS_COVERAGE.md)。5项原始TD输入字节哈希仍未能独立复现；本次没有把该保留项改写成通过。材料清单已覆盖当前已知写作缺口，材料本身须现场人员及主控填写回传。
