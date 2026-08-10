# -*- coding: utf-8 -*-
"""Count how many times the pybind dispatcher entry 0x14189FA50 runs.
Only increments a counter; minimal risk."""

import ctypes
import os
import struct
import time
from ctypes import wintypes

LOG = os.path.join(os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"),
                   "nlr_disp.log")

WM_TIMER = 0x0113
TIMER_ID = 0x4E4C4445
SUBCLASS_ID = 0x4E4C4446

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
user32.SetTimer.restype = ctypes.c_void_p
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]

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

VK_LBUTTON = 0x01
_REC_COUNT = 0x60
_cap = {"stub": 0, "active": False}


def _dlog(line: str) -> None:
    try:
        with open(LOG, "a", encoding="utf-8") as f:
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


_CAP_RVA = 0x189FA50
_CAP_ORIG = bytes.fromhex("4c894424184889542410535657")
_CONT = 0x140189FA5D


def _install() -> bool:
    if _cap["active"]:
        return True
    try:
        base = int(kernel32.GetModuleHandleW(None) or 0)
    except Exception:
        return False
    if not base:
        return False
    addr = base + _CAP_RVA
    cur = ctypes.string_at(addr, len(_CAP_ORIG))
    if cur != _CAP_ORIG:
        _dlog("orig mismatch: %s" % cur.hex())
        return False
    page = kernel32.VirtualAlloc(None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
    if not page:
        return False
    page = int(page)
    stb = bytearray()
    stb += _CAP_ORIG  # 13 bytes
    # 0x0D: inc qword [rip+0x4D] -> +0x60
    stb += b"\x48\xFF\x05" + struct.pack("<i", _REC_COUNT - 0x14)
    # 0x14: mov r11, _CONT ; jmp r11
    stb += b"\x49\xBB" + struct.pack("<Q", _CONT)
    stb += b"\x41\xFF\xE3"
    while len(stb) < 0x80:
        stb.append(0xCC)
    ctypes.memmove(page, bytes(stb), len(stb))
    patch = b"\x48\xB8" + struct.pack("<Q", page) + b"\xFF\xE0" + b"\x90" * 1
    if not _write_bytes(addr, patch):
        return False
    _cap.update(stub=page, active=True)
    _dlog("entry hook OK stub=%#x" % page)
    return True


def _count() -> int:
    if not _cap["active"]:
        return 0
    return ctypes.c_uint64.from_address(_cap["stub"] + _REC_COUNT).value


_hwnd = None
_last_report = 0.0
_last_mat = None
_last_xy = (1548.0, 948.0)


def _run() -> None:
    global _last_report, _last_mat, _last_xy
    try:
        import zbrush.commands as zbc
        try:
            pos = zbc.get_mouse_pos(global_coordinates=False)
            x, y = pos
            _last_xy = (float(x), float(y))
        except Exception:
            x, y = 1548.0, 948.0
        try:
            _last_mat = zbc.pixol_pick(5, float(x), float(y))
        except Exception:
            pass
        now = time.time()
        if now - _last_report >= 1.0:
            _last_report = now
            down = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
            _dlog("xy=%.0f,%.0f mat=%s down=%d disp_count=%d"
                  % (_last_xy[0], _last_xy[1], _last_mat, down, _count()))
    except Exception as e:
        _dlog("err %r" % (e,))


def _handle_message(hwnd, msg, wparam, lparam) -> int:
    try:
        if msg == WM_TIMER and wparam == TIMER_ID:
            _run()
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


def main() -> None:
    try:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("=== nlr disp entry ===\n")
    except Exception:
        pass
    _dlog("main start")
    if not _install():
        return
    hwnd = None
    for _ in range(20):
        _enum_result[0] = None
        try:
            user32.EnumWindows(_enum_find_zbrush, 0)
        except Exception:
            pass
        hwnd = _enum_result[0]
        if hwnd:
            break
        time.sleep(0.5)
    _hwnd = hwnd
    if hwnd:
        comctl32.SetWindowSubclass(hwnd, _subclass_proc, SUBCLASS_ID, 0)
        user32.SetTimer(hwnd, TIMER_ID, 50, None)
        _dlog("ready")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
