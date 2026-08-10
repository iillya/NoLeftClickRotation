# -*- coding: utf-8 -*-
"""Hook 0x53F (pixol_pick dispatch) to record r13 (record ptr) only.
Then Python resolves the real sampling function from the record."""

import ctypes
import os
import struct
import threading
import time
from ctypes import wintypes

LOG = os.path.join(os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"),
                   "nlr_53f.log")

WM_TIMER = 0x0113
TIMER_ID = 0x4E4C3533
SUBCLASS_ID = 0x4E4C3534

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
    "rva": 0x1898F90,
    "orig": bytes.fromhex("488b16488bcf498b06488b12"),
    "cont": 0x140189F9E,
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
    # re-execute the 12-byte load sequence
    stb += HOOK["orig"]
    # 0x0C: mov [rip+0x54], r13 -> +0x60
    stb += b"\x4C\x89\x2D" + struct.pack("<i", 0x60 - 0x13)
    # 0x13: inc qword [rip+0x5D] -> +0x78
    stb += b"\x48\xFF\x05" + struct.pack("<i", 0x78 - 0x1A)
    # 0x1A: mov r11, cont ; jmp r11 (cont = 0x1898F9E after call)
    stb += b"\x49\xBB" + struct.pack("<Q", HOOK["cont"])
    stb += b"\x41\xFF\xE3"
    while len(stb) < 0x90:
        stb.append(0xCC)
    ctypes.memmove(page, bytes(stb), len(stb))
    patch = b"\x48\xB8" + struct.pack("<Q", page) + b"\xFF\xE0" + b"\x90" * (14 - 13)
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


def _rd64(addr):
    b = _read_mem(addr, 8)
    return struct.unpack("<Q", b)[0] if b and len(b) == 8 else 0


def _probe_record():
    rec = ctypes.c_uint64.from_address(_stub + 0x60).value
    cnt = ctypes.c_uint64.from_address(_stub + 0x78).value
    _dlog("record=%#x count=%d" % (rec, cnt))
    if rec and rec != 0xCCCCCCCCCCCCCCCC:
        # scan record region for code pointers
        for off in range(0, 0x400, 8):
            v = _rd64(rec + off)
            if 0x140000000 <= v < 0x160000000:
                _dlog("  rec+%#x -> %#x CODE" % (off, v))
        # also follow heap ptrs inside record looking for code
        for off in range(0, 0x400, 8):
            v = _rd64(rec + off)
            if 0x10000 <= v < 0x7FFFFFFFFFFF and not (0x140000000 <= v < 0x160000000):
                inner = _read_mem(v, 0x80)
                if inner:
                    for i in range(0, len(inner) - 7, 8):
                        iv = struct.unpack_from("<Q", inner, i)[0]
                        if 0x140000000 <= iv < 0x160000000:
                            _dlog("  rec+%#x -> %#x +%#x = %#x CODE"
                                  % (off, v, i, iv))


_hwnd = None
_boot = time.monotonic()
_done = False


def _tick() -> None:
    global _done
    if time.monotonic() - _boot < 25:
        return
    if _done:
        return
    _done = True
    try:
        import zbrush.commands as zbc
        _dlog("calling pixol_pick idle")
        zbc.pixol_pick(5, 1548.0, 948.0)
    except Exception as e:
        _dlog("pixol err %r" % (e,))
    time.sleep(0.5)
    _probe_record()


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
            f.write("=== nlr 53f rec ===\n")
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
        user32.SetTimer(hwnd, TIMER_ID, 100, None)
        _dlog("ready")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
