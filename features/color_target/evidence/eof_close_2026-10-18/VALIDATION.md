# 原检测器 EOF 生命周期修复（2026-10-18）

角色 TARGET；范围仅 `features/color_target/**`。基线为 `5565545efb4365e192c372e5e8024332e2745fcf`。
独立仿真验证，未接入主线、未生成 bit、未上板。本轮未重测旧检测器资源或物理时序。
前一阶段完整 RGB/分类/gate 证据保留原版本，见 `../replay_2026-10-17/VALIDATION.md`。

原 `color_target_detect` 在有效 EOF 后未关闭 `open_f`。对一张 4×1 全红单拍帧
再送一个没有 SOF 的全红 EOF，原实现会把 count=4 累加为 count=8，并错误发布为有效。
新增硬编码用例独立于参考模型：正常帧 valid=1/count=4，零散 EOF valid=0/数据字段清零，
下一正常帧 valid=1/count=4。将同一测试指向基线 RTL，0/1 通过且以非零退出；
原始错误输出保留在 `before-negative.txt`。

现在 EOF 关闭帧；发布判据仍使用该时钟沿更新前的帧状态，SOF+EOF 同拍仍正常。
没有修改端口、正常结果发布时序或默认阈值。无效结果的身份仍沿用原接口行为，
不能把该身份当作有效观测。参考模型同时更新，但新增硬期望不依赖它。

ModelSim ASE 14.1 复测通过：

- 检测器默认 24 条，加完整 1280×720 用例共 **25/25**；包含中止后单拍恢复、
  连续单拍帧、帧身份和新增零散 EOF。见 `detector-after.txt`。
- 原 detect→track→overlay 链路 **396 拍**逐拍比较通过。见 `chain-after.txt`。
- 64×48 RGB 旁路回放 **76241 输入时钟、193540 有效输入像素、62 结果事件、
  61 跟踪消费事件、18276 显示查询**通过；健康/完整 abort 原检测器对照 59 组，
  另直接检查缺 SOF 的 EOF 不发布有效遗留数据。见 `replay-after.txt` 和 `replay-summary.json`。

复现命令（在仓库根目录，仿真器路径由调用者提供）：

```powershell
python features/color_target/run_color_target.py --full --sim modelsim --msim <ModelSim目录>
python features/color_target/run_color_target_chain.py --sim modelsim --msim <ModelSim目录>
python features/color_target/run_color_target.py --case stray_eof_after_complete_frame --rtl <基线color_target_detect.v> --sim modelsim --msim <ModelSim目录>
python features/color_target/run_color_target_replay.py --mode bypass --out <输出目录> --sim modelsim --msim <ModelSim目录>
```

最后一条无 manifest 时重建确定性合成控制及窄尺寸测试；本次回放命令指定前一阶段
64×48 合成 manifest、`--min-count 4`，只重跑受本轮修改影响的旁路旧 RTL 对照。
素材清单 SHA 和测试参数见 summary；源码与日志 SHA 见 `hashes.json`。
相机素材仍未取得；没有以此调整生产阈值、启用过滤或决定多个同色物体的选择策略。
