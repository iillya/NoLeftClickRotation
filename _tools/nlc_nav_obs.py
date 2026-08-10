# -*- coding: utf-8 -*-
"""Disable left-button nav via 0x808: hook 0x5E4D90, force 0x808=0 on LMB."""

import ctypes
import os
import struct
import time
from ctypes import wintypes

LOG = os.path.join(os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"),
                   "nlr_navobs.log")

WM_TIMER = 0x0113
TIMER_ID = 0x4E4C4E4F
SUBCLASS_ID = 0x4E4C4E50
VK_F9 = 0x78

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
kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.ReadProcessMemory.restype = wintypes.BOOL
kernel32.ReadProcessMemory.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t),
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


HOOK = {
    "name": "nav_5e4d90",
    "rva": 0x5E4D90,
    "orig": bytes.fromhex("488bc448895010555356574156"),
    "cont": 0x1405E4D9D,
}

_stub = 0


def _install() -> bool:
    global _stub
    try:
        base = int(kernel32.GetModuleHandleW(None) or 0)
    except Exception:
        return False
    if not base:
        return False
    addr = base + HOOK["rva"]
    cur = ctypes.string_at(addr, len(HOOK["orig"]))
    if cur != HOOK["orig"]:
        _dlog("orig mismatch: %s" % cur.hex())
        return False
    page = kernel32.VirtualAlloc(
        None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
    if not page:
        return False
    page = int(page)
    stb = bytearray()
    stb += HOOK["orig"]
    n = len(HOOK["orig"])
    # 0x0D: mov [rip+0x4C], rcx -> +0x60 (save controller)
    stb += b"\x48\x89\x0D" + struct.pack("<i", 0x60 - (n + 7))
    n += 7
    # 0x14: cmp byte ptr [rip+0x55], 0 ; flag @ +0x70
    stb += b"\x80\x3D" + struct.pack("<i", 0x70 - (n + 7)) + b"\x00"
    n += 7
    # 0x1B: je +7 -> skip (0x24)
    stb += b"\x74\x07"
    n += 2
    # 0x1D: mov byte ptr [rcx+0x808], 0
    stb += b"\xC6\x81\x08\x08\x00\x00\x00"
    n += 7
    # 0x24: inc qword [rip+0x4D] -> +0x78
    stb += b"\x48\xFF\x05" + struct.pack("<i", 0x78 - (n + 7))
    n += 7
    # 0x2B: mov r11, cont ; jmp r11
    stb += b"\x49\xBB" + struct.pack("<Q", HOOK["cont"])
    stb += b"\x41\xFF\xE3"
    while len(stb) < 0x90:
        stb.append(0xCC)
    ctypes.memmove(page, bytes(stb), len(stb))
    patch = b"\x48\xB8" + struct.pack("<Q", page) + b"\xFF\xE0" + b"\x90" * (len(HOOK["orig"]) - 13)
    if not _write_bytes(addr, patch):
        return False
    _stub = page
    _dlog("hook OK stub=%#x" % page)
    return True


_hproc = None


def _read_mem(addr, size):
    global _hproc
    if not addr:
        return None
    if _hproc is None:
        _hproc = kernel32.GetCurrentProcess()
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t()
    if kernel32.ReadProcessMemory(_hproc, ctypes.c_void_p(addr), buf, size,
                                  ctypes.byref(n)):
        return buf.raw[:n.value]
    return None


def _snap():
    ctrl = ctypes.c_uint64.from_address(_stub + 0x60).value
    cnt = ctypes.c_uint64.from_address(_stub + 0x78).value
    b808 = _read_mem(ctrl + 0x808, 1)
    b74c = _read_mem(ctrl + 0x74C, 4)
    v808 = struct.unpack("<B", b808)[0] if b808 else None
    v74c = struct.unpack("<I", b74c)[0] if b74c else None
    return ctrl, v808, v74c, cnt


_hwnd = None
_recording = False
_f9_prev = False
_last_report = 0.0
_last_flag = -1


def _tick() -> None:
    global _recording, _f9_prev, _last_report, _last_flag
    try:
        f9 = bool(user32.GetAsyncKeyState(VK_F9) & 0x8000)
        if f9 and not _f9_prev:
            _recording = not _recording
            _dlog("F9 -> recording %s" % ("ON" if _recording else "OFF"))
        _f9_prev = f9
        left = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
        right = bool(user32.GetAsyncKeyState(0x02) & 0x8000)
        flag = 1 if (left and not right) else 0
        if flag != _last_flag:
            _last_flag = flag
            ctypes.c_uint8.from_address(_stub + 0x70).value = flag
            _dlog("flag -> %d" % flag)
        if not _recording:
            return
        down = left
        rdown = right
        ctrl, v808, v74c, cnt = _snap()
        now = time.time()
        if now - _last_report >= 0.15:
            _last_report = now
            _dlog("t=%.1f down=%d rdown=%d flag=%d nav: ctrl=%#x 808=%s 74c=%s n=%d"
                  % (now % 1000, down, rdown, flag, ctrl, v808,
                     ("%#x" % v74c) if v74c is not None else None, cnt))
    except Exception as e:
        _dlog("err %r" % (e,))


def _handle_message(hwnd, msg, wparam, lparam) -> int:
    try:
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
            f.write("=== nlr nav obs ===\n")
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
