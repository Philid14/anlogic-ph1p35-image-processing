# EDGE_STABILITY_PROBE_V1 数字验证证据

- `rtl_full.json`：首次完整数据通路验证，源码faf3262之前的相同注入/监测/OSD/packer逻辑；6完整720p帧1382400拍/1036800字、6原子面板检查。随后只改FIFO启动监测启用条件，未改变这条像素通路。
- `rtl_small.json`：最终启动门控补充后的联合256×160六帧、异常监测/FIFO事件/capture_arm单元。最终固件源码与资源以bit归档SOURCE_MANIFEST和BUILD_INFO为准。
- `fixed_reference.json`：25个门限的软件参考CRC和白点数，不是实板测量。
- `fixed_rgb.png`：逐帧恒定RGB源定义图。
- `panel_reference.png`：实际字库生成的软件面板预览，SOF间隔60为示例，不可填入真实上板记录。

详细原始控制回归、启动误报警修正单元、CLI路径失败、主动终止的旧物理实现记录和最终TD全日志随bit的build_evidence归档。
未在本机采集真实Sensor控制或烧录；FIFO行为单元不模拟厂商PHY。所有“正常期望”均为契约/模型，不表示已实测正常。
