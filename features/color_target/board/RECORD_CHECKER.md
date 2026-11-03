# 板测记录校验与相机回放入口

这是辅助记录工具，不是自动板测仪器。操作者仍按 MAIN 对应版本的板测指南操作。
目前绑定的已归档候选为 STYLE_V2_TARGET_V1；不把手工录入数据当作仪器采样。

## 生成记录

仓库根目录运行，输出选择尚不存在的文件：

```powershell
python -B features/color_target/tools/check_board_run.py --template board-run.json
```

填写环境、实际下载版本、采样时间和boot_id；每次断电/重新下载另起boot_id。
样例默认值是已归档候选的身份声明，必须核实实际所用版本。所有空值表示未测，不能直接改成0或true。
samples可追加多个样本，t_s是该次启动后的相对秒数，同一个boot内必须递增。
phase为warmup/steady/fault/recovery；标签是操作者声明，工具不据运行秒数猜测相机是否已经经过600帧。

屏幕底部两行可照抄到identity_line/reason_line，保留十六进制及字段顺序。支持metadata离线时的首字符“!”；字符看不清时保留null，不能把字母O猜成数字0。

- 身份行S/F/G/L：session/frame/generation/slot；D/C/Q：dropped/cancelled/metadata fault。
- 原因行D/R/W/I/V/C/S/T/O：duplicate/reorder/wrong session/identity/invalid/guard cancelled/stale/time/timeout。
- 屏幕写满统计B、S分别填 `fifo_startup`、`fifo_steady`，是发生过写满事件的采集帧数，不是像素数量。
- observations：video_live、logo_visible、no_visible_artifacts、annotation_atomic；true仅代表操作者本次观察为满足，null表示未检查。
- evidence：照片/录像路径，建议相对JSON路径；工具验证文件存在并记录SHA256，不分析图片/视频内容。

校验实际下载的归档bit和记录：

```powershell
python -B features/color_target/tools/check_board_run.py board-run.json --bit <实际下载的bit路径> --out board-analysis.json
```

## 结果含义

| 退出码 | assessment | 含义 |
|---:|---|---|
| 0 | NO_OBSERVED_FAILURE | 录入区间中未观察到规则所识别的异常；不代表板测全部通过 |
| 1 | OBSERVED_FAILURE | bit哈希不匹配、观察到画面/Logo/标注异常或稳态写满计数增加 |
| 1 | REVIEW_REQUIRED | 其他诊断计数增长，需要关联故障操作、模式切换和策略判断 |
| 2 | INCOMPLETE | 缺测、无同boot前后样本、证据缺失、计数饱和/下降、metadata离线等 |
| 3 | INVALID_RECORD | 字段、类型、OSD格式或JSON有误 |

所有结果固定 `board_acceptance=NOT_CERTIFIED`。没有同boot前后样本不计算增量；计数下降不擅自按回绕计算；65535保持不变不能证明零事件；到达65535只给出增量下界。
重复显示同帧、跳过若干采集帧的编号本身不报异常。工具不推导精确帧率/延迟、零丢帧或30分钟验收。

## 实拍回放预检

继续复用已有schema1 PPM清单、分组划分、标注和IoU/中心误差/漏检等指标。
给每个clip补充 `pixel_tap: "post_awb_pre_style_rgb888"`，明确它是用于颜色检测的RGB观察点。
HDMI拍屏、带OSD/STYLE的数字图像或原始Bayer不能直接冒充该观察点。
没有对应采样能力时，可继续板上观察；不要伪造post-AWB数字帧来源。

```powershell
python -B features/color_target/tools/prepare_candidate_replay.py --manifest <素材清单> --source <固定MAIN源码快照> --snapshot-manifest <快照哈希清单> --out <新目录>
```

该工具只做来源/输入与候选配置预检，并输出后续已有检测回放的argv，默认support3关闭、MIN_COUNT64。
本轮不改变颜色阈值。1280x720不匹配直接拒绝，不自动缩放图像/标注；未知标注仍是未知。
`profile.json`明确记录 **replay_executed=false、integrated_guard_temporal_replay_verified=false**。
旧回放的track列来自legacy tracker，不能认证当前带时间/身份准入的guard。
后续验证guard还需显式可信的控制、capture_tick、结果到达、取消及显示事件；禁止假定固定帧率补造时间戳。
