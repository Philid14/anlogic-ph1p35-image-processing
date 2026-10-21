# A2 / MAIN 第一版实施方案：供确认

当前基线：TARGET `4ec3d35a5cd08cc2d64fe03aa403be16fd696706`；MAIN `c42168e26026425660f2a6f51eec76b04c85eea0`。
用户已同意“审查最新提交、完成现有基线板测、确认接口后集成”的推进路径；本文件将待确认事项收敛到具体行为和文件。
状态：**供确认；没有新增生产RTL或MAIN接线，也不代表PR获得人类批准。**

## 建议的第一版行为

1. 默认严格同帧：显示像素的 `{session_id,frame_id}`、DDR槽代次与标注来源必须匹配。结果缺失/晚到、文字未就绪或来源不匹配时关闭整组TARGET覆盖，视频照常输出。
2. 第一版关闭历史框显示。保留旧TRACK内部HOLD语义用于兼容，但不能把HOLD旧框换成当前帧身份。后续要展示历史框时另确认年龄/样式。
3. 即使同帧重复显示，也不能无限续命。使用可信采集时间与独立前进的时基评价新鲜度；同帧重复扫描/结果重发不刷新年龄。
4. session只由MAIN可信控制事件切换，结果数据包无权切换session；同session的frame_id严格递增，回绕前切session。
5. 保留现有颜色阈值、support3关闭、MAX_JUMP关闭；ACQ/LOST仍按有效独立观测计数，不按显示刷新计数，不将无效帧伪造为无目标。

第1–4项是拟议工程语义，第5项保持既有默认。历史显示最大年龄、可靠观测超时、真实时基与资源仍不能由小整数测试夹具替代。

## 责任与接口

| 提供方/时钟 | 事务或字段 | 使用方及约束 |
|---|---|---|
| MAIN采集适配/观察时钟 | 对齐RGB888/96bit/4PPC、valid、x0/y、有效拍上的SOF/EOL/EOF | TARGET只读消费，无ready、无反压；主线提前user保持原功能，另造规范化sideband |
| MAIN控制/本域落地 | session_start、新session[31:0]、epoch就绪/取消屏障 | TARGET清空确认历史和可见性；不能仅凭某包session不同推断重启 |
| MAIN事务账本/结果时钟 | disposition_strobe、可信key[32+32]、capture_tick[TW-1:0]、完整/无效/取消结局 | 每个key恰好退休一次；无效旧检测器包ID不能单独当账本身份 |
| TARGET检测 | valid/present/class/count/bbox/center | 与可信结局匹配后才准入TRACK；无目标与无效不同 |
| MAIN/LATENCY共同时间方案 | 本域单调now_tick[TW-1:0]及time_valid；来源频率、单位和误差 | TARGET不直接采异步宽计数器；capture_tick整包传输；停止结果输入时now仍前进 |
| TARGET准入包装/结果时钟 | accepted_strobe、拒绝原因、观测key、最近可靠/正观测时间、stale/usable、原TRACK输出 | 重复/乱序/wrong-session不增加确认、丢失计数或刷新年龄；无效key退休但不当无目标 |
| MAIN DDR域 | slot_id、write_generation、frame_key、完整/取消/错误状态、capture_tick | 新代次先退休旧内容；错误回退和覆盖不得只改指针 |
| MAIN显示适配/显示时钟 | 选定slot/generation/key、文字完成身份、scan_start、整组commit | 原子CDC、锁存后随预取到HDMI；扫描期间像素租约与整组字段稳定；实际更新点须由MAIN明确 |

`TW`、slot/generation位宽、诊断计数位宽及CDC容量均为待实现配置；不把当前2bit槽指针冒充永久契约。
不固定“一个邮箱足够”：要用到达/服务/停顿/复位边界证明容量，满时必须明确失效并计数，不能阻塞主视频。

## 可先实现的A2范围

只新增TARGET独立包装器，不改现有track、检测、文字、support3或MAIN：

