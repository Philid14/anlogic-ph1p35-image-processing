# 来源与迁移记录

| 项 | 值 |
|---|---|
| 审查对象 | `b43284c`（分支 `feat/latency-osd-display`，保留在远端作为来源记录） |
| 本次基线 | `origin/main` = `651f9bc` |
| 本次分支 | `codex/latency/same-frame-association`（从 `origin/main` 新建） |
| 迁移方式 | 仅迁入本功能必要文件到 `features/latency_view/`；未使用 `--allow-unrelated-histories`、未强推、未整仓覆盖 |

## 迁入

- 重写：`rtl/latency_meter.v`、`rtl/frame_event_bridge.v`、`tests/tb_latency_meter.v`、`tests/run_latency_sim.py`
- 修正后迁入：`rtl/text_overlay.v`（新增 vs/hs 坐标重对齐）、`rtl/char_rom.v`、`rtl/osd_layout.vh`（生成物）
- 迁入：`model/*`（模型/字体/预览）、`third_party/font8x8_basic.h`
- 新增：`tests/tb_overlay_align.v`、`docs/*`、本文件

## 未迁入（按审查要求）

另一套工程的根 `README.md`、`docs/project/STATUS.md`、`docs/verification*`、`work/algorithm_lab/app.py`
与 `registry.json` 注册、以及全部无关历史。Algorithm Lab 插件与本特性无关，故未迁入。

## 上一版被否决的根因（保留记录）

`b43284c` 的 FIFO 只按事件先后配对：DDR 丢帧时（采集 A/B/C、只显示 C）首次显示会被配到 A，
实测 10 拍被报成 27 拍且无告警。本版改为按 `{session_id, frame_id}` 关联，异常显式上报。
