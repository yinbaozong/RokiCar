# CyberBrick + DRV8833 三轮全向底盘测试程序

这个目录是给 CyberBrick Controller Core 用的 MicroPython 程序。

刷入后核心板会创建热点：

```text
WiFi: OmniCar
Password: 12345678
URL: http://192.168.4.1/
```

手机连接热点后打开网页，可以测试前进、后退、横移、旋转。

第一次测试必须把小车架空，不要让轮子落地。

## 硬件需求

- CyberBrick Controller Core x1
- DRV8833 双路电机驱动板 x2
- 6V DC 减速电机 x3
- 6V 电机电源

一块 DRV8833 只能控制两个 DC 电机。三轮小车需要两块 DRV8833。

## 引脚分配

| 轮子 | CyberBrick GPIO | DRV8833 输入 |
|---|---|---|
| W1 左前轮 | GPIO3 / GPIO2 | DRV-A AIN1 / AIN2 |
| W2 右前轮 | GPIO1 / GPIO0 | DRV-A BIN1 / BIN2 |
| W3 后轮 | GPIO21 / GPIO20 | DRV-B AIN1 / AIN2 |

如果某个轮子方向反了，优先改 `main.py` 里的 `MOTOR_SIGN`，不要急着重焊。

## 电机输出

| 轮子 | DRV8833 输出 |
|---|---|
| W1 左前轮 | DRV-A AO1 / AO2 |
| W2 右前轮 | DRV-A BO1 / BO2 |
| W3 后轮 | DRV-B AO1 / AO2 |

DRV-B 的 BO1/BO2 空着备用。

## 电源

| DRV8833 引脚 | 连接 |
|---|---|
| VM | 6V 电机电源正极 |
| GND | 6V 电源负极 + CyberBrick GND |
| STBY | CyberBrick 3V3 |
| NC | 不接 |

必须共地：CyberBrick GND 和 DRV8833 GND 要连在一起。

不要把电机直接接 CyberBrick。

## 上传

如果板子正在跑官方 CyberBrick RC 程序，需要先在串口里按 Ctrl+C 进入 REPL。

备份官方启动文件：

```powershell
mpremote connect COM9 resume fs cp :boot.py backup_boot.py
```

上传本程序：

```powershell
mpremote connect COM9 resume fs cp firmware\cyberbrick_omni_drv8833\main.py :main.py
mpremote connect COM9 resume fs cp firmware\cyberbrick_omni_drv8833\boot.py :boot.py
mpremote connect COM9 resume reset
```

恢复官方启动文件：

```powershell
mpremote connect COM9 resume fs cp backup_boot.py :boot.py
mpremote connect COM9 resume reset
```
