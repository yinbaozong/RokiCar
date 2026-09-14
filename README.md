# RIFT / OmniCar — 三轮全向小车

绿色、紧凑、可打印，一块可更换的顶盖，留给更多自己的想法。

公开仓库：[yinbaozong/RIFT-OmniCar](https://github.com/yinbaozong/RIFT-OmniCar)。本项目原创内容采用 [MIT许可](LICENSE)，欢迎修改、再分发与商用；第三方依赖见 [组件说明](THIRD_PARTY.md)。

本包于 2026-09-14 整理。车壳采用用户确认的 **V7**，Android 控制端为工作区 **1.21.0** 源码与现有 debug APK。RIFT 是设计阶段暂用名，软件仍叫 OmniCar；尚未统一改名。

![整车宣传图](04_media/01_hero_closed.png)

## 从这里开始

- 看项目全貌：[项目总览](05_docs/PROJECT_OVERVIEW.md)。
- 看最终外壳：`01_model/cad/03_shell_assembly.step`（车壳＋盖子，不含轮子）。
- 打印新外壳：`01_model/print/01_shell_print.stl`、`02_hatch_print.stl`；先打印磁铁试配块。
- 原底壳：`01_model/cad/04_original_base.step`；原完整装配体在 `01_model/reference/original_full_assembly.step`，该参考装配仍是原车壳。
- 零件汇总：[装配清单](05_docs/BOM.md)。
- 装车与打印：[制造装配说明](05_docs/PRINT_AND_ASSEMBLY.md)。
- 安装手机端：`02_software/android_apk/OmniCar-Controller-v1.21-debug.apk`。
- 主固件：`02_software/firmware/cyberbrick_omni_m1m2_plus_drv8833/`。
- 当前说明：[软件使用入口](05_docs/SOFTWARE_GUIDE.md)。
- 发布介绍：[宣传文案](05_docs/PROMO_COPY.md)；配图在 `04_media/`。
- 顶部扩展：[扩展设计说明](05_docs/EXPANSION.md)。

## 文件夹

| 文件夹 | 内容 |
|---|---|
| 01_model | V7 STEP、FDM STL、参数化生成脚本、CAD预览、剖面、验证报告、原模型参考 |
| 02_software | Android源码与APK、主固件与历史方案、UniApp备选客户端、模拟器、教程、RSSI工具 |
| 03_hardware_and_learning | 工作区现有接线图、制作方案、配置指南、规划文档 |
| 04_media | 整车主图、相机/云台概念海报、图像生成提示词 |
| 05_docs | 本次整理的统一总览、装配说明、软件入口、扩展说明、宣传文案、资料索引 |

## 当前状态

已提供模型和软件资料；本次只做整理，未重新刷机、编译APP或进行整车实测。V7基础CAD干涉、指甲进入通道和STL封闭性检查通过，打印配合及磁力仍需实物验证。AI页面在1.21中为待开发，返航为实验功能；相机、云台、图传、自动导航均不是本包已完成能力。

宣传图由AI根据CAD参考生成，外形细节以STEP为准。扩展图中的摄像头、云台、螺钉和支架仅为概念，不包含对应制造文件。

原有文档保留了历史版本记录，发生冲突时以本包 `05_docs` 的版本说明及当前源代码为准。旧V1–V6外壳、历史APK、设备备份、缓存与本机SDK路径未混入当前交付。

## MakerWorld发布入口

- [可用发布文案](05_docs/MAKERWORLD_DESCRIPTION.md)
- [硬件逐线连接表](05_docs/HARDWARE_CONNECTIONS.md)
- [现有／实验功能和开发计划](05_docs/FEATURES_AND_ROADMAP.md)
- [当前主线连接图](03_hardware_and_learning/当前主线连接总图.svg)
- [实际机械爆炸图](04_media/04_exploded_cad.png)

三张新版宣传图已修正底盖画面；参考装配体的底板定位未修改。实际装配以CAD及试装为准。

## 硬件接线图

![当前主线模块连接图](03_hardware_and_learning/当前主线连接总图.svg)

图为现有源码与资料整理的模块级接线，不是实车测绘的PCB原理图。稳压器型号、板卡供电接口和灯模块端子顺序还需要实物确认。逐线说明见[硬件连接表](05_docs/HARDWARE_CONNECTIONS.md)。

## 结构爆炸图

![V7机械结构爆炸图](04_media/04_exploded_cad.png)

## 参与开发

请通过Issues提交打印反馈、接线纠正和功能需求。已有与实验功能见[功能和开发计划](05_docs/FEATURES_AND_ROADMAP.md)。报告硬件问题时请注明固件/App版本、板卡型号、接线和复现步骤。
