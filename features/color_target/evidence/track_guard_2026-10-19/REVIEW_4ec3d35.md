# 对4ec3d35及其A1前序的实际审查

审查对象：4ec3d35、d905cdc、1e541f1；对照b4565a1，检查范围为A1两处RTL和模型、统一验证入口、接口/板测文档及证据口径。
本审查是AI技术检查，不是人类负责人对PR最新SHA的合并批准。PR #2仍4ec3d35/OPEN、无review/check、无autoMerge。

## P2：旧仿真helper丢失运行时失败状态（已披露缺口，本轮补独立复现）

源码：`features/color_target/tools/simlib.py:159` 在调用vvp/vsim后无条件 `return True`；第117行vlib返回码也未检查。
因果链：底层工具已经输出完整数据→异常退出但未打印调用者匹配的Error→helper仍ok=True→A1精确数据比对和完成标记都成立→Python child exit0→统一入口job也认为通过。

[注入汇总](legacy-exit-witness/summary.json)用已归档硬期望输出作固定数据，不改变RTL和gold；只mock工具运行返回码。

| 控制 | 独立期望 | 旧job实际 |
|---|---|---|
| runtime exit0 / 完整正确数据 | 通过 | 通过 |
| runtime exit7 / 同一正确数据，无Error文字 | 失败 | 错误地通过12/12，Python child exit0 |
| runtime exit7 / 同一数据并附Error | 失败 | 失败，Python child exit1 |

不据此指控历史ModelSim真的失败；历史结果仍有逐项数据对照的价值，但不能补造未捕获的底层退出码。
建议最小修复：每个vlib/vlog/vsim或iverilog/vvp的非零退出逐层失败并保留原始输出，再跑上述负对照和必要回归。
本轮未改旧helper；新guard runner直接逐阶段校验，六个工具失败见证已经通过，避免把此缺口带进新模块证据。

## P2：历史板测状态分散，不能用第一处“待上板”概括工程

当前A/B BUILD_INFO仍“待上板”，但IMAGE_TUNING_LOG:117–122及正式tag结果提交明确已有上板；A/B结果提交不在当前HEAD祖先链。
AWB_V2头部“尚未上板”与后面的日期反馈并存。历史候选计划不是撤销后续结果。
已建立[有来源的版本索引](board-records/INDEX.md)：11归档版本，9用户反馈，D与EDGE_CONTROL未找到完成记录；不把实测反馈等同全项验收或原始帧数据。
MAIN可另行合并文档状态；本轮不cherry-pick、不移动tag、不改共享记录。

## A1：本范围未发现新的功能缺陷

两处RTL只增加同一有效类别常量，并在结果标签使用；分类判据、count/geometry、流水和生产阈值未变。
只有1绿/2蓝，其余参数回退红/标签0，与既有classifier一致。独立硬gold、历史负对照和本轮quick的12/12仍成立。
本结论限于本次差异和所跑回归，不宣称全仓库形式化正确。

## P1：接入前的系统缺口仍开放

MAIN早user与RGB需另造对齐SOF；错误口固定0；真实帧账本/DDR代次、CDC整包/服务/双端复位、显示像素与整组标注匹配没有通过此提交实现。
原TRACK的重复/乱序/session/年龄问题在直接使用路径仍存在；本轮用户批准的新guard只建立独立实现证据。
无真实顶层时序和板测，不以MERGEABLE、模型PASS、合成画面或独立gate资源代替整机就绪。
