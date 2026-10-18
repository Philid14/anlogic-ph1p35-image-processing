# EDGE_TEMPORAL_RESEARCH_V1 验证记录

所有数字测试使用合成输入；用户PROBE固定图上板反馈单独记录，不冒称真实ROI已经采到。

## 已执行

- 本轮保护基线7343cfe：673个历史工程/算法/Sensor/约束/归档/队友文件核对保持，包含17份旧bit；允许修改5个主线RTL文件及TD入口，新加2个诊断源。AWB改动只读端口有独立旧版并行测试，不以跳过冻结清单代替验证。
- `tb_awb_diag`：实际新/旧AWB+实际signal_delay、行为RAM/divider并行，35840有效拍的正式data/valid/user/last完全相同；实际pre RGB×实际gain按旧饱和/截断规则重建post逐lane准确。未冻结或恢复1×增益。
- `tb_temporal_osd`：3个完整720p帧691200有效拍，光学开/关/再关；每拍像素和两拍valid/user/last对照旧OSD，诊断区外原图及旧状态字库一致。同步页面RAM模型验证位坐标/白框/静区与数据同拍。
- `tb_temporal_capture`：小尺寸2帧与完整720p激励下8帧ROI捕获，独立Python逐像素对照全部RGB，actual gain重建post并与实际post CRC匹配；最终8192个96bit ROI拍、24720逻辑字。连续采集seq1..8；最终时间戳间隔236325周期与测试激励构造相符，不是实测摄像头帧率。
- 实际isp_top集成：强制AWB输出边界及对齐tap，用256×160激励、2×128×32 ROI，实际Edge/OSD/packer和实际采样接线通过CRC/数量/独立像素模型。实际Camera/PHY未模拟；没有把该测试称完整Sensor验证。
- `tb_temporal_packet`：5页含0/1/2/0/1回绕、末页padding、SOF切bank，所有256字逐项匹配独立编码器。
- 光学工具：101页打包/逆序/重复汇合，精确画面、透视+gamma+噪声+JPEG80、缩放恢复bit一致。12个损坏/缺页/混burst负例拒绝；不证明真实手机/反光/滚动快门一定可恢复。
- 研究工具：移动细线反例验证majority3可能消失、一帧支持可能双线；没有标注时完整度/误检/拖影保持未测，不生成现场贡献百分比。
- 旧PROBE全720p六帧1382400拍/1036800字、256×160六帧、13帧异常/回绕监测、FIFO实际接线及三完整帧arming回归通过。
- 旧QUALITY关闭/开启各28676拍/21507字；分类2892检查；四层168500拍/1348000采样层；K3/K4、200异步配置、116初始化后50次按键无Sensor写入、256数字回归通过。

## 可复现

```text
python -m pip install -r tests/requirements-edge-temporal.txt
python -X utf8 tests/run_edge_temporal_research.py --full --regression
python -X utf8 tests/run_temporal_capture_final.py
python -X utf8 tests/test_temporal_transport.py
python -X utf8 tests/test_temporal_metrics.py
```

Python3.12.14、NumPy2.3.5、Pillow12.3.0、Matplotlib3.11.2、OpenCV4.13.0.92、Icarus12.0。当前主运行时没有改包：OpenCV为tmp下隔离安装；用户建议独立Python环境。

## 修正与局限

1. 首次手工Icarus参数未在PowerShell引用，`-P...W=1280`被解析拆开，未进入仿真；正式runner通过参数数组传递。
2. 首次runner完整捕获及CRC对照已通过，到packet调用时使用错误关键字args（函数是plus）退出；修正后完整重跑通过，不是RTL失败。
3. 后加SOF周期计数后，手工检查误写激励间隔238544，RGB/CRC/捕获本身通过但外部断言失败。可复现最终测试从SOF/空白/行长度构造公式得236325，完整重跑通过；没有改RTL计数去满足错误期望。
4. 帧时间戳加入后单独完整8帧捕获复测；旧PROBE完整回归测试的是未变化的TEMPORAL_ENABLE=0路径。actual ISP集成测试在时间戳加入前通过，最后变化只增加只读时间戳字段；其输入采样、像素、packet和算法未改。

没有SDF门级/真实RAM或MIPI/DDR/HDMI PHY验证，没有实际手机视频和真实连续RGB文件。无独立轮廓真值与运动试验，不能宣布时间滤波改善。

## TD与归档

完整Synthesis→Physical Design→final Timing Check→bitgen由脚本执行，65项实际输入对齐源码commit，历史bit哈希前后比较。最终路由结果、warnings、Gray约束Ignored、bit SHA以同版本BUILD_INFO补录；时序失败只保留Rn检查点，不称candidate。
