# 软件使用入口

## 当前主线

Android：`02_software/mobile/omni-car-android`，build.gradle标注versionName=1.21.0、versionCode=23，Java17、compileSdk34、minSdk24、arm64-v8a。安装包为原工作区现有的1.21 debug APK，本次没有重新构建或验证APK与源码可重复构建一致性。

固件：`02_software/firmware/cyberbrick_omni_m1m2_plus_drv8833`，当前main.py含RGB灯控协议12，配合1.20/1.21手机端。保留boot.py、main.py、omni_core.py和tests；index.html属于历史文件，当前固件不提供板载控制网页。

手机连接Wi-Fi `OmniCar`（代码默认密码 `12345678`），控制端连接 `ws://192.168.4.1/ws`。先架空三轮完成轮位、正反转、最低起转值与增益校准，再落地低速测试。具体刷机方法沿用硬件配置指南，本次未对板卡执行刷写。

## 接线主方案

- W1左前：接收板M1；W2右前：M2；W3后轮：外接DRV8833 A路。
- 外接驱动控制：D1/GPIO21、D2/GPIO20；不要同时把这两个口当灯控。
- 当前灯控：S1/GPIO3；现有1.20说明写CN301信号接此处、稳压5V供电并共地，需实际确认灯型号与颜色顺序。
- 7.4V是电池标称电压；旧接线方案中的6V电机电源、5V灯电源不能混为电池直连。具体供电按原实车稳压方案核对。

## 不要混淆历史功能

以README顶部1.21记录为准：AI页待开发，原生语音监听关闭，返航标为实验功能，闭环方形按钮移除。更早README提到的云端AI与语音配置是历史内容。

手机姿态输入不等于车载IMU；没有编码器/视觉定位，不保证无头模式、位置闭环或精准返航。当前资料不包含摄像头图传固件。

## 构建与维护

在Android工程目录执行 `gradlew.bat :app:assembleDebug`；需自行配置Android SDK。已保留Gradle wrapper、源码、tests及现有app/libs依赖，未携带本机local.properties与缓存。

备选/学习：`mobile/omni-car-controller` 为UniApp早期端，`firmware/cyberbrick_omni_drv8833` 为另一接线方案，`firmware/phone_wifi_demo` 为演示。不要将其默认覆盖到当前主线。HTML模拟器与课程可用浏览器直接打开。
