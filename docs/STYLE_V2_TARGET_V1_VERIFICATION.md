# STYLE_V2_TARGET_V1 验证范围与证据映射

2026-10-22，MAIN。生产 TARGET 固定来源 `49641eef`，不改队友 RTL。
独立交付工具的 `integration_ready:false` 原样保留；下面是 MAIN 新建的接入证据，不改写历史交付结论。

| 检查 | 实际证据 | 结论及范围 |
|---|---|---|
| TARGET 独立来源/功能 | `target_handoff_20261022.json` 和同名证据 zip | 固定 checkout，16 项独立任务完成；不等于真实相机整机通过 |
| 台账/完整写/取消/晚结果/重复乱序/槽代次/租约 | 生产172800字/152位台账测试；`ledger_latest_eq_08` | 41个接口检查及691242周期全部公开输出与旧版相同；控制器实际接受另见联合测试 |
| 33项事务模型 | 独立 TARGET handoff 中 `run_frame_transactions.py` | 政策模型，不冒充物理DDR或全部MAIN故障输入穷举 |
| 邮箱原子性/两侧复位/停钟 | `cdc_pulse_11`、`cdc_registered_11`，快源慢目的与提前ACK负对照 | 506位整包、内容/顺序、ACK晚于消费；负对照确实检出错误；物理延迟另审 |
| 原生像素/命令FIFO/MC接受/240字突发 | `final_system_09`、`fault_system_13` | 实际可仿真原生模块，独立issued/accepted核算；不是DDR PHY仿真 |
| 完整720p/图文同帧/共享字库/Logo/CNT/诊断 | `final_system_09` | 210ms、52405117检查、1382400接受写、1859040读、8次完整提交；最终HDMI逐像素独立期望 |
| 真实首输出沿/年龄/全扫描保持 | `display_pipeline_09`、`display_legacy_09`、`final_system_09` | 生产请求流水2475309检查；旧14场景2380564检查；首输出年龄相等允许，随后过期隐藏；不是预取时刻计时 |
| 正目标出现/移动/消失/无输入过期 | `final_system_09` | 6次正目标扫描、1次无目标隐藏、3次过期隐藏；CSI停钟35ms时公共显示时基继续 |
| 坏帧与epoch物理排空恢复 | `fault_system_13` | 90ms、29904827检查，MC暂停300us造成一次启动期FIFO满帧；packet error及校准失效；2取消、1epoch恢复、3后续完整提交，结束写排空 |
| 五模式/按键/OSD/打包 | `five_modes_alignment_10` | 当前完整ISP、独立STYLE模型：720p五帧1152000有效拍/864000打包字，另测小光栅、K3/K4与配置CDC |
| 无复位payload存储的启动/中途复位/参数 | `alignment_eq_11`、`alignment_full_line_eq_11`、`alignment_short_eq_12` | 全算法6158/35975周期、短配置2280周期逐拍一致；无warm屏蔽负对照确实失败 |
| TARGET关闭的旧显示行为 | `logo_rom_02`、TARGET_ENABLE=0实际接线及旧五模式参考 | 32768地址、1237512完整光栅周期mixer逐拍相同；只在TARGET开启时增加读控制对齐和最终图文流水 |
| 全局复位实际接线 | 当前 `design_top_wrapper.v` | 台账/MC FIFO/DDR同属PLL lock复位；没有单独清台账却保留MC队列的侧复位接线。任意硬件故障仍不由数字仿真证明 |
| 最终资源/时序/CDC | 同源SYN10/place10、待完成route10及独立Routed CDC审查 | **未完成最终路由门，尚无candidate/bit** |

上表证据均位于 `docs/evidence/STYLE_V2_TARGET_V1/`。SOURCE_MANIFEST/COMMIT_BINDING 记录实际仿真文件；
混合换行的少数旧vendor文件保留准确字节zip。原有功能计算源码与新SYN的83项实际输入逐项检查，60项旧输入完全冻结。

## 不能声称已经证明的内容

- 真实 Sensor/MIPI 电气、DDR PHY、板卡复位瞬态、显示器和长时间硬件稳定性。
- 任意未知 FIFO 服务停顿都不丢帧：这里只保证有界正常服务及明确故障下坏帧不提交、排空后恢复。
- 使用一组联合测试穷举全部协议政策。身份重放/乱序等由实际台账、guard和显示适配单元覆盖，联合测试覆盖真实连接和关键服务故障。
- 把旧FIFO Gray约束被async屏蔽当作安全；独立物理审查须给出本次实际数据，正式覆盖缺口仍需记录。
- 采集至显示的实测延迟或新相机帧率；本轮未接入 LATENCY，不以显示重复次数代替采集帧率。

若最终资源或时序失败，以上功能通过仍可保留，但不能据此签发可烧录candidate。
