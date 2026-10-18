# 新真实采样 6A23858A

来源video_20261018_184242.mp4，完整101页/8帧CRC通过；原录像SHA、实际bit及现场说明见provenance.json。原录像不入库。

- decode_audit.json / frame_ledger.csv：全片3332帧扫描和页面覆盖；46帧无合格包，不能简单当作46次CRC错误。
- valid_pages.zip / pages_manifest.json：原始合格页面及SHA；独立重组和NPZ全数组核对已通过。
- capture.npz：pre/post/meta/global_header；post按实际AWB gain重建并匹配实板直接计算的CRC。
- evaluation.json / frame_metadata.csv：RGB、AWB、视频数量、各历史模型及门限统计。
- analysis_th40/60/80.json：既有模型与既有离线时间proposal。无真值及运动测试，不用于宣布排名。
- stage_diagnosis.json：中心对齐、强边缘判决布尔变化分解、有限依赖、局部连通分量及距离分箱；不是物理原因贡献百分比。
- real_roi_contact.png / stage_contact.png / input_awb_gradient.png / flicker_maps.png：真实RGB与旧算法模型重放，未以手机亮度作为RGB。
- awb_counterfactual.json：首帧gain反事实，不是硬件冻结或已收敛基准。
- previous_capture_comparison.json：本批pre/post与旧批完全不同，确认取得新数据。
- pc_sources.zip / source_hashes.json / pc_validation.txt / verification.json：实际PC工具快照、哈希与验证；不含新RTL或bit。
- pr_snapshot.json：开工时未合并依赖快照，不冒充提交后的最新PR head。

**限制：** 目标手持，未见预热绿框；ROI未辨认出清晰黑白边界。写侧FIFO历史溢出sticky全为1，发生时刻和重复事件未知。不能把这批数据当纯噪声、真实纸边追踪或FIFO完全正常的证明。详细判断及下一步见../../EDGE_TEMPORAL_RESEARCH_V1_RECORDING_184242.md。
