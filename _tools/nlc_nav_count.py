# -*- coding: utf-8 -*-
"""Nav-function counter experiment: hook candidate entries, count only."""

import ctypes
import os
import struct
import time
from ctypes import wintypes

LOG = os.path.join(os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"),
                   "nlr_navcount.log")

WM_TIMER = 0x0113
TIMER_ID = 0x4E4C4E41
SUBCLASS_ID = 0x4E4C4E42
VK_LBUTTON = 0x01
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t

user32 = ctypes.WinDLL("user32")
comctl32 = ctypes.WinDLL("comctl32")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

SubclassProcType = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM,
    ctypes.c_void_p, ctypes.c_void_p,
)
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

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


HOOKS = [
    {"name": "nav_entry", "rva": 0x5E4D90,
     "orig": bytes.fromhex("488bc448895010555356574156"),
     "cont": 0x1405E4D9D},
    {"name": "nav_check", "rva": 0x5E5127,
     "orig": bytes.fromhex("84c00f840e020000498b816821"),
     "cont": 0x1405E5134},
    {"name": "rot_math", "rva": 0x5EE414,
     "orig": bytes.fromhex("44383539686e0ec5f829bc2420060000"),
     "cont": 0x1405EE423},
    {"name": "frame_proc", "rva": 0x5F0FC0,
     "orig": bytes.fromhex("4c8bdc5553498d6ba14881ecc8000000"),
     "cont": 0x1405F0FD0},
    {"name": "action_proc", "rva": 0x12D88A0,
     "orig": bytes.fromhex("488954241048894c240855574155"),
     "cont": 0x1412D88AE},
]

_hooks = []


def _install() -> bool:
    try:
        base = int(kernel32.GetModuleHandleW(None) or 0)
    except Exception:
        return False
    if not base:
        return False
    for h in HOOKS:
        addr = base + h["rva"]
        cur = ctypes.string_at(addr, len(h["orig"]))
        if cur != h["orig"]:
            _dlog("orig mismatch %s: %s" % (h["name"], cur.hex()))
            return False
        page = kernel32.VirtualAlloc(
            None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
        if not page:
            return False
        page = int(page)
        stb = bytearray()
        stb += h["orig"]
        n = len(h["orig"])
        # inc qword [rip+disp] -> +0x60
        stb += b"\x48\xFF\x05" + struct.pack("<i", 0x60 - (n + 7))
        stb += b"\x49\xBB" + struct.pack("<Q", h["cont"])
        stb += b"\x41\xFF\xE3"
        while len(stb) < 0x80:
            stb.append(0xCC)
        ctypes.memmove(page, bytes(stb), len(stb))
        patch = b"\x48\xB8" + struct.pack("<Q", page) + b"\xFF\xE0" + b"\x90" * (n - 13)
        if not _write_bytes(addr, patch):
            return False
        _hooks.append({"name": h["name"], "stub": page})
        _dlog("hook OK %s stub=%#x" % (h["name"], page))
    return True


def _counts():
    out = {}
    for h in _hooks:
        out[h["name"]] = ctypes.c_uint64.from_address(h["stub"] + 0x60).value
    return out


_hwnd = None
_last_report = 0.0
_last_msg = 0.0


def _tick() -> None:
    global _last_report
    try:
        import zbrush.commands as zbc
        mat = "?"
        try:
            x, y = zbc.get_mouse_pos(global_coordinates=False)
            mat = zbc.pixol_pick(5, float(x), float(y))
        except Exception:
            pass
        down = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
        c = _counts()
        now = time.time()
        if now - _last_report >= 0.2:
            _last_report = now
            _dlog("mat=%s down=%d %s"
                  % (mat, down, " ".join("%s=%d" % (k, c[k]) for k in sorted(c))))
    except Exception as e:
        _dlog("err %r" % (e,))


def _handle_message(hwnd, msg, wparam, lparam) -> int:
    global _last_msg
    try:
        if msg in (WM_LBUTTONDOWN, WM_LBUTTONUP, WM_RBUTTONDOWN, WM_RBUTTONUP):
            now = time.time()
            if now - _last_msg > 0.25:
                _last_msg = now
                _dlog("MSG %#x" % msg)
        if msg == WM_TIMER and wparam == TIMER_ID:
            _tick()
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
            f.write("=== nlr navcount ===\n")
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
        user32.SetTimer(hwnd, TIMER_ID, 20, None)
        _dlog("ready")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
