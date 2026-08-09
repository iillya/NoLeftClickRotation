# -*- coding: utf-8 -*-
"""NoLeftClickRotation（禁用左键视图旋转）— ZBrush 2026 Python 部分。

插件结构（符合官方 ZPlugin 与 ZBrush Python SDK）：

- NoLeftClickRotation.zsc 在启动时通过官方 [FileExecute] 加载 DLL；
- DLL 在本进程内子类化 ZBrush 主窗口，负责鼠标事件时机与动作；
- 本文件由 DLL 通过 ZBrush 内置 Python VM 执行：
  1. 按 Windows 系统 UI 语言创建中/英文界面（位于 Zplugin 菜单下）；
  2. 注册 zb_noleftclickrotation 模块，提供 query()/point_kind() 供 DLL
     在鼠标事件发生时同步查询画布状态（全部使用官方 zbrush.commands API）；
  3. DLL 不拦截画笔/界面消息；仅在“Edit 模式 + 空白画布 + 画布光标”时，
     让点击正常到达 ZBrush 后立即补发一次抬起，取消视图旋转拖拽；光标随后
     进入模型时补发一次按下，笔刷从进入点正常起笔。
"""

import ctypes
import os
import sys
import types
from typing import Callable

PLUGIN_DIR: str = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH: str = os.path.join(PLUGIN_DIR, "config.txt")
DLL_PATH: str = os.path.join(PLUGIN_DIR, "NoLeftClickRotation.dll")

# 由 DLL 通过 [FileExecute] 执行本文件时置为 1，避免重复加载 DLL。
IN_PROCESS: bool = os.environ.get("NOBLANKROTATE_INPROCESS", "") == "1"


def detect_language() -> str:
    """中文 Windows 系统返回 'zh'，其他系统返回 'en'。"""
    try:
        lang_id: int = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        if (lang_id & 0x3FF) == 0x04:
            return "zh"
    except Exception:
        pass
    return "en"


LANG: str = detect_language()
if LANG == "zh":
    PLUGIN_NAME: str = "禁用左键视图旋转"
    SWITCH_LABEL: str = "启用"
    SWITCH_INFO: str = "左键按住空白画布不再旋转视图；拖到模型上时笔刷从进入点正常起笔。"
else:
    PLUGIN_NAME = "Disable Left-Button View Rotation"
    SWITCH_LABEL = "Enable"
    SWITCH_INFO = (
        "Left-drag on blank canvas won't rotate the view; "
        "strokes start when the cursor reaches the mesh."
    )

PALETTE: str = "Zplugin:" + PLUGIN_NAME
BODY: str = PALETTE + ":Body"
SWITCH_PATH: str = BODY + ":" + SWITCH_LABEL


def load_enabled() -> bool:
    """读取持久化的启用状态（与 DLL 共用 config.txt）。"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return f.read(8).strip() != "0"
    except Exception:
        return True


def save_enabled(value: bool) -> None:
    """持久化启用状态，供 DLL 与下次启动读取。"""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write("1\n" if value else "0\n")
    except Exception:
        pass


def on_toggle(sender: str, value: bool) -> None:
    """开关回调（官方签名 fn(sender, value)）。"""
    save_enabled(bool(value))


def _canvas_point() -> "tuple[float, float] | None":
    """返回当前鼠标在画布空间的坐标；不在画布内返回 None。"""
    try:
        import zbrush.commands as zbc

        doc_w: float = zbc.get("Document:Width")
        doc_h: float = zbc.get("Document:Height")
        # 官方 API 直接返回画布坐标，无需窗口/屏幕坐标换算，DPI 缩放不影响。
        px, py = zbc.get_mouse_pos(global_coordinates=False)
        if 0 <= px < doc_w and 0 <= py < doc_h:
            return (px, py)
    except Exception:
        pass
    return None


def query(screen_x: int, screen_y: int, is_down: bool = False) -> bool:
    """由 DLL 在 ZBrush UI 线程同步调用：按下点是否为可取消的空白画布。"""
    try:
        import zbrush.commands as zbc

        if not load_enabled():
            return False
        if not bool(zbc.get("Transform:Edit")):
            return False
        point = _canvas_point()
        if point is None:
            return False
        px, py = point
        # 材质索引 0 = 空白画布；不比较颜色。
        return float(zbc.pixol_pick(5, px, py)) == 0.0
    except Exception:
        return False


def point_kind(screen_x: int, screen_y: int) -> int:
    """0=空白画布，1=模型，2=其他（不处理）。"""
    try:
        import zbrush.commands as zbc

        if not bool(zbc.get("Transform:Edit")):
            return 2
        point = _canvas_point()
        if point is None:
            return 2
        px, py = point
        return 0 if float(zbc.pixol_pick(5, px, py)) == 0.0 else 1
    except Exception:
        return 2


def register_query_module() -> None:
    """把判定函数注册为模块，供 DLL 通过 Python C API 回调。

    仅注册本插件专用的唯一模块名，不改动共享模块状态。
    """
    mod = types.ModuleType("zb_noleftclickrotation")
    mod.query = query
    mod.point_kind = point_kind
    sys.modules["zb_noleftclickrotation"] = mod


def setup_ui() -> None:
    """创建插件界面：外层显示插件名，内层 Body 隐藏标题栏避免开关被遮挡。"""
    import zbrush.commands as zbc

    # 重复加载时先关闭旧界面，保证只有一份。
    if zbc.exists(PALETTE):
        zbc.close(PALETTE)
    if zbc.exists(BODY):
        zbc.close(BODY)

    state: bool = load_enabled()
    zbc.add_subpalette(PALETTE, title_mode=0)
    zbc.add_subpalette(BODY, title_mode=2)
    zbc.add_switch(
        SWITCH_PATH,
        state,
        SWITCH_INFO,
        on_toggle,
        initially_disabled=False,
        width=1.0,
    )


def ensure_dll() -> None:
    """独立加载本脚本时（非 DLL 注入）也确保 DLL 已安装。"""
    if not os.path.isfile(DLL_PATH):
        return
    try:
        dll = ctypes.WinDLL(DLL_PATH)
        install: Callable = dll.Install
        install.restype = ctypes.c_float
        install.argtypes = [
            ctypes.c_char_p,
            ctypes.c_double,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        install(None, 0.0, None, None)
    except Exception:
        pass


def main() -> None:
    """ZBrush 启动时执行插件入口。"""
    if not os.path.isfile(CONFIG_PATH):
        save_enabled(True)
    try:
        setup_ui()
    except Exception:
        pass
    register_query_module()
    if not IN_PROCESS:
        ensure_dll()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
