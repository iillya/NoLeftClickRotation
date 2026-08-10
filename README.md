# NoLeftClickRotation（禁用左键视图旋转）

ZBrush 2026 纯 Python 插件，用于禁用“左键按住空白画布拖动触发视图旋转”，
同时保留雕刻、UI 交互与 Ctrl+左键框选遮罩。只有一个 `NoLeftClickRotation.py`，
无 .zsc、无 DLL、无环境变量、无安装程序，随 ZBrush 启动/退出。

## 原理

插件基于 ZBrush 官方 `Draw:Lock Camera`（锁定摄像机）命令，配合一个
窗口子类实现：

- **相机锁常开**：插件启用期间持续保持“锁定摄像机”开启（`zbc.set(
  "Draw:Lock Camera"`，状态不一致时用官方 `toggle`，等价于手动点击，
  会同步更新相机的锁定参考点），视图旋转/平移/缩放全部由 ZBrush 自己
  锁住。左键拖空白画布不再旋转，Alt+左键不再平移。
- **右键临时解锁**：右键按住时立刻关闭相机锁（`WM_RBUTTONDOWN` 即时
  处理，50ms 定时器兜底），右键拖动画布照常旋转；松开右键后延迟约
  250ms 再恢复锁定——ZBrush 在松开瞬间仍认为旋转手势未结束，立即锁定
  会触发官方“旋转中锁定即回弹”行为。
- **模型起笔桥接**：ZBrush 原生“空白按下拖到模型”不会起笔（笔画由物理
  按键轮询驱动）。插件不吞任何消息：空白按下原样放行，期间 IAT 钩
  GetAsyncKeyState 对 VK_LBUTTON 返回 0；光标进入模型后先补发一次抬起
  清掉空白处的手势状态，再恢复真实按键并补发一次 `WM_LBUTTONDOWN`，
  笔刷从进入点正常起笔，之后移动/抬起原样放行。

不吞任何消息，界面按钮、滑块全部由 ZBrush 原生处理。GetAsyncKeyState
钩只在“空白按下等待进入模型”阶段对左键生效，其余时刻一律透传真实按键
状态。Ctrl+左键框选遮罩是文档操作，相机锁下照常工作。

## 目录

- `NoLeftClickRotation.py`：插件源码（本文件即发布物）
- `_archive/`：历史版本备份
- `_tools/`：开发期诊断脚本
- `ZBrush_Python_SDK_2026_1_0.zip`：官方 Python SDK 参考
- `ZScript-Command-Reference-2022.pdf`：官方 ZScript 命令参考

## 安装

把 `NoLeftClickRotation.py` 复制到用户资产目录：

```
%APPDATA%\Maxon\Maxon ZBrush 2026_XXXX\ZStartup\ZPlugs64\
```

重启 ZBrush 即生效。开关位于 Zplugin 菜单的“禁用左键视图旋转”，
界面文字随 Windows 系统语言自动切换中/英文。
