# 最终定稿验证记录

日期2026-11-04；范围：文档与只读证据复核。本轮没有修改生产RTL/SDC/TD入口或重跑综合、P&R、bitgen；硬件结果来自MAIN已归档的独立重建。没有新上板、量具真值、真实延迟或长稳实验。

## 仓库同步

工作分支沿用`codex/target/technical-report-vision-v7`及现有PR35；原文稿217e282保留。fetch成功，最新main为`6055a560b020373e77328e7518d200e358401363`，随后merge到现有分支，merge提交`18fb0a9f3016d2b6f67f6ecf48c43a1ea02fe644`，无冲突。没有push/merge main、移动tag或覆盖历史证据。

```powershell
git -c core.longpaths=true -c http.proxy=http://127.0.0.1:7890 -c http.version=HTTP/1.1 fetch origin '+refs/heads/*:refs/remotes/origin/*' --tags
git -c core.longpaths=true merge --no-edit origin/main
```

## 固定源码与构建证据

- 复核10个固定归档文档的Git对象SHA，见SOURCE_EVIDENCE.json。
- 从固定Git对象重新计算最终bit SHA，与MANIFEST和BUILD_INFO一致。
- 将独立重建源码6432c91与交付6055a56逐一比较：191项输入Git blob一致，TD .al也一致；包括95项正式输入和96项辅助IP。
- 用直接字节/LF/CRLF三种形式匹配SOURCE_MANIFEST：184/191匹配，**7项原始构建字节哈希仍未独立闭合**。路径与逐项方法全部保留；不以Git blob相同冒称191项原始构建字节全匹配。原独立构建目录在本机不存在，本轮未猜测未匹配原因。
- 归档SYN/PHY/STA/bitgen已PASS；Slice19177/21216、LUT618498、FF16374、ERAM105/108、DSP25/40；Setup/Hold WNS+0.137/+0.020ns，TNS0；PHY-5060/5079未隐去。
- 精确重建bit的板测仍为NOT_RUN；静态报告不代替实板CDC/PVT、长期连续显示、测量准确度或光学端到端延迟。

## 视频与文档

F01完整解码至EOF退出0；2Hz共342样本，查看全部15张1Hz顺序图、概览及关键原尺寸抽帧。可见DEMO，真实延迟数值未确认。两张新图保持完整帧；旧30图文件字节不变。原始370MB视频不入Git，也不发布其容器定位元数据。

```powershell
# 本机 authoring/QA 入口；使用已安装python-docx/Pillow/pypdf的运行环境
$reportRun = 'C:/Users/Kelinna/Documents/Codex/2026-10-16/AnlogicTrack2/outputs/technical-report-2026-11-04/run-01'
$reportRepo = 'C:/Users/Kelinna/Documents/Codex/2026-10-16/AnlogicTrack2/work/technical-report-vision-v2'
python -X utf8 "$reportRun/inspect_final_video.py"
python -X utf8 "$reportRun/prepare_final.py"
python -X utf8 "$reportRun/build_final.py"
python -X utf8 'C:/Users/Kelinna/Documents/Codex/2026-10-16/AnlogicTrack2/outputs/technical-report-2026-11-01/run-01/render_with_word.py' "$reportRepo/docs/technical_report/FINAL_REPORT_V1/技术文档_最终定稿_V1.docx" --output_dir "$reportRun/qa/verified" --dpi 140 --emit_pdf
python -X utf8 "$reportRun/check_final.py" verified
```

以上为本机步骤名称；精确渲染路径及页面哈希记录在RELEASE_CHECKS.json，公开复核请使用下方可直接执行命令。排版经历三轮调整：移除重复段落，资源表整体保留，删除视频映射表孤立尾页。最终Word38页，逐页视觉检查，14项结构/模板/限字/原图/来源检查PASS；Zip/XML、原生公式、原页眉页脚与节属性保留。QA的PDF/PNG仅内部存档，不列入正式交付。

## 可重复只读检查

在仓库根目录，Python标准库即可：

```powershell
python docs/technical_report/FINAL_REPORT_V1/verify_package.py --check-git
python docs/technical_report/FINAL_REPORT_V1/verify_package.py --check-git --video 'C:/Users/Kelinna/Downloads/11月3日(1).mp4'
git -c core.longpaths=true diff --check
```

实际执行便携脚本并同时检查Git对象及本机F01视频：18项PASS、0项失败；最终发布检查10项PASS、文档结构检查14项PASS。验证未改变视频、bit或生产源码。发布检查首次因Git默认引用中文文件名导致范围识别误报，已改用`--name-only -z`解析；重新检查仅有既有V7和新增最终文档目录，没有生产改动。原始过程记录留在本机run目录与工具日志。

包清单排除自引用RELEASE_CHECKS.json；所有新文本以LF保存并使用目录.gitattributes固定字节。文档检查结果及页面数量见DOCUMENT_CHECKS.json与RELEASE_CHECKS.json；程序PASS只表示已定义证据检查通过，7项原始字节审查与未量化性能仍明确保留。
