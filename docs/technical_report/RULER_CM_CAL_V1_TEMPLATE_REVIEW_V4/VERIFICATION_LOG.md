# 第四稿文档验证记录

日期2026-11-02。任务仅修改文档；未运行新的RTL/TD/板测，未编辑MAIN/RTL/阈值/约束/bit或历史证据。

## 输入与同步

通过团队现有本机代理执行Git fetch，工程候选仍为8dd6702，main仍c42168e。文档分支codex/target/technical-report-vision-v2原HEAD为0aac1be；PR #26 OPEN Draft、Philid14待审。工程PR #27独立，未合并。新增第四稿目录，保留V2/V3历史。

不可变源码证据及SHA见SOURCE_EVIDENCE.json。本机独立计算bit SHA=6372f765f61ec31d8a18923596c8326ce84a0fd7637850847d5ac364cc3aebc2，与归档一致；原生unit/full_roi/stream_r1/features/controls的results.json均passed=true。这里只读取归档，不伪装重新执行。

## 文档操作及检查

采用托管Python/python-docx，克隆官方模板后按保留清单复原包部件。任务本地脚本位于AnlogicTrack2/outputs/technical-report-2026-11-02/run-01，顺序为：

```text
python -X utf8 prepare_v4.py
python -X utf8 build_v4.py
python -X utf8 companions.py
python -X utf8 <2026-11-01/run-01>/render_with_word.py <第四稿.docx> --output_dir qa/v4-final --dpi 140 --emit_pdf
python -X utf8 finalize_v4.py
python -X utf8 finish_package.py
git diff --cached --check
```

所有Python命令使用本机托管运行时。Word以独立隐藏实例只读打开任务副本、更新域、导出PDF并关闭自身；页面渲染使用技能render_docx.py的栅格化路径，仅以本地适配器替换PDF转换入口，未改托管运行时或用户已打开文档。

结果：24页Word/PDF；全部页140DPI目检。首轮25页检查后修复强制分页留白、长文件名导致的两端对齐大空隙与一处引用编号；最终12张变化页再次目检，其余12张与已检查图片字节一致。无裁切、重叠、缺字、孤标题或空白页。页码1…24连续。

官方原件SHA不变；21个保留包部件、14个原样式、原关系和节几何均一致；4幅示意、1个原生公式；11条文献。摘要467/800；1.1 219/400；1.2 111/400；1.3 175/400；1.4 148/200；1.5 116/200；1.6 104/200；4.1 124/300；4.2 513/1000（全部非空字符保守计）。本地Markdown链接检查通过；旧跟踪文件无改动。

独立检查详情：DOCUMENT_CHECKS.json、PACKAGE_FIDELITY.json。模板调整已注明于TEMPLATE_COMPARISON.md。模板要求的实物全景/局部、电路图纸对应、实际性能与仪器数据仍待补，不能把格式检查PASS写成作品板测PASS。尚未提供的门户大小/提交窗口规则不声称已全面核验。

## 当前风险与主控下一步

新候选板测NOT_RUN；旧CAL:OK与R5失败均不能证明厘米粗标定成功。首要补：加载版本/七模式、1CM→R3→同平面独立X/Y与间隙、倍数误读排除、长稳计数/变光/恢复、整机照片。随后颜色分组及TRACK/MOTION动态，最后补帧率和延迟口径。资源97.69%高密度及现有FIFO/Gray/CDC覆盖风险不因文档完成而消失。
