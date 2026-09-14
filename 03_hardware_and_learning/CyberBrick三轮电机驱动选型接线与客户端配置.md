# CyberBrick 三轮电机驱动选型、接线与客户端配置

日期：2026-07-05

## 1. 最终推荐

买两个 `DRV8833 双路直流电机驱动模块`。

原因：

- 一个 DRV8833 模块可以驱动 2 个 DC 电机。
- 两个模块一共 4 路，用其中 3 路，剩 1 路备用。
- 模块很小，容易塞进 135 mm 轮心圆底盘。
- 支持 3.3 V 逻辑，适合 CyberBrick 核心板的 ESP32-C3。
- 电机电压覆盖 6 V 小减速电机场景。
- 比 L298N 小很多，效率也高很多。

搜索关键词：

```text
DRV8833 双路电机驱动模块
DRV8833 2路 直流电机驱动板 3V 10V
DRV8833 dual motor driver module
```

不要买：

- L298N：太大、压降大、发热，低压小车不划算。
- L9110S：便宜但余量小，不适合你后面 700-800 g 负载。
- 只写“电机驱动板”但没写芯片和电流参数的杂板。

## 2. 备选方案

如果你想一块板解决，也可以买 `四路 TB6612FNG 直流电机驱动板`。

搜索关键词：

```text
四路 TB6612FNG 直流电机驱动板
TB6612 四路电机驱动模块
Quad Motor Driver TB6612FNG
```

优点是一块板更整洁。缺点是板子更大，线也不一定少；很多四路板是 Arduino Shield 形式，不适合直接塞进你现在这个紧凑底盘。

所以第一版还是推荐：`DRV8833 x2`。

## 3. 重要参数

按官方和常见模块资料：

| 驱动 | 路数 | 电机电压 | 单路电流 | 适合本项目 |
|---|---:|---:|---:|---|
| DRV8833 双路模块 | 2 | 约 2.7-10.8 V | 约 1.2-1.5 A 连续，2 A 左右峰值 | 推荐 |
| TB6612FNG 双路模块 | 2 | 约 2.5-13.5 V | 约 1.2 A 连续，3.2 A 峰值 | 可用 |
| 四路 TB6612FNG 板 | 4 | 约 2.5-13.5 V | 约 1.2 A 连续 | 可用但偏大 |
| L298N | 2 | 高压范围大 | 发热大、压降大 | 不推荐 |

你买电机时要看堵转电流。如果单电机堵转电流明显超过 1.5-2 A，就不要用小 DRV8833，得换更大电流的驱动。

## 4. 接线总原则

三件事必须记住：

1. 电机不能直接接 CyberBrick 核心板。
2. 电机电源和 CyberBrick 供电可以分开，但 GND 必须共地。
3. 先只接一个电机测试，确认方向和发热，再接三个。

推荐供电：

```text
2S 电池 7.4 V
  |
  +-- 6 V 降压模块 --> DRV8833 VM / 电机电源
  |
  +-- CyberBrick 官方供电 / 5 V 稳压

CyberBrick GND 必须连接 DRV8833 GND
```

## 5. DRV8833 x2 接线表

这里假设两个 DRV8833 模块分别叫 `DRV-A` 和 `DRV-B`。

### 电机输出

| 轮子 | 驱动模块 | 输出端 |
|---|---|---|
| W1 左前轮 | DRV-A | AOUT1 / AOUT2 |
| W2 右前轮 | DRV-A | BOUT1 / BOUT2 |
| W3 后轮 | DRV-B | AOUT1 / AOUT2 |
| 备用 | DRV-B | BOUT1 / BOUT2 空着 |

如果轮子方向反了，优先在程序里改符号；也可以交换该电机的两根输出线。

### 电源

| DRV8833 引脚 | 接哪里 |
|---|---|
| VM / VIN / Motor V+ | 6 V 电机电源正极 |
| GND | 电机电源负极 + CyberBrick GND |
| VCC | 如果模块有 VCC，接 CyberBrick 3V3 |
| SLEEP / nSLEEP | 如果模块有这个脚，接 3V3 拉高 |

不同商家的 DRV8833 模块命名不完全一样。只要认准：电机电源、地、输入脚、输出脚。

## 6. CyberBrick 到 DRV8833 的信号线

第一版建议用 6 根控制线，每个电机 2 根：

| 轮子 | DRV8833 输入 | CyberBrick 建议 GPIO | 物理取线建议 |
|---|---|---:|---|
| W1 左前轮 | IN1 | GPIO3 | 接收板 S1 信号脚或核心板焊盘 |
| W1 左前轮 | IN2 | GPIO2 | 接收板 S2 信号脚或核心板焊盘 |
| W2 右前轮 | IN1 | GPIO1 | 接收板 S3 信号脚或核心板焊盘 |
| W2 右前轮 | IN2 | GPIO0 | 接收板 S4 信号脚或核心板焊盘 |
| W3 后轮 | IN1 | GPIO21 | 核心板右侧焊盘 |
| W3 后轮 | IN2 | GPIO20 | 核心板右侧焊盘 |

注意：

- 如果使用 S1-S4 的信号脚，就不要在 CyberBrick 客户端里把 S1-S4 配置成舵机。
- S1-S4 的 V 脚不要接到 DRV8833 的 VM。DRV8833 的 VM 要接 6 V 电机电源。
- GPIO20/GPIO21 是串口相关脚。如果后面发现调试串口冲突，可以把 W3 改到 GPIO4/GPIO5，但那会和官方 M1 电机控制脚重叠，需要实测。
- GPIO8 是板载 RGB LED，GPIO9 是用户按键，不建议拿来驱动电机。

