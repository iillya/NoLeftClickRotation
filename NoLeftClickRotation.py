# -*- coding: utf-8 -*-
"""临时诊断：验证 0x1412D88A0 入口 [rdx+0xa0] 的命中结果是否可用。

只读钩子：每帧把 [rdx+0xa0]（ZBrush 自己的"光标是否在模型上"命中结果）
抄到存根内存；左键按住期间定时采样并显示到状态栏 + 写日志。
0 = 空白画布，非 0 = 模型。
"""

import ctypes
import os
import struct
import time
from ctypes import wintypes

DEBUG_LOG: str = os.path.join(
    os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"), "nlr_hit.log"
)

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_TIMER = 0x0113

VK_LBUTTON = 0x01
TIMER_ID = 0x4E4C5448  # 'NLTH'
SUBCLASS_ID = 0x4E4C5448

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t

SubclassProcType = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM,
    ctypes.c_void_p, ctypes.c_void_p,
)
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32 = ctypes.windll.user32
comctl32 = ctypes.WinDLL("comctl32")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [
    wintypes.HWND, ctypes.POINTER(wintypes.DWORD),
]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.SetTimer.restype = ctypes.c_void_p
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p]
user32.KillTimer.restype = wintypes.BOOL
user32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_void_p]

comctl32.SetWindowSubclass.restype = wintypes.BOOL
comctl32.SetWindowSubclass.argtypes = [
    wintypes.HWND, SubclassProcType, ctypes.c_size_t, ctypes.c_size_t,
]
comctl32.DefSubclassProc.restype = LRESULT
comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]

kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [
    ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD,
]
kernel32.VirtualProtect.restype = wintypes.BOOL
kernel32.VirtualProtect.argtypes = [
    ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]

# ---------------- 命中记录钩子 ----------------

HIT_RVA = 0x12D88A0
HIT_ORIG = bytes.fromhex("488954241048894c240855574155488dac2490c9ffff")

# 0x00 cmp byte [rip+0x59],0        flag@stub+0x60
# 0x07 je +0x11 -> 0x1A（PASS：复刻原序言）
# 0x09 mov rax,[rdx+0xa0]
# 0x0D mov [rip+0x58],rax           value@stub+0x6C
# 0x14 jmp +0x04 -> 0x1A（PASS）
# 0x16 nop*4
# 0x1A 22 字节原序言（必须复刻，否则栈帧错乱崩溃）
# 0x30 mov rax, cont; jmp rax
_HIT_STUB_CODE: bytes = bytes([
    0x80, 0x3D, 0x59, 0x00, 0x00, 0x00, 0x00,
    0x74, 0x11,
    0x48, 0x8B, 0x42, 0xA0,
    0x48, 0x89, 0x05, 0x58, 0x00, 0x00, 0x00,
    0xEB, 0x04,
    0x90, 0x90, 0x90, 0x90,
])

_hit = {"addr": 0, "stub": 0, "active": False}


def _dlog(line: str) -> None:
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
    except Exception:
        pass


def _write_bytes(addr: int, data: bytes) -> bool:
    try:
        old = wintypes.DWORD()
        if not kernel32.VirtualProtect(
            ctypes.c_void_p(addr), len(data), PAGE_READWRITE, ctypes.byref(old)
        ):
            return False
        ctypes.memmove(addr, data, len(data))
        kernel32.VirtualProtect(
            ctypes.c_void_p(addr), len(data), old.value, ctypes.byref(old)
        )
        return True
    except Exception:
        return False


