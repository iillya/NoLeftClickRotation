Python IAT 版备份（2026-08-09）
==============================
本目录备份的是“纯 Python + IAT 钩子”实现，功能与后续 ZScript+DLL 版一致：
- 空白画布：左键旋转、Alt+左键平移均禁用；
- 模型上：原样雕刻；Ctrl+左键框选遮罩保留；
- 核心机制：进程内把 ZBrush.exe 导入表的 GetAsyncKeyState 指向机器码存根，
  光标在空白画布时对 VK_LBUTTON 返回 0，模型上返回真实状态；
  窗口子类处理起笔/收笔状态机。

文件说明
--------
- NoLeftClickRotation.py         ：源码（与安装版相同）
- NoLeftClickRotation_Plugin.py  ：发布目录副本
- 安装说明.txt                   ：发布说明
- NoLeftClickRotation_2026.1_Plugin.zip ：发布压缩包

安装版位于 ZStartup\ZPlugs64\NoLeftClickRotation.py（config.txt 保留）。
