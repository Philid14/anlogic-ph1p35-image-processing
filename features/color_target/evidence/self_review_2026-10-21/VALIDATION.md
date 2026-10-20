# 自检修正验证记录

2026-10-21；原TARGET提交 `131b4382507cc0979c9aeda0f522fac092ffbab8`。
受测LATENCY固定 `531ef616dd53efa200e16b3839319f18b4c48d72`，未修改其源码。
问题逻辑链、前后差异和方案见 [SELF_REVIEW](../../integration/SELF_REVIEW_2026-10-21.md)。

## 已执行验证

1. 对原131b438真实控制日志分别篡改gold、pass=2、检查类别。原parser三次均错误接受；
   原始篡改日志和before-parser-probes.json保留。新parser对同三份日志全部判证据无效，见after-probes.json。
2. 原编译测试架导出公开输入be的VCD（1ps单位），20次上升沿的19个间隔全为60000ps。
   新测试相同测法全为50000ps，源时钟10ns；分别为6拍和5拍。修正前后VCD与工具原始输出均保留。
3. 新RTL用例9场景33检查，新增单错误正对照通过；两个CLI门各执行一次相同场景：
   integration与component均exit1、证据有效，54个vlib/vlog/vsim阶段全部exit0。
   不能将重复执行相加成18类故障或66条独立覆盖。
4. 证据解析/判定门10项软件测试通过。独立gold、非二进制标志、前提失败、截断/重复/矛盾、
   工具失败、缺场景及组件门不能认证MAIN均被检查；不是RTL或物理CDC证明。

3个控制通过；2个component_contract各有1条失败；1个proposed_policy有2条建议未满足；
3个main_adapter_dependency各有1条未满足，总计7条。模块缺陷、待决策和外部依赖单独标记，
不能汇总成7个RTL bug。两个新summary的schema为2；旧schema1结果及原75成员日志不改。

## 命令

仓库根目录，Python3.12.14、ModelSim ASE10.3c：

```powershell
python -B -X utf8 features/color_target/tb/test_latency_review_evidence.py
python -B -X utf8 -u features/color_target/run_latency_handoff_review.py --revision 531ef616dd53efa200e16b3839319f18b4c48d72 --gate integration --msim <ModelSim目录> --out <全新目录A>
python -B -X utf8 -u features/color_target/run_latency_handoff_review.py --revision 531ef616dd53efa200e16b3839319f18b4c48d72 --gate component --msim <ModelSim目录> --out <全新目录B>
```

实际路径：`outputs/self-review-2026-10-21/rtl-01`、`rtl-02-component`（仓库外AnlogicTrack2工作目录下）。
--gate默认integration；exit0只代表所选门通过，exit1为有效证据下所选门不满足，exit2为无效证据/工具失败。
任何门都保留integration_ready=false。当前组件门也失败，没有借分类变化制造绿灯。

## 证据与边界

summary.json为integration结果，component-summary.json为组件门结果。
RAW_LOGS.zip共69成员：54工具日志、2原始summary，以及输入波形、原始反例、解析器自测和复现实验脚本。
LOG_ARCHIVE_INDEX.json记录每个成员长度/SHA256，打包后逐项读回验证。
工具额外执行了2次vsim导出修正前后VCD，复用相应已编译测试架；与54个新RTL工具阶段分开记账。
复现实验脚本包含本机证据路径，仅作实验记录；跨机使用上方仓库runner，不依赖这些绝对路径。

source-state.json与summary源码哈希绑定实际工作区受测文件；当时HEAD是131b438，不能只靠HEAD代表新测试。
两种门源码快照相同，且与归档时runner/TB/helper逐字节一致；9个TARGET生产RTL的LF哈希与既有交付一致。
本目录SHA256清单绑定本轮当前文件；旧latency_handoff_2026-10-20清单须按其131b438快照校验，
不能把那个旧清单当成更新后HEAD的哈希表。

原handoff16未改、未重跑；未做新的guard综合、整机P&R、资源/时序评估、bitgen、tag或上板。
support3关闭，颜色阈值不变。实际MAIN接入与LATENCY生产修复仍由队友完成。
