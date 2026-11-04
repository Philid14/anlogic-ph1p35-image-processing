# 文档优化验证记录

2026-11-04。基线为文稿d92c2d0 / FINAL_REPORT_V1，代码为main6055a56 / final-submission-v1.2。开始时工作区干净，fetch后main仍为6055a56，原PR35处于OPEN Draft。

本轮未修改生产RTL、约束、阈值、bit、板测记录或实验结论。SOURCE_EVIDENCE.json及MEDIA_INVENTORY.json逐字节继承V1，32份图片文件和原Word图像部件字节不变；新增的是Word原生裁剪属性和版面元素。

采用bundled Python、python-docx及OOXML定向编辑，除document.xml、document.xml.rels、core.xml和Content Types外的原部件保持字节一致。保留原生OMML、A4节、样式及页眉页脚。官方模板原件哈希不变。首次33页渲染后修复版本表跨页、板卡图与模式图组留白，最终32页；15项文档检查PASS。所有最终页面使用Word原生PDF导出并经技能render_docx.py管线生成140dpi PNG，逐页目检。PDF/PNG只作内部QA。

本机作者脚本位于AnlogicTrack2/outputs/technical-report-2026-11-04/run-02：build_v2.py、render_native.py、check_v2.py。渲染结果qa/final，完整页面哈希列于RELEASE_CHECKS.json。最终32页已全部逐页目检；文档结构15项、发布包装11项及带固定Git对象复核的便携检查18项均通过。便携检查原始输出保留于同目录PORTABLE_VERIFICATION.json。

尺寸转录在原生局部放大时再次核对，发布值维持W/H98.3/98.3MM；首轮临时审读把末位误读为8的判断已撤回。原照片、V1及该轮QA均保留。

可在仓库根目录运行标准库便携检查：

```powershell
python docs/technical_report/FINAL_REPORT_V2/verify_package.py --check-git
python docs/technical_report/FINAL_REPORT_V2/verify_package.py --check-git --video 'C:/Users/Kelinna/Downloads/11月3日(1).mp4'
git -c core.longpaths=true diff --check
```

检查范围为文档文件清单/哈希、结构、裁剪来源及固定Git对象。191项源码Git内容和.al一致、最终bit SHA一致的复核方法沿用V1；原始构建哈希184/191匹配、7项原始字节未闭合仍明确保留。静态P&R19177 Slice、105 ERAM、WNS+0.137/+0.020ns为已归档整机结果，本轮未重跑TD。

真实内部延迟、独立尺寸误差、连续运行、AUTO12实物对照及T/L实物证据的状态未因文档PASS改变，集中见正文3.3.4及前稿主控说明。PR由Philid14审核，本轮不合并main。