def _hit_install() -> bool:
    if _hit["active"]:
        return True
    base = int(kernel32.GetModuleHandleW(None) or 0)
    if not base:
        _dlog("install FAIL no base")
        return False
    addr = base + HIT_RVA
    if ctypes.string_at(addr, len(HIT_ORIG)) != HIT_ORIG:
        _dlog("install FAIL orig mismatch: %s" % ctypes.string_at(addr, 22).hex())
        return False
    page = kernel32.VirtualAlloc(None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
    if not page:
        _dlog("install FAIL alloc")
        return False
    page = int(page)
    stb = bytearray(_HIT_STUB_CODE)
    stb += HIT_ORIG  # 0x1A..0x30 复刻原序言
    cont = addr + len(HIT_ORIG)
    stb += b"\x48\xB8" + struct.pack("<Q", cont) + b"\xFF\xE0"
    while len(stb) < 0x60:
        stb.append(0xCC)
    stb += b"\x00" * 16  # 0x60 flag + 填充 + 0x6C value
    ctypes.memmove(page, bytes(stb), len(stb))
    ctypes.c_ubyte.from_address(page + 0x60).value = 0
    # 入口补丁用 rax（不碰 r11），22 字节
    patch = b"\x48\xB8" + struct.pack("<Q", page) + b"\xFF\xE0" + b"\x90" * 10
    if not _write_bytes(addr, patch):
        _dlog("install FAIL patch")
        return False
    _hit.update(addr=addr, stub=page, active=True)
    _dlog("HIT hook OK addr=%#x stub=%#x" % (addr, page))
    return True


def _hit_set_record(on: bool) -> None:
    if _hit["active"]:
        ctypes.c_ubyte.from_address(_hit["stub"] + 0x60).value = 1 if on else 0


def _hit_value() -> int:
    if not _hit["active"]:
        return 0
    return ctypes.c_uint64.from_address(_hit["stub"] + 0x6C).value


# ---------------- 窗口子类 + 显示 ----------------

_hwnd = None
_last_disp = 0.0
_last_sample = 0.0
_last_move_log = 0.0


def _sample_pixol(tag: str) -> None:
    """采样一次坐标/HIT/pixol 并写日志（节流）。"""
    global _last_sample
    now = time.monotonic()
    if now - _last_sample < 0.1:
        return
    _last_sample = now
    try:
        import zbrush.commands as zbc

        px, py = zbc.get_mouse_pos(global_coordinates=False)
        mat = float(zbc.pixol_pick(5, px, py))
        nx = float(zbc.pixol_pick(6, px, py))
        ny = float(zbc.pixol_pick(7, px, py))
        nz = float(zbc.pixol_pick(8, px, py))
        kind = 1 if (mat != 0.0 or nx != 0.0 or ny != 0.0 or nz != 0.0) else 0
        _dlog("%s L=1 pos=(%.0f,%.0f) HIT=%#x mat=%g n=(%.3f,%.3f,%.3f) kind=%d"
              % (tag, px, py, _hit_value(), mat, nx, ny, nz, kind))
    except Exception as e:
        _dlog("%s sample err %r" % (tag, e))


def _update_display() -> None:
    global _last_disp
    now = time.monotonic()
    if now - _last_disp < 0.15:
        return
    _last_disp = now
    v = _hit_value()
    left = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
    txt = "HIT=%d L=%d" % (1 if v else 0, int(left))
    try:
        import zbrush.commands as zbc
        zbc.set_notebar_text(txt)
    except Exception:
        pass
    if left:
        _dlog("left=1 HIT=0x%x" % v)


def _handle_message(hwnd, msg, wparam, lparam) -> int:
    try:
        if msg == WM_LBUTTONDOWN:
            _hit_set_record(True)
        elif msg == WM_LBUTTONUP:
            _hit_set_record(False)
        elif msg == WM_TIMER and wparam == TIMER_ID:
            left = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
            _hit_set_record(left)
            if left:
                _sample_pixol("timer")
            _update_display()
            return 0
        elif msg == 0x0200:  # WM_MOUSEMOVE
            left = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
            if left:
                now = time.monotonic()
                if now - _last_move_log >= 0.05:
                    _last_move_log = now
                    px = lparam & 0xFFFF
                    py = (lparam >> 16) & 0xFFFF
                    _dlog("MOVE pos=(%d,%d) L=1" % (px, py))
                _sample_pixol("move")
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


def _find_window():
    _enum_result[0] = None
    try:
        user32.EnumWindows(_enum_find_zbrush, 0)
    except Exception:
        pass
    return _enum_result[0]


def main() -> None:
    global _hwnd
    try:
        with open(DEBUG_LOG, "w", encoding="utf-8") as f:
            f.write("=== nlr hit test ===\n")
    except Exception:
        pass
    _dlog("main start")
    if _hit_install():
        hwnd = _find_window()
        for _ in range(20):
            if hwnd:
                break
            time.sleep(0.5)
            hwnd = _find_window()
        _hwnd = hwnd
        if hwnd:
            comctl32.SetWindowSubclass(hwnd, _subclass_proc, SUBCLASS_ID, 0)
            user32.SetTimer(hwnd, TIMER_ID, 50, None)
            _dlog("ready hwnd=%s" % (hwnd,))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
