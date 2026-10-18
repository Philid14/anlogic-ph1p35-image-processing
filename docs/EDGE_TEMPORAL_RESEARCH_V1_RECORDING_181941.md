# video_20261018_181941：完整解码、数据来源核对与分析

日期：2026-10-18；角色MAIN；本轮只处理数据。文件确为用户指定的`D:\anlogic_formal_project\video_20261018_181941.mp4`。

## 结论

**A/B通过：101/101页完整恢复，8帧128×32 RGB888及AWB元数据全部校验通过。**

**关键发现：101个原始页面、全部pre/post RGB、AWB统计、增益和采样时间戳，与上一份17:43录像导出的数据逐字节相同。** 新录像文件确实不同，但没有提供一批新的含边缘ROI。不能用它验证纸边/眼镜框抖动，也不能计为第二次独立真实采样。

已按顺序在完整性通过后重跑C项分析，结果仍是旧平坦暗部数据。当前优先级是**确认新的ROI采样实际触发并取得代表性轮廓**。**尚不具备开发/发布EDGE_TEMPORAL_V1候选的证据条件。** 未修改正式RTL、PC算法或参数，未生成bit。

## A. 本次录像独立解码

| 项目 | 实际结果 |
|---|---|
| 输入文件 | `video_20261018_181941.mp4`，56556090字节 |
| 视频SHA-256 | `B84FA07CE2516C0532293117DFDD8448A694EE9FD6707E4AA2654262422C7323` |
| 格式/时长 | HEVC，1920×1080，121.745900秒 |
| 解码帧数 | OpenCV及FFprobe均3653帧，与容器计数一致 |
| 方法 | 每帧自动检测白框、四角透视校正、中心取格；原MSB-first/04C11DB7 CRC，无猜位补位、无放宽校验 |
| 合格图像帧 | 3346帧返回完整CRC合格包；307帧未返回合格包，不能直接称为307次CRC错误 |
| 页面 | **101/101**，编号0–100，缺页[]；无缺页时段 |
| header/payload CRC、bounds、padding | 保存的101页全部通过，末页20个有效载荷字，其余padding为0 |
| 合格重复页冲突 | 0 |
| 数据identity / 字数 | `897350F6` / 24720个32-bit字 |
| 整逻辑流SHA-256 | `54EEF957E3732E0996C094C46CF24CA70EF6EA9D6AD358473EB0612EBE7606B9` |

本次使用新的空输出目录`tmp/edge_temporal_edges_20261018/full_audit`，没有预装或混入旧页。完成独立解码后才比较旧数据，排除了“解码目录复用导致误读旧缓存”的处理错误。

## B. 重建8帧与来源核对

- ROI形状`(8,32,128,3)`；原点X576/Y344；采集local SOF600–607连续。
- burst pre CRC、每帧pre CRC、实际gain重建的post CRC均通过。post由实际pre×实际Q4.16 gain重建，不使用手机拍屏亮度。
- 每帧IN230400、720行×320拍、ROI1024、PACK172800；bubble/line/phase errors均0；ROI内gain changed均0；两FIFO已armed，sticky均0。
- SOF间隔均629785个MIPI周期，未冒充经校准的FPS或TEAM同帧端到端延迟。
- `capture.npz` SHA-256：`D50C47E6A099F234A18BFBDE418B82991856BA8F708215251C46FCFD866D419A`。

### 与上一份完整数据的直接比较

参考为`docs/edge_temporal_evidence/board_20261018_complete/`，来源`video_20261018_174321.mp4`。

| 比较对象 | 相同数量/改变数量 |
|---|---|
| 原始1024-byte页面 | **101/101页逐字节相同** |
| pre RGB | 98304个通道元素全部相同，改变0 |
| post RGB | 98304个通道元素全部相同，改变0 |
| 8×16元数据 | 全部相同，改变0；包含实际gain、AWB统计、CRC及SOF周期时间戳 |
| 16字global header | 全部相同，改变0 |

这项判断不只依赖32-bit identity或CRC相等，而是检查了全部页面与数组原值。不同视频SHA证明没有选错成同一个视频文件；字节比较证明本次导出内容与旧capture相同。

