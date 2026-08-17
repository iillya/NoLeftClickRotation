# 右键解锁相机（Right Click Camera Unlock）

适用于 Windows 版 ZBrush 2026 的轻量 Python 插件。

插件在 Edit 模式下锁定相机；按住右键时临时解除相机锁定，松开右键后重新锁定。

## 功能

- 启用且处于 Edit 模式时锁定相机。
- 按住右键时临时解除相机锁定。
- 松开右键后重新锁定相机。
- 关闭插件或退出 Edit 模式时解除相机锁定。
- 保留哔哩哔哩和 GitHub 跳转按钮。

插件不会处理左键，也不会拦截或模拟任何鼠标消息。它只在 ZBrush 主窗口上安装一个窗口子类，用于接收右键按下和抬起事件；不安装 `SetCursor` 监视或全局鼠标钩子。

## 安装

1. 完全退出 ZBrush。
2. 将 `NoLeftClickRotation.py` 复制到：

   ```text
   %APPDATA%\Maxon\Maxon ZBrush 2026_*\ZStartup\ZPlugs64\
   ```

3. 重新启动 ZBrush。
4. 打开 `Zplugin > 右键解锁相机`。

## 插件面板

- **启用**：开启或关闭相机锁定功能。
- **哔哩哔哩**：打开作者的哔哩哔哩主页。
- **GitHub**：打开项目主页。

## 工作方式

右键按下事件会在交给 ZBrush 前解除 `Draw:Lock Camera`；右键抬起事件先由 ZBrush 完成处理，随后重新锁定相机。插件另用一个 100ms 定时器检查 Edit 模式变化，不使用定时器读取鼠标按键。

## 卸载

1. 完全退出 ZBrush。
2. 删除 `ZStartup\ZPlugs64\NoLeftClickRotation.py`。
3. 重新启动 ZBrush。

## 版本

v2.1.0
