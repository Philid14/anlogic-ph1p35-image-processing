# 最终代码整合记录 / MAIN

授权依据：用户本轮要求“回退随机数之前版本、删除随机数相关内容、整体合并、整理本地和GitHub、输出最终全部代码RAR200MB以内”。这是本次合并/清理的具体授权，不伪造GitHub APPROVED审查，不视作对未来合并的授权。

## 选定版本

以 `latency-frame-fix-v1-candidate` / `ad7bc680601d29ac9097803608e0b648068a8a8d` 为基线，移出临时随机延迟分支，不将其提交合入main。真实测量失败判据保持；原bit和所有非随机历史tag保留，不移动tag、不force-push、不改可见性。95项正式输入/.al/当前bit哈希见MANIFEST及验证工具。

主线现有算法/颜色/标尺/尺寸/红跟踪/运动/真实延迟的祖先PR链统一由此次集成PR纳入main，不逐项重放旧RTL。旧黑屏TARGET整机分支和固定RGB诊断分支不替换当前formal源，实验历史仍可恢复。

## 独立交付与资料

| PR | 整合内容 | 正式TD状态 |
|---|---|---|
| #2 | TARGET原始模块、接口和证据 | 主线已有的9个核心RTL与原交付逐字相同；主线使用的具体条目以.al为准，不新增接线 |
| #5 | LATENCY独立模块与接口/测试 | 入库参考；当前实际同帧计量仍为MAIN的latency_capture_tag/slot_journal/display_meter，不把独立库误报为另一次实板集成 |
| #15 | mechanical/frame_concept | 机械设计参考，不是实物已制造证明 |
| #19 | 技术初稿/模块注意事项 | 历史资料，当前入口以submission为准 |
| #20 | 提交简介及测量计划 | 文档资料，未将计划表改成已测结果 |
| #25 | 最终应用技术文档归档 | 保留原始文档 |
| #26 | 技术第六稿、实拍素材与待补清单 | 配合TECHNICAL_REPORT_ADDENDUM说明最新版本边界 |

所有来源SHA固定在INTEGRATION_INPUTS.json；操作前PR快照见PR_INVENTORY_BEFORE.json。没有修改队友独立RTL；所有local merge后95项实际构建输入均相同。合并采用merge commit保留实验源码SHA，不使用squash/rebase。

## 本地清理与保留

用户原有38行研究笔记已双重保留：Git stash“preserve user research notes before final submission integration”和 `D:/anlogic_project_backups/final_prep_20261103/USER_GITHUB_REFERENCE_RESEARCH.md`。没有将这些历史草稿混入最终结论。历史Git非随机refs先创建本地安全bundle；活动队友worktree不删除。

可重建TD *_Runs、临时随机延迟构建、根TD运行日志删除；其余tmp诊断/解码研究资料迁移到工作区外备份，原始录像移至local_assets/recordings。用户厂家参考2026-10-05和Sensor文档保留本地，不入提交包。已归档非随机bits与证据不修改。

## 当前不可宣称完成的内容

真实延迟修复尚无本版实板反馈；既有稳态FIFO溢出是否复发、Gray约束覆盖、长期/PVT稳定与独立计量精度仍需验收。源清单一致、仿真和TD通过不替代真实摄像头/DDR/显示器长期测试。RAR和仓库整合是代码交付，不伪造上述结果。
