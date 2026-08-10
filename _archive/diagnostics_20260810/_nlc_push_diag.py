# -*- coding: utf-8 -*-
"""临时诊断：钩住事件推入函数，右键旋转时抓事件生成器调用者。

钩住 0xF11D0 / 0xF12A0 / 0xF1370（事件队列推入），捕获寄存器与栈上
返回地址链。右键旋转"无论如何触发"，其事件推入的调用者 = 旋转事件生成器。
日志：%TEMP%\\nlr_push.log
"""

import ctypes
import os
import struct
import sys
import traceback
from ctypes import wintypes

LOG = r"C:\Users\liuwenbo\AppData\Local\Temp\nlr_push.log"

WM_TIMER = 0x0113
DIAG_TIMER_ID = 0x50555348  # 'PUSH'

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
        "name": "PUSH_A",
        # 钩在入口后的纯指令区（避开 RIP 相对 cmp 与相对 jne）
        "rva": 0xF11E2,
        "orig": bytes.fromhex("66ff414848634144488d1440"),
        "orig_len": 12,
        "addr": 0, "stub": 0, "active": False, "last": 0,
    },
    {
        "name": "PUSH_B",
        "rva": 0xF12B4,
        "orig": bytes.fromhex("48895c24200f1f8000000000"),
        "orig_len": 12,
        "addr": 0, "stub": 0, "active": False, "last": 0,
    },
    {
        "name": "PUSH_C",
        "rva": 0xF1382,
        "orig": bytes.fromhex("4863414466ff4148488b0a488d0440"),
        "orig_len": 15,
        "addr": 0, "stub": 0, "active": False, "last": 0,
    },
]

# 数据槽：0xA0 起 9 个栈 qword（[rsp+0x30..0x70]），0xE8 起 rcx/rdx/r8/r9
DATA0 = 0xA0
REG0 = 0xE8


def _build_stub(orig, page, base, rva):
    st = bytearray()
    pos = 0
    for i in range(9):
        sdisp = 0x30 + i * 8
        daddr = DATA0 + i * 8
        st += bytes([0x48, 0x8B, 0x44, 0x24, sdisp])   # mov rax,[rsp+sdisp]
        st += b"\x48\x89\x05" + struct.pack("<i", daddr - (pos + 12))
        pos += 12
    for i, (reg, opc) in enumerate(((0x48, 0x0D), (0x48, 0x15), (0x4C, 0x05), (0x4C, 0x0D))):
        # mov [rip+disp], rcx/rdx/r8/r9
        st += bytes([reg, 0x89, opc]) + struct.pack("<i", (REG0 + i * 8) - (pos + 7))
        pos += 7
    st += orig
    cont = base + rva + len(orig)
    st += b"\x48\xB8" + struct.pack("<Q", cont) + b"\xFF\xE0"
    while len(st) < DATA0:
        st.append(0xCC)
    st += b"\x00" * (9 * 8 + 4 * 8)
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


_tick = [0]


@SubclassProcType
def _proc(hwnd, msg, wparam, lparam, u_id, ref_data):
    try:
        if msg == WM_TIMER and wparam == DIAG_TIMER_ID:
            _tick[0] += 1
            if _tick[0] % 100 == 0:
                _log("TICK %d" % _tick[0])
            base = int(kernel32.GetModuleHandleW(None) or 0)
            left = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
            right = bool(user32.GetAsyncKeyState(0x02) & 0x8000)
            for h in HOOKS:
                if not h["active"]:
                    continue
                caller = _rd64(h["stub"] + DATA0)
                if caller and caller != h["last"]:
                    h["last"] = caller
                    rcx = _rd64(h["stub"] + REG0)
                    rdx = _rd64(h["stub"] + REG0 + 8)
                    r8 = _rd64(h["stub"] + REG0 + 16)
                    r9 = _rd64(h["stub"] + REG0 + 24)
                    parts = []
                    for i in range(9):
                        v = _rd64(h["stub"] + DATA0 + i * 8)
                        if base and base <= v < base + 0x1E937000:
                            parts.append("%#x" % (v - base))
                        else:
                            parts.append("%#x" % v)
                    rva = (caller - base) if base and caller >= base else 0
                    _log("%s caller=%#x rva=%#x rcx=%#x rdx=%#x r8=%#x r9=%#x "
                         "left=%d right=%d stack=[%s]"
                         % (h["name"], caller, rva, rcx, rdx, r8 & 0xFFFF,
                            r9 & 0xFFFF, int(left), int(right), ", ".join(parts)))
            return 0
    except Exception as e:
        _log("PROC ERR %r" % (e,))
        return 0
    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


_proc_ref = _proc


def main():
    try:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("=== PUSH 观察 ===\npy=%s pid=%d\n" % (sys.version.split()[0], os.getpid()))
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
    if not comctl32.SetWindowSubclass(hwnd, _proc, 0x50555348, 0):
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
