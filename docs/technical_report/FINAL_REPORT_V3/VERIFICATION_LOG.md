# 独立提交稿验证记录

基线为dfce97d / FINAL_REPORT_V2；最终代码仍为main6055a56 / final-submission-v1.2。本轮仅新增FINAL_REPORT_V3，V1/V2及生产文件不变。

文档由V2派生，保留所有不在允许编辑列表中的包部件、原生OMML、官方节/样式/页眉页脚与图像字节。35页经Word原生只读PDF导出，使用文档技能render_docx.py生成140dpi PNG。1—12页曾完整目检且与最后渲染逐字节一致；13—35页按最后渲染完整目检。内部PDF/PNG不作为交付文件。

21项文档检查包括五部分、20参考、限字、18图组、34嵌图、24表、4处原生裁剪、部件保留、外部索引措辞、无本机路径/链接、F01身份和图像嵌入。发布检查另核页码、图文件、文稿与渲染身份、旧稿未改及交付范围。见DOCUMENT_CHECKS.json及RELEASE_CHECKS.json。

首次校验脚本有旧目录路径替换错误，误在V2生成两份诊断文件；立即保存失败结果并按已发布HEAD恢复该两文件，复核V2无diff。首次版面中有两处段尾空白页，已在保留技术内容后缩并重复说明；最终35页通过。失败诊断和各轮渲染保留在本机outputs/technical-report-2026-11-04/run-03，不覆盖原证据。

可复现检查（仓库根目录）：

```powershell
python docs/technical_report/FINAL_REPORT_V3/verify_package.py --check-git
git -c core.longpaths=true diff --check
```

SOURCE_EVIDENCE.json和MEDIA_INVENTORY.json继承V2，固定Git对象/191输入/.al/bit核对方法不变。最终资源19177 Slice、105 ERAM、WNS+0.137/+0.020ns来自已归档整机P&R；本轮未重跑RTL、TD或板测。7项原始构建字节哈希、逐片段bit身份和独立误差/真实延迟/长稳仍未闭合。
