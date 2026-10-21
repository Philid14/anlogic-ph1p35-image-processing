# TARGET guard 实施、审查和验证 — 2026-10-19

本轮从4ec3d35a5cd08cc2d64fe03aa403be16fd696706开始，隔离分支 `codex/target/track-guard-v1`。
用户确认原文：“**按推荐方案实施 TARGET 独立 guard，MAIN另行确认**”。范围见 [当时提交的具体方案](APPROVED_PLAN.md)。
本记录在本地提交前写入；实际交付commit由Git给出，运行时HEAD与未提交文件在各summary保留。
没有push/merge、MAIN接线、TD构建、bit生成、下载或新板测。

## 1. 已确认事实及源码

- 新增 `../../rtl/color_target_track_guard.v`，封装未改的原TRACK；新增同名TB、`../../run_track_guard_contract.py` 和 `../../integration/TRACK_GUARD_INTERFACE.md`。
- MAIN控制session；guard按可信当前session递增key退休，区分取消/无效/可靠无目标/可靠有目标/重复/乱序/时间故障。
- 时间年龄使用可信capture_tick，结果停输也由独立now输入推进；两个年龄参数默认0，显式配置前不准入，不自定生产阈值。
- 不生成时钟或运行时复位；私有core token始终与**最后消费**的token不同，下一可靠结果触发旧TRACK自身的session清确认逻辑。控制空转多次不会因简单翻转回到旧token。
- 同拍过期＋新鲜结果可以重新ACQ；无队列/复位气泡，测试覆盖每拍一个结果。
- `O_observation_usable`仅表示身份/年龄及TRACK层可用；最终同帧匹配、文字准备、DDR代次和整组commit仍由MAIN实现。
- 所有原56个回归源文件哈希保持4ec阶段值，见 [原源码复核](original-source-check.json)；未修改旧RTL、旧模型、simlib、颜色门限、support3或MAIN。

## 2. 用户要求核对的已有板测记录

[版本索引](board-records/INDEX.md)、[机器可读来源/bit身份](board-records/index.json) 区分历史计划与后续反馈。
11个归档版本中9个有用户报告：V0、AWB_V1、BLC_V1、AWB_V2、GAIN_TEST_A/B/C/E、EDGE_V1。
未找到完成反馈的是GAIN_TEST_D及EDGE_CONTROL_V1；不能据此断言用户从未测试，只能说未在检查的记录中归档完成结果。

已知结论可沿用：BLC黑场较好、AWB颜色改善、A/B/C同场景单调增亮、E=15.75×亮度基本满意、EDGE可输出但弱边缘不足。
记录主要为用户目视反馈，没有因此补造寄存器读回、像素精度、溢出计数、精确延迟或30分钟验收。
A/B结果提交7665bb1/3551f85在各自正式tag中，但不是当前HEAD祖先；当前A/B BUILD_INFO仍“待上板”，主调试日志已记A/B/C反馈。AWB_V2也同时保留候选和后续反馈。
本轮仅建立索引，没有越权修改MAIN全局记录或合并结果分支。

后续补测缩小为EDGE_CONTROL_V1新增K3/K4、至少20次模式切换、文字/画面对应及明暗/长期稳定性；不要求重做整套BLC/AWB/增益画质实验。
仓库外已准备绑定旧bit的board-run-01及zip，所有实测格仍NOT_RUN。本轮没有把文件校验当成硬件下载或板测。

## 3. 执行命令与结果

工具：Python3.12.14、ModelSim ASE10.3c（实际 `vsim -version` exit0，见tool-version.txt；安装目录名14.1不是仿真器版本）。
从仓库根目录执行，所有输出目录均为新目录：

