# TARGET 工程审计与本轮交付（2026-10-18）

角色：TARGET RTL架构评审/验证；以项目外 PROJECT_REVIEW.md 为评审基线。
权限：只读MAIN、独立测试与文档；仅A1最小生产RTL修复。禁止push/merge，不改MAIN或其他生产RTL。
本轮输出保存在功能目录；没有向任何角色发送消息或修改PR。

## 1. 事实基线与证据分层

初始C工作副本与D规范检出均clean，分支 `codex/target/color-target-detect-v1`，
HEAD/PR #2 head为 `b4565a152458d251d694d850a48058a325d66bfb`。
PR OPEN、reviews空、保留Philid14请求、无auto-merge。只读GH核对未授予推送权限。
从该在研基线建立本地隔离分支 `codex/target/a1-integration-audit`；原分支和D检出不随本地提交改变。
A1本地提交 `1e541f193c14d9cf98f767a62f6a16782612ea4c`；后续审计提交仅模型/测试/证据/文档。

| 层次 | 本轮核实结果 | 能说明/不能说明 |
|---|---|---|
| 真实RTL回归 | 类别12组、检测25/25、分类40/40+8、链路396拍、RGB12轮全部通过 | 指定模拟输入正确；不是实拍准确率 |
| 当前TRACK RTL特征 | 九采样、六项OPEN_GAP | 当前真实行为；不是拟议要求通过 |
| 拟议集成模型 | 36轨迹，覆盖用户十类故障 | 示例契约逻辑一致；不是MAIN/CDC/DDR已实现 |
| 静态源码审计 | 21文件位置/哈希；TD58入口路径存在，TARGET入口0 | 绑定当前可见源码；不是新构建 |
| 历史整机证据 | 58/58构建输入与历史源码LF一致 | 可追溯历史MAIN报告，未包含TARGET |
| 需求/决策 | 年龄、任务语义、预算、恢复等未批准 | 不擅设生产值 |

原始记录位于 `../evidence/integration_audit_2026-10-18/`，完整本机输出路径见其中A1_VALIDATION。
历史evidence未覆盖；PROJECT_REVIEW.md本身保留原样，用本报告说明新增发现与纠正。

## 2. 已确认事实、位置与架构问题

下面路径前缀 H 指 `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/`。
实际行号/片段/LF哈希见 `source-manifest.json` 和 `source-excerpts-formatted.md`；源码优先于文字总结。

| 编号/严重程度 | 已验证事实与位置 | 因果与影响 | 当前状态 |
|---|---|---|---|
| A1/P2 | 分类器1/2绿蓝、其余红；旧detect和mask_stats发布参数低2bit | 非法类别命中与标签矛盾 | 已最小修复及硬期望验证 |
| I1/P1 | H/awb.v:303-307 的user直接接输入；valid经过延迟；edge_control_stream.v:3也声明提前通知 | 不能把RAW处的首像素user等同AWB处SOF；直接接会漏开帧/错位 | MAIN规范化sideband待实现 |
| I2/P1 | H/isp/uial2axis.v:55-56，last是EOL；H/awb.v:307由valid包络产生last | EOL不是EOF；任意行内valid空洞可能被误当EOL | 需独立EOF/几何及空洞契约 |
| I3/P1 | H/design_top_wrapper.v:613 的video_in错误输入接1'b0 | 不能假设已把真实MIPI/溢出/截断通知TARGET | MAIN错误聚合待实现 |
| I4/P1 | H/video_in.v:103-137有2bit写/读指针；:175-203有错误覆盖回退；H/video_out.v:114-128选槽地址 | 槽复用/回退而缺代次与唯一帧键，无法证明检测结果匹配实际像素 | 元数据/扫描租约待实现 |
| I5/P1 | H/design_top_wrapper.v:589,609,615,644,655,754分别连接观察/DDR/显示域 | 单域回放不覆盖真实整包CDC、复位、服务能力 | MAIN适配待实现 |
| I6/P1 | TARGET track:81-97,144-159无frame_id准入/独立时间；text:140,171,197-198只保证转换事务快照 | 重复/乱序/过期观测可被接受；图文整显示帧一致性未闭合 | A2仅提案，生产RTL未改 |
| I7/P1 | TARGET新封装有323拍全宽尾延迟及复位清尾；旧检测器无完整光栅校验 | 结果晚到/取消须列账；旧接口不能替代新统计器校验保证 | MAIN调度/恢复契约待确认 |
| I8/P1 | TARGET V1只有pixel_valid，无lane_valid/keep | 三个有效像素与四个像素若给出相同总线无法区分 | 部分尾拍需源端错误信息，禁止静默接受 |
| I9/P1集成门 | .al中58个入口，无TARGET；SDC有异步时钟分组 | 功能目录存在不等于实际综合；异步分组不证明CDC安全 | 尚未接入/P&R/bit/板测 |

