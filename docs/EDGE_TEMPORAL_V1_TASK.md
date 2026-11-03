# EDGE_TEMPORAL_V1 开工与边界

角色MAIN / Philid14；授权来源2026-10-18当前用户任务。

- 基线：edge-quality-v1-candidate→b64daf39af09980621adb1138df1674a8501ea09；实际QUALITY构建源码97858d51c7599a504a733b2302db797207c1ac0e。
- 分支codex/main/edge-temporal-v1，从准确QUALITY tag创建，按用户要求覆盖通常origin/main起分支规则；Draft PR将指向codex/main/edge-quality-v1，依赖#6/#4/#3，不合并。
- 本轮最多一个正式候选、合理一次构建修正；不继承PROBE/ROI采样RAM/编码页面。研究依据为58f3a6d提交中的18:42真实数据诊断与旧模型，非算法最优证明。
- 主要变量：有当前梯度支持、最多一采集帧的非递归边缘保持。与三帧投票、仅NMS弱候选保持独立比较后决定。
- 可修改Edge内部及等量Original/config寄存延迟、TD源清单和必要测试；Sensor/ISP参数、按键、Logo/CNT、视频格式、PLL/SDC保持。
- FIFO另作只读事件计数/启动与稳态分桶，验证证据和提交与算法分开；没有实板新计数反馈前，不宣称持续溢出或风险已排除。不修改全局异步约束。
- 共享观察/帧身份接口仍未接入；本算法历史只在DDR前真实采集SOF与完整230400拍帧上更新，与HDMI重复刷新无关。缓存复位/中断/参数变更必须使历史失效。
- 交付：模型证据、独立RTL/旧路径回归、完整TD/最终STA/bitgen、源码commit/归档bit/SHA/BUILD_INFO、Draft PR和最小上板对照。用户上板前保持candidate，不开发下一版本。
