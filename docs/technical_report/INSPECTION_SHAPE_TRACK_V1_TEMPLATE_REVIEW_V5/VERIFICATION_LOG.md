# 第五稿验证与操作记录

日期2026-11-02。仅新建第五稿文档目录，保留V2/V3/V4与所有工程证据；未修改MAIN、RTL、Sensor/颜色阈值、约束和bit，未合并PR。使用文档/ PDF技能的托管运行时和官方原模板；无第三方代码/照片/整份报告复制入库。

## 固定输入

Git fetch通过既有代理成功，发现新工程分支codex/main/inspection-shape-track-v1：HEAD4d0f779，实际TD517697c、归档8fe9dbb，tag inspection-shape-track-v1-candidate、工程Draft PR28依赖未合并PR27。文档PR26原HEADdd39f7a，仍Draft、Philid14待审。

本地从Git读取bit字节计算SHA，5d93f2ec5b80ee288455bc942a654de84166ecb202cda7b139b7a4f701b13f9a匹配BUILD_INFO。固定快照/文件SHA见SOURCE_EVIDENCE.json；12份归档结果JSON的passed均true，仅只读核验，未重跑RTL、TD或板测。

## 源码核验及没有消除的差异

原始Git blob SHA比较在首文件失败：多数归档记录Windows CRLF而Git为LF。允许明确记录的换行转换后，28项原字节匹配、56项CRLF转换匹配，**5项仍未复现原始字节哈希**：mc_to_user_interface.v、ph1p35_324_ddr_wrapper.v、hdmi_tx.v、measure_background.v、camera_to_dsi_display.sdc（完整路径见TD_INPUT_HASH_CHECK.json）。不能断言全部只是换行，也不能由SHA不匹配直接认定RTL变化。

另独立逐文件比较89个实际TD输入，源码提交517697c、归档8fe9dbb、工程HEAD4d0f779的Git内容完全一致。原构建脚本记录在各阶段前后检查工作区CRLF规范化内容等于固定提交；本机未取得原D盘工作区，未重新执行该门禁。请构建方补LF规范化内容哈希或原始源文件，以闭合5项原字节来源。bit自身SHA匹配不替代这个检查。

首次长路径Git读取失败，改用单命令git -c core.longpaths=true后读取成功，未更改全局Git配置。失败与未完成项保留，不为得到全部PASS修改已有证据。

## 文档命令及结果

任务脚本位于AnlogicTrack2/outputs/technical-report-2026-11-02/run-04，顺序如下，python均为Codex托管Python，Word适配器为既有本地脚本：

```text
python -X utf8 snapshot.py
python -X utf8 prepare.py
python -X utf8 build_v5.py
python -X utf8 companions_v5.py
python -X utf8 check_inputs_final.py
python -X utf8 <2026-11-01/run-01>/render_with_word.py <第五稿.docx> --output_dir qa/v5-delivery --dpi 140 --emit_pdf
python -X utf8 check_document.py
git diff --cached --check
```

DOCX和PDF各调用一次对应技能操作标记。通过独立隐藏Word实例只读打开任务副本、更新页码/域、导出PDF并关闭自身，渲染采用技能render_docx.py的PDF/PNG路径；没有修改托管依赖或用户打开的文档。

初稿26页，改用可点击不可变来源短显示、取消多余分页，最终24页。目检发现运动状态表整表后移留白、长文件名两端对齐空隙、总结换行缩进问题，分别修复并保留各轮PNG/PDF。最终24页全部完成140DPI目检；其中最终四张变化页与参考两页单独检查，其余18张与已目检页字节相同。页码1…24连续，无裁切/重叠/缺字/孤标题/空白页。

官方原件SHA不变；21保留部件、14原样式、原关系和节几何一致；4图1原生公式，16条文献14个不可变原生超链接。本地Markdown链接、ZIP/XML、来源快照SHA、13个实验入口与仅表头空CSV均通过。限字按非空字符：摘要482/800、1.1为206/400、1.2为104/400、1.3为167/400、1.4为157/200、1.5为129/200、1.6为112/200、4.1为154/300、4.2为527/1000。详情及最终文件SHA见DOCUMENT_CHECKS.json。

模板调整明列TEMPLATE_COMPARISON.md；正文保留官方五部分。结构/流程图只是功能示意，整机/电路/实物实验照片与真实性能数据仍待补。未提供的门户大小/时间/后续模板规则不宣称已经全部核验。

## 主控回填与风险

优先E00/E01/E02；连续E04厘米尺→E11空台面BG→E05独立W/H/GAP，再E12手选圆片D/R与E06红色LAST框，颜色/帧差/恢复随后分组。记录真值、仪器、失败和单位，B/S按600帧前/后的FIFO-full事件帧HEX计数。新候选仍NOT_RUN，严禁以旧界面、合成140px例、18帧数字回归或完整P&R替代实物效果。

资源仅余113 Slice/3 ERAM，Setup +0.111ns、STA覆盖95.69%只适用于已有约束；FIFO/Gray/CDC、温度和长稳风险保留。蓝色、严格同显示帧历史框和内部同帧延迟计时未完成。五项原字节哈希由构建方补证，本轮文档不代替工程审核。
