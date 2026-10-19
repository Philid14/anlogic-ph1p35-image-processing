# TARGET 独立 TRACK guard：接口与验证

版本：`TRACK_GUARD_V1`。基线：4ec3d35；用户于2026-10-19明确确认“按推荐方案实施 TARGET 独立 guard，MAIN另行确认”。
状态：**TARGET独立RTL已实现并自检；未加入TD、未接MAIN、没有新P&R/bit/板测。**
新模块 `../rtl/color_target_track_guard.v` 封装原 `color_target_track.v`；原track/detect/text/support3和MAIN文件未改。
旧TRACK直接使用时的六个OPEN缺口仍存在。本guard通过不能据此宣称原模块、CDC或整机已修复。

## 1. 所处位置和工程前置条件

建议：可信MAIN帧事务结局＋TARGET检测结果 → 本guard → MAIN整包传输/同帧显示提交。
本模块全端口处于同一**结果处理时钟域**；这不意味着相机、DDR和HDMI处于同一域。
跨域整包、复位屏障及MAIN事务账本必须在模块外落实。没有ready，没有视频数据通路，不生成时钟/运行时复位。

MAIN必须提供可信身份，尤其无效/取消结局不能单独使用旧检测器可能遗留的结果ID。
结果为顺序流：较大的身份一旦退休，随后较小的迟到结果会被拒绝，不作回填。
session控制必须由可信控制面发行，生命周期内不复用旧session；guard只保存当前session并检测直接重用，不能无限保存全部历史。
本guard私有的core token仅重置旧TRACK的确认历史，不是对外帧身份，不得用于DDR或延迟测量。

## 2. 参数：没有擅定生产年龄

| 参数 | 默认 / 契约 |
|---|---|
| XW/YW | 11/10；与原图坐标一致 |
| TIME_W | 64，须>=2；无符号时间戳位宽，不代表某个已确认时钟频率 |
| COUNTER_W | 16，须>=1；诊断饱和计数位宽，不回绕 |
| ACQ_FRAMES/LOST_FRAMES | 3/15，沿用原TRACK及其1..255夹取行为；按独立有效观测计算 |
| MAX_TARGET_AGE_TICKS | 默认0；必须显式给出1..2^TIME_W−1，目标观测寿命 |
| MAX_RELIABLE_AGE_TICKS | 默认0；必须显式给出1..2^TIME_W−1，可靠观测活性上界 |

两个年龄参数是TIME_W+1位有符号参数，以识别负值/超位。任何一个非正或超范围，整个准入保持禁用，不能默默选一个经验值。
MAX_JUMP在包装内部固定0，support3和颜色阈值不变。本模块没有改动原ACQ/LOST生产默认。
测试中5/5、3/7、7/3和8bit时间只作反例夹具；整机值仍须MAIN依据真实时钟、延迟及场景确认。

## 3. 输入事务

| 输入 | 位宽 / 语义 |
|---|---|
| clk/rst_n | 本域时钟 / 低有效异步全局复位；上游须按各域同步释放 |
| I_session_start / I_control_session_id | 1/32；明确的新session屏障，优先于同拍数据 |
| I_time_valid / I_now_tick | 1/TIME_W；本域可信单调时基，停止结果输入时仍须前进 |
| I_result_strobe / I_identity_valid | 1/1；一项终态结局 / MAIN已从账本解析身份 |
| I_session_id / I_frame_id | 32/32；当前结局身份；无反压，每拍最多一项 |
| I_result_valid / I_cancelled / I_target_present | 1/1/1；有效测量 / 取消 / 有目标；取消优先于valid |
| I_capture_tick | TIME_W；采集首有效像素的可信时间，随身份整包关联 |
| I_color_class / I_pixel_count | 2/20；检测结果类别和匹配像素数；类别语义沿用A1 |
| I_xmin/xmax/center_x | XW各一项；inclusive包围框和框中心 |
| I_ymin/ymax/center_y | YW各一项；原图坐标，非Sobel半采样坐标 |

无效/取消结局不要求使用capture_tick，不增加miss，也不刷新可靠或目标时间，但会退休可信身份。
完整有效且无目标会进入旧TRACK的LOST逻辑并刷新可靠时间，不能刷新旧目标时间。
有效有目标必须同时满足可靠年龄与目标年龄；有效无目标只检查可靠年龄。

优先级：全局reset → session_start → 时间故障 → 身份/顺序准入 → 取消 → 无效 → future/stale时间 → 有效观测。
session_start同拍数据不消费；MAIN须在屏障完成后交付新epoch结局，或明确取消，不得静默遗失。
同session仅接受严格递增帧号；frame_id由0xffffffff回到0会拒绝，必须先换session。

## 4. 输出和显示责任

