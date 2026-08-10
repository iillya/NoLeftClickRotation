# -*- coding: utf-8 -*-
"""临时诊断：IAT 钩 GetAsyncKeyState，捕获 vKey 与调用者（不改行为）。

右键旋转"无论如何都触发"：若旋转由轮询驱动，GAKS(VK_RBUTTON=2) 的调用者
就是旋转轮询函数。同时记录 VK_LBUTTON=1 的调用者用于对比。
日志：%TEMP%\\nlr_gaks.log
"""

import ctypes
import os
import struct
import sys
import traceback
from ctypes import wintypes

LOG = r"C:\Users\liuwenbo\AppData\Local\Temp\nlr_gaks.log"

WM_TIMER = 0x0113
DIAG_TIMER_ID = 0x47414B53  # 'GAKS'

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40
ORDINAL_FLAG = 0x8000000000000000

user32 = ctypes.windll.user32
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
comctl32 = ctypes.WinDLL("comctl32")

SubclassProcType = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
    ctypes.c_size_t, ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_void_p)
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.SetTimer.restype = ctypes.c_void_p
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p]

comctl32.SetWindowSubclass.restype = wintypes.BOOL
comctl32.SetWindowSubclass.argtypes = [wintypes.HWND, SubclassProcType, ctypes.c_size_t, ctypes.c_size_t]
comctl32.DefSubclassProc.restype = ctypes.c_ssize_t
comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]

kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetProcAddress.restype = ctypes.c_void_p
kernel32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
kernel32.VirtualProtect.restype = wintypes.BOOL
kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]


def _log(line):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _rd16(a):
    return ctypes.c_uint16.from_address(a).value


def _rd32(a):
    return ctypes.c_uint32.from_address(a).value


def _rd64(a):
    return ctypes.c_uint64.from_address(a).value


def _wr64(a, v):
    old = wintypes.DWORD()
    if not kernel32.VirtualProtect(ctypes.c_void_p(a), 8, PAGE_READWRITE, ctypes.byref(old)):
        return False
    ctypes.c_uint64.from_address(a).value = v
    kernel32.VirtualProtect(ctypes.c_void_p(a), 8, old.value, ctypes.byref(old))
    return True


# 存根：保存 vkey(+0x18)、8 个栈 qword(+0xA0..)、跳转真实函数(指针 +0xE8)
STUB_PREFIX = bytes([
    0x48, 0x8B, 0x04, 0x24,                    # 0x00 mov rax,[rsp]
    0x48, 0x89, 0x05, 0x95, 0x00, 0x00, 0x00,  # 0x04 -> +0xA0
    0x48, 0x8B, 0x44, 0x24, 0x08,              # 0x0B mov rax,[rsp+8]
    0x48, 0x89, 0x05, 0x91, 0x00, 0x00, 0x00,  # 0x10 -> +0xA8
    0x48, 0x8B, 0x44, 0x24, 0x10,              # 0x17 mov rax,[rsp+16]
    0x48, 0x89, 0x05, 0x8D, 0x00, 0x00, 0x00,  # 0x1C -> +0xB0
    0x48, 0x8B, 0x44, 0x24, 0x18,              # 0x23 mov rax,[rsp+24]
    0x48, 0x89, 0x05, 0x89, 0x00, 0x00, 0x00,  # 0x28 -> +0xB8
    0x48, 0x8B, 0x44, 0x24, 0x20,              # 0x2F mov rax,[rsp+32]
    0x48, 0x89, 0x05, 0x85, 0x00, 0x00, 0x00,  # 0x34 -> +0xC0
    0x48, 0x8B, 0x44, 0x24, 0x28,              # 0x3B mov rax,[rsp+40]
    0x48, 0x89, 0x05, 0x81, 0x00, 0x00, 0x00,  # 0x40 -> +0xC8
    0x48, 0x8B, 0x44, 0x24, 0x30,              # 0x47 mov rax,[rsp+48]
    0x48, 0x89, 0x05, 0x7D, 0x00, 0x00, 0x00,  # 0x4C -> +0xD0
    0x48, 0x8B, 0x44, 0x24, 0x38,              # 0x53 mov rax,[rsp+56]
    0x48, 0x89, 0x05, 0x79, 0x00, 0x00, 0x00,  # 0x58 -> +0xD8
    0x48, 0x89, 0x0D, 0x7A, 0x00, 0x00, 0x00,  # 0x5F mov [rip+0x7A],rcx -> +0xE0 (vkey)
    0xFF, 0x25, 0x7C, 0x00, 0x00, 0x00,        # 0x66 jmp [rip+0x7C] -> +0xE8 (real)
    0xCC, 0xCC, 0xCC,
])


