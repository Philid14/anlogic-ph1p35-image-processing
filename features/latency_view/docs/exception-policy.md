# 异常策略（与实现一一对应）

| 场景 | 输入 | 行为 | 告警 |
|---|---|---|---|
| 正常配对 | 采集 X 后显示 X | 首次显示计入统计 | 无 |
| 跳帧（A/B/C 只显示 C） | 采集 A,B,C；显示 C | 只把 C 与 C 配对；A/B 保持 pending | 无（上游若丢弃应发 abort） |
| 上游中止/覆盖 | `cap_kind=1`（同 id） | 删除该记录，之后显示视为未匹配 | bit0（未匹配） |
| 重复显示 | 同 id 第二次 `dsp_event` | 只输出 `age_cycles`，不计统计 | 无 |
| 未匹配显示 | 无对应采集的 `dsp_event` | 不产生测量，`stats_valid=0` | bit0 |
| 关联表满（覆盖） | 第 9 个 pending 采集 | 淘汰最老 pending（轮转），`stats_valid=0` | bit1 |
| 会话切换 | 采集/显示 `session_id` 变化 | 清空旧会话记录，`stats_valid=0` | bit3 |
| 事件过密 | 源事件间隔 < 2 采 clock | 丢弃该事件 | bit2（`cap_too_fast`） |
| 跨域后仍过密 | 出队间隔 < 3 拍 | 保留但置告警 | bit2（`evt_gap_alarm`） |
| `alarm_clr` | 脉冲 | **只清告警位**，不动关联表与统计有效性 | — |
| `resync_req` | 脉冲 | 清空关联表，`stats_valid=0`；之后第一个干净的“采集→首次显示”配对使统计重新有效 | — |

补充规则：

- `alarm_clr` 不会让旧表恢复可信；只有 `resync_req` + 新的干净配对才会（审查要求）。
- 关联失效（`stats_valid=0`）期间，`lat_valid` 与 `age_valid` 均不会产生（不输出看似有效的值）。
- 多拍高电平：`cap_event` 只在**上升沿**计一次；电平保持 N 拍仍为 1 个事件。
- 已知限制：同一 `{sid,fid}` 被重新采集（会话内不应发生）会覆盖旧记录；`session_id` 必须正确递增。
