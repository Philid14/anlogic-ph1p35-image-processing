# STYLE_V2_TARGET_V1 交付状态

- 日期/角色：2026-10-21 / MAIN。
- Version：STYLE_V2_TARGET_V1，**RESOURCE-BLOCKED WIP，非可上板candidate**。
- Git Branch：`codex/main/style-v2-target-v1`。
- 代码及失败证据提交：`49be137ddb8622ce8888606fe6ce07871be73583`；本页是其后仅文档状态补记。
- 实际RAM版TD综合/布局输入提交：`0342a0bc4a1040f92c1d6a2a118409debb8a3c8d`。
- Git Tag：没有创建 `style-v2-target-v1-candidate`，没有移动任何旧tag。
- Git Status：本任务已提交；用户原有参考工程、PDF、录像和未跟踪进度文档保留，未纳入提交。
- Remote：`origin` = `https://github.com/Philid14/anlogic-ph1p35-image-processing.git`；API确认Private。
- Push Status：上述代码/证据提交已push成功，并由PR API核实；本页随后独立提交推送。
- Draft PR：[PR #14](https://github.com/Philid14/anlogic-ph1p35-image-processing/pull/14)，base=`codex/main/edge-style-fill-v2`，依赖PR #13；未合并。
- Bit Path / SHA256：**未生成**，不能使用TD Runs目录残留bit代替。
- 构建结果：SYN完成；实际布局容量门PHY-9053失败（21825 Slice > 21216，超609）；route/bitgen未执行。
- Setup WNS / Hold WNS：最终路由未测；仅综合估计−1.724ns / +0.114ns，不作路由通过结论。
- Board Test Status：**NOT_RUN**；完整联合回归/五模式回归/故障矩阵/实际CDC尚未完成。
- 回退：`edge-style-fill-v2-candidate`，`artifacts/bitstreams/EDGE_STYLE_FILL_V2/camera_to_dsi_display.bit`。
- 回退bit SHA256：`CFB7435648ED50310F053AFE138702F2094B0061B6A7DD68B3B064B6B3D88F51`，历史归档哈希复核保持。

详细原因、验证范围和后续最小方案：
[资源门失败报告](STYLE_V2_TARGET_V1_RESOURCE_REPORT.md)。
当前停止此结构的candidate收尾，不进行TARGET上板、STYLE V3或LATENCY集成。
