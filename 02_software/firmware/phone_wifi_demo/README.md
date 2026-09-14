# CyberBrick Phone WiFi Demo

这个 demo 只测试手机连接链路，不驱动电机。

刷入后 CyberBrick 会创建热点：

```text
WiFi: OmniCar-Demo
Password: 12345678
URL: http://192.168.4.1/
```

手机连接热点后打开网页，点击按钮时板载灯会闪一下，页面会显示收到的 `vx / vy / rot`。

## 上传

先关闭 CyberBrick 客户端，否则串口可能被占用。

查看可用串口：

```powershell
Get-PnpDevice -Class Ports
```

上传到指定串口，例如 `COM9`：

```powershell
.\firmware\phone_wifi_demo\upload.ps1 -Port COM9
```

如果要恢复官方 CyberBrick 程序，需要重新用 CyberBrick 官方客户端或官方固件流程刷回。
