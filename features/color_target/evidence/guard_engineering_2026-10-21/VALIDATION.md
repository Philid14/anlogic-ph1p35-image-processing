# guard工程证据：2026-10-21

状态：独立综合测量与配置预检完成，`integration_ready=false`。生产9 RTL不变。
受测工作区HEAD为 d247788，新增工具当时未提交；不能仅用HEAD标识本次受测输入。
`SOURCE_BINDING.json`绑定全部受测文件原始SHA256；两种仿真/综合运行器另保留各自源哈希与运行前后不变检查。

## 实际执行

本机Python3.12运行环境；TD V6.2.168116、PH1P35MDG324 speed3；
ModelSim ASE 10.3c（安装目录名称14.1不是模拟器内核版本）。工具绝对路径和命令保存在下列JSON，
可移植重跑命令见 [工程报告](../../integration/GUARD_RESOURCE_PREFLIGHT_2026-10-21.md)。

| 操作 | 实际结果 | 证据 |
|---|---|---|
| `run_guard_synthesis.py --td <显式路径> --out .../gate-03` | exit0；3组证据有效；人工10ns下均正slack | `synthesis-summary.json`；3组area/timing-status文本 |
| `run_guard_fixture.py --sim modelsim --msim <显式路径> --out .../fixture-02` | exit0；vlib/vlog/vsim各exit0；6项硬检查、0失败 | `fixture-summary.json`；ZIP内原始日志 |
| `test_guard_engineering.py` | exit0；15个测试方法通过，覆盖非法/未决配置、篡改源、缺失/重复测量证据、负slack | ZIP `checks-02/engineering-tests.log` |
| 7个CLI场景 | 全部符合独立指定的退出码；其中pending=2、合法声明=0、合法声明的integration门=2，4非法配置=1 | `configuration-tests.json`；ZIP内逐项summary及stdout |

active64：1132 LUT/1471 reg/1113 gate Slice/0 ERAM/0 DSP，SWNS/HWNS=+1.494/+0.502 ns。
active32对照：936/1247/927/0/0，+1.644/+0.502 ns。
disabled64负对照：10/7/7/0/0，TRACK被优化掉；该数字不能当guard生产预算。
所有资源含输入加载和输出采样/选择逻辑；完整原生层级列见area文本。
STA coverage分别73.51/72.72/61.51%，存在未绑定引脚警告，未生成bit。

## 保留的失败尝试

1. `probe-01`：工具exit0，但独立路径导出未生成文件，验证运行器exit1，未报测量通过。
   改用已经包含完整关键路径的timing summary，不再调用未指定路径组的导出命令。
2. `gate-02`：3组TD均exit0，但禁用配置的资源列名为`#slice`、有效配置为`#slice*`，
   初版严格解析器拒绝前者，整组退出1。修正两种明确列名并增加回归后，重新执行gate-03。
3. `fixture-01`：Windows沙箱启动vlib报WinError623（系统DLL重定位），无仿真完成标记；
   保留为工具启动失败。经自动审批允许在正常工具环境运行fixture-02，才得到真实6/6。
4. 本机打包助手首次遇Windows路径分隔符导致重复ZIP成员，完整性检查拒绝包；
   失败中间产物留在本机outputs/guard-budget-2026-10-21/packaging-failed-01。
   最终包统一路径后，逐成员检查数量唯一、字节长度及SHA256，不覆盖任何既有证据。

没有修改生产RTL来得到PASS。未重跑不变生产RTL的旧818检查或全量handoff16，未改写旧结论。

## 原始证据与边界

`RAW_EVIDENCE.zip`：118个成员，含probe-01、gate-02、gate-03、失败/成功仿真、CLI场景、
软件测试日志及受测源快照；2079193字节原文，压缩228370字节。未将TD数据库纳入仓库，原数据库保留本机。
`RAW_INDEX.json`逐成员记录SHA256和大小，`SHA256.json`绑定随包JSON、报告和ZIP。
本目录`.gitattributes`禁用证据文件的Git换行转换，保留原始字节；暂存区逐文件回读验证，避免上传后SHA失配。

独立gate证据不能称整机P&R、真实Fmax、CDC物理验证或上板通过。
参数工具检查的是声明与TARGET源绑定，`elaborated_parameters_verified=false`、`integration_verified=false`；
MAIN真实实例、跨域/帧缓存/公共mask及整机资源时序仍待验证。
