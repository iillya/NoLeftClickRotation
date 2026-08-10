# -*- coding: utf-8 -*-
"""NoLeftClickRotation（禁用左键视图旋转）— 纯 Python 版（ZBrush 2026）。

ZBrush 2026 启动时自动执行 ZStartup\\ZPlugs64 下的 *.py 文件，因此本插件
无需 .zsc、无需 DLL、无需环境变量、无需安装程序，安装 = 复制这一个文件。

工作原理：
ZBrush 处理画布鼠标移动时，会先调用一个"能否导航"的虚函数判定；判定为真
才进入视图旋转/导航计算（RVA 0x5E4D90 内部，判定结果使用点 0x5E5127）。
插件在该使用点打一个 15 字节原生存根：
    左键按住（且未按 Ctrl）-> 判定结果被强制当作"否"，跳过旋转/导航计算，
                              视图不再旋转或平移；
    否则                   -> 原样执行，一切照常（右键缩放、UI 按钮/滑块、
                              雕刻、Ctrl+左键框选遮罩等不受影响）。
雕刻笔划、UI 控件交互不经过该导航分支，因此插件不需要任何画布/UI 光标
判定，也不会干扰画笔运动与界面操作。钩子全部位于 ZBrush 进程内存，
随 ZBrush 启动/退出，不修改任何文件或系统设置。
"""

import ctypes
import os
import struct
import time
from ctypes import wintypes

# 自诊断日志（正式版可删除此开关）
DEBUG: bool = True
DEBUG_LOG: str = os.path.join(
    os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"), "nlr_final.log"
)


def _dlog(line: str) -> None:
    if not DEBUG:
        return
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
    except Exception:
        pass

# ---------------- Win32 常量与类型 ----------------

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_TIMER = 0x0113

VK_LBUTTON = 0x01
VK_CONTROL = 0x11

TIMER_ID = 0x4E4C5449  # 'NLTI'
SUBCLASS_ID = 0x4E525442  # 'NRB'

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40

# 路由器 0x50001 分支 3 的转发点（0x1807DEC，12 字节窗口，无 call，可安全打计数器）
CTRL_RVA = 0x1807DEC
CTRL_ORIG12 = bytes.fromhex("488b8eb00100004889742450")

user32 = ctypes.windll.user32
comctl32 = ctypes.WinDLL("comctl32")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t

SubclassProcType = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    WPARAM,
    LPARAM,
    ctypes.c_void_p,
    ctypes.c_void_p,
)

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(wintypes.DWORD),
]
user32.GetKeyState.restype = ctypes.c_short
user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.SetTimer.restype = ctypes.c_void_p
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p]
user32.KillTimer.restype = wintypes.BOOL
user32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_void_p]

comctl32.SetWindowSubclass.restype = wintypes.BOOL
comctl32.SetWindowSubclass.argtypes = [
    wintypes.HWND,
    SubclassProcType,
    ctypes.c_size_t,
    ctypes.c_size_t,
]
comctl32.DefSubclassProc.restype = LRESULT
comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]

kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [
    ctypes.c_void_p,
    ctypes.c_size_t,
    wintypes.DWORD,
    wintypes.DWORD,
]
kernel32.VirtualProtect.restype = wintypes.BOOL
kernel32.VirtualProtect.argtypes = [
    ctypes.c_void_p,
    ctypes.c_size_t,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.VirtualFree.restype = wintypes.BOOL
kernel32.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD]

# ---------------- 配置 ----------------

PLUGIN_DIR: str = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH: str = os.path.join(PLUGIN_DIR, "config.txt")

_enabled: bool = True


def _read_enabled() -> bool:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return f.read(8).strip() != "0"
    except Exception:
        return True


def load_enabled() -> bool:
    return _enabled


def save_enabled(value: bool) -> None:
    global _enabled
    _enabled = bool(value)
    try:
        tmp_path = CONFIG_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write("1\n" if _enabled else "0\n")
        os.replace(tmp_path, CONFIG_PATH)
    except Exception:
        pass


