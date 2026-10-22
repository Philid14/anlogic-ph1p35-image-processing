# STYLE_V2_TARGET_V1 架构优化记录

角色 MAIN；2026-10-21。续接 `d0342f0` 和 Draft PR #14，基线与独立 TARGET 来源不变。
目标为资源、时序和真实适配器联合验收；此文档中的计划不表示 candidate 已完成。

## 1. 原始资源归因

SYN03 源 `0342a0b`。下表为原生层级 logic/ripple/seq/ERAM，**不是物理 Slice**。
父模块含子模块，不能将父子相加；最终容量仍以 place/route 为准。

| 范围 | logic LUT | ripple | seq | ERAM |
|---|---:|---:|---:|---:|
| STYLE V2 原完整基线 gate | 11957 | 3940 | 17079 | 85 |
| SYN03 完整集成 gate | 14617 | 4994 | 22885 | 89 |
| MAIN target_frame_system，包含以下子项及原像素FIFO | 2255 | 1045 | 5345 | 12 |
| TARGET detector（含分类/统计） | 528 | 135 | 391 | 0 |
| TARGET guard（含原track） | 212 | 258 | 557 | 0 |
| MAIN ledger | 703 | 82 | 590 | 4 |
| MAIN display CDC | 81 | 0 | 997 | 0 |
| MAIN begin/control/grant/terminal CDC 合计 | 61 | 0 | 963 | 0 |
| MAIN 公共时基，含两个时间邮箱 | 35 | 64 | 394 | 0 |
| MAIN observer | 134 | 86 | 260 | 0 |
| MAIN 显示提交，含原TARGET文字 | 481 | 129 | 841 | 0 |
| 其中 TARGET text | 122 | 0 | 194 | 0 |
| HDMI mixer/共享Logo/字体（基线已有2557 logic） | 2578 | 85 | 174 | 0 |
| 原生 writer/reader（含两只4 ERAM像素FIFO） | 311 | 186 | 417 | 8 |

实际原始 place 打包 21825/21216，超609；gate估算22754不是这个数。
共享显示邮箱存在源/目的各约506位以及显示prepare 506位的副本；其原子性不能通过直接删保持寄存器破坏。
ledger的4组frame/generation选择比较、64位时间比较及扫描快照也有成本。
另一方面，mixer虽主要是基线成本，却是MAIN拥有、允许等价重构且占比较大的组合网络。

## 2. 第一项：Logo无损字典ROM

原Logo为6387项稀疏组合case，579种非透明25bit值，所有非透明地址位于5494..20426。
采用 `[address-5440]` 的16384×10索引ROM和1024×25调色板ROM。
字典含透明0，共580项；其余地址和字典项均明确初始化为0。
不改图像、不改透明度、不重采样；原文件保留作逐地址独立参考。

两次同步读取利用已有 `S_x/S_y → S_x_2d/S_y_2d` 提前请求，保持最终RGB/DE/HS/VS原周期。
生成器穷举32768地址内容一致；独立RTL还必须验证32768地址及完整1650×750扫描与旧mixer逐拍相同。
这项实验先不动共享字体仲裁、元数据CDC、TARGET算法或任何模式算法。
估计会消耗若干ERAM，具体数量与Slice收益等待TD实际测量，不能用理论bit数替代。

## 3. 迭代状态

| 实验 | 功能验证 | gate/实际place | 决策 |
|---|---|---|---|
| SYN03历史 | 独立适配器通过，整机未完成 | 22754 / 21825，失败 | 保留原证据 |
| Logo ROM 01 | 首次ROM夹具未触发原case初始事件，失败；修正初始地址后，32768 ROM地址和1237512 mixer周期逐拍RGB/DE/HS/VS全等通过 | 待测 | 未认定面积收益 |

Logo ROM 01 实际SYN源 `176923e`：gate Slice21892（少862），ERAM91（多2），实际place21279（少546），仍超63。
属性 `bram_fast` 被TD警告并回退AUTO，索引大部分仍为组合逻辑；不把理论容量当作实际推断。
本机官方TD V6.2手册PDF第125–126页明确有效指令 `// synthesis ram_style=bram`。
Logo ROM 02 使用这一有效指令，初始化常量用分段packed常量和循环表达，避免Starter按近2万初始化语句限速；
内容、周期不变。ModelSim实际32768地址和1237512周期全等通过，原Icarus慢尝试中止不计通过。
生产规模台账172800接受字/152位标注41检查、506bit CDC93检查通过，仍非整机替身。

