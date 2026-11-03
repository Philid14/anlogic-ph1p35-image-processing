# PH1P35 最终提交代码包 V1.2

**请解压到短路径，例如 D:/P35，不要在桌面重复套多层文件夹后直接编译。**

压缩文件名为P35.rar，顶层目录为P35；建议解压到D:/，形成D:/P35。请勿再套多层长目录。

本包仅保留可重建当前工程的全部有效代码及必需配置，不包含开发历史、无效算法、独立未使用模块、全量测试、原始视频或旧bit。

- 仓库：https://github.com/Philid14/anlogic-ph1p35-image-processing ，main为整合主线；固定tag：final-submission-v1.2。
- 正式TD入口：in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display.al。
- 芯片PH1P35MDG324 speed3，使用Tang Dynasty6.2及安路设备/IP环境。
- 使用本次从独立解压目录完整TD流程实际重建的FINAL_SUBMISSION_REBUILD_V1 bit（算法同LATENCY_FRAME_FIX_V1），源码6432c918fea3b8ea25d65f5c5fe3816400b0cbfe。没有随机延迟模拟。
- 当前可烧录文件：artifacts/bitstreams/FINAL_SUBMISSION_REBUILD_V1/camera_to_dsi_display.bit。
- bit SHA256：ce6d17efe38297709ff71f24fd57f260270e16ff1bb6ed7031f5a03adc866515。
- 完整构建的Setup/Hold +0.137/+0.020ns；本版真实延迟修复和长期实板验收仍待完成，未虚填。

## 包内目录为什么必需

in_out_example保留原工程路径，含主RTL、MIPI/ISP/DDR/HDMI、OSD/算法、引脚与时序约束、厂商IP内部RTL/配置和四个ROM初始化文件。features只保留正式.al引用的目标模块。不能只交顶层.v，省去IP内部约束/配置会导致重建失败。

scripts只保留构建、准备与校验三个工具；submission保留源清单、TD设置、本说明和待验收清单；artifacts只保留当前唯一bit和BUILD_INFO。历史版本和完整研究证据去GitHub查看，不在包内重复。

包内共203文件：188工程/IP/约束/ROM，4目标RTL，3构建/校验工具，5说明/清单/TD设置，2当前bit及BUILD_INFO，1打包校验清单。未压缩约5.6MB。

## Windows路径要求

TD6.2 GUI请解压到短目录，例如D:/P35。桌面嵌套长目录会令TD拼接出的相对路径达到260字符，文件虽在也会报找不到。CLI现在提前检查解压根路径长度，并正确使用正斜杠传递Tcl脚本路径。GUI与CLI均建议使用D:/P35这类短目录，不能靠修改RTL解决TD长路径限制。

## 使用

1. 解压整个文件夹，勿移动其中子目录。
2. Python3执行 `python scripts/submission_package.py verify`。核对源清单与bit哈希。
3. GUI可打开上述.al；若TD要求更新旧工程路径，先另存到解压目录。也可运行 `python scripts/build_submission.py --td-root D:/TD`，脚本生成使用相对路径的CLI工程，依次综合、布局布线、时序检查、bitgen。`--prepare-only`只检查/准备工程，不执行TD。
4. 本地新编译bit输出到dist/local_build，必须重新核对资源和Setup/Hold，再归档为新的构建；不要覆盖包内已签发bit。
5. PROGRAM_SRAM先验收，具体功能/控件与待测项目见ACCEPTANCE.md。标尺和背景是运行时状态，复位后重新学习。

本包不是把随机数当实测延迟的演示版。提交清单与源码绑定在DELIVERY_MANIFEST.json；当前代码包交付不代替真实板卡测试。

本次独立解压副本的Synthesis/Physical Design/Timing Check/bitgen均已实际通过。191项源码/IP支持和.al在构建前后哈希相同。请在首次打开TD前校验；TD GUI可能自动更新工程位置/编译排序，不要把打开后的.al当原封不动的压缩包原件。