# ---------------- 语言与界面 ----------------


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
    SWITCH_INFO: str = "左键拖动不再旋转或平移视图；雕刻、UI、Ctrl+左键遮罩不受影响。"
else:
    PLUGIN_NAME = "Disable Left-Button View Rotation"
    SWITCH_LABEL = "Enable"
    SWITCH_INFO = (
        "Left-drag won't rotate or pan the view; "
        "sculpting, UI, and Ctrl+left mask selection are unaffected."
    )

PALETTE: str = "Zplugin:" + PLUGIN_NAME
BODY: str = PALETTE + ":Body"
SWITCH_PATH: str = BODY + ":" + SWITCH_LABEL


def on_toggle(sender: str, value: bool) -> None:
    """开关回调（官方签名 fn(sender, value)）。"""
    save_enabled(bool(value))
    if value:
        if _view_install():
            if _hwnd:
                _timer_start(_hwnd)
            _set_flag(False)
    else:
        _set_flag(False)


def setup_ui() -> None:
    """创建插件界面：外层显示插件名，内层 Body 隐藏标题栏避免开关被遮挡。"""
    import zbrush.commands as zbc

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


# ---------------- 导航拦截钩子 ----------------

# 0x5EDFC0 内部"旋转/非旋转"分流点（movzx; cmp ebx,2; jne）：
#   ebx==2 且 bit9 置位 -> 旋转路径（0x5EE1A2）
#   其它              -> 非旋转路径（0x5EE309，雕刻也走这里）
# 左键按下时强制跳 0x5EE309，跳过旋转；雕刻路径不受影响。
NAV_HOOKS = [
    {"name": "BR", "rva": 0x5EE192,
     "orig": bytes.fromhex("0fb705eb07ab0e83fb020f8567010000"), "plen": 16,
     "special": True},
]

for _h in NAV_HOOKS:
    _h["state"] = {"addr": 0, "stub": 0, "active": False}

_hwnd = None


def _build_nav_stub(page: int, orig: bytes, cont_va: int, jreg: str) -> bytes:
    """导航处理器存根：左键按下 -> 直接返回；否则复刻原序言并跳回。"""
    st = bytearray()
    st += b"\x80\x3D" + struct.pack("<i", 0x50 - 7) + b"\x00"   # cmp byte [rip+0x49],0
    st += b"\x74\x0D"                                            # je +0x0D -> 原逻辑
    st += b"\xFF\x05" + struct.pack("<i", 0x5C - 15)             # inc [rip+0x4D]
    st += b"\xC3"                                                # ret（入口处无栈改动，安全）
    while len(st) < 0x16:
        st.append(0xCC)
    st += orig
    if jreg == "rax":
        st += b"\x48\xB8" + struct.pack("<Q", cont_va) + b"\xFF\xE0"
    else:
        st += b"\x49\xBB" + struct.pack("<Q", cont_va) + b"\x41\xFF\xE3"
    while len(st) < 0x50:
        st.append(0xCC)
    st += b"\x00" * 16
    return bytes(st)


def _build_branch_stub() -> bytes:
    """分支钩子存根：左键按下 -> 强制走非旋转路径 0x5EE309；
    否则复刻原分流（movzx 全局字; cmp ebx,2; jne）。"""
    st = bytearray()
    st += b"\x80\x3D" + struct.pack("<i", 0x50 - 7) + b"\x00"
    st += b"\x74\x13"
    st += b"\xFF\x05" + struct.pack("<i", 0x5C - 15)
    st += b"\x49\xBB" + struct.pack("<Q", 0x1405EE309)
    st += b"\x41\xFF\xE3"
    st += b"\x48\xB8" + struct.pack("<Q", 0x14F09E984)   # mov rax, 全局字地址
    st += b"\x0F\xB7\x00"                                 # movzx eax, word [rax]
    st += b"\x83\xFB\x02"                                 # cmp ebx, 2
    st += b"\x75\x0D"                                     # jne +0x0D
    st += b"\x49\xBB" + struct.pack("<Q", 0x1405EE1A2)    # ebx==2 -> 原旋转续点
    st += b"\x41\xFF\xE3"
    st += b"\x49\xBB" + struct.pack("<Q", 0x1405EE309)    # 其它 -> 非旋转路径
    st += b"\x41\xFF\xE3"
    while len(st) < 0x50:
        st.append(0xCC)
    st += b"\x00" * 16
    return bytes(st)


