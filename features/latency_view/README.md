# `features/latency_view/` —— 帧身份延迟测量与性能可视化（LATENCY）

对应赛题 **进阶三**；对应 `TEAM_PROTOCOL_V1` 的 LATENCY 角色与 §2.3（L1 帧计数/帧率、L2 模拟事件计时与异常、L3 由 MAIN 接入）。

> ⚠️ **状态（协议 §5.3.4、§6）**：独立模块完成、模拟事件验证通过；**未接入主线、未生成 bit、未上板**。不得表述为"进阶三已整机完成"。

## 口径

- 起点：MIPI 解码后该帧首个有效像素（`cap_event` kind 0）；终点：同一帧首个有效像素送至 HDMI（`dsp_event`）。
- 用 `{session_id, frame_id}`（各 32 位）关联；**只有完整帧首次显示**进入主统计；重复显示只报 AGE。
- 不含曝光与显示器内部延迟；不改 DDR 调度、主线时钟、顶层接线、共享 OSD。

## 内容

| 路径 | 作用 |
|---|---|
| `rtl/frame_event_bridge.v` | 上升沿事件（多拍高电平=1 次）、最小间隔、`{kind,sid,fid}` 异步 FIFO |
| `rtl/latency_meter.v` | 同帧关联、首次显示统计、AGE、帧计数与帧率窗口、粘滞告警、`resync_req` |
| `rtl/latency_osd.v` | 8 行面板：LAT / AVG / AGE / CAP fps / DSP fps / FRM+E / CNT / ALM |
| `rtl/text_overlay.v` | 叠加；坐标由 `vs`/`hs` 重对齐 |
| `rtl/char_rom.v`、`rtl/osd_layout.vh` | 生成物，勿手改 |
| `model/latency_model.py` | 面板布局/格式/字形；`model/gen_osd_layout.py` 生成布局头 |
| `tests/` | 18 场景回归 + 面板内容 + 坐标对齐 |
| `INTERFACE.md` / `VERIFICATION.md` / `INTEGRATION.md` / `TASK.md` / `DEMO_STEPS.md` / `PROVENANCE.md` | 接口、验证、接线、任务卡、演示、来源 |

## 运行

```powershell
python model/latency_model.py
python model/gen_osd_layout.py --check
python tests/run_latency_sim.py
python tests/run_bridge_sim.py         # 事件桥丢失账本（满队列/连续错误）
python tests/run_osd_sim.py            # 小分辨率 normal + fault
python tests/run_osd_sim.py --full     # 追加 1280x720 单帧回归
python model/preview.py --out .build/preview.png   # 面板预览 PNG
```
（`IVERILOG_BIN` 可指定 iverilog；否则尝试 `.tools/iverilog/bin` 与 PATH。）