在所列六个主路径文件中检索 session_id/frame_id/generation_id/slot_generation 没有命中。
这是有边界的静态证据，不声称全仓库不存在任何同义命名逻辑。实际接口端口也未提供这些元数据。
主线已有双时钟像素FIFO和edge配置邮箱；这些不构成TARGET结果包及其身份/复位代次已跨域的证据。
本轮未对整机CDC作完整证明，也未因缺少TARGET元数据而断言已有视频CDC必然故障。

**纠正旧交接：**INTERFACE.md旧清单中“awb user直接接SOF”的默认建议不成立。
RAW uial2axis的user定义虽正确，AWB为video_in保留早通知；不允许为了TARGET破坏已有早通知链。
本轮以追加审计/契约更正该假设，不改MAIN接线。AWB正常行尾包络能否满足场景需独立波形确认。

## 3. 时钟、资源、约束与P&R边界

TD实际入口：`.../td_project/camera_to_dsi_display.al`，top=design_top_wrapper，PH1P35MDG324/-3，
58项输入存在；本轮没运行会写Runs的 `scripts/prepare_td_runs.py`，也没有打开/改写TD主工程。
该脚本要求已有settings.cfg并会生成run prj，不能当作无副作用读取命令。
活动约束为同目录 camera_to_dsi_display.sdc 及pin.adc；user_source/constraints_source/timing.sdc为空，
不能只看这个空文件便断言工程无时序约束。原生.al有未转义&，审计使用只读匹配而未重排XML。

历史 `EDGE_CONTROL_V1` 的 SOURCE_MANIFEST 绑定 dff499a75cf0a348aaf2167548b4fe34bf4a78a9；
本轮逐项以Git blob与当前文件LF归一比较，58/58一致。历史路由报告：

| 项目 | 历史实际报告 | 本轮能否作为TARGET集成结论 |
|---|---|---|
| MIPI观察域约束频率 | 59.995MHz | 否，须集成后核实clock派生/覆盖 |
| DDR usr域 | 66.667MHz | 否，具体dhi/读写时钟还需关联 |
| HDMI pixel / serial | 75.002 / 375.094MHz | 否，不是PLL界面请求74.25/371.25的值 |
| 名称pll_clk_24m | 23.810MHz | 不能按名字24MHz推导精确超时 |
| 路由资源 | LUT6 14724/21216；Slice 16473/21216；ERAM39/108；DSP9/40 | 不是当前TARGET预算或剩余资源分配 |
| 路由SWNS/HWNS | +0.100/+0.020ns；STA覆盖96.14% | 历史MAIN接近时序边界，不保证新增扇出后仍通过 |
| 板测 | BUILD_INFO仍记待用户上板 | 不能声称历史bit已实板验收 |

当前TARGET此前918/1224 LUT、579/950 reg、0/1 ERAM、0DSP和+1.170/+1.140ns
是含输入影子寄存器/输出选择器的独立gate架结果，不能与MAIN路由LUT6/Slice机械相加。
本轮A1没有重新综合；即使常量归一预期不增加合法配置运行时逻辑，也只属于推论。