def _patch_template(page: int, plen: int) -> bytes:
    if plen == 14:
        return b"\x49\xBB" + struct.pack("<Q", page) + b"\x41\xFF\xE3" + b"\x90"
    if plen == 16:
        return b"\x49\xBB" + struct.pack("<Q", page) + b"\x41\xFF\xE3" + b"\x90\x90\x90"
    return b"\x49\xBB" + struct.pack("<Q", page) + b"\x41\xFF\xE3" + b"\x90" * (plen - 13)


def _read_u64(addr: int) -> int:
    return ctypes.c_uint64.from_address(addr).value


def _write_bytes(addr: int, data: bytes) -> bool:
    try:
        old = wintypes.DWORD()
        if not kernel32.VirtualProtect(
            ctypes.c_void_p(addr), len(data), PAGE_READWRITE, ctypes.byref(old)
        ):
            return False
        ctypes.memmove(addr, data, len(data))
        kernel32.VirtualProtect(ctypes.c_void_p(addr), len(data), old.value, ctypes.byref(old))
        return True
    except Exception:
        return False


def _view_install() -> bool:
    """在导航模式动作处理器入口安装拦截；版本不匹配或失败时安全放行。"""
    try:
        if all(h["state"]["active"] for h in NAV_HOOKS):
            return True
        _dlog("install begin")
        base = int(kernel32.GetModuleHandleW(None) or 0)
        if not base:
            _dlog("install FAIL: no base")
            return False
        ok = False
        for h in NAV_HOOKS:
            st = h["state"]
            if st["active"]:
                ok = True
                continue
            _dlog("%s: start rva=%#x" % (h["name"], h["rva"]))
            addr = base + h["rva"]
            cur = ctypes.string_at(addr, len(h["orig"]))
            if cur != h["orig"]:
                _dlog("%s FAIL: version mismatch cur=%s" % (h["name"], cur.hex()))
                continue
            _dlog("%s: ver ok" % h["name"])
            page = int(kernel32.VirtualAlloc(
                None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE
            ) or 0)
            if not page:
                _dlog("%s FAIL: alloc" % h["name"])
                continue
            _dlog("%s: page=%#x" % (h["name"], page))
            if h.get("special"):
                stb = _build_branch_stub()
            else:
                stb = _build_nav_stub(
                    page, h["orig"], 0x140000000 + h["rva"] + h["plen"],
                    h.get("jreg", "r11"))
            ctypes.memmove(page, stb, len(stb))
            ctypes.c_ubyte.from_address(page + 0x50).value = 0
            _dlog("%s: stub written" % h["name"])
            patch = _patch_template(page, h["plen"])
            if not _write_bytes(addr, patch):
                _dlog("%s FAIL: patch" % h["name"])
                continue
            st.update(addr=addr, stub=page, active=True)
            _dlog("%s OK stub=%#x" % (h["name"], page))
            ok = True
            time.sleep(0.02)
        return ok
    except Exception as e:
        _dlog("install EXC %r" % (e,))
        return False


def _view_restore() -> None:
    """恢复原始状态（存根内存保留，可再次启用）。"""
    for h in NAV_HOOKS:
        st = h["state"]
        if st["active"]:
            if _read_u64(st["addr"]) == int(st["stub"]):
                _write_bytes(st["addr"], h["orig"])
            st["active"] = False


