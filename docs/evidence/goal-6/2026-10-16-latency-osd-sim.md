# 证据：延迟测量与 OSD 显示仿真通过（2026-10-16）

- 验收 ID：G6-L（见 `docs/verification/acceptance-matrix.md`）
- 状态：`SIM_PASS`（仿真与黄金模型逐位一致）；**未上板**
- 日期 / 执行者：2026-10-16，Codex（本仓库工作副本）
- 工具：Icarus Verilog 14.0 (devel, s20260301-579-g15d870a52) + `vvp`
- 命令：

```powershell
# 生成物一致性
python scripts/gen_char_rom.py --check
python scripts/gen_osd_layout.py --check

# 全部用例（含 1280x720 整帧）
python work/tests/run_latency_sim.py --full

# 模型自检与预览
python work/models/latency_osd_model.py --self-test
python work/models/latency_osd_preview.py --out work/output/latency-osd/preview.png
```

- 结果摘要：`cases: 7, failed: 0`（`RESULT: PASS`）

| 用例 | 比对内容 | 判定 |
|---|---|---|
| `meter_same_clock` | 4 次测量的 `lat_ticks`/`lat_cycles`/`lat_valid` 精确相等 | PASS |
| `meter_queue` | 30 个源事件、8 深度队列的组对与溢出粘滞位 | PASS |
| `meter_edges` | 空队列出队、下溢粘滞位、整数刻度 | PASS |
| `meter_cross_clock` | 24 ns 源钟下 4 次测量的逐拍精确值 | PASS |
| `overlay_small` | 8192 有效像素哈希 + 首行 64 像素逐个 + `de` 三拍延迟 | PASS |
| `overlay_full_720p` | 921 600 有效像素哈希 | PASS |
| `osd_small` | 测量值、48 字节字符缓冲区、20480 像素哈希、`err_clr` 后错误半字节为 0 | PASS |

- 证据文件：
  - 原始输出：`work/output/latency-osd/*.log`（每个用例一份），汇总 `results.json`
  - 预览图：`work/output/latency-osd/preview.png`、`preview-panel.png`
  - 测试代码：`work/tests/tb_latency_meter.v`、`tb_text_overlay.v`、`tb_latency_osd.v`、`run_latency_sim.py`
  - 模型：`work/models/latency_osd_model.py`（`--self-test` 通过）
- 证据类型：`project`（本机仿真与生成脚本）
- 未覆盖：TD 综合/布局布线/位流、上板测量、真实工程中的插入点、帧缓存带来的整帧延迟。
- 保留的失败记录：集成用例的 `lat_cycles` 曾与模型相差 1 拍，已定位为测试台激励相位
  （源事件在时钟沿后 1 ns 驱动），保留 1 拍容差并在测试代码中注明；同钟与跨域的精确周期比对
  由 `tb_latency_meter` 覆盖。另有两次测试台自身缺陷（同步信号零延迟驱动、向量行字段数不一致）
  已修复，修复前后的日志保留在 git 历史中。
