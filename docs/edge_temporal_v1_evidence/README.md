# EDGE_TEMPORAL_V1 证据索引

- model_comparison.json/csv/png：四方法×TH40/60/80，6合成12帧场景及两真实8帧ROI。前两帧在所有方法中统一排除；不是现场画质排名。
- real_184242.npz / real_flat.npz：来自研究PR#9提交58f3a6d中已经完成101页/整批/逐帧pre/post CRC校验的数据，SHA见verification_lineage.json；旧暗部/新手持ROI各自限制保留。
- [legacy_small.log](../../artifacts/bitstreams/EDGE_TEMPORAL_V1/build_evidence/legacy_small.log)：旧QUALITY/NMS及link各尾数/1280地址回归。
- [reliability_osd.log](../../artifacts/bitstreams/EDGE_TEMPORAL_V1/build_evidence/reliability_osd.log)：1280×160多帧Original/Edge与第三行B/S字形、实际打包验证。
- [strict_small.log](../../artifacts/bitstreams/EDGE_TEMPORAL_V1/build_evidence/strict_small.log)：最终严格行尾门禁5481周期单元及小尺寸多帧路径。
- [fixed_full.log](../../artifacts/bitstreams/EDGE_TEMPORAL_V1/build_evidence/fixed_full.log) / final_strict_verification.json：最终严格门禁720p×2帧，460800拍/345600字、含B/S覆盖；测试源SHA匹配最终实际RTL。
- r0_balanced_eol_failure.txt：R0组合重复/缺失行尾定向反例，保留失败；R0不是上板候选。
- [confidence.log](../../artifacts/bitstreams/EDGE_TEMPORAL_V1/build_evidence/confidence.log) / confidence_results.json：支持位中心直接随机位验证，64/68/72/76/1280宽，覆盖尾数、valid停顿、提前/同拍SOF、全1到全0跨帧。
- verification_lineage.json：区分R0核心10帧测试与最终门禁版2帧测试，不互相冒充。

完整TD、原始资源/路由/最终STA/ignored、warning、64输入SHA及旧bit检查位于`artifacts/bitstreams/EDGE_TEMPORAL_V1/build_evidence/`。候选SHA与步骤见同版本BUILD_INFO及docs/EDGE_TEMPORAL_V1_REPORT.md。R0在独立归档和tag保留，历史资料不改。

复现模型：

```powershell
python -X utf8 tests/edge_temporal_model.py --output tmp/temporal_model_replay --real docs/edge_temporal_v1_evidence/real_184242.npz docs/edge_temporal_v1_evidence/real_flat.npz
python -X utf8 tests/run_edge_temporal_v1.py
```

`--full`可复现更长10帧720p测试，但不会把尚未执行的未来运行当成本次证据。构建使用build_edge_temporal_v1.py，归档脚本拒绝以时序失败结果签发candidate；只在干净且全部TD输入已提交后构建，勿覆盖已有归档。
