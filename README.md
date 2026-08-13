# No Left Click Rotation

适用于 Windows 版 ZBrush 的鼠标交互插件。

插件用于阻止左键从模型外的空白画布开始拖动时旋转视图，同时保留正常的界面操作、模型雕刻、LightBox 点击与拖动，并允许左键从空白处拖入模型后直接开始雕刻。

当前版本：正式版 v1.0.0（Python 版 + ZScript 版，两版逻辑一致，安装时二选一）。

## 主要功能

- Edit 模式下自动锁定相机，避免左键拖动画布造成视图旋转。
- 右键按下时直接解除相机锁定，右键抬起 2ms 后恢复锁定。
- ZBrush 普通界面上的左键操作完整放行。
- 直接在模型上按下左键时完整放行，正常雕刻。
- 左键从空白画布开始拖动，进入模型后自动补发起笔并开始雕刻。
- 支持 Alt + 左键，使用与普通左键相同的区域判断流程。
- 保留 LightBox 的单击、双击和拖动操作。
- 光标变为 Windows 系统光标（箭头、I 形、手形等）时按原生 UI 放行。
- 起笔延时固定 1ms。

## 版本

### Python 版

- 文件：`NoLeftClickRotation.py`
- 设置面板：`Zplugin > 禁用左键导航`（中文界面：启用、锁定相机、BiliBli、Github）
- 使用 Win32 定时器驱动，不受 ZBrush 脚本调度中断影响。

### ZScript 版

- 文件：`NoLeftClickRotation2022.txt` + `NoLeftClickRotation2022Data/NoLeftClickRotation2022.dll`
- 设置面板：`Zplugin > No Left Click Rotation`（Enable、Camera Lock、Reset Sleep、BiliBli、Github）
- 内置 Sleep 心跳与 F12 watchdog，脚本循环中断时自动恢复。

两版请勿同时安装，避免互相干扰。

## 安装

完全关闭 ZBrush，将所选版本的插件文件复制到当前 ZBrush 版本的用户插件目录：

    %APPDATA%\Maxon\Maxon ZBrush 2026_*\ZStartup\ZPlugs64\

重新启动 ZBrush 后打开 `Zplugin > No Left Click Rotation`，确认「启用 / Enable」已开启。

## 卸载

关闭 ZBrush 后，删除上述目录中的插件文件（Python 版删除 `.py`，ZScript 版删除 `.txt`、`.zsc` 和 `Data` 目录），重新启动 ZBrush。

## 已知限制

- LightBox 不是独立窗口，插件通过光标行为判断 LightBox 区域。
- 空白拖入模型起笔依赖 `PixolPick` 的材质值 `mat`；若光标确实在可雕刻模型表面仍无法起笔，请确认处于 Edit 模式。
- 画布/界面判定依赖隐藏调试项 `Preferences:Utilities:View Window Id`；该路径不可用时仅相机锁定生效。
- 在其他 ZBrush 大版本中，LightBox 光标行为可能发生变化，需要单独验证。
