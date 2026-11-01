# 当前审阅入口：简介第三稿与下一轮实测补证

2026-11-01 / TARGET / PR20追加文档。用户要求“把简介再优化一版，注明接着优化需要哪些实验数据与现象，然后进行上传”。沿用原PR，避免新建PR绕过此前审阅请求。目录名submission_intro_v2保留，**当前正文是第三稿**。

1. **[简介第三稿](INTRODUCTION_V3.md)**：名称“色尺—安路FPGA视觉检测系统”15字符、正文469字符；可粘贴正文为WORK_INTRODUCTION.txt。
2. **[下一轮优化所需实验数据与现象](EXPERIMENT_DATA_FOR_NEXT_REVISION.md)**：本次重点，连接输入→现象→指标→可写句及边界。
3. [板测空记录](BOARD_RUN_TEMPLATE.md)、[MAIN审核回复模板](MAIN_REPLY_TEMPLATE.md)：没有代填任何实测结果。
4. [赛题逐项状态](REQUIREMENTS_STATUS.md)、[来源索引](EVIDENCE_INDEX.json)、[往届文字参考/官网限制](REFERENCE_RESEARCH.md)。
5. [第二稿历史](INTRODUCTION_V2.md)、WORK_INTRODUCTION_V2.txt、EVIDENCE_INDEX_V1.json及[用户初版](INITIAL_SUBMISSION.md)保留，不改写历史测试。

## 当前候选与文案的对应

| 项目 | 事实基线 |
|---|---|
| 本文档分支起点 | main c42168e26026425660f2a6f51eec76b04c85eea0；本分支不含候选生产接线 |
| 文档分支 | codex/target/submission-intro-review-v2，PR20→main |
| 颜色/尺寸继承基线 | INSPECTION_USABILITY_V4 / 43ff61b4f1791782e74100c92b9612317e0d2249，PR23 |
| 新增红色标记/分块运动候选 | VISION_TRACK_MOTION_V1 / 123186a9d339990b207b846cb15e6a7e309c22a7，Draft PR24 |
| 真正TD源码 | c3bdf9240647d9f98a2ff68c416693ad1e20f4b9 |
| 归档/tag | be226969254331561de1e6376610cd6bf99af601 / vision-track-motion-v1-candidate |
| 最新候选bit SHA256 | f3dfd9f1ad42bbca95199ac128b9d4808327d4482a1465019ce85a678c0b63a0 |

候选未合入main，Board NOT_RUN。这里的“最新”指已上传的工程候选，实际展示采用哪版须由MAIN明确；旧V4与新候选的记录不能混用。

## 本次改变

- 改正旧稿分别两轴手调标定，突出一键读已知毫米刻线、共用比例、工件旁尺寸线。
- 颜色增加归一化占比、疑似明暗因素及低质量输入提示，保留RGB原值，未宣传消除光照或标准色差。
- 上传前发现PR24已集成新的TRACK/MOTION；正文明确按候选扩展描述，附上专门的待验收项。没有把旧红蓝完整框选/同帧坐标/物体数混进去。
- 实测清单更新为32×32颜色框、768×288区域读尺、共同尺度横竖独立验证、R码/CHR/DV、七模式候选观察；保留颜色/尺寸核心主线。

## 请MAIN在本PR解释

1. 选择实际展示/测试版本，确认第三稿中“候选扩展”是否保留；按最新文档SHA审核，不将旧审阅视作新批准。
2. 对每项说明：实际观察/原始证据→原因和适用范围→能支持或推翻哪句→推荐替换句。未测写未测，不用预期代替现象。
3. 优先确认真实尺子成功率/耗时、W/H误差与重复性、同材互换位置及补光下的RGB/CHR/DV/状态分布、长稳异常/缓存记录；再选择一两项写入500字符，其他留技术报告。
4. 新上传[技术报告说明](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/449f03ec516c8dc7766ae4dc0750190e4613f440/docs/technical_report/README.md)自述基线仍为EDGE_CONTROL_V1，颜色/尺寸和检测舱写作目标方案。应按源码与真实确认核对并统一文档版本，不能把旧报告状态或资源数字套到最新候选，也不能反向补写未测成绩。本PR不修改MAIN技术报告。

实物平台/基础显示是用户此前口头确认；新候选的物理SW映射、读尺成功率、颜色解释、尺寸精度、跟踪/运动现场效果、长稳/FPS/延迟仍无本包实测结果。

本PR只改审阅文档与空模板，无生产RTL/约束/固件变更，没有新增综合、P&R或板测。参考[候选交付报告](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/docs/VISION_TRACK_MOTION_V1_REPORT.md)及[操作步骤](https://github.com/Philid14/anlogic-ph1p35-image-processing/blob/123186a9d339990b207b846cb15e6a7e309c22a7/docs/VISION_TRACK_MOTION_V1_BOARD_TEST.md)；数字仿真通过不能替代实板。