**已确认的是数据相同。** 录像不能确定现场哪一步复位/重新烧录/定位操作是否生效，因此不将结果写成“用户一定未复位”，也不凭此认定RTL发生了新的故障。当前程序按设计只在一次初始化后采一批，之后持续导出；屏幕ORIGIN纸边或CNT变化不代表冻结RAM已经更新。

### 可视化

- [本次重建的8帧拼图](edge_temporal_evidence/board_20261018_181941/real_roi_contact.png)：固定0–255显示，无提亮；仍为平坦暗部。
- [旧/新ROI、逐像素差及Sobel/NMS/四跳图](edge_temporal_evidence/board_20261018_181941/old_new_roi_and_stages.png)：旧/新RGB差为0，TH60的NMS/连接输出为空。不存在可放大的真实纸边区域，不能制造轮廓图代替采样。
- [RGB变化、实际AWB和梯度分布](edge_temporal_evidence/board_20261018_181941/input_awb_gradient.png)。

## C. 定量分析：当前文件中的实际内容

已在本次capture上实际执行`temporal_roi_analysis.py`（TH40/60/80）及既有`temporal_capture_evaluation.py`。中间算法级是经过旧RTL对照验证的独立整数模型重放，并非本次实板直接采集的梯度/NMS内部波形。

全RGB指标使用128×32 ROI。各级对照扣除7内部横采样/7行halo后，统一有效区为50×18=900个内部点；横向每点对应2个原像素。只有8帧、7次相邻比较。

| 用户要求项 | 本次可计算结果与限制 |
|---|---|
| AWB前相邻RGB平均绝对差 | **1.91369048**个8-bit码值 |
| AWB后相邻RGB平均绝对差 | **2.20298549**码值 |
| Sobel幅值逐帧变化 | Gaussian+Sobel相邻MAE **2.92126984**；78.5556%位置幅值改变；有效内区幅值最大18 |
| NMS前后位置变化 | TH40/60/80下Sobel/NMS均无门限边缘；白线位置位移**N/A**。NMS keep状态相邻改变45.8571%，属于低幅值局部排序，不能当白线跳动 |
| 四跳前后连通性 | NMS种子及四跳输出各帧均0个边缘点，局部连通分量均为空；轮廓连通性改善/恶化**N/A** |
| 白线闪烁幅度 | 无边缘union，条件闪烁率**null/N/A**；ROI全像素翻转数0不能说明白线稳定 |
| 白线位置跳动幅度 | 无匹配对象，位移**null/N/A**，不能填0像素当测得稳定 |

公共区域配对灰度相邻MAE1.30444，Gaussian后0.71492；方向码改变69.4444%。TH40的weak门限已为20，高于本ROI最大Gaussian+Sobel幅值18，所以TH40/60/80均不能激活可见轮廓。原Sobel、Gaussian+Sobel、NMS、四跳四种历史模型各帧均0个门限边缘点。未人为降低TH制造白线，也未新增算法。

### AWB来源区分

- 实际R gain范围1.10003662–1.10134888；B范围1.28573608–1.28709412。增益在微调，ROI内每帧保持常量。
- 同一当前pre改用上一帧gain，7次输出RGB差均为0；8帧全部改用首帧gain，所有post元素仍逐字节相同。
- 因此该窗口的RGB码值变化在AWB前已存在，动态gain微调未改变本ROI的RGB888。常量gain会缩放前级变化；不能把post/pre MAE差直接当因果贡献比例，也不能推广为AWB对其他位置或时间段无影响。
- Sensor噪声、照明、微小位移、前级ISP的贡献缺少受控现场对照，仍未知。这次数据也没有新增独立样本支持归因。

### 来源判断汇总

| 假设 | 当前证据 |
|---|---|
| 真实输入亮度/色彩微扰 | 同一已恢复burst内直接测得，但尚不能解释真实轮廓位置变化 |
| AWB动态变化造成该ROI码值变化 | 固定gain精确回放不支持此项 |
| Sobel阈值跨越导致白线闪烁 | 本ROI没有触及实际门限，未复现 |
| NMS峰位切换导致可见白线跳动 | 测得低幅值keep变化，没有门限白线可验证位移 |
| 四跳连接放大强锚变化 | 本ROI没有激活强/弱轮廓，无法量化 |
| 打包/FIFO/页恢复异常 | 本次完整页和该8帧被监测项正常；未见此窗口证据，不等于排除长期/未覆盖问题 |

