# No Left Click Rotation（禁用左键导航）

适用于 Windows 版 ZBrush 的鼠标交互插件，正式版 v1.0.0。

## 简介

在 ZBrush 编辑模式下，左键从模型外的空白画布开始拖动会旋转视图。本插件锁定相机以阻止这一行为，同时保留正常的界面操作、模型雕刻、LightBox 点击与拖动，并支持左键从空白画布拖入模型后直接开始雕刻。

## 主要功能

- 编辑模式下自动锁定相机，左键拖动空白画布不再旋转视图。
- 右键按下时解除相机锁定；ZScript 版在右键回放结束后立即恢复锁定，Python 版保留 2ms 宽限。
- 普通界面（按钮、菜单、滑块等）上的左键操作原样放行。
- 直接在模型上按下左键时完整放行，正常雕刻。
- 左键从空白画布开始拖动，进入模型后自动补发起笔（固定 1ms 延时）。
- 支持 Alt + 左键，与普通左键使用相同的区域判断流程。
- Ctrl + 左键保留 ZBrush 原生画布手势，不进入空白画布桥接流程。
- 保留 LightBox 的单击、双击和拖动操作。
- 光标变为 Windows 系统光标（箭头、I 形、手形等）时按原生界面放行。

## 版本说明

插件提供 Python 版与 ZScript 版两个实现，功能与逻辑一致，**安装时二选一，请勿同时安装**。

### Python 版

- 插件文件：`NoLeftClickRotation.py`
- 设置面板：`Zplugin > 禁用左键导航`
- 界面语言：根据 Windows 系统界面语言自动选择简体中文或英文，其他语言回退英文；中英文控件提示与 ZScript 版一致。
- 使用 Win32 定时器驱动，不受 ZBrush 脚本调度中断的影响。

### ZScript 版

- 插件文件：`NoLeftClickRotation.txt` 与 `NoLeftClickRotationData/NoLeftClickRotation.dll`
- 设置面板：中文为 `Zplugin > 禁用左键导航`，英文为 `Zplugin > No Left Click Rotation`
- 界面语言：自动跟随 ZBrush 当前界面语言（ZBrush 默认跟随系统语言）；已提供简体中文与英文，其他语言回退英文；中英文控件提示与 Python 版一致。
- 内置 Sleep 心跳与 F12 看门狗，脚本循环中断时自动恢复。

## 安装方法

1. 完全关闭 ZBrush。
2. 将所选版本的插件文件复制到当前 ZBrush 版本的用户插件目录：

   `%APPDATA%\Maxon\Maxon ZBrush 2026_*\ZStartup\ZPlugs64\`

   - Python 版：复制 `NoLeftClickRotation.py`。
   - ZScript 版：复制 `NoLeftClickRotation.txt` 与整个 `NoLeftClickRotationData` 文件夹。

3. 重新启动 ZBrush。
4. 打开对应的设置面板，确认「启用 / Enable」已开启。

## 卸载方法

1. 完全关闭 ZBrush。
2. 删除上述插件目录中的插件文件：
   - Python 版：删除 `NoLeftClickRotation.py`。
   - ZScript 版：删除 `NoLeftClickRotation.txt`、`NoLeftClickRotation.zsc` 与 `NoLeftClickRotationData` 文件夹。
3. 重新启动 ZBrush。

## 已知限制

- LightBox 不是独立窗口，ZBrush 也没有公开其持续打开状态，插件通过光标行为进行判断。
- 空白拖入模型的起笔判定依赖 `PixolPick` 的材质值 `mat`；若光标确实位于可雕刻表面仍无法起笔，请确认处于编辑模式。
- 画布与界面判定依赖隐藏调试项 `Preferences:Utilities:View Window Id`；该路径不可用时，仅相机锁定生效（空白拖入起笔与 LightBox 判定不会启用）。
- 在其他 ZBrush 大版本中，LightBox 光标行为可能发生变化，需要单独验证。
- 起笔延时固定为 1ms，不受用户设置影响。
