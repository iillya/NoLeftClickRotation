# 左键按住时保持 PixolPick 可用的方法

## 文档目的

本文记录旧版插件中使用的一种特殊方法：在用户持续按住左键时，临时调整 ZBrush 的内部画布状态，使 `zbrush.commands.pixol_pick()` 仍能读取鼠标位置下的材质值。

该实现来自 Git 提交 `128ad96`，仅作为技术记录和后续研究依据。它依赖特定 ZBrush 版本的内部内存布局，不应直接用于未经验证的版本。

## 使用场景

插件需要实现以下操作：

1. 用户从空白画布按下左键。
2. 插件阻止空白画布触发相机旋转。
3. 用户保持左键按下并将光标拖入模型。
4. 插件持续使用 `PixolPick` 检测光标是否已经进入模型。
5. 检测到模型后，插件补发雕刻起笔消息。

问题在于，ZBrush 进入某些左键操作状态后，普通 `PixolPick` 可能无法继续稳定读取画布。旧版通过临时设置内部状态位绕过了这一限制。

## 核心实现

```python
def _material_under_pointer():
    """读取光标下的材质值，并在结束后恢复 ZBrush 内部状态。"""

    if not _pixol_flags_address:
        return 0.0

    import zbrush.commands as zbc

    x, y = zbc.get_mouse_pos(global_coordinates=False)
    flags = ctypes.c_uint32.from_address(_pixol_flags_address)
    original = flags.value

    try:
        flags.value = original | PIXOL_STABLE_CANVAS_BIT
        return float(zbc.pixol_pick(5, float(x), float(y)))
    finally:
        flags.value = original
```

相关常量和状态：

```python
PIXOL_FLAGS_OFFSET = 0x11584
PIXOL_STABLE_CANVAS_BIT = 0x00200000

_pixol_flags_address = 0
```

## 工作原理

`_pixol_flags_address` 指向 ZBrush 内部的一组画布状态标志。

调用 `PixolPick` 前，代码执行按位或操作：

```python
flags.value = original | PIXOL_STABLE_CANVAS_BIT
```

这会临时开启 `0x00200000` 状态位，使 `PixolPick` 按稳定画布状态读取鼠标位置。读取完成后，`finally` 无条件恢复原始值：

```python
flags.value = original
```

使用 `finally` 非常重要。即使 `pixol_pick()` 抛出异常，ZBrush 的内部状态也必须恢复，否则可能造成输入、画布或界面异常。

## 左键按住期间的轮询

旧版在等待光标进入模型时持续执行以下逻辑：

```python
def _poll_waiting(hwnd):
    if _gesture != WAIT_FOR_MESH:
        return

    if not _active() or _lightbox_open() or not _key_down(VK_LBUTTON):
        _reset_gesture()
        return

    if _pointer_on_mesh():
        _start_sculpting(hwnd)
```

`_pointer_on_mesh()` 内部调用 `_material_under_pointer()`：

```python
def _pointer_on_mesh():
    try:
        return _material_under_pointer() != 0.0
    except Exception as exception:
        _log("pixol_error=" + repr(exception))
        return False
```

因此只要处于 `WAIT_FOR_MESH` 状态且物理左键仍按住，插件就会反复读取光标下的材质值：

- 返回 `0.0`：仍在空白区域，继续等待。
- 返回非 `0.0`：已经进入模型，开始模拟雕刻起笔。
- 左键松开、插件停用或 LightBox 打开：立即结束等待。

## 内存地址的定位方式

旧版并非直接使用绝对地址，而是根据 ZBrush 主模块基址、指令 RVA 和 RIP 相对寻址计算内部状态指针：

```python
image_base = int(kernel32.GetModuleHandleW(None) or 0)
site = image_base + PIXOL_STATE_LOAD_RVA
actual = ctypes.string_at(site, len(PIXOL_STATE_LOAD_SIGNATURE))

if actual != PIXOL_STATE_LOAD_SIGNATURE:
    return False

displacement = struct.unpack("<i", actual[3:7])[0]
pointer_slot = site + 7 + displacement
state = ctypes.c_void_p.from_address(pointer_slot).value

if not state:
    return False

_pixol_flags_address = int(state) + PIXOL_FLAGS_OFFSET
```

这里的指令签名用于确认当前程序版本的机器码与已知版本一致。签名不匹配时必须停止使用此方法，不能猜测地址或强行写入。

## 必要的安全条件

如果以后重新采用此方法，至少应满足以下条件：

1. 仅支持经过实际验证的 ZBrush 精确版本。
2. 使用机器码签名验证目标指令，签名不匹配时禁用相关功能。
3. 检查状态指针不为空，并确认目标内存可读写。
4. 每次修改标志位后都通过 `finally` 恢复原值。
5. 不在 LightBox、原生 UI、非 Edit 模式或插件停用状态下调用。
6. 捕获所有读取异常；异常后停止轮询，不能继续写入未知地址。
7. ZBrush 更新后重新查找并验证 RVA、指令签名、字段偏移和状态位含义。

## 风险说明

此方法调用了官方 Python API，但同时直接读取和修改 ZBrush 的内部内存，因此不属于稳定的官方接口。

主要风险包括：

- ZBrush 更新后，指令位置、对象布局或字段偏移发生变化。
- 相同状态位在新版本中具有不同含义。
- 写入错误地址造成 ZBrush 卡死或崩溃。
- 在 UI、LightBox 或工程加载期间调用，干扰 ZBrush 的内部状态切换。
- 多个回调同时访问该状态时发生时序冲突。

因此，当前插件没有恢复这段内部状态位补丁。当前版本仅在 `WAIT_MODEL` 状态下调用普通 `PixolPick`，安全性更高，但左键按住期间的读取能力取决于 ZBrush 当时的内部状态。

## 来源

- Git 提交：`128ad96`
- 提交说明：`还没完善`
- 原文件：`NoLeftClickRotation.py`
- 关键函数：`_material_under_pointer()`、`_pointer_on_mesh()`、`_poll_waiting()`