实际FIFO/DDR联合回归已运行到36.522ms：至少两帧真实完整提交，随后HDMI逐像素断言失败。
该失败保存在 `system_failure_04`，须定位坐标和读延迟；不把已有独立mixer等价当作整条链路对齐。

最终联合回归、共享字体时序、CDC物理覆盖和完整P&R仍为候选的前置门。

## 4. 已定位的读出对齐问题（与面积优化分开）

第二次完整链路复现同一失败：x=0,y=160，所选source3应为303030，HDMI为000000，读出RGB已为303030。
独立使用原安路128bit FIFO和生产video_out的1280像素行做判别实验：
旧控制直接进mixer，在x160输出9e1308（像素158），应为a01436（像素160）；
控制五信号同步增加两拍后，1280个DE完整、非Logo区域1120个独立像素全部准确。
负对照只取消对齐，保持同样数据与期望，确实触发像素断言；未放宽期望或忽略首尾像素。
首个夹具尝试未显式执行事务FIFO初始化屏障，失败并保留；正式夹具先执行生产接口flush。

最小修复 `video_read_controls`：原DE继续发读请求，VS/HS/DE/user/last共同延迟两拍后进入mixer。
只在TARGET事务路径启用；TARGET_ENABLE=0保留原STYLE V2接线和周期行为，Logo/五模式算法不变。
这是修复完整链路坐标对齐，不是改变TARGET识别语义；全帧联合重跑仍在执行。

## 5. ROM属性复核与下一资源项

SYN05 源 `2f3ae57` 修正属性后，TD仍未将完整索引/调色板映射为块RAM：
gate21892 Slice/91ERAM、实际place21279，**与SYN04相同，属性修改没有额外面积收益**。
TD给出SYN-5105：优化后的palette读口未保留完整寄存器边界。保留原始警告与证据，不继续盲试属性。
下一资源优化选MAIN宽邮箱的接收副本：保留源整包锁存和同步/稳定等待，
由消费沿直接采样源锁存总线，ACK延至消费沿之后，避免另存一份完整目的域包。
只允许在严格由receive脉冲消费的通道使用；连续读取的公共时基邮箱保持原结构。
须通过506位、极端快源/慢目的、停钟与单侧复位检查，再决定是否进入整体SYN。

## 6. 对齐修复联合结果与邮箱结构

2026-10-22，`system_msim_06`完整执行到115ms并通过：30203218检查、1382400写接受、864000读请求、8次完整提交。
实际原安路像素/命令FIFO、packer、MC适配、台账及mixer已串联；RAW和AWB边界为合成场景，DDR为显式有界服务模型。
该套仍未串最终TARGET显示提交、未覆盖所有故障/五模式，不称整机验收完成。

`frame_bundle_cdc.PULSE_PAYLOAD=1`：源整包寄存器保持到消费沿之后的ACK，目的不再复制全包；
3拍request同步+2拍稳定等待后发receive，再过1个目的沿才ACK。
这比依赖某个时钟比更严格：即使源比目的快23倍，也不能在消费前改变总线。
控制33、begin128、grant99、terminal186、display506五条仅脉冲消费通道启用，公共时间64位通道不启用。
字面受理队列验证506位内容和顺序，正常/极端时钟、停目的钟、单侧复位通过；故意将ACK提前的负对照在529ns触发内容/顺序断言。
最初极端时钟夹具因复位短于目的首沿、#1采样撞上源负沿而失败，已分别修正夹具并保留原失败。
这些测试不替代物理总线路径界限和整机异常恢复证明。

## 7. 面积门进展与台账索引优化

SYN07 源 `7059a31`：gate Slice21680、FF21962，91ERAM/21DSP。
与Logo阶段比少923FF、212 gate Slice（包含对齐的10控制FF，不能将FF直接换算Slice）。
实际pack21171；完成place后的正式area为21174 Slice、19476 LUT6、21685 FF。
这是首次完整place通过；只剩42 Slice，未route/bitgen，不能当作合理候选。

台账下一项依据：fresh_start严格递增、单个active writer、分配不覆盖最新完整回退帧，
所以每次新commit必为最新complete；保留latest_slot/valid等价于每拍四帧32位最大值网络。
barrier/new session清valid；取消不改变回退帧；同拍select仍读取旧完整状态。
不减少任何身份、时间、代次、计数、租约或排空保护。
以冻结旧版为参考，对生产172800字/152位标注的全部公开输出逐拍比较：
41个独立接口检查、691242个输出等价周期通过，包含早/晚结果、重复乱序、租约、取消和屏障。
这一证明针对结构重构；实际面积收益仍待SYN/place，不预报数字。

