# RokiCar 当前三文件固件

适用接收板 M1/M2 + 单块 DRV8833。将 boot.py、main.py、rokicar_core.py 三份文件放到设备根目录；boot.py 只做有限初始化，随后由标准 MicroPython 启动流程执行 main.py。电机与灯光逻辑不变，作者确认灯转接板接 D2 正常。

优先交给能够访问本机终端和 USB 串口的 AI：Codex、Claude Code、Trae、WorkBuddy 或 DeepSeek 搭配本地 Agent/Harness。安装 Python 和 mpremote，备份原程序与校准 JSON，上传后逐份回读核对，再硬复位并架空验收。

- [刷写教程](../../../05_docs/用户刷写教程.md)
- [给 AI 的提示词](../../../05_docs/交给AI刷写.txt)
- [简明复刻 PDF](../../../05_docs/RokiCar_复刻指南.pdf)

热点 RokiCar，密码 12345678，App 地址 ws://192.168.4.1/ws。index.html 和旧版说明属于历史学习内容，不作为当前控制网页入口。没有连接实车重新执行本轮刷写。
