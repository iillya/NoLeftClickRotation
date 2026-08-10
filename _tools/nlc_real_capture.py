# -*- coding: utf-8 -*-
"""Capture the real implementation function called by pybind dispatcher.

All zbrush.commands functions enter the shared dispatcher at 0x14189FA50.
Near its end (0x1418A1CA3) it loads the target function pointer:
    mov rax,[rsp+0x248]; mov r8,[rax+0x30]; xor edx,edx;
    mov rcx,[rsp+0x230]; call r8
We patch that 24-byte window, re-execute the loads, record r8 (the real
function) into a ring buffer, then call and jump back to 0x1418A1CBC.
"""

import ctypes
import os
import struct
import time
from ctypes import wintypes

LOG = os.path.join(os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"),
                   "nlr_real.log")

WM_TIMER = 0x0113
TIMER_ID = 0x4E4C5250
SUBCLASS_ID = 0x4E4C5251

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


_CAP_RVA = 0x18A1CA3
_CAP_ORIG = bytes.fromhex("488b8424480200004c8b403033d2488b8c243002000041ffd0")
_CONT = 0x14018A1CBC

_REC_LAST = 0x60
_REC_COUNT = 0x70
_REC_BUF = 0x80
_REC_SLOTS = 64

_cap = {"addr": 0, "stub": 0, "active": False}


def _build_stub(page: int) -> bytes:
    stb = bytearray()
    # 0x00: re-execute the first 22 bytes of the original window (no call)
    stb += _CAP_ORIG[:22]
    # 0x16: mov [rip+0x43], r8  -> +0x60 (last real fn)
    stb += b"\x4C\x89\x05" + struct.pack("<i", _REC_LAST - 0x1D)
    # 0x1D: lea r9,[rip+0x5C]    -> &buf (+0x80)
    stb += b"\x4C\x8D\x0D" + struct.pack("<i", _REC_BUF - 0x24)
    # 0x24: mov rax,[rip+0x45]   -> counter (+0x70)
    stb += b"\x48\x8B\x05" + struct.pack("<i", _REC_COUNT - 0x2B)
    # 0x2B: mov r10, rax
    stb += b"\x49\x89\xC2"
    # 0x2E: inc rax
    stb += b"\x48\xFF\xC0"
    # 0x31: mov [rip+0x38], rax  -> counter (+0x70)
    stb += b"\x48\x89\x05" + struct.pack("<i", _REC_COUNT - 0x38)
    # 0x38: and r10d, 63
    stb += b"\x41\x83\xE2\x3F"
    # 0x3C: shl r10, 3
    stb += b"\x49\xC1\xE2\x03"
    # 0x40: mov [r9+r10*8], r8   -> buf[idx] = real fn
    stb += b"\x4F\x89\x04\xD1"
    # 0x44: call r8 (single call)
    stb += b"\x41\xFF\xD0"
    # 0x47: mov r11, _CONT ; jmp r11
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
    patch = b"\x48\xB8" + struct.pack("<Q", page) + b"\xFF\xE0" + b"\x90" * 11
    if not _write_bytes(addr, patch):
        _dlog("install FAIL: write bytes err=%d" % ctypes.get_last_error())
        return False
    _cap.update(addr=addr, stub=page, active=True)
    _dlog("capture hook OK stub=%#x" % page)
    return True


def _cap_last() -> int:
    if not _cap["active"]:
        return 0
    return ctypes.c_uint64.from_address(_cap["stub"] + _REC_LAST).value


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
            down = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
            _dlog("xy=%.0f,%.0f mat=%s down=%d count=%d uniq=%s last=%#x"
                  % (_last_xy[0], _last_xy[1], _last_mat, down,
                     _cap_count(),
                     ",".join("%#x" % u for u in uniq),
                     _cap_last()))
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
            f.write("=== nlr real capture ===\n")
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
