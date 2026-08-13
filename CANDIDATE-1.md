# No Left Click Rotation 候选版 1

状态：候选测试版（RC1）

候选版 1 冻结当前 ZScript + 64 位 DLL 实现，目标版本为不提供 Python API 的 ZBrush 2022 及之后版本。

## 冻结规则

- 插件默认启用，仅在 Edit 模式工作。
- Edit 模式下相机保持锁定；右键按下时解锁，右键松开 2ms 后重新锁定。
- UI 区域完整放行左键。
- 模型判断只使用 `PixolPick` 的 `mat`。
- 左键从空白画布按下时进入等待状态；只有物理左键仍按住时才每 5ms 查询一次 `mat`。
- 检测到 `mat != 0` 后结束等待并补发雕刻起笔；左键松开或手势取消后立即停止查询。
- 空闲、UI 操作和右键拖动期间不轮询 `PixolPick`。
- LightBox 使用左键按下后伪装抬起产生的光标行为进行分类，并保留点击、双击和拖动。
- 起笔延迟范围为 0–10ms，默认 0ms。
- 内部桥使用 F12。插件每次启动都会在当前会话注册，并幂等写入当前版本用户目录的 `ZStartup\\HotKeys\\StartupHotkeys.txt`。
- Ctrl、Alt 或 Shift 按住时，普通桥请求暂停；右键解锁请求会临时释放修饰键、发送纯 F12、恢复修饰键，然后回放带原始修饰键状态的右键按下。

## 安装内容

将候选包中的 `ZPlugs64` 内容复制到当前 ZBrush 用户目录的：

`ZStartup\\ZPlugs64`

安装后完整重启 ZBrush。

## 文件

- `NoLeftClickRotation2022.txt`：ZScript 面板与按需桥。
- `NoLeftClickRotation2022Data\\NoLeftClickRotation2022.dll`：鼠标状态机、相机控制及快捷键持久化。
- `source`：与候选二进制对应的完整源码。

此候选版后续如需修改，应另建候选版，不直接覆盖本快照。
