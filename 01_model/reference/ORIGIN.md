# 输入与参照资产来源

- `original_shell.step`：用户提供的终版 `车体.STEP`，原始输入未修改；它是本次外观改型的建模依据。
- `render_context/original_0.stl`：用户提供装配体中的底壳。
- `render_context/original_1.stl`、`original_2.stl`、`original_3.stl`：用户提供装配体中的三个全向轮组。
- `render_context/original_14.stl`：用户提供装配体中的灯窗组件。

参照网格由用户提供的 `全部装配体.STEP` 提取，转换到原车壳坐标后仅用于展示。它们不是此次新设计的轮子、电子件或底盘，未核实各自第三方许可。正式公开这些文件前，由项目所有者确认再分发条件；可以单独移除 `render_context`，核心 CAD 建模仍可进行，但整车预览需要另行提供参照。

没有附带用户原项目的固件、APP、账号数据、个人配置或整个历史版本目录。
