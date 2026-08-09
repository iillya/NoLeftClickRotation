# NoLeftClickRotation（禁用左键视图旋转）

ZBrush 官方格式插件（.zsc + DLL + 数据目录），用于禁用雕刻时“左键按住空白
画布拖动触发视图旋转”。无安装程序、无环境变量、不写开机启动项，随 ZBrush
启动/退出。

## 版本支持

- ZBrush 2026.0 / 2026.1：精确模式。使用官方 Python API（zbrush.commands），
  在 Edit 模式 + PixolPick 材质索引 0（空白画布）时取消左键拖动旋转；
  启动即生效，无需校准。
- ZBrush 2022 - 2025：兼容模式。这些版本没有官方 Python API；插件使用
  官方 [FileExecute] DLL 机制 + 官方 ZScript 界面，空白画布判定优先用
  文档化的 ZScript 事件循环（Sleep + IGet Transform:Edit + MouseHPos/VPos
  + PixolPick）推送给 DLL，被打断时自动退回 F2 光标校准。

## 目录

- `NoLeftClickRotation_Plugin/`：发布包，按《安装说明.txt》手动安装
- `NoLeftClickRotation_Source/`：源码（C DLL + ZScript 文本 + init.py）
- `ZScript-Command-Reference-2022.pdf`：官方 ZScript 命令参考

## 构建

1. `NoLeftClickRotation_Source\build_dll.cmd` 编译 DLL（需 VS Build Tools）；
2. 把 `NoLeftClickRotation.zscript.txt` 在目标 ZBrush 版本上编译为 .zsc
   （用 ZScript 面板 Load，或官方 DefaultZScript 方式，详见发布包说明）；
3. 按《安装说明.txt》复制到用户资产目录的 `ZStartup\ZPlugs64`。

## 原理

.zsc 启动时通过官方 `[FileExecute]` 加载 DLL；DLL 在本进程内子类化 ZBrush
主窗口，随 ZBrush 启动/退出：

- 2026+：每次左键按下时同步调用官方 Python API 判断“Edit 模式 + 空白画布”，
  命中后点击照常到达 ZBrush，再立即补发一次抬起，在旋转开始前取消拖拽；
  光标进入模型后补发一次按下，笔刷从进入点起笔。
- 2022-2025：ZScript 事件循环把精确状态推给 DLL（UpdateState）；循环被
  其他插件/宏打断时，DLL 退回 F2 校准的光标判断兜底。

注：ZBrush 只允许一个 ZScript 同时运行，这是平台限制；事件循环被打断属
预期情况，插件会降级而不是失效。
