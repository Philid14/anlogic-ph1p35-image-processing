# LATENCY 接入复审验证记录

日期2026-10-20；TARGET基线 `a715061546db72232d23876146b457355a4a4695`，
受测LATENCY `531ef616dd53efa200e16b3839319f18b4c48d72`。
新测试/runner在工作区执行，不能仅用TARGET HEAD代表受测文件；实际文件哈希在 summary 的
`snapshot_sha256`，两份外部RTL另经Git blob SHA1和SHA256逐字节校验。源码快照仅在本地输出保留，
不向TARGET生产目录复制LATENCY RTL。

## 最终结果及边界

最终运行 `rtl-03`：ModelSim ASE **10.3c**、Python **3.12.14**；8场景31检查。
所有测试前提成立，2控制场景要求满足，6场景共7条安全要求失败；
24工具阶段全部exit0，0个编译/仿真错误。runner按设计exit **1**，
`evidence_valid=true`、`requirements_satisfied=false`、`integration_ready=false`。
这不是8场景全部PASS。具体输入/不变量/失败条件/严重程度/责任与源码位置见
[复审报告](../../integration/LATENCY_REVIEW_531ef61.md)。

| 场景 | 要求失败数 |
|---|---:|
| 正常首次及重复显示 | 0 |
| resync重启统计窗口 | 0 |
| bridge满时静默丢失 | 1 |
| 两次错误toggle抵消 | 1 |
| 溢出后未resync即恢复（建议安全策略，待确认） | 2 |
| 旧会话数据重新打开会话 | 1 |
| 目的单侧reset重放已消费事件 | 1 |
| resync清表后在途旧包仍可计数 | 1 |

前两项仅验证其列出的计数/状态，不验证LATENCY面板/平均值除法或生产延迟精度。
后面三项会话/reset/在途场景显示外部适配与控制屏障的必要性，不宣称MAIN已发生这些故障。
桥满场景暂停公开ready；meter实际ready常1，不推断正常视频运行已经丢事件。
没有修改生产RTL。9份TARGET生产源LF哈希与原交付清单一致（见 baseline.json）。
未重跑未改动的原handoff16；未覆盖旧日志、旧模型或旧PASS/OPEN记录。
无新综合、P&R、资源增量、Fmax、bit、tag、烧录或板测。

## 实际命令

从仓库根目录使用：

```powershell
& 'C:/Users/Kelinna/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -X utf8 -u features/color_target/run_latency_handoff_review.py --revision 531ef616dd53efa200e16b3839319f18b4c48d72 --msim 'D:/altera/14.1/modelsim_ase/win32aloem' --out 'C:/Users/Kelinna/Documents/Codex/2026-10-16/AnlogicTrack2/outputs/latency-handoff-review-2026-10-20/rtl-03'
& 'C:/Users/Kelinna/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -X utf8 features/color_target/tb/test_latency_review_evidence.py
```

证据解析器4测试通过，原始输出见 `evidence-parser-tests.log`，命令/退出码/测试源哈希在
`tool-selftests.json`。它拒绝工具失败、缺项/重复项、完成标记错误、数值与pass标志矛盾和前提失败，
不将软件失败注入称为RTL仿真通过。

## 原始日志与迭代保存

`RAW_LOGS.zip`保留rtl-01/02/03全部72个原始工具输出及3份原始summary，共75成员。
`LOG_ARCHIVE_INDEX.json`记录成员大小/SHA256，已读回逐项核验；最终summary另在当前目录便于阅读。
zip不含编译库、bit或重复生产RTL。rtl-01存在未连接输出端口的测试架warning，后续明确空接；
rtl-02增加公开toggle变化次数前提，rtl-03补强Git commit校验与异常退出分类，既有功能结果保持。
这些中间记录不覆盖最终rtl-03；最终受测runner/TB/helper已与本地源逐字节再比对。
初版证据整理包也保留在仓库外 `outputs/latency-handoff-review-2026-10-20/package-02`。

共享接口仍需人类/MAIN/LATENCY确认恢复策略、权威会话、时基、服务与排空条件。
最新远端网络校验及上传情况以本轮最终Git回执为准；baseline.json保留审查开始时的真实失败尝试，
不据缓存remote ref冒称已经完成本轮网络同步。
