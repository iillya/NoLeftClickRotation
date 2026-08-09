# -*- coding: utf-8 -*-
"""NoLeftClickRotation（禁用左键视图旋转）ZBrush 插件 Python 部分。

NoLeftClickRotation.zsc 在 ZBrush 启动时通过官方 [FileExecute] 接口调用
NoLeftClickRotation.dll；DLL 再通过 ZBrush 内置的官方 Python VM 执行本文件：

1. 按 Windows 系统 UI 语言创建中/英文界面（位于 Zplugin 菜单下）。
2. 注册 zb_noleftclickrotation 模块，提供 query()/point_kind() 供 DLL 在
   鼠标事件发生时同步查询画布状态（全部使用官方 zbrush.commands API）。
3. DLL 不拦截画笔/界面消息；仅在“Edit 模式 + 空白画布 + 画布光标”时，让
   点击正常到达 ZBrush 后立即补发一次抬起，取消视图旋转拖拽；光标随后进入
   模型时补发一次按下，笔刷从进入点正常起笔。
"""

import ctypes
import os
import sys
import types

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PLUGIN_DIR, "config.txt")
DLL_PATH = os.path.join(PLUGIN_DIR, "NoLeftClickRotation.dll")

# 由 DLL 通过 [FileExecute] 执行本文件时置为 1，避免重复加载 DLL。
IN_PROCESS = os.environ.get("NOBLANKROTATE_INPROCESS", "") == "1"


def detect_language():
    """中文 Windows 系统返回 'zh'，其他系统返回 'en'。"""
    try:
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        if (lang_id & 0x3FF) == 0x04:
            return "zh"
    except Exception:
        pass
    return "en"


LANG = detect_language()
if LANG == "zh":
    PLUGIN_NAME = "禁用左键视图旋转"
    SWITCH_LABEL = "启用"
    SWITCH_INFO = "左键按住空白画布不再旋转视图；拖到模型上时笔刷从进入点正常起笔。"
else:
    PLUGIN_NAME = "Disable Left-Button View Rotation"
    SWITCH_LABEL = "Enable"
    SWITCH_INFO = ("Left-drag on blank canvas won't rotate the view; "
                   "strokes start when the cursor reaches the mesh.")

PALETTE = "Zplugin:" + PLUGIN_NAME
BODY = PALETTE + ":Body"
SWITCH_PATH = BODY + ":" + SWITCH_LABEL

# ZScript 旧版界面（2022-2025 无 Python 时的官方 UI）使用的两种语言名称，
# 2026 启动时若存在则先关闭，保证只有一份 Python 界面。
LEGACY_NAMES = ("禁用左键视图旋转", "Disable Left-Button View Rotation")


def load_enabled():
    """读取持久化的启用状态（与 DLL 共用 config.txt）。"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return f.read(8).strip() != "0"
    except Exception:
        return True


def save_enabled(value):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write("1\n" if value else "0\n")
    except Exception:
        pass


def on_toggle(sender, value):
    save_enabled(bool(value))


def query(screen_x, screen_y, is_down=False):
    """由 DLL 在 ZBrush UI 线程同步调用：按下点是否为可取消的空白画布。"""
    try:
        import zbrush.commands as zbc
        if not load_enabled():
            return False
        if not bool(zbc.get("Transform:Edit")):
            return False
        doc_w = zbc.get("Document:Width")
        doc_h = zbc.get("Document:Height")
        # 官方 API 直接返回画布坐标，无需窗口/屏幕坐标换算，DPI 缩放不影响。
        px, py = zbc.get_mouse_pos(global_coordinates=False)
        if not (0 <= px < doc_w and 0 <= py < doc_h):
            return False
        # 材质索引 0 = 空白画布；不比较颜色。
        return float(zbc.pixol_pick(5, px, py)) == 0.0
    except Exception:
        return False


def point_kind(screen_x, screen_y):
    """0=空白画布，1=模型，2=其他（不处理）。"""
    try:
        import zbrush.commands as zbc
        if not bool(zbc.get("Transform:Edit")):
            return 2
        doc_w = zbc.get("Document:Width")
        doc_h = zbc.get("Document:Height")
        px, py = zbc.get_mouse_pos(global_coordinates=False)
        if not (0 <= px < doc_w and 0 <= py < doc_h):
            return 2
        return 0 if float(zbc.pixol_pick(5, px, py)) == 0.0 else 1
    except Exception:
        return 2


def register_query_module():
    """把判定函数注册为模块，供 DLL 通过 Python C API 回调。"""
    mod = types.ModuleType("zb_noleftclickrotation")
    mod.query = query
    mod.point_kind = point_kind
    sys.modules["zb_noleftclickrotation"] = mod


def setup_ui():
    import zbrush.commands as zbc
    # 重复加载或旧版 ZScript 界面存在时先关闭，保证只有一份界面。
    for legacy_name in LEGACY_NAMES:
        for path in ("Zplugin:" + legacy_name,
                     "Zplugin:" + legacy_name + ":Body"):
            if zbc.exists(path):
                zbc.close(path)
    if zbc.exists(PALETTE):
        zbc.close(PALETTE)
    if zbc.exists(BODY):
        zbc.close(BODY)
    state = load_enabled()
    # 外层显示插件名；内层 Body 隐藏标题栏，避免开关被顶部标题遮挡。
    zbc.add_subpalette(PALETTE, title_mode=0)
    zbc.add_subpalette(BODY, title_mode=2)
    zbc.add_switch(SWITCH_PATH, state, SWITCH_INFO, on_toggle, False, 1.0)


def ensure_dll():
    """独立加载本脚本时（非 DLL 注入）也确保 DLL 已安装。"""
    if not os.path.isfile(DLL_PATH):
        return
    try:
        dll = ctypes.WinDLL(DLL_PATH)
        install = dll.Install
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


def main():
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