```text
python -B -X utf8 -u features/color_target/run_track_guard_contract.py --selftest-tools --out <guard-tools-02>
python -B -X utf8 -u features/color_target/run_track_guard_contract.py --sim modelsim --msim <本机win32aloem> --out <guard-rtl-03>
python -B -X utf8 -u features/color_target/run_track_guard_contract.py --sim modelsim --msim <本机win32aloem> --guard-rtl <隔离故障副本.v> --only core_time8 --out <新故障目录>
```

| 运行 | 事实 / 退出 | 证据 |
|---|---|---|
| 原提交quick | 7项完成：6功能CHECK通过＋1当前TRACK特征吻合/六OPEN；非整机通过 | 原始运行保留在仓库外integration-readiness-2026-10-19/quick-01 |
| 首轮guard-rtl-01 | 0/9、exit1；测试台误把Verilog保留字event作task名，全部停在vlog；不是RTL功能通过 | 全部工具日志、summary和当时源快照保留 |
| guard-rtl-02 | 改task名为send_result后9/9、800硬检查、exit0；源执行期稳定 | summary、27阶段日志及源快照 |
| 自审补强 | 目标过期不应抹掉仍新鲜的可靠无目标；独立保留可靠时间/身份，并补“接受了有延迟结果后仍按capture过期”的硬预期 | 最终RTL/TB及下面03；02源快照保留，不覆盖 |
| 最终guard-rtl-03 | **9/9配置、818硬断言、exit0**；8bit与64bit时间各398，其他年龄/禁用边界22；27个vlib/vlog/vsim进程逐项exit0，源5项执行期稳定 | [summary](guard-rtl-03/summary.json)及各子目录原始log |
| 最终guard-tools-02 | 6/6：正常进程、完成后exit7、完成后错误文本、缺完成、零检查、重复场景；错误均被拒绝 | [summary](guard-tools-02/summary.json)与原始log |
| 故障RTL副本 | 4/4被抓；各副本编译成功、运行硬断言失败，runner exit1是预期 | [summary](guard-mutations-01/summary.json)及副本/工具日志 |

故障副本分别为：重复key误准入（10断言失败）、以到达时间刷新年龄（3）、不更换core token（7）、目标过期误删可靠无目标（1）。
测试只从端口读取字面期望，不读取DUT内部寄存器、不调用生产参考模型来产生gold。
原TRACK的六个问题仍通过未包装审计保留OPEN；本guard的对外行为有独立证据，不能用它覆盖原路径的失败事实。

## 4. 输入、独立预期、不变量和失败条件

| 注入主题 | 输入 | 独立预期 / 不变量 | 失败条件 |
|---|---|---|---|
| 无可信session | reset后直接结果 | 原因15、不准入、不显示 | 结果数据自动建立session |
| 重复/乱序 | 99三次、98、再100；最大帧号后0 | 只99/100算独立观测；较小/回绕拒绝 | ACQ虚增、框移动、年龄续命 |
| 可信身份不可得 | 高帧号但identity_valid=0，后跟正常小帧号 | 高号不污染高水位；下一可信帧正常准入 | 后续真实帧被屏蔽 |
| invalid/cancelled | 无效/取消后相同key有效重发 | key已退休；不增加miss、不刷新时间、不补写 | 伪造缺失目标或恢复旧key |
| 有效无目标 | 确认后两次可靠absence | 第一次HOLD且保留旧box_key，第二次SEARCH | 与invalid混同或把box换成当前key |
| 正/可靠时间分开 | 正观测时间0，无目标时间5，now6 | 目标过期/隐藏；可靠无目标age1与身份保留 | 旧框续命或可靠链路活性被抹掉 |
| 停输入/无效长列 | 可靠确认后停止结果或连续invalid，now递增 | 等于limit仍有效，大于limit退休一次；高水位保留 | 靠新strobe才超时、重复timeout、旧key复活 |
| 迟到/未来 | capture已超龄或大于now；同key再发 | 原因9/10，退休但不准入 | 到达时间使旧结果变新 |
| 合法传输延迟 | now10/capture8、now11/capture9，再到14/15 | 14为age5边界，15已过期 | 使用arrival导致延长寿命 |
| session重启 | 可信新session且无效首包/没数据，旧session迟到 | 即刻隐藏旧确认；新session重新ACQ；旧包不得切回 | 等到有效首包才清旧框 |
| 空epoch/直接重用 | 连续两个新session但没数据；再次请求当前SID | 不与旧core token别名；直接重用原因14且关闭run | 旧TRACK确认历史被继承 |
| 同拍屏障/数据 | session_start与新结果同一上升沿 | 仅控制成立、数据不退休；屏障后交付才可准入 | 同拍数据静默算作独立观测 |
| 时间失效 | time_valid丢失、时间倒退/回绕 | 关闭run；恢复time_valid不足，需新的可信session | 负年龄、旧状态复活 |
| 年龄配置 | 0、负值、超位；最大可表示值 | 非法配置禁用；最大值合法但time回绕仍须换epoch | 静默截断成另一有效年龄 |
| 计数与服务 | 2bit诊断反复超限、连续260独立结果 | 各诊断饱和、不回绕；每拍一个可靠结果无气泡 | 诊断回零或漏事件/身份错配 |
| 过期与新结果同拍 | TRACK正观测时间0，now6带fresh正观测 | timeout一次且本拍重新ACQ，下一独立正观测才TRACK | 继承旧确认或丢掉新观测 |