def _find_iat_slot(func_name):
    try:
        base = int(kernel32.GetModuleHandleW(None) or 0)
        if not base or _rd16(base) != 0x5A4D:
            return None, None
        pe = base + _rd32(base + 0x3C)
        if _rd32(pe) != 0x00004550:
            return None, None
        opt = pe + 24
        if _rd16(opt) != 0x20B:
            return None, None
        image_size = _rd32(opt + 56)
        imp_rva = _rd32(opt + 120)
        imp_size = _rd32(opt + 124)
        if not (0 < imp_rva < image_size and 0 < imp_size < 0x10000):
            return None, None
        real = int(kernel32.GetProcAddress(user32._handle, func_name) or 0)
        desc = base + imp_rva
        idx = 0
        while idx * 20 < imp_size:
            d = desc + idx * 20
            oft_rva = _rd32(d)
            ft_rva = _rd32(d + 16)
            if 0 < ft_rva < image_size:
                i = 0
                while i < 2048:
                    slot = base + ft_rva + i * 8
                    if not (0 < ft_rva + i * 8 < image_size and ft_rva + i * 8 + 8 <= image_size):
                        break
                    if oft_rva and 0 < oft_rva + i * 8 + 8 <= image_size:
                        entry = _rd64(base + oft_rva + i * 8)
                        if entry == 0:
                            break
                        if entry & ORDINAL_FLAG:
                            i += 1
                            continue
                        byname = entry & ~ORDINAL_FLAG
                        if 0 < byname + 2 < image_size:
                            nm = ctypes.string_at(base + byname + 2, 32).split(b"\x00", 1)[0]
                            if nm == func_name:
                                return slot, _rd64(slot)
                    else:
                        val = _rd64(slot)
                        if val == 0:
                            break
                        if val == real:
                            return slot, val
                    i += 1
            idx += 1
    except Exception:
        return None, None
    return None, None


_iat = {"slot": 0, "original": 0, "stub": 0, "active": False, "last": 0}
_tick = [0]


def _install():
    if _iat["active"]:
        return True
    slot, original = _find_iat_slot(b"GetAsyncKeyState")
    if not slot or not original:
        _log("IAT FAIL slot=%s" % (hex(slot) if slot else None))
        return False
    real = int(kernel32.GetProcAddress(user32._handle, b"GetAsyncKeyState") or 0)
    if not real or original != real:
        _log("IAT FAIL original != real")
        return False
    page = int(kernel32.VirtualAlloc(None, 0x1000, MEM_COMMIT | MEM_RESERVE,
                                     PAGE_EXECUTE_READWRITE) or 0)
    if not page:
        _log("IAT FAIL alloc")
        return False
    ctypes.memmove(page, STUB_PREFIX, len(STUB_PREFIX))
    ctypes.memmove(page + 0xE8, struct.pack("<Q", real), 8)
    if not _wr64(slot, page):
        _log("IAT FAIL patch")
        return False
    _iat.update(slot=slot, original=original, stub=page, active=True)
    _log("IAT OK slot=%#x stub=%#x real=%#x" % (slot, page, real))
    return True


@SubclassProcType
def _proc(hwnd, msg, wparam, lparam, u_id, ref_data):
    try:
        if msg == WM_TIMER and wparam == DIAG_TIMER_ID:
            _tick[0] += 1
            if _tick[0] % 100 == 0:
                _log("TICK %d" % _tick[0])
            base = int(kernel32.GetModuleHandleW(None) or 0)
            if _iat["active"]:
                vkey = _rd64(_iat["stub"] + 0xE0)
                caller = _rd64(_iat["stub"] + 0xA0)
                if caller and caller != _iat["last"]:
                    _iat["last"] = caller
                    parts = []
                    for i in range(8):
                        v = _rd64(_iat["stub"] + 0xA0 + i * 8)
                        if base and base <= v < base + 0x1E937000:
                            parts.append("%#x" % (v - base))
                        else:
                            parts.append("%#x" % v)
                    rva = (caller - base) if base and caller >= base else 0
                    _log("GAKS vkey=%d caller=%#x rva=%#x stack=[%s]"
                         % (vkey & 0xFFFF, caller, rva, ", ".join(parts)))
            return 0
    except Exception as e:
        _log("PROC ERR %r" % (e,))
        return 0
    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


_proc_ref = _proc


def main():
    try:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("=== GAKS 信标 ===\npy=%s pid=%d\n" % (sys.version.split()[0], os.getpid()))
    except Exception:
        pass
    pid = os.getpid()
    found = [None]

    @WNDENUMPROC
    def enum_cb(h, lp):
        try:
            cls = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(h, cls, 256)
            if cls.value == "ZBrush":
                wpid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(h, ctypes.byref(wpid))
                if wpid.value == pid:
                    found[0] = h
                    return False
        except Exception:
            pass
        return True

    try:
        user32.EnumWindows(enum_cb, 0)
    except Exception as e:
        _log("ENUM ERR %r" % (e,))
    hwnd = found[0]
    if not hwnd:
        _log("NO WINDOW")
        return
    if not comctl32.SetWindowSubclass(hwnd, _proc, 0x47414B53, 0):
        _log("SUBCLASS FAIL")
        return
    user32.SetTimer(hwnd, DIAG_TIMER_ID, 50, None)
    try:
        _install()
    except Exception as e:
        _log("INSTALL ERR %r\n%s" % (e, traceback.format_exc()))
    _log("READY hwnd=%#x" % int(hwnd))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write("FATAL %r\n%s\n" % (e, traceback.format_exc()))
        except Exception:
            pass
