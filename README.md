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

相机锁定后，右键导航同样会失效。插件在 ZBrush 主窗口的右键事件中调整锁定状态：

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

右键双击的第二次按下也按此顺序处理。正常按下、抬起没有人为延迟，也不模拟鼠标消息。每条原生输入消息只交给 ZBrush 一次，插件处理出错时也不会重复转发。

切换到其他程序、手势取消或鼠标捕获意外丢失后，插件通过后续定时检测恢复锁定，避免在 ZBrush 尚未完成原生事件处理时调用相机 API。

### Edit 模式检测

插件启用时，每 100ms 读取一次 `Transform:Edit` 状态；右键按下和抬起时也会读取，避免使用过期状态：

- 进入 Edit 模式：锁定相机。
- 退出 Edit 模式：解除相机锁定。
- 插件关闭：解除相机锁定并停止定时器。

状态未改变时，不重复写入相机开关。设置失败会保留待重试状态，在后续检测中重试。

正常情况下不轮询鼠标按键。仅在右键手势期间发生捕获转移后，临时检查按键是否已经松开，以处理抬起事件被其他窗口接收的情况；同时遵循 Windows 的左右键互换设置。

## 输入处理范围

插件仅在 ZBrush 主窗口上安装 Windows 窗口子类，用来接收：

- `WM_RBUTTONDOWN`
- `WM_RBUTTONUP`
- `WM_RBUTTONDBLCLK`
- `WM_CANCELMODE`
- `WM_CAPTURECHANGED`、`WM_ACTIVATEAPP`、`WM_MOUSEMOVE`，用于异常手势恢复。
- 本插件的 `WM_TIMER`，用于状态检测；其他定时器消息原样转发。
- `WM_NCDESTROY`，用于清理定时器和窗口子类。

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

如果右键事件钩子或定时器无法安装，插件会解除相机锁定并禁用“启用”开关；两个链接按钮仍然可以使用。

更新脚本时请退出并重新启动 ZBrush。脚本重复加载前会尝试清理旧实例；如果旧实例正在处理窗口事件或无法安全清理，会拒绝替换，保留原有回调引用。

## 兼容性

插件不依赖 ZBrush 内部地址、机器码签名或特定内存偏移。只要 Windows 版 ZBrush 满足以下条件，原则上即可运行：

- 支持 ZBrush Python API。
- 主窗口类名为 `ZBrush`。
- 存在 `Transform:Edit`。
- 存在 `Draw:Lock Camera`。
- Windows 支持 `SetWindowSubclass`。
- 插件在 ZBrush 主窗口所属线程中执行；跨线程时不会安装窗口子类。

目标环境为 Windows 版 ZBrush 2026。其他版本，以及不同鼠标、数位板驱动的实际行为，需要在对应环境中验证。

## 开发验证

在项目目录使用 Windows Python 运行：

```powershell
python -B -m unittest discover -s tests -v
```

测试使用模拟的 ZBrush API 和 Windows 接口，检查事件转发顺序、状态恢复、资源清理及闲置调用次数，不安装真实钩子、不操作鼠标。这些测试不能替代 ZBrush 内的实际使用验证。

## 卸载

1. 完全退出 ZBrush。
2. 删除：

   ```text
   ZStartup\ZPlugs64\NoLeftClickRotation.py
   ```

3. 重新启动 ZBrush。

## 版本

v2.1.0
