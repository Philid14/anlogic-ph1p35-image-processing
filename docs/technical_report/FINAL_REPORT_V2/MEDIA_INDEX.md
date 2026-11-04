# 图组与媒体索引

所有原始图片及其文件SHA继承[前稿选图记录](../FINAL_REPORT_V1/SELECTED_MEDIA.json)，最终展示视频仍为F01，SHA及抽帧方法见[媒体身份](MEDIA_INVENTORY.json)。本轮未处理或替换原视频。

| 本稿图组 | 来源及内容 | 重排方式 |
|---|---|---|
| 图1—3 | V1图1—3 | 结构、公共流水、比例与背景流程保持 |
| 图4 | 最终observer、LAST及内部计时接口 | 原生Word关系表替换历史结构图；无新增实测 |
| 图5—7 | V1图5—7 | 正视/斜视、相机/灯具及板卡；板卡图缩小并与内部安装同页 |
| 图8 | V1图8、9 | 原图、灰度、二值、STYLE合成2×2图组 |
| 图9 | V1图10 | EDGE及阈值 |
| 图10 | V1图11成功帧cal_ok | 完整帧及状态表；失败帧留在历史索引 |
| 图11 | V1图12 | 两个完整帧及同图尺寸局部；W/H98.3/98.3，D/R60.1/30.1MM |
| 图12 | V1图13 | 两个完整帧及原面板局部；CHECK/LIGHT转录表 |
| 图13 | V1图14 | 红目标TRACK与移出SEARCH |
| 图14 | V1图17 | 最终橙红密集运动提示与STILL回落，DEMO标记保留 |
| 图15 | V1图19 | F01约152、155秒的完整变光画面 |

四处局部采用Word `a:srcRect` 原生裁剪，同一媒体部件用于全帧和局部；没有新建裁剪JPEG、调色、锐化、重绘或改数字。源像素坐标和SHA见[FIGURE_LAYOUT.json](FIGURE_LAYOUT.json)。在线Markdown链接到完整原图，局部布局以Word为准。

历史材料仍可追溯：[旧标定失败](figures/cal_fail.jpg)、[旧运动提示](figures/motion_on.jpg)、[旧静止](figures/motion_off.jpg)、[外部巡览](figures/new_exterior.jpg)、[内腔巡览](figures/new_interior.jpg)、[DEMO全帧](figures/new_demo.jpg)、[原DEMO局部](figures/new_demo_detail.jpg)、[原历史结构图](figures/observer_flow.png)。这些材料未删去或改标为当前bit验收。

DEMO模拟值不作真实延迟；视频剪辑长度不作连续运行时长；尺寸小数位不作独立精度；BG:NEED/CUT示例不作AUTO12实物改善对照。正式稿3.3.4统一列明这些状态，原[十主题时间索引](../FINAL_REPORT_V1/MEDIA_INDEX.md)保持可查。
