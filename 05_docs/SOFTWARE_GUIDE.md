# 软件与刷写入口

Android 1.22.0：应用 ID com.rokicar.controller。安装现有 APK，无需先编译；本次没有更改 App 版本或功能。

当前主固件为 `02_software/firmware/cyberbrick_rokicar_m1m2_plus_drv8833` 中的 boot.py、main.py、rokicar_core.py。本轮只修正 boot.py 为有限初始化，电机、灯光和协议保持不变。作者确认 LED 转接板 IN 接 D2，按最新实车图使用，不再套用旧文档的灯口描述。

- [优先阅读复刻 PDF](RokiCar_复刻指南.pdf)：AI 刷写优先，手动方法在最后。
- [完整用户刷写教程](用户刷写教程.md)
- [给本地 AI 的提示词](交给AI刷写.txt)
- [下载 Android APK](https://github.com/yinbaozong/RokiCar/releases/latest/download/RokiCar-Controller-v1.22-debug.apk)
- [下载三文件固件](https://github.com/yinbaozong/RokiCar/releases/latest/download/RokiCar-Firmware-20261008.zip)

主固件热点 RokiCar，密码 12345678，地址 ws://192.168.4.1/ws。保留实车校准 JSON；新车默认参数必须架空校准后保存。AI 网页、语音、图传和云台不是基础版当前可用功能。UniApp、双驱动与 Wi-Fi 演示目录属于历史/学习方案，不能混入当前主线。

当前本地启动回归、语法和辅助模块依赖检查通过。文件写入、自动启动和实际控制需在用户板子上按教程验收，本轮未执行实车刷写。