源审计首次历史比较遇Windows git-show长路径限制，原错误日志保留。
改为ls-tree取得blob ID再cat-file读取，未改全局Git配置，最终完整比较成功。

## 4. 本轮操作、范围与验证

生产RTL仅改旧detect与mask_stats各一个类别常量及发布选择；两个参考模型同步标签。
classifier/stream/support3/track/text及MAIN相对基线字节归一化不变；support3默认关闭，门限不改。
新增类别硬期望、TRACK特征台、集成提案模型、故障矩阵生成、只读审计提取器和三份接口/方案文档。

| 测试/审计 | 结果 | 证据 |
|---|---|---|
| 正确硬期望对基线 | 5/12通过、7组失败，退出1 | a1-before.txt/json |
| 修复后类别/四路径 | 12/12、240结果包；仅42包cls改变 | a1-after、a1-differences |
| 两Python模型对硬期望 | 12/12 | a1-models |
| 既有分类/检测/链路/RGB | 40/40+8；25/25；396拍；7760408像素 | *-regression.txt、rgb-summary |
| 当前TRACK异常行为 | 九采样复现、六OPEN_GAP | track-audit.json/txt、track-transcript |
| 拟议集成契约 | 36/36轨迹、覆盖十类；三个错误提交负样本被拒 | contract-model-final.json/txt |
| MAIN静态审计/历史输入比对 | 21文件、58入口、TARGET0、58/58历史一致 | source-manifest、source-excerpts-formatted |

测试台首轮abort/hit期望订正及原日志见A1_VALIDATION，未删除失败或把它混入最终缺陷计数。
36/36是模型例子通过，六项TRACK开放缺口仍保持OPEN；部分尾拍还存在现有端口不可观测的硬限制。
最终模型还包含不同源/目的时钟边沿调度、延迟通道、年龄等号边界和无效包不续命检查；
这些是离散事件夹具，不仿真亚稳态或物理CDC。首轮31轨迹输出与对应runner快照另存原始输出目录。

复现新增审计/模型（Python输出目录均须新建，避免覆盖证据）：

```powershell
& $py -B -X utf8 -u features/color_target/run_track_admission_audit.py --sim modelsim --msim $msim --out <track审计目录>
& $py -B -X utf8 -u features/color_target/run_integration_contract.py --out <契约模型目录>
& $py -B -X utf8 -u features/color_target/tools/audit_integration_sources.py --out <源码审计目录>
```

A1及已有回归完整命令见 `../evidence/integration_audit_2026-10-18/A1_VALIDATION.md`。
FAULT_MATRIX逐项列输入、独立预期、不变量和失败条件；它区分模型、RTL与缺失硬件证据。

## 5. 仍未关闭的风险与决策门

1. 规范化SOF/EOF、错误事件和lane完整性未实现，直接接线不可接受。
2. DDR真实frame_key/写代次、扫描租约、CDC复位隔离/容量和显示整组提交未实现。
3. A2身份准入/年龄机制只是方案；没有批准生产阈值、接口或负责方。
4. 当前同色全局框语义、最小尺寸/形状/场景、允许检测延迟、历史框年龄、取消恢复和预算未定。
5. 缺相机保留集；没有真实采集→HDMI正确标注、长期运行或明暗剧变证据。
6. 复杂候选、连通域和CNN不进入本阶段；保留support3关闭与原生产阈值。

建议下一步：人工确认A2职责及MAIN契约 → 批准后实现适配/断言 → 实际跨域与缓存时序回归 →
负责人审查/接入 → 新整机P&R与bit来源归档 → 按明确场景板测。A1局部修复不依赖这些决策，已完成。
本地提交尚未推送；PR #2仍为b4565a1，D规范检出保持原状。后续推送/MAIN改动必须重新取得授权。