- `features/color_target/rtl/color_target_track_guard.v`：本域准入、控制session、独立时间年龄、现有track封装、诊断输出。
- `features/color_target/tb/tb_color_target_track_guard.v`：硬期望故障注入；新testbench不从生产实现推导gold。
- `features/color_target/run_track_guard_contract.py`：保留命令、工具/源码身份和原始日志。
- `features/color_target/integration/TRACK_GUARD_INTERFACE.md`：正式候选端口、时序和参数约束。
- 上述范围的独立证据文档；现有入口接入新测试时保留历史行为审计，不以新guard通过删除旧TRACK六个OPEN。

输入事件优先级：reset/epoch屏障优先于数据；session_start同拍的数据不准入，生产者须在屏障完成后开始交付新epoch结果。
年龄过期清除确认历史及显示可用性，保留本session高水位，避免旧包重新被当新观测。
新鲜的可靠观测可重新ACQ，不能由迟到旧包直接恢复过期TRACK。
时间不可信/倒退/回绕及来源未知须使标注不可用，并报诊断；不拿错误时间计算负年龄。
实际硬件不保存无限session集合；使用当前epoch和经证明的排空/取消屏障。

年龄参数必须显式指定并校验正值，不附会生产默认。独立验证可用明确标注的age=5、ACQ=2、LOST=2等反例夹具。
它们不授权把数值写入整机配置；接入前仍需用真实时钟、帧间隔和显示延迟确认阈值。

## 硬预期与验收

| 注入 | 必须出现的行为 | 失败条件 |
|---|---|---|
| 同key连续三次 | 仅第一次是独立观测 | ACQ/age被重复刷新 |
| 3→2→1及0xffffffff→0同session | 拒绝更小/回绕帧号 | 旧包移动框或回到TRACK |
| invalid/cancelled后同key有效重发 | 该key已退休；不得补写 | 重复观测进入TRACK |
| 显式新session且首包无效/无包 | 立即隐藏旧框并清确认；旧session包不能切回 | 等有效结果才换session或复活旧状态 |
| 可靠无目标与invalid分别注入 | 前者按LOST推进，后者不伪造miss；两者均不刷新旧目标时间 | 二者混同或延长旧目标年龄 |
| 停输入/迟到包 | 独立now触发stale；迟到不变新 | 需要新strobe才过期、到达时间续命 |
| 过期边界与重新出现 | 明确采用elapsed<=limit有效、>limit过期；过期后重新ACQ | 越界仍可用或旧确认历史越过过期点 |
| 所有故障连续叠加 | 主视频拍数与节奏不变；只影响观察/标注 | 反压、阻塞或清复位主视频 |

上述guard通过只关闭其独立实现项。真实SOF/EOF、账本、DDR租约、CDC、图文commit和物理时序必须在MAIN另行验证。
严格年龄上界还需显示SOF检查 `display_start + max_scan_duration - capture_time <= max_age`；没有实测/证明的扫描上界时不能宣称整帧年龄有界。

## MAIN后续分阶段接入

1. 板测收口EDGE_CONTROL_V1新增控制/OSD功能及长稳；沿用已有BLC/AWB/增益/EDGE反馈，不重开画质调参。
2. MAIN确认本表端口/时钟/错误来源、时间与超时、DDR完成与取消事件、扫描租约、CDC服务边界和OSD区域。
3. 形成逐文件接线变更清单后，再取得MAIN具体文件修改授权；预计涉及ISP输出适配、top、video_in/out元数据、HDMI提交和TD入口，但本文件**不授权**修改这些文件。
4. 先独立guard RTL，再真实多时钟顶层与CDC/DDR故障，再整机P&R与bit归档，最后目标框板测。
5. 未完成的层次分别记OPEN/NOT_RUN；不能把36条模型轨迹、独立gate资源或旧bit板测替代后续层次。

## 本次需要确认

建议确认：**严格同帧、第一版不显示历史框；MAIN发行可信身份/时间/缓存事务，TARGET新增上述独立guard作防御准入与年龄输出，MAIN负责最终显示与CDC；先做TARGET独立实现，不修改MAIN。**

如果选择允许历史框显示，需要另给最大年龄及标注语义；如果选择把所有准入/年龄放MAIN，本guard范围应撤回重划。
数值阈值和MAIN具体接线授权暂不假定已给出。
确认要求来源于用户此前“A2先审查并提出方案，不立即修改生产RTL”和“其他生产RTL变更需先提交方案等待批准”。这次提供的是具体可审阅范围，而非请求重复批准整体推进路径。
