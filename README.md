# NoLeftClickRotation（禁用左键视图旋转）

ZBrush 2026 纯 Python 插件，用于禁用雕刻时“左键按住空白画布拖动触发视图
旋转”。只有一个 `NoLeftClickRotation.py`，无 .zsc、无 DLL、无环境变量、
无安装程序，随 ZBrush 启动/退出。

## 原理

ZBrush 2026 启动时会自动执行 `ZStartup\ZPlugs64` 下的 `*.py` 文件（官方
Python 插件机制）。插件启动后：

1. 按 Windows 系统 UI 语言在 Zplugin 菜单下创建中/英文界面；
2. 用 ctypes 在本进程内子类化 ZBrush 主窗口；
3. 每次左键按下时调用官方 `zbrush.commands` API（Edit 状态、画布坐标、
   PixolPick 材质索引 0）判断空白画布；命中后点击照常到达 ZBrush，再立即
   补发一次抬起，在旋转开始前取消拖拽；光标进入模型后补发一次按下，
   笔刷从进入点起笔。

界面控件（标准系统光标）与 Ctrl/Shift/Alt 操作不受影响。

## 目录

- `NoLeftClickRotation_Plugin/`：发布包，按《安装说明.txt》手动安装
- `NoLeftClickRotation_Source/`：源码（NoLeftClickRotation.py）
- `ZBrush_Python_SDK_2026_1_0.zip`：官方 Python SDK 参考
- `ZScript-Command-Reference-2022.pdf`：官方 ZScript 命令参考
- `_backup_hybrid_2026-08-09/`、`_backup_old_zsc_2026-08-09/`：历史版本备份

## 构建

无需编译。修改 `NoLeftClickRotation_Source\NoLeftClickRotation.py` 后，
按《安装说明.txt》复制到用户资产目录的 `ZStartup\ZPlugs64` 即可。
