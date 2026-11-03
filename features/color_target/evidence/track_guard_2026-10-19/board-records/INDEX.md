# 仓库上板记录索引（2026-10-19）

**有历史上板记录：11个归档版本中，9个有用户实测反馈。** GAIN_TEST_D、EDGE_CONTROL_V1未找到完成反馈。
当前HEAD与现有tag一起检查；“已反馈”不等于全部验收通过，更不是本轮新上板。

| 版本 | 反馈日期/状态 | 已有结论 | 来源 |
|---|---|---|---|
| BASELINE_V0 | 2026-10-05 | 白偏青蓝/青绿、蓝绿难分、红不足；基础颜色测试不通过。 | [记录](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/4ec3d35a5cd08cc2d64fe03aa403be16fd696706/artifacts/bitstreams/BASELINE_V0/BUILD_INFO.md#L56) |
| AWB_V1 | 2026-10-08 | 色彩仅轻微改善，仍发灰、黑位高、对比度低。 | [记录](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/4ec3d35a5cd08cc2d64fe03aa403be16fd696706/artifacts/bitstreams/AWB_V1/BUILD_INFO.md#L66) |
| BLC_V1 | 2026-10-08 | 遮光黑位较好、白绿改善，白仍青绿、红蓝偏暗；保留BLC=15。 | [记录](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/4ec3d35a5cd08cc2d64fe03aa403be16fd696706/docs/IMAGE_TUNING_LOG.md#L80) |
| AWB_V2 | 2026-10-09 | 白绿及红蓝改善、中性灰基本灰；室内及暗场偏暗。 | [记录](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/4ec3d35a5cd08cc2d64fe03aa403be16fd696706/docs/IMAGE_TUNING_LOG.md#L97) |
| GAIN_TEST_A | 2026-10-10 | A→B→C在同场景稳定、明显、单调增亮；A为最低增益对照。 | [记录](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/4ec3d35a5cd08cc2d64fe03aa403be16fd696706/docs/IMAGE_TUNING_LOG.md#L117) |
| GAIN_TEST_B | 2026-10-10 | 同场景A→B→C单调增亮；B为中间对照。 | [记录](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/4ec3d35a5cd08cc2d64fe03aa403be16fd696706/docs/IMAGE_TUNING_LOG.md#L117) |
| GAIN_TEST_C | 2026-10-10 | 8×比此前改善，室内仍略暗；为扩展增益的起点。 | [记录](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/4ec3d35a5cd08cc2d64fe03aa403be16fd696706/docs/IMAGE_TUNING_LOG.md#L117) |
| GAIN_TEST_D | 未找到完成记录 | 12×候选；未找到本版补报实测。 | [记录](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/4ec3d35a5cd08cc2d64fe03aa403be16fd696706/docs/IMAGE_TUNING_LOG.md#L130) |
| GAIN_TEST_E | 2026-10-10 | 15.75×亮度基本满意，暂选算法集成固定基线。 | [记录](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/4ec3d35a5cd08cc2d64fe03aa403be16fd696706/docs/IMAGE_TUNING_LOG.md#L135) |
| EDGE_V1 | 2026-10-10 | 能够输出边缘图像，弱光弱边缘不足；30分钟稳定性未报。 | [记录](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/4ec3d35a5cd08cc2d64fe03aa403be16fd696706/docs/IMAGE_TUNING_LOG.md#L154) |
| EDGE_CONTROL_V1 | 未找到完成记录 | 本版仍待用户上板；按键/切换/文字同步和30分钟未有结果。 | [记录](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/4ec3d35a5cd08cc2d64fe03aa403be16fd696706/docs/IMAGE_TUNING_LOG.md#L162) |

## 记录中需要区分的状态

- IMAGE_TUNING_LOG 按时间追加：较早候选段写“待上板”，后面的反馈段更新了结论，不能只取第一处关键词。
- AWB_V2 BUILD_INFO 开头仍有“尚未上板”，但第58行已记录2026-10-09反馈；以明确日期的后续反馈表达最新实测状态。
- 当前HEAD中 GAIN_TEST_A/B BUILD_INFO 第15行仍是“待上板”，但 IMAGE_TUNING_LOG:117–122已记A/B/C测试。
- A/B各自正式tag的结果提交7665bb1/3551f85还更新了对应BUILD_INFO为已上板；两个提交不是当前HEAD的祖先。记录存在于tag历史，没有丢失；本轮不合并或cherry-pick。
- 11个归档bit的实际SHA均在各自BUILD_INFO中找到一致值。身份核对不证明下载了哪个文件或测试效果。
- 当前docs/bit归档中的媒体仅见status_layout.png，文档说明为模型预览；V0实拍引用了仓库外旧电脑路径。未把模拟图当实拍。

## 应缩小到哪些补测

沿用BLC/AWB和增益已有反馈，不要求重做整套历史画质实验。GAIN_TEST_E的15.75×与EDGE_V1边缘输出已有用户报告。
本阶段优先补EDGE_CONTROL_V1新增功能：K3单次切换（至少20次）、K4短/长按及边界、文字与画面整帧对应；启动/真实移动/明暗恢复作为本版回归，再做至少30分钟长测。
如果本版已有尚未归档的测试，只补录版本、现象和证据即可，不应假定用户没有做过。
现有记录未关闭DDR长期撕裂/溢出、精确帧率/延迟、TARGET帧匹配、I2C读回和颜色像素定量要求；后者不应在无仪器/原始帧时伪造通过。

本轮只新增仓库外索引与证据，没有修改MAIN全局日志、BUILD_INFO、tag或Git历史。原始命令与哈希见index.json及git-history.log。
