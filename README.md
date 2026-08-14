# No Left Click Rotation（禁用左键导航）

适用于 Windows 版 ZBrush 2026 的 Python 鼠标交互插件。

## 简介

在 ZBrush 编辑模式下，左键从模型外的空白画布开始拖动会旋转视图。本插件锁定相机以阻止这一行为，同时保留正常的界面操作、模型雕刻、LightBox 点击与拖动，并支持左键从空白画布拖入模型后直接开始雕刻。插件只改变视图交互，不修改模型数据。

## 功能

- 编辑模式下自动锁定相机，左键在空白画布拖动不再旋转视图。
- 右键按下时解除相机锁定，松开后延迟 2ms 重新锁定。
- 界面按钮、菜单、滑块等控件上的左键操作原样放行。
- LightBox 的单击、双击、拖动原样放行。
- 模型上按下左键正常雕刻。
- 左键从空白画布开始拖动、进入模型后自动补发起笔（固定 1ms 延时）。
- Alt + 左键与普通左键使用相同的区域判断流程；Ctrl + 左键保留 ZBrush 原生画布手势。
- 光标变为 Windows 系统光标（箭头、I 形、手形等）时按原生界面放行。

## 文件

插件为单文件：

```text
NoLeftClickRotation.py
```

## 安装

1. 完全退出 ZBrush 2026。
2. 将 `NoLeftClickRotation.py` 复制到当前用户的 ZBrush 插件目录：

   ```text
   %APPDATA%\Maxon\Maxon ZBrush 2026_*\ZStartup\ZPlugs64\
   ```

3. 重新启动 ZBrush 2026。
4. 打开 `Zplugin > 禁用左键导航` 面板，确认「启用」已开启。

## 卸载

完全退出 ZBrush 2026，删除 `ZPlugs64\NoLeftClickRotation.py`，重新启动。

## 面板

- **启用**：插件总开关，默认开启。
- **仅锁定相机**：勾选后左键不做任何处理、完全放行；仅保留锁定相机与右键解锁/重锁。默认不勾选。

## 工作原理

插件基于 ZBrush 官方 Python API（`zbrush.commands`）读写相机、编辑模式与材质，并借助 Windows 的窗口子类化拦截鼠标消息、用 `SetTimer` 定时器轮询、用 `SetCursor` 导入表钩子判断光标类型。整个过程不依赖 ZBrush 脚本循环。

## 已知限制

- LightBox 不是独立窗口，ZBrush 也没有公开其持续打开状态，插件通过光标行为进行判断；其他 ZBrush 大版本的光标行为可能变化，需单独验证。
- 空白拖入模型的起笔判定依赖 `PixolPick` 的材质值 `mat`，请确认处于编辑模式。
- 画布与界面判定依赖隐藏调试项 `Preferences:Utilities:View Window Id`；该路径不可用时，仅相机锁定生效。
- 起笔延时固定为 1ms，不受设置影响。
- 若 ZBrush 升级后不再从 USER32 导入 `SetCursor`，光标钩子会静默失效，插件整体降级为不拦截输入并保持相机解锁。

## 版本

v1.0.0
