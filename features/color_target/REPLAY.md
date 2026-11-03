# RGB 回放与独立流封装

状态：**独立实验路径；FILTER_ENABLE=0；未接入主线、未生成 bit、未上板。**
用户已要求相机素材、最小目标和同色目标选择策略暂时保留，因此不依据下面的合成控制
调整生产阈值或启用去噪。现有 `color_target_detect` 的端口保持不变。

## 1. 本轮交付

`color_target_detect_stream` 把现有 RGB 分类、可选 `support3` 和新的 `mask_stats` 串联。
`run_color_target_replay.py` 将 RGB 文件送入该 RTL，再连接现有 track、框线及文字模块，
逐项检查结果包、跟踪状态、几何覆盖、字形像素和两行 28 字符。
旁路模式同时实例化原检测器，对健康/完整 abort 帧作实际 RTL 对照。
新统计器额外检查固定光栅、帧内身份、孤立 EOF 和计数溢出，EOF 关闭统计事务。

回放工具的图像存放和显示查询都在**主机/测试台**，没有为 FPGA 增加整帧缓存。
显示查询在本轮结果和文字稳定之后进行。它不实现 MAIN 的缓存身份、CDC 或显示帧锁存，
不能报告为采集到 HDMI 的整机端到端通过。文字模板当前用于红色演示。

## 2. 时序与取消契约

单一 clk，1280×720 RGB888、每有效拍 4 像素，lane0 位于 `[95:72]`。
尺寸可参数化，但须为完整固定光栅、宽度可被 4 整除、坐标位宽足够、总像素数≤1048575。
无 ready，允许 valid 间断和行/帧间无消隐。身份必须满足 TEAM 协议：回绕前开启新 session。

| 项目 | 约定 |
|---|---|
| 旁路 | 新结果在输入 EOF 后 1 拍发布；比原检测器多一级寄存 |
| 启用支持过滤 | 在输入 EOF 后 WIDTH/4+3 拍发布；1280 宽为 323 拍 |
| 跟踪 | 下一拍消费结果；无效结果不作为目标消失 |
| 文字 | 测试台延迟更新通知，等 track 字段锁存后再取快照；忙时可合并更新 |
| 完整错误帧 | 继续送完固定光栅，发布 `result_valid=0`，计数和坐标清零 |
| 空闲拍 abort | 输入帧仍打开时粘滞捕获，到该帧 EOF 作废；不要求 abort 与 valid 同拍 |
| 协议诊断 | `O_protocol_error` 是复位才清的全局诊断，不是某个结果的有效位；后续健康帧仍可有效 |
| 截断/丢拍 | 必须由外部复位此独立路径，随后从新 session 的完整 SOF 重启 |
| 复位取消 | 取消全部未发布数据，包括上一帧已输入完整但尚在排空的尾部；同复位的 track 也清空 |

后来的错误帧可能在较早健康帧发布前就置全局诊断；不能简单用该粘滞位否决所有后续结果。
逐帧是否可用由结果包的 `O_result_valid` 决定。
复位时若结果已经发布、但 track 尚未消费，结果与跟踪事件数也可能不同。工具逐项记录
`published` / `reset_cancelled_partial` / `reset_cancelled_pending`，不把取消帧伪装成漏检或正常无目标。
这里是显式复位恢复，不是“无需复位自动重同步”；MAIN 若不能接受取消在途帧，须另定恢复契约。

## 3. 运行

```text
python features/color_target/run_replay_data_checks.py
python features/color_target/run_color_target_replay.py --out <输出目录>
python features/color_target/run_color_target_replay.py --full --out <输出目录>
python features/color_target/run_color_target_replay.py --manifest <manifest.json> --out <输出目录>
```

按本机仿真器追加 `--sim modelsim --msim <win32aloem>` 或现有 Icarus 配置。
未给 manifest 时生成明确标注为 synthetic 的 RGB 控制：64×48 的 11 个序列、4 种窄光栅，
`--full` 再加 1280×720。合成结构测试 MIN_COUNT=4；提供 manifest 时默认 MIN_COUNT=64，
可以显式 `--min-count` 覆盖。这些不是相机调参建议，生产默认仍为 64。

输出包括逐帧 JSON/CSV、帧图像哈希、状态及来源身份、取消记录、总计、按来源/拆分汇总，
以及只比较**两路都成功发布且有效的相同标注帧**的 `paired-ablation.json`。
不同模式因延迟造成的取消数量差异单独报告，不利用不同样本分母宣称算法改善。
HOLD 保留旧观测身份；CSV `current_observation=0` 明确区分历史框与本帧测量。
框中心使用包围框中点，不是像素质心。

## 4. 相机数据约定（待实际素材）

模板：`datasets/manifest.example.json`。图像采用单帧 P6 PPM、RGB8、maxval=255。
每帧填写相对路径、session/frame 和可选文件 SHA-256；工具计算实际文件及 RGB 像素哈希。
路径不得逃逸 manifest 目录。`source_kind=camera` 是提供者声明，工具不鉴别相机来源。

- `annotation=null`：未知，排除质量评价；不能当作没有目标。
- `present=false,bbox=null`：确认无目标，用于误报统计。
- `present=true,bbox=[xmin,ymin,xmax,ymax]`：包含两端的原图坐标。
- clip 的 `group_id` 对应同一场景/采集组；不得跨 tune/validation/heldout。
- 相同 RGB 内容也不得跨拆分；按场景划分，不能随机拆相邻帧。
- 漏检记 IoU=0、中心误差=宽+高；无目标 IoU/中心误差为空；P95 包含漏检处罚。
- 已有标注但因异常/取消未评价的帧与未知标注分开计数。故障注入只允许 synthetic 控制。

实际素材到位后再确定最小尺寸、颜色阈值、同色目标选择、允许遮挡和恢复要求。
需要覆盖正常、暗光、明暗突变、侧光、快移、消失重现、细目标与同色干扰；
记录曝光/白平衡/观察点、分辨率、时钟、掉帧及 session 重启信息。
当前没有相机质量通过结论，没有 B/C 连通域选择或高级跟踪部署。

## 5. 自我迭代及硬件边界

首版统计对四个 lane 连续比较，TD 找到 16 级到中心寄存器的关键路径，10 ns 下不满足。
利用固定光栅的 4 像素对齐，改为首/末命中优先编码，去掉串行比较。
还发现 TD 将分类器的常数乘法映射成每 lane 两个 DSP；改为等价常数移位加减后实测 0 DSP。
分类器端口、门限、参数夹取和数学判据不变，完整独立数学回归通过。

资源脚本 `tools/synth_replay.tcl` 的测试架包含输入影子寄存器和输出选择器，
通过少量 I/O 保留完整可观测性。其加载接口不用于实际视频；面积不能直接作为整机增量。
独立 gate 时序估计不等于布线后的 Fmax，完整构建与上板仍由 MAIN 负责。
实测版本、失败对照与原始报告见 [验证记录](evidence/replay_2026-10-17/VALIDATION.md)。