## 7. CyberBrick 客户端怎么配置

### 7.1 先做官方链路验证

先不要接外部驱动板。

在 CyberBrick 客户端里：

1. 新建项目。
2. 添加/配对发射端核心板。
3. 添加/配对接收端核心板。
4. 发射端添加摇杆模块。
5. 接收端先用官方 M1/M2 接两个电机做测试。
6. 确认摇杆能控制两个电机正反转。

这一步只证明 CyberBrick 发射、接收、供电、电机口都正常。

### 7.2 外部三路驱动时的配置

最终三轮全向底盘时：

- 接收端不要再把 M1/M2 当正式驱动。
- S1-S4 如果被我们拿来当 GPIO，就不要配置成舵机。
- 在接收端添加 `Code`，用于测试外部 GPIO 和驱动板。

客户端大致流程：

1. 进入你的项目。
2. 选择接收端 Receiver。
3. 找到 `Code` 或代码模块。
4. 点击 `Add` 新增代码片段。
5. 粘贴测试代码。
6. 给发射端按钮添加事件。
7. 事件动作选择 `Code`，选择刚才的代码片段。
8. 保存并发送配置到设备。
9. 按按钮触发测试。

## 8. 客户端 Code 测试片段

下面这段只用于测试外部驱动板，不是最终摇杆控制。

先把小车架空，轮子不要碰桌面。

```python
from machine import Pin, PWM
import uasyncio as asyncio

FREQ = 1000
MAX_DUTY = 65535

W1A = PWM(Pin(3), freq=FREQ)
W1B = PWM(Pin(2), freq=FREQ)
W2A = PWM(Pin(1), freq=FREQ)
W2B = PWM(Pin(0), freq=FREQ)
W3A = PWM(Pin(21), freq=FREQ)
W3B = PWM(Pin(20), freq=FREQ)

def duty(x):
    x = max(0, min(1, abs(x)))
    return int(MAX_DUTY * x)

def set_pair(a, b, speed):
    if speed > 0:
        a.duty_u16(duty(speed))
        b.duty_u16(0)
    elif speed < 0:
        a.duty_u16(0)
        b.duty_u16(duty(speed))
    else:
        a.duty_u16(0)
        b.duty_u16(0)

def stop_all():
    set_pair(W1A, W1B, 0)
    set_pair(W2A, W2B, 0)
    set_pair(W3A, W3B, 0)

set_pair(W1A, W1B, 0.35)
set_pair(W2A, W2B, 0)
set_pair(W3A, W3B, 0)
await asyncio.sleep(1.5)
stop_all()
```

测试顺序：

1. 改代码，只让 W1 转。
2. 改代码，只让 W2 转。
3. 改代码，只让 W3 转。
4. 每个轮子都能正反转后，再做混控。

## 9. 为什么客户端 Code 不能直接完成最终摇杆混控

我看了 CyberBrick 官方 RC 代码。官方 `MotorsController` 只封装了 M1/M2 两个电机；客户端的 Code 片段可以触发运行代码，但默认执行环境没有直接把实时摇杆 `remote_data` 暴露给代码片段。

所以：

- Code 片段适合做外部驱动板测试、固定动作、启动/停止脚本。
- 真正的三轮全向连续摇杆控制，最好做成接收端自定义 MicroPython 程序，或者修改官方 `app_rc` 里的控制逻辑。

这不是坏事。我们仍然先用客户端完成配对、摇杆校准和硬件验证，然后进入自定义代码阶段。

## 10. 最终三轮混控逻辑

等三个电机都测试通过后，最终代码要做：

```python
w1 = -0.5 * vx - 0.866 * vy + rot_gain * rot
w2 = -0.5 * vx + 0.866 * vy + rot_gain * rot
w3 =  1.0 * vx               + rot_gain * rot
```

然后归一化限幅：

```python
scale = max(1, abs(w1), abs(w2), abs(w3))
w1 /= scale
w2 /= scale
w3 /= scale
```

最后分别输出到三个 DRV8833 通道。

## 11. 我的下一步建议

现在按这个顺序做：

1. 买 `DRV8833 双路电机驱动模块 x2`。
2. 先只接 W1 一个电机。
3. 用客户端 Code 片段测试 W1 正反转。
4. 再接 W2、W3。
5. 三个轮子单独测试都通过后，再写真正的三轮混控程序。

不要一开始就把三个电机、手机、舵机、电池全接上。先让一个轮子听话，整车就稳了一半。

## 12. 参考资料

- DRV8833 官方数据手册：<https://www.ti.com/lit/gpn/DRV8833>
- Pololu DRV8833 双路驱动说明：<https://www.pololu.com/product/2130>
- SparkFun TB6612FNG 接线指南：<https://learn.sparkfun.com/tutorials/tb6612fng-hookup-guide/all>
- DFRobot 四路 TB6612FNG 驱动板：<https://wiki.dfrobot.com.cn/_SKU_DRI0039_Quad_Motor_Driver_Shield_for_Arduino%E5%9B%9B%E8%B7%AF%E7%9B%B4%E6%B5%81%E7%94%B5%E6%9C%BA%E9%A9%B1%E5%8A%A8%E6%89%A9%E5%B1%95%E6%9D%BF>
- CyberBrick 官方控制核心源码：<https://github.com/CyberBrick-Official/CyberBrick_Controller_Core>
- CyberBrick MotorsController API：<https://makerworld.com/en/cyberbrick/api-doc/cyberbrick_core/lib/MotorController.html>
