# TARGET 上传整合验证：2026-10-20

用户授权整合后上传，随后明确选择“先上传TARGET，由MAIN队友接入”。
本次沿原 `codex/target/color-target-detect-v1` / PR #2 更新；不改MAIN/LATENCY、不合并main。
**交付状态：独立模块与验证完成，供MAIN接入；没有新整机P&R、bit或真实TARGET板测。**

## 1. 源码与改动

- 原远端/PR2：`4ec3d35a5cd08cc2d64fe03aa403be16fd696706`。
- 原已完成本地工作：`8f49444`新增独立guard；`e995866`新增帧事务联合模型/显示联动验证；本轮一并上传，保留原提交与证据。
- 本次受测源码：`e71b0696a09bfe3a57b0ccccc0d429aaf793cca4`，运行开始工作区干净；运行期间全部受测源及Git状态稳定。
- 本轮修复公共仿真工具退出码传播，新增显式handoff档位与失败注入测试，整理MAIN交接/板测方法。
- 受测提交之后只补充STYLE V2版本审查与本证据；受测代码LF哈希再次逐项核验相同。
- 9个生产RTL与e995866一致，本轮未继续更改生产RTL/颜色门限/support3；相对原PR2唯一新增生产RTL是此前已批准的guard。
- 全部上传改动限制在 `features/color_target/`，不导入队友的主工程、参考资料或自动生成库。

## 2. 实际命令与结果

Python3.12.14，ModelSim ASE10.3c。实际ModelSim路径由本机显式传入。
从仓库根目录运行；以下参数中的路径由本机填写，原始绝对argv在summary及日志中保留。

```powershell
python -B -X utf8 features/color_target/tb/test_simlib_failures.py
python -B -X utf8 features/color_target/tb/test_verification_runner.py
python -B -X utf8 -u features/color_target/run_verification.py --profile handoff --sim modelsim --msim <win32aloem目录> --out <新的handoff目录>
```

完整handoff约327.469秒（子任务耗时之和），16任务达到各自预期：15 CHECK PASS，
1旧TRACK特征测试 MATCHED / OPEN。总进程退出0，`integration_ready=false`。

| 验证 | 实际结果 | 口径 |
|---|---|---|
| A1两模型/RTL | 各12/12配置 | 原非法类别硬期望回归 |
| 原系统契约 | 36/36、10类故障 | 提案模型，不证明实际CDC/DDR |
| 数据契约 | 17检查通过 | 合成素材契约 |
| 旧TRACK缺口 | 9采样吻合、6 OPEN仍保留 | 未包装路径，不是guard失败，也不是缺口已关闭 |
| 动态文字/原链 | 7962拍/396拍通过 | 文字自身原子快照不等于实际显示整帧commit |
| 分类/检测 | 40/40配置、39079像素；25/25含720p | 独立RTL |
| 几何/原TRACK/真实字库 | 10/10+5/5；21/21；28/28、307078像素 | 独立RTL、只读使用原字体 |
| RGB回放 | 12轮、7760408像素、179结果/178跟踪、39928显示查询、87旧RTL对照、5取消 | 合成场景，无相机颜色准确率结论；发布/消费间reset解释179/178差异 |
| 新帧事务模型 | 33/33 | 区分预取与实际首像素，含租约、取消、年龄和排空屏障 |
| 新guard | 9配置、818硬检查通过 | 真实生产guard，可信身份/时基由夹具提供 |
| 显示联动 | 14场景、187硬检查通过 | 真实TARGET模块，传输/显示调度是测试夹具 |
| 五负对照 | 依次触发2/3/2/2/1失败，全部识别 | 忽略代次/实时新框/忽略frame/不等文字/停钟冻结年龄；不是坏策略通过 |

486个公共simlib阶段、27个guard阶段、18个显示阶段共531个真实工具阶段均exit0。
显示负对照的功能FAIL明确保留；不能把编译/启动失败当作成功检出。
阶段原始字节、命令与退出码均归档；[公共工具阶段索引](tool-stage-index.json)、
[guard原报告](guard-summary.json)、[显示原报告](display-summary.json)。