## D. 结论、优先级与下一步

1. **当前真实数据直接支持“输入存在码值微扰”。** “真实轮廓附近的微扰被阈值/NMS/四跳放大”仍与旧机制实验及用户观察相容，但缺少含边缘的新RGB数据，不能把它写成已经完成现场定量确认的主因。
2. **优先做ROI/采样生效确认。** 当前不足以在时间域稳定、阈值策略或NMS/连接调整之间客观取舍，不据全黑输出排名。
3. **尚不具备开发EDGE_TEMPORAL_V1正式候选的证据条件。** 至少需要一批有代表性轮廓的静态数据；选定时间算法还需运动出现/消失及重复场景以检查拖影与响应。

### 现有固件的采样状态

源码只读检查`isp/temporal_roi_capture.v`：

- 第72行仅在`collect && roi && !done`时写入RGB RAM；
- 第74–75行在`rst_n`复位时清`done/next_slot/seq`；
- 第92–94行只在预热完成且`next_slot<FRAMES`时继续采帧；
- 第122行最后一帧完成后置`done=1`。

流程为：**实际复位 → 预热600 SOF → 捕获8帧 → 冻结 → 101页循环导出**。采完后移动纸张、切K3显示模式、改K4阈值或再录录像，均不会触发新ROI采集。某个实板按键是否真正拉低采样模块rst_n，不能从这份录像证明；推荐使用明确完成的PROGRAM_SRAM流程。

### 下一次最小操作

1. 先准备固定纸边/眼镜框，保持灯光和FPGA相机稳定；按现有协议用同一个归档bit重新PROGRAM_SRAM，明确确认编程完成。
2. 立即K3切ORIGIN，使纸边穿过绿色框**中央**；若600 SOF预热内来不及，先定位好，再重新PROGRAM_SRAM。保持静止直至自动编码出现。编码出现后才改变目标，不会改变已冻结内容。
3. 推荐先提供一张清晰完整编码页，让PC快速检查其identity/载荷是否仍为旧批次，再录整圈；可附一张预热期间绿色框横跨纸边的照片用于定位。照片不作为RGB数值输入。
4. 确认新批次后，再按成功的完整白框拍法录约4分钟，独立恢复101页。不混拼不同采样；若强纸边定位明确而新CRC合格ROI仍平坦，应先排查定位/实际像素坐标对应关系。

## 证据、复现与版本

目录：`docs/edge_temporal_evidence/board_20261018_181941/`。包含本次独立扫描ledger/CRC审计、101页ZIP及SHA清单、NPZ、与上一批的逐数组比较、TH40/60/80 JSON、元数据CSV、8帧拼图/对照放大图、PC源码原字节ZIP及验证记录。原始手机录像留本机，不上传Git。

```powershell
python -X utf8 tests/temporal_video_audit.py video_20261018_181941.mp4 --output tmp/recording181941_fresh
python -X utf8 tests/temporal_roi_analysis.py docs/edge_temporal_evidence/board_20261018_181941/capture.npz --threshold 60 --output tmp/recording181941_analysis.json
```

独立数组比对示例：

```python
import numpy as np
old = np.load('docs/edge_temporal_evidence/board_20261018_complete/capture.npz')
new = np.load('docs/edge_temporal_evidence/board_20261018_181941/capture.npz')
for key in ('pre', 'post', 'meta', 'global_header'):
    print(key, np.array_equal(old[key], new[key]))  # 全部True
```

沿用诊断candidate `edge-temporal-research-v1-candidate` / e3a6943857116b0a037aa1776a94e4b9f3602180，实际TD源码84299d42fb88842b837794bdf43b61a88f1e2049，bit SHA `5D01156E08E69DDAA51AB41A3E3C2DFB1BC8B60436E97FBAE6555754AE6EB27D`。本轮开工HEAD2a18cab，分支codex/main/edge-temporal-research-v1；复核#9→#8→#7→#6→#4→#3均open Draft且未合并，快照随证据。

本轮只新增数据/报告，不修改正式RTL、已有PC处理算法、ISP参数、按键、OSD、PLL/SDC、历史bit或BUILD_INFO；未运行TD、未生成bit、未移动tag或合并PR。停止于解码与诊断，等待含真实边缘的新采样。
