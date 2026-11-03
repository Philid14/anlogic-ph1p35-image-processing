# 第七稿验证方法与结果

适用范围为文档和只读证据审查。文档检查PASS不能解释为RTL、真实延迟、尺寸精度、连续运行或全设计CDC/PVT通过。

## 实际执行

1. 在原文档工作区核对 branch/HEAD/status 与团队规则，代理fetch全远端分支/tag。首次保持旧文档HEAD48cbd02；上传前发现PR26已由主控合并，再fetch取得main6432c91。从该基线新建 `codex/target/technical-report-vision-v7`。无MAIN编辑或自行合并。
2. 四段原视频完整解码到EOF，4Hz缩放抽帧；各文件解码退出0，共175帧。人工查看四张9帧概览、全部五张1Hz顺序联络图及关键1280像素宽帧。保留容器edit-list提示，不声称原生逐帧观看或音频分析。原片哈希在结束前重新核对。
3. 固定提交读取延迟原集成、parts/motion、真实修复、临时DEMO与最终V1.1资料；核对DEMO源码口径与画面。独立计算Git中真实修复bit SHA匹配d516…2c16。
4. 95项正式Git blob在最新交付6432c91与真实TD源码ebbd3cd间一致。构建清单90项可直接或按LF/CRLF复现；5项原始字节哈希未对齐，明确保留。没有把换行转换后的哈希称作原始字节相同；没有独立重做全构建或V1.1全部辅助IP闭环。
5. 由第六稿副本编辑第七稿，按保留清单覆盖包部件，保留原节、样式、页眉页脚、原生公式和旧24幅图。更新字数、参考20条、图组18组/嵌图30幅，具体见DOCUMENT_CHECKS.json与PACKAGE_FIDELITY.json。
6. 本机Word隐藏只读导出PDF，调用文档技能render_docx.py栅格化140DPI，全部37页对应PNG已目检：25页本轮原尺寸查看、12页与此前已目检第六稿PNG逐字节相同。上传前V1.1修订仅17/33/34/37页变化，均重新查看，其余33页哈希一致。渲染PDF/PNG仅内部QA，不随本包交付。
7. 调整一次分页：移除重复补测表，保留补测说明，37页代替首次38页。修复本地检查脚本的PDF数学字符JSON编码问题；文档原生公式未变。
8. Git长路径使新主线切换时有一个证据JSON未能正常创建；核实该文件是本次新增checkout内容后，从HEAD blob按长路径精确恢复，状态不再有生产/归档修改。仅新文档目录进入提交。
9. 初次暂存检查发现Windows生成文本的CRLF被证据目录的字节保留规则识别为行尾空白；统一本次新增文本为LF后重新计算交付清单，再执行diff检查。DOCX、图片与旧证据均未受影响。

## 命令与日志

原视频检查及作者脚本在本地 `outputs/technical-report-2026-11-03/run-02/`：inspect_new_media.py、prepare_v7.py、build_v7.py、check_v7.py、FORMAL_REHASH_ATTEMPT.json及qa/first、qa/final、qa/release。含私人原件路径或容器元数据的日志只留本机，不上传。

实际渲染通过已建立的Windows适配器运行，参数为第七稿docx、`--output_dir .../qa/release --dpi 140 --emit_pdf`；适配器使用Word只读导出，再调用文档技能渲染流程。不是通过LibreOffice另存后覆盖原包。

团队可以在仓库根用标准Python复核本包，不依赖作者机绝对路径：

```powershell
python docs/technical_report/REAL_MEDIA_MOTION_LATENCY_V7/verify_package.py --check-git --output evidence_check.json
```

可选再传 `--qq-dir 'QQ原视频所在目录' --original-dir '两个原始视频所在目录'`，重新核对四个原件哈希；不解码、不修改原件。核验输出写新文件，不覆盖冻结报告。

验收依据：DOCUMENT_CHECKS.json为14项文档/证据结构检查；RELEASE_CHECKS.json为最终页码、链接、范围、隐私和文件SHA检查。verify_package.py复核已发布文件清单、结构、固定Git来源及原片哈希。所有失败/保留边界在同一文档和FOLLOWUP中可见。

## 未执行与未解决

本轮未跑RTL仿真、TD/P&R、bitgen或上板。58项parts/motion门禁、5组真实修复测试、资源/时序为MAIN归档结论，不能写成本轮重跑。拍摄bit身份、真实有效延迟、尺寸真值/误差、BG:OK/AUTO12改善、长稳、T/L实物、匹配机械/电路图与5项原始构建输入哈希仍有缺口。

Word与Markdown均保留原版/现版思路变化。原登记名称与简介不修改；运动改进、延迟新增及DEMO与真实测量的区别明确写入摘要、算法、赛题矩阵、图注和补测表。没有以填满PASS为目标补造任何实验值。
