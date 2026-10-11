# RokiCar

一台六边形的三轮全向小车。能前后移动、横着走，也能原地旋转，支持手机控制，外壳可以用普通 FDM 打印机制作。

![RokiCar](04_media/01_hero_real.png)

## 下载

- [复刻指南 PDF](https://github.com/yinbaozong/RokiCar/releases/latest/download/RokiCar-Replication-Guide.pdf)：物料、购买链接、接线、装配和固件刷写方法都在里面，建议先看这份。
- [安卓安装包](https://github.com/yinbaozong/RokiCar/releases/latest/download/RokiCar-Controller-v1.22-debug.apk)
- [小车固件](https://github.com/yinbaozong/RokiCar/releases/latest/download/RokiCar-Firmware-20261008.zip)
- [小车模型](https://github.com/yinbaozong/RokiCar/releases/latest/download/RokiCar-V8-Models.zip)

## 准备物料

**全向轮请使用 PDF 中推荐的 47 mm 全向轮，共 3 只。** 当前外壳和轮组空间按这个规格设计，换成其他尺寸或结构的轮子，可能需要修改模型。轮子与电机之间还需要匹配的联轴器。

其余主要配件包括 3 台 6 V / 200 rpm N20 电机、1 块 DRV8833 驱动板，以及 CyberBrick 核心板、接收板、电池、开关和 LED。可以选全能套件，也可以按需单买。完整清单和部分配件的购买链接见 PDF；购买前核对规格与接口。

## 接线

![RokiCar 接线图](03_hardware_and_learning/RokiCar接线图_D2.png)

M1 为右前轮，M2 为左前轮，M3 为后轮；LED 转接板接 D2。具体接线与刷写步骤请按 PDF 操作，首次运行先架空轮子，确认方向和停车正常后再落地。

## 继续改装

![相机搭载示例](04_media/02_camera_real.png)

本项目的小车模型及软硬件资料全部开源，欢迎自由改装、加装和二次开发。顶部可根据需要改造，搭载摄像头、传感器等模块，探索更多玩法，让 RokiCar 拥有属于你的新功能。相机及相关拓展需自行加装。

也欢迎分享你的改装作品和新玩法。如有任何问题，欢迎[提交 Issue](https://github.com/yinbaozong/RokiCar/issues)，或通过邮箱 [yinbaozong@163.com](mailto:yinbaozong@163.com) 联系我。
