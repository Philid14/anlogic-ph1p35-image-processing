# latency_view - 同帧关联的延迟测量与 OSD 叠加

三人分工中「延迟显示」部分。本目录是**独立特性目录**，从本项目 `origin/main` 新建分支后迁入，
不携带另一套工程的 README、状态文件、应用注册或无关历史（见 `PROVENANCE.md`）。

## 内容

| 路径 | 作用 |
|---|---|
| `rtl/frame_event_bridge.v` | 采集事件**边沿检测**（多拍高电平只算 1 次）+ 最小间隔检查 + `{kind,sid,fid}` 跨时钟（gray 指针 async FIFO） |
| `rtl/latency_meter.v` | 以 `{session_id, frame_id}` 关联采集/显示事件；首次显示计入统计、重复显示只报图像年龄；粘滞告警 + `resync_req` 重新同步 |
| `rtl/text_overlay.v` | 字符面板；坐标由 `vs`/`hs` 重新对齐（修复仅靠 DE 累计导致的错位） |
| `rtl/char_rom.v`、`rtl/osd_layout.vh` | 生成物（公开领域字体 + 模型），勿手改 |
| `model/` | 硬件等价模型、字体表、预览脚本（预览仅需标准库） |
| `tests/` | 12 个场景回归 + 坐标对齐测试 |
| `docs/` | 接口契约、异常策略、测试报告 |
| `third_party/` | 上游字体原文件（Public Domain） |

## 状态

`RTL_SIM_PASS`（Stage E）：`tests/run_latency_sim.py` 12/12 通过；坐标对齐测试通过。
**未做 TD 综合、未生成位流、未上板**，因此没有资源/时序/整机结论。OSD 顶层格式化器
（原 `latency_osd.v`）本次未迁入：它需按 MAIN 确认后的事件接口重新接线（见 `docs/interface-contract.md` 第 6 节）。

## 运行

```powershell
python tests/run_latency_sim.py            # 12 个场景（需要 iverilog）
python tests/run_latency_sim.py --list
# 坐标对齐（独立测试台）
iverilog -g2012 -s tb_overlay_align -o align.vvp tests/tb_overlay_align.v rtl/text_overlay.v rtl/char_rom.v
vvp align.vvp
```
`IVERILOG_BIN` 可指定 iverilog 路径；否则依次尝试 `.tools/iverilog/bin` 与 PATH。
