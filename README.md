# 禁用 ZBrush 左键导航

适用于 Windows 版 ZBrush 的轻量 Python 插件。

插件会在 Edit 模式下自动启用 ZBrush 的相机锁定，从而禁止左键在空白画布上旋转视角；按住右键时临时解除相机锁定，仍可正常使用右键旋转视角。

## 功能

- 在 Edit 模式下自动锁定相机。
- 禁止左键拖动空白画布时旋转视角。
- 不拦截、不修改也不模拟左键消息。
- 右键按下时立即解除相机锁定。
- 右键抬起后立即重新锁定相机。
- 关闭插件或退出 Edit 模式时解除相机锁定。
- 提供哔哩哔哩和 GitHub 跳转按钮。

## 工作原理

### 禁用左键导航

ZBrush 的 `Draw:Lock Camera` 开启后，相机不会响应画布导航操作。插件在启用且处于 Edit 模式时，通过 ZBrush Python API 开启此选项。

因此，插件并不是通过拦截左键来禁止导航，而是直接锁定相机：

```text
进入 Edit 模式
    ↓
开启 Draw:Lock Camera
    ↓
左键画布导航失效
```

左键消息始终由 ZBrush 原样处理。插件不会判断光标位置，不使用 `PixolPick`，也不会发送模拟的左键按下、移动或抬起消息。

### 保留右键导航

相机锁定后，右键导航同样会失效。为了保留右键旋转，插件只监听 ZBrush 主窗口的两个右键事件：

```text
WM_RBUTTONDOWN
    ↓
先解除相机锁定
    ↓
再把右键按下事件交给 ZBrush

WM_RBUTTONUP
    ↓
先让 ZBrush 完成右键抬起处理
    ↓
再重新锁定相机
```

右键处理没有人为延迟，也不模拟任何鼠标消息。

### Edit 模式检测

插件每 100ms 读取一次 `Transform:Edit` 状态：

- 进入 Edit 模式：锁定相机。
- 退出 Edit 模式：解除相机锁定。
- 插件关闭：解除相机锁定。

该定时器只检查 Edit 模式，不轮询鼠标按键。右键按下和抬起均由窗口事件直接触发。

## 输入处理范围

插件仅在 ZBrush 主窗口上安装 Windows 窗口子类，用来接收：

- `WM_RBUTTONDOWN`
- `WM_RBUTTONUP`
- `WM_CANCELMODE`

插件不会：

- 处理任何左键消息。
- 拦截或吞掉任何鼠标消息。
- 模拟鼠标按键或移动。
- 安装全局鼠标钩子。
- 修改 `SetCursor` 导入表。
- 访问 ZBrush 内部内存。
- 查询画布、模型或 LightBox 状态。

## 安装

1. 完全退出 ZBrush。
2. 将 `NoLeftClickRotation.py` 复制到当前 ZBrush 用户插件目录：

   ```text
   %APPDATA%\Maxon\Maxon ZBrush 2026_*\ZStartup\ZPlugs64\
   ```

3. 重新启动 ZBrush。
4. 打开 `Zplugin > 禁用左键导航`。
5. 确认“启用”处于开启状态。

## 使用方法

- 左键拖动空白画布：相机保持锁定，不会旋转。
- 右键按住并拖动：临时解除锁定，正常旋转视角。
- 松开右键：恢复相机锁定。
- 需要恢复 ZBrush 默认导航时：关闭“启用”。

## 插件面板

- **启用**：开启或关闭相机锁定功能。
- **哔哩哔哩**：打开作者的哔哩哔哩主页。
- **GitHub**：打开项目主页。

如果右键事件钩子无法安装，插件会解除相机锁定并禁用“启用”开关；两个链接按钮仍然可以使用。

## 兼容性

插件不依赖 ZBrush 内部地址、机器码签名或特定内存偏移。只要 Windows 版 ZBrush 满足以下条件，原则上即可运行：

- 支持 ZBrush Python API。
- 主窗口类名为 `ZBrush`。
- 存在 `Transform:Edit`。
- 存在 `Draw:Lock Camera`。
- Windows 支持 `SetWindowSubclass`。

当前版本以 ZBrush 2026 为主要测试环境，其他版本需要实际测试确认。

## 卸载

1. 完全退出 ZBrush。
2. 删除：

   ```text
   ZStartup\ZPlugs64\NoLeftClickRotation.py
   ```

3. 重新启动 ZBrush。

## 版本

v2.1.0
