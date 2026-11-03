# 参数表与派生关系

所有尺寸单位 mm，角度单位 °。**以下数值全部是概念假设值，不是 HX1P35/SC500CS/显示器实测规格。** 唯一参数入口是 `parameters.scad`，本表用于解释含义；改变参数后需更新本文档中相关假设。

## 1. 底座、框架和载板

| 参数 | 默认假设值 | 定义/后续确认 |
|---|---:|---|
| `frame_w / frame_d / frame_h` | 600 / 500 / 720 | 暗箱框架外尺寸；高度从固定台面起算 |
| `profile` | 20 | 2020 型材方包络；未核实槽型和连接件 |
| `base_margin` | 20 | 框架左右基础边缘余量 |
| `electronics_bay_w` | 400 | 框架右侧扩展区，不含最外 20 mm 边缘 |
| `base_d / base_t / foot_h` | 600 / 18 / 30 | 底座深度、厚度和脚高；材料平整度、承载另核实 |
| `base_w`（派生） | 1040 | `frame_w + electronics_bay_w + 2*base_margin` |
| `insert_w / insert_d / insert_t` | 360 / 240 / 3 | 可换载板；参考面在 Z=3 |
| `fov_w / fov_d` | 320 / 180 | 目标拍摄范围，不是已知镜头规格 |
| `card_w / card_d` | 90 / 110 | 每个色卡包络；两卡中心 X=±`card_center_x`=±75 |
| `measure_roi / measure_roi_xy` | [210,120] / [25,0] | 尺寸测量 ROI 的物理示意尺寸及中心；FPGA ROI 需另映射 |
| `reference_len / reference_width` | 280 / 15 | 前沿尺度条、后沿灰参考条的示意包络 |
| `reference_y / gray_y` | -75 / 75 | 尺度条/灰参考条中心 Y |
| `grid_square / grid_cols / grid_rows` | 20 / 14 / 8 | 标定占位方格，280×160；内角点 13×7 |

框架立柱默认 4×720；上、下各 2 条 X 梁 560 与 2 条 Y 梁 460；相机横梁 2×560、Y 桥梁 200；灯位及托盘横向侧梁共 3×460。此为几何长度估算，**不可直接作为下料单**：型材端接方式、斜撑、角码、滑块、端部加工和锯缝会改变数量/尺寸。

## 2. 相机与光学

| 参数 | 默认假设值 | 定义/待确认 |
|---|---:|---|
| `camera_h` | 400 | 镜头前端到载板参考面的机械间距 |
| `camera_min_h / camera_max_h` | 280 / 500 | 模型可调范围；实际焦距、排线、灯位限制后重定 |
| `camera_xy` | [0,0] | 光轴偏移；首版居中；更改后重新检查画面/夹具关系 |
| `camera_body` | [38,38,16] | 模组含元件的长宽高包络 |
| `lens_d / lens_len` | 18 / 20 | 镜头柱体外径/向下伸出量；无螺纹模型 |
| `camera_standoff` | 8 | PCB 上表面到相机托板的概念间隙 |
| `camera_plate` | [90,130,4] | 托板长宽厚；左右通用锁紧长孔不代表模组孔 |
| `camera_holes` | [] | 实测孔 [x,y] 列表，相对光轴；空列表不打模组孔 |
| `camera_hole_d` | 3.2 | 仅是默认通孔直径假设 |

派生：`lens_z=insert_t+camera_h=403`；相机托板底部 `camera_plate_z=lens_z+lens_len+camera_body[2]+camera_standoff=447`。

空孔位时，模组和托板之间的 8 mm 空隙只表达待定连接关系；实测后使用螺柱或合适的边夹，不能把悬空占位当成可装配结构。模组孔位、镜头偏心、连接器方向、对焦环操作空间应一起确认。

目标全视角的针孔近似：`2*atan(FOV/(2*H))`。默认约 43.6°×25.4°，仅用于判断空间是否合理。真正 FOV 必须在使用的分辨率、ROI、裁剪、缩放、镜头设置下实测。

## 3. 灯、遮光和外部设备