独立字库流水预览以真实1280×720、1650×750完整光栅对旧提交器延迟一拍逐像素比较，
2475309检查通过；实际首输出沿才做年龄门，验证request沿合法而output沿过期时整组隐藏，
并验证年龄相等允许显示、FrameRef和即时fault关闭。当前尚未进入生产TD，不混入台账面积实验。

## 8. 台账实测与显示流水接入

SYN08 源 `095c6ab`：gate21595 Slice、21965FF、91ERAM/21DSP；实际pack21097，最终place21102 Slice、19458 LUT6、21698FF。
对上一项最终place21174，实测再少72 Slice。累计容量已经通过，但仍仅114 Slice余量，未route/bitgen。

显示流水现在正式接入MAIN，生产显式 `PIPELINE_GLYPH=1`：请求字符/行/像素上下文一起寄存，
下一拍共享字库返回后合成，RGB/DE/HS/VS统一多一拍。身份发布与年龄检查位于真正最终首输出沿。
生产源码重新通过2475309项完整光栅/年龄检查；保留PIPELINE_GLYPH=0参考路径，旧14场景2380564检查仍通过。
框/文字/底色统一遮罩，Logo/CNT/状态优先。没有更改TARGET独立RTL。

五模式当前ISP回归完成：64×32为5632有效拍/3872打包字，1280×720五帧为1152000拍/864000字，
包括逐像素独立模型、K3/K4、配置CDC与OSD。ModelSim因冻结旧Edge源码的声明位置不兼容而编译失败，
保留失败后改用既有Icarus跑真实未改RTL，没有修改冻结算法或靠改期望通过。
最终共享字库/框/十字/文字/诊断/最终输出的整机联合测试正在执行，不提前宣告通过。

下一面积热点为MAIN的固定延迟存储。若实施，只改变相同拍数的存储表示和启动资格，
必须扩展对齐存储文件的允许范围并逐拍等价验证，STYLE/Edge计算模块及Sensor/ISP参数仍冻结。

## 9. 公共对齐存储重构与最终联合结果

SYN09 字库流水源 `8d655a2`：gate21560 Slice、22014FF、91ERAM/21DSP，
SYN WNS -0.013/+0.114ns（原 -1.724/+0.114），未单独place，物理增量不作推算。
该提交已真实push至Draft PR #14，仍无candidate/bit。

`final_system_09`已完整执行210ms：52405117检查、1382400实际写接受、1859040读请求、8次完整提交。
全部像素比较包含底图、共享字库下Logo/CNT保护、框/十字、字面坐标/计数/状态文字和两行诊断。
观测到6次可信图文扫描、1次目标消失整组隐藏、3次过期隐藏；CSI观察钟停止35ms后恢复，显示公共时间仍前进。
输入仍是合成RAW/post-AWB及有界DDR服务模型，不称真实MIPI/DDR PHY/上板证明；异常恢复矩阵另需收口。
固定49641eef的隔离checkout重新完成TARGET handoff全部16任务；integration_ready仍false，不改其独立工具结论。

为获得合理面积余量，允许修改范围新增MAIN `isp/edge_control_stream.v`的固定延迟存储；原66个输入现有60个逐字冻结。
不修改STYLE/Gaussian/Sobel/NMS/四跳/Temporal/灰度/二值化计算，不改分支拍数或对外接口。
四类payload阵列去复位，valid/user/last仍复位；饱和warm_count在每个读tap恢复旧版启动值：
STYLE输入22拍、空间配置25拍、最终RGB/灰度/二值化/配置27拍（生产配置）。
旧版逐拍移位和值都保留，只允许工具改用移位存储；不是直接删除复位后让旧帧数据穿过。
1280点整行35975周期、68点6158周期的真实全算法旧/新公开输出逐拍一致，覆盖各种模式到STYLE、阈值、valid间隙和中途异步复位；
最小5级/4点参数另有2280周期一致。第一版夹具阈值拼接位宽修正后重新验证，采用后续11/12证据。
故意去掉warm屏蔽的负对照在中途复位后2798检查处检出旧数据泄漏；保留失败源和日志。
完整720p独立模型正在重跑。是否推断成功及实际Slice收益由下一SYN/place决定，暂不预报。

SYN10首次调用在进入TD前被全工作区clean检查阻止：并行研究更新了未提交的 `docs/GITHUB_REFERENCE_RESEARCH.md`。
该研究文档不属于本轮提交，不覆盖、不暂存、不推送。构建器仍要求代码/工程/配置已提交，
逐个TD输入与源码commit匹配并在构建后复核；只允许无关docs保持未提交，不把它们当作构建输入。
此次没有执行综合、没有新的数据库或资源数字，后续重新固定构建脚本commit后再运行。


