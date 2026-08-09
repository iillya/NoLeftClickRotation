# NoLeftClickRotation（禁用左键视图旋转）— ZScript + DLL 版

纯 Win32 实现，无 Python。结构参照官方 MiddleButton 插件：

- `NoLeftClickRotation.zscript.txt`：ZScript（编译为 `.zsc` 后安装）。
  负责官方界面（开关）与画布状态检测循环：
  事件掩码 15（定时器|鼠标移动|左键按下|左键抬起），移动 >=4px 或按键
  事件时才做 `[PixolPick, 5, ...]` 并推送给 DLL；
- `NoLeftClickRotation.c`：DLL 源码。负责全部输入拦截：
  - IAT 钩子：把 ZBrush.exe 导入表的 `GetAsyncKeyState` 指向机器码存根，
    空白画布上对 VK_LBUTTON 返回 0（旋转/Alt 平移无从触发），模型上返回
    真实状态；
  - 窗口子类：起笔/收笔状态机（空白按下吞掉、进入模型补发按下、模型按下
    原样放行、Ctrl 框选遮罩保留）。

## 构建 DLL

1. 安装 VS2022 Build Tools（含“使用 C++ 的桌面开发”）；
2. 运行 `build_dll.cmd`，生成 `NoLeftClickRotation.dll`。

## 编译 .zsc 并安装

1. 完全关闭 ZBrush；
2. 把 `NoLeftClickRotation.zscript.txt` 编译为 `.zsc`：
   - 方式 A（ZScript 面板）：启动 ZBrush，ZScript 面板 Load 该 .txt 后
     Save/Export 为 .zsc；
   - 方式 B（DefaultZScript 法，旧版文档化方法）：备份
     `ZData\ZScripts\DefaultZScript.txt` 与 `.zsc`，用本 .txt 覆盖
     DefaultZScript.txt 并删除其 .zsc，启动一次 ZBrush 生成新的
     DefaultZScript.zsc 后退出，复制为 NoLeftClickRotation.zsc，再恢复
     原 DefaultZScript；
3. 把 `.zsc` 与 `NoLeftClickRotationData\NoLeftClickRotation.dll` 放入
   `ZStartup\ZPlugs64`，最终结构：
   ```
   ZStartup\ZPlugs64\NoLeftClickRotation.zsc
   ZStartup\ZPlugs64\NoLeftClickRotationData\NoLeftClickRotation.dll
   ```
4. 重启 ZBrush，Z插件 菜单中打开开关（默认启用）。

首次运行会在 `NoLeftClickRotationData` 下自动生成 `config.txt`（1=启用）。
卸载 = 关闭 ZBrush 后删除上述两个文件（含 config.txt）。

## 说明

- 检测循环受 ZBrush“同一时间只运行一个 ZScript”的平台限制：被其他插件/
  宏打断时，DLL 按最近一次推送的状态降级（空白=屏蔽、模型=放行），
  不再需要旧版的 F2 手动校准；
- 仅支持 ZBrush 2026（依赖官方 Python API 的部分已移除，本版完全不用
  Python，兼容面更广，但以 2026 实测为准）。