| 参数 | 默认假设值 | 定义/待确认 |
|---|---:|---|
| `light_count` | 2 | 支持 1 或 2 路，1 为左侧；更多光源下一轮增加模块 |
| `light_h / light_x` | 260 / 225 | 灯转轴距参考面高度/距中心的左右偏移 |
| `light_len / light_w / light_t` | 200 / 65 / 12 | 灯具包络；实际发光面/散热器另确认 |
| `light_tilt` | 35 | 从向下垂线向中心倾斜；相对水平面是 55° |
| `cloth_gap / cloth_overlap / cloth_hem` | 8 / 60 / 25 | 布与框架间隙、闭合搭接、每边折边量 |
| `cloth_hook_pitch` | 120 | 上梁示意挂点间距；末端可另加一个挂点 |
| `board_size` | [140,120,18] | 板卡含元件占位，不是官方板卡尺寸 |
| `board_tray` | [170,150,4] | 托盘包络，四组边缘通用长孔 |
| `board_standoff / board_y / board_z_offset` | 10 / 20 / -30 | 板间隙、前后位置、托盘底与镜头前端的 Z 差 |
| `board_holes / board_hole_d` | [] / 3.2 | 实测孔位与通孔；默认没有虚构板卡孔 |
| `cable_lane_w / connector_keepout` | 30 / 35 | 外侧线槽宽与接头操作空间；不代表厂家允许弯曲半径 |
| `cable_pass_w / cable_pass_h` | 45 / 25 | 右侧布帘软穿线口，需错位遮光挡片 |
| `monitor_size` | [360,225,35] | 显示器机身 W/H/T，不是英寸或有效屏幕尺寸 |
| `monitor_gap / monitor_y / monitor_z` | 35 / 205 / 300 | 机身左边与框架右边间距、机身前面 Y、机身中心 Z |
| `vesa / vesa_hole_d / monitor_plate_t` | [100,100] / 4.5 / 4 | 假设后孔间距、通孔、板厚；须核实有没有 VESA |
| `monitor_mass_kg` | 2 | 仅设计输入记录，模型不根据它计算安全承载 |

遮光布粗裁公式（非缝纫成品图）：

- `Wc=frame_w+2*cloth_gap=616`；`Dc=frame_d+2*cloth_gap=516`。
- 顶布：`(Wc+2*cloth_overlap+2*cloth_hem) × (Dc+2*cloth_overlap+2*cloth_hem)` = 786×686。
- 背布：`(Wc+2*cloth_overlap+2*cloth_hem) × (frame_h+cloth_overlap+2*cloth_hem)` = 786×830。
- 左/右布各：`(Dc+2*cloth_overlap+2*cloth_hem) × (frame_h+cloth_overlap+2*cloth_hem)` = 686×830。
- 前双帘每幅：`(Wc/2+cloth_overlap+2*cloth_hem) × (frame_h+cloth_overlap+2*cloth_hem)` = 418×830，缝好后中缝搭接量还需现场调整。

模型帘布仅为 1 mm 平面示意，不模拟褶皱、搭接、折边和垂坠；`cloth_overlap/cloth_hem` 用于裁布公式，不改变总装平面网格。前帘底部需盖住底边，线缆挡片与通风遮光需现场处理。预览的半透明效果不能用于判断漏光。

## 4. 输入格式与修改示例

```scad
// 下列孔位只是语法示例，绝不是实测孔位；勿直接填入正式参数。
// camera_holes = [[x1,y1],[x2,y2],[x3,y3],[x4,y4]];
// board_holes  = [[x1,y1],[x2,y2],[x3,y3],[x4,y4]];
// vesa = [measured_pitch_x, measured_pitch_z];
```

孔位采用原始列表，可以表达非对称布局；孔径不等时需要下一轮改为逐孔直径。若实际模组或板卡大于假设包络，先更新 `camera_body/board_size`、托板尺寸和槽位，再填孔。相机托板槽中心 X=±35 的初始结构也必须同步检查，不能只改外框就出图。

参数断言覆盖：主要包络、灯位范围、托盘与屏幕服务区、载板/FOV、孔位边界。未覆盖完整碰撞、工具可达性、光线遮挡、重心、强度、排线长度及真实镜头投影；预览和实物摆位仍是必做步骤。
