NoLeftClickRotation（禁用左键视图旋转）
========================================

适用版本：ZBrush 2026.0 / 2026.1（含后续 2026 小版本）。

功能
----
在 ZBrush 雕刻（Edit 模式）下，禁用“左键按住空白画布拖动触发视图旋转”。
- 左键点击本身不被拦截，界面滑块/按钮/画布内自定义 UI 均可正常拖动；
- 光标从空白处拖到模型上时，笔刷从进入点正常起笔，不拦截画笔运动；
- Ctrl/Shift/Alt + 左键（框选遮罩等）原样交给 ZBrush，不受影响；
- 判定使用官方 PixolPick 材质索引（0 = 空白画布），不比较颜色；
- 右键缩放、中键平移不受影响。

原理
----
1. NoLeftClickRotation.zsc 在 ZBrush 启动时通过官方 [FileExecute] 接口
   加载 NoLeftClickRotation.dll；
2. DLL 只在本进程内子类化 ZBrush 主窗口，随 ZBrush 启动/退出；
3. 每次左键按下时，DLL 同步调用 ZBrush 内置 Python VM 中的官方 API
   （zbrush.commands）判断“Edit 模式 + 空白画布 + 画布光标”；
4. 命中时点击正常到达 ZBrush，随后立即补发一次抬起，在旋转开始前取消
   拖拽；光标进入模型后补发一次按下，笔刷从进入点起笔。
   （无 ZScript 轮询、无 Sleep，因此启动即生效，且不与其他插件抢脚本。）

文件
----
NoLeftClickRotation.zsc           官方编译插件
NoLeftClickRotationData\
  NoLeftClickRotation.dll         进程内钩子（随 ZBrush 启动/退出）
  init.py                         Python 界面与画布判定
  config.txt                      启用状态

安装 / 卸载见《安装说明.txt》。