工具边界测试4个方法内13个探针：两后端正常、各编译/运行阶段exit7即使有完成文本、exit0但Error、启动异常，
均符合硬期望并保留原始CRLF日志。入口8项失败注入/报告检查通过，包含不完整模型报告与负对照工具失败的拒绝。
这是模拟的Icarus子进程边界，不是实际Icarus RTL执行；本轮实际RTL只使用ModelSim。

开始时沙箱内Python创建的临时目录出现WinError5，改用工作区临时目录仍失败；
正常本机权限下同一工具测试成功。失败日志保留在归档的 `simlib-selftest-01.log` / `launcher-selftest-01.log`，
不当作RTL功能失败，也没有把失败尝试改写为PASS。详见 [工具测试记录](tool-selftests.json)。

## 3. 原始证据如何读取

[summary.json](summary.json) 与 [REPORT.md](REPORT.md) 是受测e71b069的原始总报告，
16个直接子任务日志与报告并列，便于点开。报告中的本机路径保留其原始含义，不重写成新路径。

[RAW_LOGS.zip](RAW_LOGS.zip) 包含1078个原始输出/日志/JSON/报告成员，
原始1384271字节压缩为524857字节；没有编译库、RGB输入向量、bit或用户照片。
[LOG_ARCHIVE_INDEX.json](LOG_ARCHIVE_INDEX.json) 为每个成员记录原始长度与SHA256。
解压到新目录后，从 `handoff-01/REPORT.md` 读取完整嵌套报告与工具日志。
打包后逐成员解压核对原始SHA通过。当前证据文件的精确SHA另见SHA256.json，旧证据不覆盖。

## 4. 队友最新版本与接入影响

中断前快照为STYLE V1；续跑后远端新增STYLE V2 PR13。
已核对head `89093f428878b918036c8a30a0d1afe7764946b8`，实际构建源
`694559fd76676093e134229d435161ecb44ab00c`，主工程相对V1构建源042345仅改style_fill_96.v。
其余观察/ISP/DDR/HDMI/TD/SDC不变；不能把STYLE渲染后的色块作为TARGET颜色输入。
V2 bit实际SHA为`CFB7435648ED50310F053AFE138702F2094B0061B6A7DD68B3B064B6B3D88F51`，1789539字节，与BUILD_INFO一致。
新V2 TD仍不含TARGET/LATENCY。详见 [V2只读审查](style-v2-review.json)。

V2现有路由报告为17170 LUT6/16814 FF/18140 Slice/85 ERAM/21 DSP，WNS +0.100/+0.020ns，STA96.14%。
这些是MAIN历史构建数字；未计入本交付TARGET/guard/新适配器。
旧FIFO/Gray风险、I²C时钟缓存跨区warning及V2冷启动/真实画质/长稳仍待MAIN板测。
V1与四模式原快照与bit核验保留在 [remote-baseline-01](remote-baseline-01.json)，不覆盖为V2。
之前66/66来源闭合证据只属于V1实际构建源042345，不能直接称作V2完整来源复核。

## 5. 上板前仍缺什么

MAIN真实规范化观察流、可信身份/完成取消/缓存代次/读租约/排空、物理CDC与独立显示年龄、
整组图文commit及实际HDMI首像素关联尚未实现。LATENCY容量/事件口径问题未在本包修改。
生产年龄/时基、显示区域、最小目标和同色干扰策略尚待MAIN/实拍确认，不能照搬测试夹具阈值。

先由MAIN审阅 [交接包](../../board/MAIN_HANDOFF.md) 并接入，
完成实际适配器/多时钟顶层验证、完整P&R、输入/bit归档与新candidate，再用
[TARGET上板方法](../../board/TARGET_ACCEPTANCE.md) 和 [回报模板](../../board/TARGET_REPORT_TEMPLATE.md)。
本次不生成整机tag、不下载板卡、不声称精确同帧或真实摄像头检测已通过。
