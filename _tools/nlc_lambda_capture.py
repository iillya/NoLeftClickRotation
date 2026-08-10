# -*- coding: utf-8 -*-
"""Capture the real sampling lambda used by pixol_pick.

Hook the pybind parameter-processing window at 0x141898F90 (14-byte window):
    mov rdx,[rsi]; mov rcx,rdi; mov rax,[r14]; mov rdx,[rdx]; call rax
The stub re-executes those loads (12 bytes), records the lambda address into
a ring buffer, then jumps back to 0x141898F9E. A timer keeps calling
pixol_pick continuously (idle and while left button is pressed) so we can
compare which lambda runs in each state.
"""

import ctypes
import os
import struct
import time
from ctypes import wintypes

LOG = os.path.join(os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"),
                   "nlr_lambda.log")

WM_TIMER = 0x0113
TIMER_ID = 0x4E4C544C
SUBCLASS_ID = 0x4E4C544C

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


_CAP_RVA = 0x1898F90
_CAP_ORIG = bytes.fromhex("488b16488bcf498b06488b12")
_CONT = 0x1401898F9E

_REC_LAMBDA = 0x60
_REC_COUNT = 0x70
_REC_BUF = 0x80
_REC_SLOTS = 64

_cap = {"addr": 0, "stub": 0, "active": False}


def _build_stub(page: int) -> bytes:
    stb = bytearray()
    # 0x00: re-execute the 4 original loads (12 bytes)
    stb += bytes.fromhex("488b16488bcf498b06488b12")
    # 0x0C: mov [rip+disp], rax  -> +0x60 (last lambda); next RIP = 0x13
    stb += b"\x48\x89\x05" + struct.pack("<i", _REC_LAMBDA - 0x13)
    # 0x13: lea r9,[rip+disp]    -> &buf (+0x80); next RIP = 0x1A
    stb += b"\x4C\x8D\x0D" + struct.pack("<i", _REC_BUF - 0x1A)
    # 0x1A: mov rax,[rip+disp]   -> counter (+0x70); next RIP = 0x21
    stb += b"\x48\x8B\x05" + struct.pack("<i", _REC_COUNT - 0x21)
    # 0x21: mov r8, rax
    stb += b"\x49\x89\xC0"
    # 0x24: inc rax
    stb += b"\x48\xFF\xC0"
    # 0x27: mov [rip+disp],rax   -> counter (+0x70); next RIP = 0x2E
    stb += b"\x48\x89\x05" + struct.pack("<i", _REC_COUNT - 0x2E)
    # 0x2E: and r8d, 63
    stb += b"\x41\x83\xE0\x3F"
    # 0x32: shl r8, 3
    stb += b"\x49\xC1\xE0\x03"
    # 0x36: mov rax,[rip+disp]   -> last lambda (+0x60); next RIP = 0x3D
    stb += b"\x48\x8B\x05" + struct.pack("<i", _REC_LAMBDA - 0x3D)
    # 0x3D: mov [r9+r8*8], rax   -> buf[idx] = lambda
    stb += b"\x4B\x89\x04\xC1"
    # 0x41: call rax
    stb += b"\xFF\xD0"
    # 0x43: mov r11, _CONT ; jmp r11 (absolute jump, no +/-2GB limit)
    stb += b"\x49\xBB" + struct.pack("<Q", _CONT)
    stb += b"\x41\xFF\xE3"
    while len(stb) < _REC_BUF + _REC_SLOTS * 8:
        stb.append(0xCC)
    return bytes(stb)


def _cap_install() -> bool:
    if _cap["active"]:
        return True
    try:
        base = int(kernel32.GetModuleHandleW(None) or 0)
    except Exception as e:
        _dlog("install FAIL: base err %r" % (e,))
        return False
    if not base:
        _dlog("install FAIL: no base")
        return False
    addr = base + _CAP_RVA
    try:
        cur = ctypes.string_at(addr, len(_CAP_ORIG))
    except Exception as e:
        _dlog("install FAIL: read orig err %r (addr=%#x)" % (e, addr))
        return False
    if cur != _CAP_ORIG:
        _dlog("capture hook orig mismatch: %s" % cur.hex())
        return False
    page = kernel32.VirtualAlloc(None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
    if not page:
        _dlog("install FAIL: VirtualAlloc err=%d" % ctypes.get_last_error())
        return False
    page = int(page)
    stb = _build_stub(page)
    ctypes.memmove(page, stb, len(stb))
    patch = b"\x48\xB8" + struct.pack("<Q", page) + b"\xFF\xE0" + b"\x90\x90"
    if not _write_bytes(addr, patch):
        _dlog("install FAIL: write bytes err=%d" % ctypes.get_last_error())
        return False
    _cap.update(addr=addr, stub=page, active=True)
    _dlog("capture hook OK stub=%#x" % page)
    return True


def _cap_lambda() -> int:
    if not _cap["active"]:
        return 0
    return ctypes.c_uint64.from_address(_cap["stub"] + _REC_LAMBDA).value


def _cap_count() -> int:
    if not _cap["active"]:
        return 0
    return ctypes.c_uint64.from_address(_cap["stub"] + _REC_COUNT).value


def _cap_ring() -> list:
    if not _cap["active"]:
        return []
    count = _cap_count()
    out = []
    n = min(count, _REC_SLOTS)
    start = max(0, count - _REC_SLOTS) if count > _REC_SLOTS else 0
    for i in range(n):
        v = ctypes.c_uint64.from_address(
            _cap["stub"] + _REC_BUF + ((start + i) % _REC_SLOTS) * 8
        ).value
        out.append(v)
    return out


_hwnd = None
_last_report = 0.0
_last_err = ""
_last_xy = (1548.0, 948.0)
_last_mat = None


def _run() -> None:
    global _last_report, _last_err, _last_xy, _last_mat
    try:
        import zbrush.commands as zbc
        err = ""
        try:
            pos = zbc.get_mouse_pos(global_coordinates=False)
            x, y = pos
            _last_xy = (float(x), float(y))
        except Exception as e:
            err = "mouse %r" % (e,)
            x, y = 1548.0, 948.0
        try:
            v = zbc.pixol_pick(5, float(x), float(y))
            _last_mat = v
        except Exception as e:
            err = (err + " pixol %r" % (e,)).strip()
        if err and err != _last_err:
            _last_err = err
            _dlog("run err: %s" % err)
        now = time.time()
        if now - _last_report >= 1.0:
            _last_report = now
            ring = _cap_ring()
            uniq = sorted(set(ring))
            _dlog("xy=%.0f,%.0f mat=%s count=%d uniq=%s last=%#x"
                  % (_last_xy[0], _last_xy[1], _last_mat,
                     _cap_count(),
                     ",".join("%#x" % u for u in uniq),
                     _cap_lambda()))
    except Exception as e:
        _dlog("probe err %r" % (e,))


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
            f.write("=== nlr lambda capture ===\n")
    except Exception:
        pass
    _dlog("main start")
    if not _cap_install():
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