| 输出 | 含义 |
|---|---|
| O_session_ready/O_current_session_id | 配置/可信时基/session可用；session_start期间ready为0 |
| O_event_strobe | 本拍采样了输入结果脉冲；不表示准入 |
| O_retired_strobe | 可信的当前session递增key已消费，包括取消/无效/未来时间/过旧结果 |
| O_admitted_strobe | 本拍确有一个完整、可靠、新鲜的独立观测交给TRACK |
| O_reason[7:0] | 下表的控制/当前结果原因；无事件默认0 |
| O_timeout_strobe | 一个活跃TRACK确认周期因任一年龄上界失效而退休；只发一次，不用新结果驱动 |
| O_track_state[1:0] | 0 SEARCH / 1 ACQ / 2 TRACK / 3 HOLD；不可用/过期时对外SEARCH |
| O_reliable_valid/age/tick | 近期可靠观测的有效标记、年龄、采集时间；目标过期不抹掉仍新鲜的可靠无目标记录 |
| O_observation_session_id/frame_id | 最近准入的可靠观测；无目标也更新 |
| O_positive_valid/age/tick | 当前确认周期最近正观测的有效标记、年龄、采集时间；确认周期退休后不能复用旧框 |
| O_box_session_id/frame_id | 最近正观测的真实来源，HOLD时保留旧身份，不能偷换为当前观测 |
| O_observation_usable | 原TRACK允许显示，且当前确认周期/可靠年龄/正观测均有效；**不是最终显示enable** |
| O_color_class/count/xmin/xmax/center_x/ymin/ymax/center_y | 同一次正观测的数据；observation_usable=0时输出0 |
| *_count | duplicate、reorder、wrong_session、identity_error、invalid、cancelled、stale_result、time_error、timeout九类独立饱和计数 |

有效的年龄满足 `elapsed<=limit`；`elapsed>limit`时过期。年龄无效输出全1，必须先看valid位。
时间有效丢失、倒退或回绕使当前run不可用；恢复time_valid本身不足以恢复，需要可信的新session屏障。
首次复位后未有session控制时，不接受“第一包结果”作为session来源。
now_tick与所有输入须满足本域同步时序；模块不能在自己的clk停止时继续计算超时，外部显示域仍须有独立失效门控。

**MAIN第一版严格同帧**：所选像素key/generation必须与可用box的来源匹配，框/十字/文字/count/state整组准备并一次commit。
在HOLD中observation_key可能已经更新，box_key仍旧；即使observation_usable=1，当前像素若不是box对应帧，也必须关闭整组覆盖。
不能只把O_observation_usable直接接现有overlay/text。文字70拍转换、观测ID/完成握手、扫描租约、重复帧/跳帧和DDR代次仍是MAIN工作。
严格整扫描年龄还需验证 `display_start+max_scan_duration-capture_time<=max_age`，本模块没有显示时钟和扫描上界。

| reason | 含义 | 是否退休 / 准入 |
|---:|---|---|
| 0 | 无事件 | 否/否 |
| 1/2 | 可靠有目标 / 可靠无目标 | 是/是 |
| 3/4 | 无效 / 取消 | 是/否 |
| 5/6 | 重复 / 更小帧号或同session回绕 | 否/否 |
| 7/8 | 错误session / 身份无法可信关联 | 否/否 |
| 9/10 | 结果过旧 / 来自未来的采集时间 | 是/否 |
| 11 | 时间不可用/倒退，或session_start时无可信时间 | 否/否 |
| 12 | 新session屏障 | 否/否；同拍数据也不消费 |
| 13/14/15 | 配置禁用 / 直接复用当前session / 未就绪 | 否/否 |

time_error计数覆盖活跃时钟故障及有效结果future-time；同一时钟故障不逐拍重复计数。计数跨session保留，全局reset清零。

## 5. 验证命令与实际结果

从仓库根目录运行，所有输出目录必须新建；ModelSim只接受显式安装路径或既有环境变量。

```text
python -B -X utf8 -u features/color_target/run_track_guard_contract.py --selftest-tools --out <新工具测试目录>
python -B -X utf8 -u features/color_target/run_track_guard_contract.py --sim modelsim --msim <win32aloem> --out <新RTL目录>
```

新runner只复用simlib的路径发现，不调用其simulate。vlib/vlog/vsim或iverilog/vvp每一阶段都记录独立退出码和原始输出。
非零退出、错误文本、缺失/重复结束标记、零检查、缺失/重复场景或执行期间源变化都会失败。
当前实际执行ModelSim ASE 10.3c；Icarus路径已提供但本轮没有执行，不能宣称双仿真器通过。

最终9/9配置、818次字面硬断言：TIME_W=8和64各398次；独立目标/可靠年龄、禁用、负值、超位、最大可表示年龄共22次。
测试工具6/6失败见证通过；4个故意破坏的RTL副本均被硬断言抓住。逐项输入/预期/不变量/失败条件见本testbench和归档VALIDATION。
原TRACK六个缺口在未包装路径仍OPEN；本guard只给出了经过独立验证的可选准入层，仍依赖MAIN提供可信输入和显示契约。

## 6. 尚未建立的证据

- MAIN实际SOF/EOF、取消账本、时间来源、跨域原子性/容量/复位及DDR槽代次/扫描租约。
- 图文同一观测的commit实现、真实显示帧选择、历史最大年龄/可靠超时的生产值。
- 新guard的综合资源、时序、整机P&R、bit和实板；本轮不外推既有gate或EDGE_CONTROL路由结果。
- EDGE_CONTROL_V1新增控制和至少30分钟板测仍未找到完成反馈；历史BLC/AWB/增益/EDGE的用户反馈已经索引，不要求全部重做。

实现与失败日志见 [本轮验证记录](../evidence/track_guard_2026-10-19/VALIDATION.md)。
