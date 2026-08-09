NoLeftClickRotation（禁用左键视图旋转）
========================================

版本支持
--------
- ZBrush 2026.0 / 2026.1（精确模式）：
  使用官方 Python API（zbrush.commands）。仅在 Edit 模式且按下点为空白画布
  （PixolPick 材质索引 0）时取消左键拖动旋转；界面控件、Ctrl/Shift/Alt 操作
  完全不受影响；启动即生效，无需校准。
- ZBrush 2022 - 2025（兼容模式）：
  这些版本没有官方 Python API。插件以官方 ZPlugin（.zsc + DLL）格式加载。
  判定优先使用文档化的 ZScript 事件循环：用 [Sleep] 在鼠标移动/左键按下时
  唤醒，以 IGet Transform:Edit + MouseHPos/VPos + PixolPick 精确计算“Edit
  模式 + 空白画布”，再把状态经 UpdateState 推给 DLL。
  受 ZBrush“同一时间只能运行一个 ZScript”的限制，如果用户运行了其他插件或
  宏，事件循环会被打断；此时 DLL 自动退回 F2 光标校准（把鼠标移到空白画布
  按一次 F2，结果保存在 config.txt），保证功能不静默失效。

文件
----
NoLeftClickRotation.zsc           官方编译插件（2026 编译版；旧版请重新编译）
NoLeftClickRotationData\
  NoLeftClickRotation.dll         进程内钩子（随 ZBrush 启动/退出）
  init.py                         Python 界面与画布判定（2026+）
  NoLeftClickRotation.txt         ZScript 源码（旧版重新编译用）
  config.txt                      启用状态与 F2 校准数据

旧版（2022-2025）重新编译 .zsc
------------------------------
.zsc 是版本相关编译产物，2026 编译的 .zsc 不保证能在旧版加载，请在目标版本
重新编译：
1. 备份该版本 ZData\ZScripts\DefaultZScript.txt 和 DefaultZScript.zsc；
2. 把 NoLeftClickRotation.txt 复制为 DefaultZScript.txt，并删除
   DefaultZScript.zsc；
3. 启动一次 ZBrush，等生成新的 DefaultZScript.zsc 后退出；
4. 把生成的 DefaultZScript.zsc 复制为 NoLeftClickRotation.zsc；
5. 恢复原来的 DefaultZScript.txt / .zsc；
6. 按安装说明安装。

也可以打开 ZScript 面板，用 Load 加载 NoLeftClickRotation.txt，ZBrush 会
在相同目录自动生成 NoLeftClickRotation.zsc。