def _set_flag(value: bool) -> None:
    """更新所有存根的左键标志（1=阻断导航，0=放行）。"""
    v = 1 if value else 0
    try:
        for h in NAV_HOOKS:
            if h["state"]["active"]:
                ctypes.c_ubyte.from_address(h["state"]["stub"] + 0x50).value = v
    except Exception:
        pass


def _key_ctrl_down() -> bool:
    try:
        return bool(user32.GetKeyState(VK_CONTROL) & 0x8000)
    except Exception:
        return False


# ---------------- 窗口子类化（维护左键标志 + 定时器兜底） ----------------


def _handle_message(hwnd, msg, wparam, lparam) -> int:
    try:
        if msg == WM_LBUTTONDOWN:
            # 子类先于 ZBrush 处理该消息，标志即时生效；Ctrl 按下时放行
            # （保证 Ctrl+左键框选遮罩等原生操作不受影响）。
            _set_flag(not _key_ctrl_down())
        elif msg == WM_LBUTTONUP:
            _set_flag(False)
        elif msg == WM_TIMER and wparam == TIMER_ID:
            left = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
            ctrl = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
            _set_flag(left and not ctrl)
            if (left or ctrl):
                parts = []
                for h in NAV_HOOKS:
                    st = h["state"]
                    if st["active"]:
                        parts.append("%s=%d" % (
                            h["name"],
                            ctypes.c_uint32.from_address(st["stub"] + 0x5C).value))
                if parts:
                    _dlog("blocked %s L=%d C=%d"
                          % (" ".join(parts), int(left), int(ctrl)))
            return 0
    except Exception:
        pass
    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


@SubclassProcType
def _subclass_proc(hwnd, msg, wparam, lparam, u_id, ref_data) -> int:
    try:
        return _handle_message(hwnd, msg, wparam, lparam)
    except Exception:
        pass
    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


_subclass_callback = _subclass_proc

_enum_result: list = [None]


@WNDENUMPROC
def _enum_find_zbrush(hwnd, lparam) -> bool:
    try:
        buf = ctypes.create_unicode_buffer(256)
        if user32.GetClassNameW(hwnd, buf, 256) and buf.value == "ZBrush":
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == os.getpid():
                _enum_result[0] = hwnd
                return False
    except Exception:
        pass
    return True


_enum_callback = _enum_find_zbrush


def _find_zbrush_window():
    _enum_result[0] = None
    try:
        user32.EnumWindows(_enum_find_zbrush, 0)
    except Exception:
        pass
    return _enum_result[0]


def _install_subclass(hwnd) -> bool:
    return bool(comctl32.SetWindowSubclass(hwnd, _subclass_proc, SUBCLASS_ID, 0))


def _timer_start(hwnd) -> bool:
    try:
        return bool(user32.SetTimer(hwnd, TIMER_ID, 50, None))
    except Exception:
        return False


def _timer_stop(hwnd) -> None:
    try:
        user32.KillTimer(hwnd, TIMER_ID)
    except Exception:
        pass


# ---------------- 入口 ----------------


def main() -> None:
    """ZBrush 启动时执行插件入口。"""
    global _enabled, _hwnd
    try:
        with open(DEBUG_LOG, "w", encoding="utf-8") as f:
            f.write("=== final plugin ===\npy=%s pid=%d\n" % (__import__("sys").version.split()[0], os.getpid()))
    except Exception:
        pass
    _dlog("main start")
    if not os.path.isfile(CONFIG_PATH):
        save_enabled(True)
    else:
        _enabled = _read_enabled()
    try:
        setup_ui()
    except Exception:
        pass

    # 主窗口在 Python 启动脚本执行时可能尚未就绪，做短暂重试。
    hwnd = _find_zbrush_window()
    installed = bool(hwnd and _install_subclass(hwnd))
    for _ in range(20):
        if installed:
            break
        time.sleep(0.5)
        hwnd = _find_zbrush_window()
        installed = bool(hwnd and _install_subclass(hwnd))
    _hwnd = hwnd

    if load_enabled():
        if _view_install():
            if hwnd:
                _timer_start(hwnd)
            _set_flag(False)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
