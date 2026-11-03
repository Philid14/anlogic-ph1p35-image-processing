# 对第六稿技术文档的版本更新说明

已合并docs/technical_report/REAL_MEDIA_REVIEW_V6及其现场材料、原稿和机械概念资料，保留其原始时间点与记录，不覆盖已有Word/PDF。第六稿所称“parts/motion仍在研”和“最新为LATENCY_PERFORMANCE”是写作当时状态，当前以submission/MANIFEST.json为准。

当前整合包含密集橙红运动点阵、T/L七项同步尺寸标注、精确等价AWB帧级除法资源优化，以及LATENCY_FRAME_FIX_V1真实测量修复。后者最终Slice19177/21216、ERAM105/108、DSP25/40，Setup+0.137ns、Hold+0.020ns。

本次没有把旧实拍重新标成当前bit，也没有补写未测的尺寸误差、真实延迟或长稳指标。前一随机延迟显示仅为临时模拟演示，已从当前代码/提交包撤下，不作为赛题进阶三完成证据。真实延迟问题的最终实板结论尚缺。

机械frame_concept为设计参考，不等于现已制造结构或尺寸真值。用户的最终需求以最终作品实现/关于最终作品实现.txt为依据。比赛提交时应把本更新说明、当前BUILD_INFO、最新实板记录与第六稿配套，不直接宣称旧Word内版本状态已经自动更新。
