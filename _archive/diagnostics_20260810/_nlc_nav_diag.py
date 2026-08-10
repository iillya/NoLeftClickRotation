# -*- coding: utf-8 -*-
"""临时诊断插件：观察候选导航函数何时被调用（不改变行为）。

钩住三个候选函数入口，记录每次调用（调用者、this、左键状态、光标索引）：
  0x1817020  每帧视图/导航更新（含旋转增量计算）
  0x1819B90  视图变换应用（接收旋转量）
  0x180F220  拖动应用
日志：%TEMP%\\nlr_nav.log
"""

import ctypes
import os
import struct
import sys
import traceback
from ctypes import wintypes

LOG = r"C:\Users\liuwenbo\AppData\Local\Temp\nlr_nav.log"

WM_TIMER = 0x0113
DIAG_TIMER_ID = 0x4E415654  # 'NAVT'

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40

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
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.SetTimer.restype = ctypes.c_void_p
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p]

comctl32.SetWindowSubclass.restype = wintypes.BOOL
comctl32.SetWindowSubclass.argtypes = [wintypes.HWND, SubclassProcType, ctypes.c_size_t, ctypes.c_size_t]
comctl32.DefSubclassProc.restype = ctypes.c_ssize_t
comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]

kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
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


def _rd32(a):
    return ctypes.c_uint32.from_address(a).value


def _rd64(a):
    return ctypes.c_uint64.from_address(a).value


HOOKS = [
    {
        "name": "NAV_UPDATE",
        "rva": 0x1817020,
        "orig": bytes.fromhex("40555657415541564157488dac24b8f7ffff"),
        "orig_len": 18,
        "addr": 0, "stub": 0, "active": False, "last": 0,
    },
    {
        "name": "VIEW_APPLY",
        "rva": 0x1819B90,
        "orig": bytes.fromhex("4c8bdc5341574881ecd8000000"),
        "orig_len": 13,
        "addr": 0, "stub": 0, "active": False, "last": 0,
    },
    {
        "name": "DRAG_APPLY",
        "rva": 0x180F220,
        "orig": bytes.fromhex("48894c2408555741574881ec70010000"),
        "orig_len": 16,
        "addr": 0, "stub": 0, "active": False, "last": 0,
    },
]


def _build_stub(orig, page, base, rva):
    """捕获 [rsp](调用者)、RCX(this)、RDX，执行原始序言，跳回 rva+len。"""
    st = bytearray()
    # mov rax,[rsp]; mov [rip+0x35],rax -> +0x40
    st += b"\x48\x8B\x04\x24"
    st += b"\x48\x89\x05" + struct.pack("<i", 0x40 - 0x0B)
    # mov [rip+0x36],rcx -> +0x48
    st += b"\x48\x89\x0D" + struct.pack("<i", 0x48 - 0x12)
    # mov [rip+0x37],rdx -> +0x50
    st += b"\x48\x89\x15" + struct.pack("<i", 0x50 - 0x19)
    st += orig
    cont = base + rva + len(orig)
    st += b"\x48\xB8" + struct.pack("<Q", cont) + b"\xFF\xE0"
    st += b"\xCC" * (0x40 - len(st))
    st += b"\x00" * 24
    return bytes(st)


def _install(h):
    base = int(kernel32.GetModuleHandleW(None) or 0)
    if not base:
        return
    addr = base + h["rva"]
    try:
        if ctypes.string_at(addr, h["orig_len"]) != h["orig"]:
            _log("SKIP %s version mismatch" % h["name"])
            return
    except Exception:
        return
    page = int(kernel32.VirtualAlloc(None, 0x1000, MEM_COMMIT | MEM_RESERVE,
                                     PAGE_EXECUTE_READWRITE) or 0)
    if not page:
        return
    st = _build_stub(h["orig"], page, base, h["rva"])
    ctypes.memmove(page, st, len(st))
    patch = b"\x48\xB8" + struct.pack("<Q", page) + b"\xFF\xE0"
    old = wintypes.DWORD()
    if not kernel32.VirtualProtect(ctypes.c_void_p(addr), 12, PAGE_READWRITE,
                                   ctypes.byref(old)):
        return
    ctypes.memmove(addr, patch, 12)
    kernel32.VirtualProtect(ctypes.c_void_p(addr), 12, old.value, ctypes.byref(old))
    h.update(addr=addr, stub=page, active=True)
    _log("HOOK OK %s addr=%#x stub=%#x" % (h["name"], addr, page))


@SubclassProcType
def _proc(hwnd, msg, wparam, lparam, u_id, ref_data):
    try:
        if msg == WM_TIMER and wparam == DIAG_TIMER_ID:
            base = int(kernel32.GetModuleHandleW(None) or 0)
            left = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
            cidx = _rd32(base + 0x1D881AD8) if base else 0
            for h in HOOKS:
                if not h["active"]:
                    continue
                caller = _rd64(h["stub"] + 0x40)
                if caller and caller != h["last"]:
                    h["last"] = caller
                    vthis = _rd64(h["stub"] + 0x48)
                    rva = (caller - base) if base and caller >= base else 0
                    _log("%s caller=%#x rva=%#x this=%#x left=%d cidx=%d"
                         % (h["name"], caller, rva, vthis, int(left), cidx))
            return 0
    except Exception as e:
        _log("PROC ERR %r" % (e,))
        return 0
    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


_proc_ref = _proc


def main():
    try:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("=== NAV 观察 ===\npy=%s pid=%d\n" % (sys.version.split()[0], os.getpid()))
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
    if not comctl32.SetWindowSubclass(hwnd, _proc, 0x4E415653, 0):
        _log("SUBCLASS FAIL")
        return
    user32.SetTimer(hwnd, DIAG_TIMER_ID, 50, None)
    for h in HOOKS:
        try:
            _install(h)
        except Exception as e:
            _log("INSTALL ERR %s %r\n%s" % (h["name"], e, traceback.format_exc()))
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