## 10. SYN10/物理布局及故障夹具复核

SYN10实际源码 `4a1e08b8c7af0eccef92f8a05f738d096eb6baca`：gate21520 Slice、21947FF、91ERAM/21DSP，综合Setup/Hold为+0.049/+0.114ns。
实际pack20931、完成place20940 Slice、19368 LUT6、21673FF；低于容量276 Slice，累计对原21825减少885。
SYN09未单独place，不能将该物理差额全部归给对齐存储；对已测SYN08/place21102，当前累计再少162 Slice。
完整720p五模式独立模型重跑已通过：1152000有效拍、864000打包字，K3/K4/配置CDC兼容，证据five_modes_alignment_10。

复核实际顶层：MAIN事务控制、MC命令FIFO和DDR控制器均使用S_rst_n，来自PLL lock；
没有“CSI/HDMI单侧复位清台账而MC命令队列继续运行”的独立接线。邮箱单侧复位仍由独立CDC测试覆盖。
新增真实MAIN/FIFO/MC故障联合夹具，通过MC ready暂停300us制造源frame3溢出，并向frame5注入packet_error。
持续检查实际issued-accepted等于pending_writes、写接受不覆盖读租约、epoch flush前物理排空、每次完整提交严格172800接受字。
首次夹具运行到100ms及6次完整提交，最后错误地检查FIFO计数低16位；该监控前600帧累积在高16位。
原失败源码按manifest哈希恢复归档fault_fixture_failure_11，非RTL通过；修正检查高16位后另跑fault_system_12，未改生产RTL。

布线正在针对同一SYN10/place10数据库执行，未生成bit。面积余量仅1.30%，仍存在严重布线拥塞风险，不预报通过。
物理CDC先在旧place08数据库验证审查流程：独立副本移除全局async屏蔽，审查SDC显式加入40ns datapath bound，
7类邮箱/1638端点全覆盖，最差数据路径10.225ns、界限裕量29.711ns；这是Placed证据，不能替代最终Routed审查。
正式SDC、时钟、IP、引脚均未更改；审查数据库禁止export/实现/bitgen，避免把audit约束带回正式构建。


fault_system_12的高16位溢出检查通过，但最后要求packet_error引起全局metadata_fault的夹具预期错误。
实际observer的external_error只标记当前RAW/RGB无效，epoch_fault用于重叠/身份等故障；两者应分别检查。
保留fault_fixture_failure_12及准确源码。fault_system_13增加32ms时100us的公开calib_ready失效，
保留26ms MC暂停300us与42.5ms packet_error，分别验证坏帧取消与全局epoch排空恢复，生产RTL保持不变。


fault_system_13完整90ms通过：29904827项检查，6次完整提交，3次故障后的完整提交，2次坏帧取消、1次校准epoch恢复，FIFO计数00010000（启动600帧内注入溢出1帧）。
结束时recovery=0、pending_writes=0，全部实际写接受已排空。此为故意注入、合成RAW/post-AWB和有界DDR模型证据，不能等同实板长期无溢出。
该测试准确绑定b769b5e的33项实际输入，包含原安路FIFO/MC、MAIN台账/guard/reader，未使用强制私有状态替代真实握手。


路由拥塞仍较高，额外进行一次隔离ROM映射判别，未改正式RTL：
current独立gate为1456估算Slice、1753LUT、0FF、2ERAM；对index/pixel增加keep后为1714/1914/35/0。
保留读寄存器反而增加258个独立gate Slice并丢失2ERAM，明确拒绝该变体，不进入整机综合。
两份准确源码、TD脚本和原始area/stdout保存logo_mapping_isolated_14；没有把独立映射数字当作整机物理收益。


## 11. 长时间路由未收敛与明确ERAM映射

2026-10-22 13:17：route10运行约4.4小时CPU后，迭代29仍有2091个overused edge（over2092），近期在约2000附近反复，净长增长到1.09672e7。
保留完整flow/stdout并核对命令行后终止PID34112，状态ENGINEERING_ABORT_NO_CONVERGENCE，不宣称工具已证明不可布线。
未完成route/STA/bitgen，没有candidate/tag；证据route_alignment_10_aborted。