单个主题中使用多条断言；全量具体输入和字面gold保留在TB。这里的时间、ACQ2/LOST2与2bit计数全部为夹具。

## 5. 最新提交审查：问题与严重程度

[4ec及A1审查结论](REVIEW_4ec3d35.md)。P2旧simlib退出码问题有三路独立注入：
正常exit0被接受；无错误文本但底层exit7仍被旧A1 Python及统一job判通过；加Error文本后会拒绝。
这是受控mock进程返回的证据，不是声称真实ModelSim在旧回归中发生了exit7。
旧helper未改。新guard runner已通过每阶段返回码与错误/完成/场景检查规避此缺口；旧功能入口仍待后续修复。

P1的MAIN真实帧规范化、错误汇总、CDC、DDR/扫描租约、图文原子提交仍OPEN。guard全端口同域只界定自身，不会把整系统变成同域。
历史板测记录有状态散落的P2文档风险，已索引而非越权改写全局日志/tag。

## 6. 资源、时序和板测适用边界

本轮没有综合、P&R、bit或板测，不给新guard LUT/Fmax结论。
64bit年龄比较/减法、诊断计数及核心TRACK的实际资源与时序须在MAIN真实配置下测量。
独立RGB gate历史918/1224 LUT和旧MAIN routed dff499a的+0.100/+0.020ns都不能代替此版本整机结果。
EDGE_CONTROL_V1 bit不含本guard；旧bit的用户实测也不能证明guard或TARGET接入效果。

## 7. 下一步及人工事项

1. MAIN确认可信session/时间/结局账本、生产两个年龄、CDC服务及复位、DDR代次与扫描租约、图文commit和OSD区域。
2. 按版本索引补EDGE_CONTROL_V1新增控制与30分钟记录；已有画质用户反馈保留。若已有未归档结果，先补录。
3. MAIN逐文件接线授权后，使用本guard并执行真实不同频率/相位/复位的顶层故障验证，保持视频不反压。
4. 再做整机P&R、来源归档和TARGET上板。严格同帧失败时整组隐藏，历史框年龄策略没有自动获批。

本轮所有新源码/证据仅在features/color_target；默认保留本地隔离分支，原PR/远端/D规范检出未推进。
提交前格式检查首次将按原字节保存的Windows CRLF识别为行尾空白；原始失败输出保留在仓库外precommit-whitespace-before.log。
仅在本新证据目录设置cr-at-eol和原始log空白属性，保留原始日志/JSON字节；未改全局Git配置，也未靠清洗证据消除失败。