下一项仅针对MAIN Logo映射：官方本机UG1310_1.2第13-17页规定PH1P_LOGIC_ERAM可例化、支持初始化文件，适用PH1P35MDG324。
用两个逻辑ROM原语（16384×10索引、1024×25调色板）明确映射，物理共10ERAM，保持原有两次同步读、像素及透明度。
独立实测gate21估算Slice/28LUT/2FF/10ERAM，对原独立1456/1753/0/2显著降低；不是整机物理承诺。
第一隔离SYN同时指定INIT_FILE和FILL_ALL产生warning，随后仅保留完整初始化文件，FILL_ALL=NONE；全部空间都显式填0。
官方加密模型首次仿真缺PH1P_PHY_GSR顶层，失败已保留；加入官方GSR模型及顶层后，32768地址和1237512完整光栅周期逐拍通过。
正式相对文件名版本logo_production_equivalence_17再独立通过，使用真实官方模型，不以自写行为stub替代原语。

新增两份tracked .dath存于td_project；prepare_td_runs与仿真runner复制到各自工作目录，运行前后校验。
TD仍83项工程条目，另2份实际初始化输入列入SOURCE_MANIFEST，总85项；旧60输入继续冻结。
厂商仿真库不复制入仓库，只记录安装路径和SHA256；原语定义由TD原生器件库提供。
仅Logo存储实现改变；五模式算法、Sensor、AWB、TARGET生产RTL、时钟、ADC/SDC均不变，整机SYN/P&R及联合回归将重测。


正式SYN18在RTL sanity处因INIT_FILE解析失败停止，完整标志检查将其判为失败，没有归档Runs中的旧gate面积。
TD按RTL源文件目录查找裸文件名，而非当前run/project目录。将同字节的两份初始化数据放到target/源码旁后，
隔离实测再次得到21估算Slice/10ERAM，且不再有INIT_FILE/FILL_ALL组合告警。
canonical初始化现在位于target/；td_project保留完全一致的生成镜像以兼容已开始的仿真，builder逐字核对两份并记录镜像关系。
本次没有改RTL或初始化数值，因此正在执行的真实官方模型联合测试输入字节不变；源码旁的实际TD输入85项将绑定新的提交。


## 12. 明确ERAM整机实测与最终功能结果

SYN20真实源码 `7c7e5ee7d6c52260bcf557d9dabd4014f84e2687`：20514估算Slice、24255原生LUT、21949FF、99ERAM、21DSP，SYN Setup/Hold +0.125/+0.114ns。
相对SYN10少1006估算Slice、1857原生LUT，ERAM多8；不能直接用独立ROM1456→21差额当整机物理节省。
实际pack19947；完成place19952 Slice、18063 LUT6、21649FF、99ERAM/21DSP。
对前一place20940再少988 Slice，对最初21825累计少1873，余1264（5.96%）；完整route仍待完成。

正式相同RTL+真实官方ERAM/GSR模型的 final_system_18 完整210ms再次通过：52405117检查、1382400写、1859040读、8完整提交、6可见/1无目标/3过期扫描。
故障重跑fault_system_19再次得到29904827检查、2取消/1epoch/3后续提交，全部写排空。
为补上“epoch发生时确有物理在途写与正在扫描的读租约”边界，新增独立active_epoch_21：
在source4实际pending=1、leased=1时注入校准失效；24648825检查、5完整提交、3故障后提交、1取消、1epoch，通过结束写排空。
source3溢出、source4中断及source5错误均未完整提交，读租约未被写覆盖；不靠force内部状态构造测试。
原fault13/19的32ms校准失效位于帧间空闲，保留原证据，不能用它替代新active-epoch证明。
这些仍是实际数字RTL和有界DDR模型，不代表真实Sensor/MIPI/DDR PHY及长期实板验证。

## 13. 最终路由与物理CDC

route20完成，最终19952 Slice /18063 LUT6 /21649FF /99ERAM /21DSP，保留1264 Slice；对最初21825少1873。
最终Setup+0.165ns、Hold+0.020ns、TNS0。HDMI mixer最差路径12.927ns；原TARGET字库跨模块组合路径已拆开。
独立Routed CDC审查24覆盖7类邮箱1706端点、40ns界限最差+25.799ns；逻辑网络选择避免物理双FF命名遗漏，36位Gray均覆盖，额外同域扇出共305端点在13.033ns界限最差+3.232ns。
22/23的覆盖断言失败保留；没有降低门限或删路径，没有修改正式SDC/实现数据库。
旧相机/I2C布线告警、全局async对原Gray约束覆盖缺口仍记录，见CDC_REVIEW；本次as-built物理检查不替代未来约束修复或实板。
全部功能门通过后从原route.db生成bit并归档，不复用Runs旧bit。
