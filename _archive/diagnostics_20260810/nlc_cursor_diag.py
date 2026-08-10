# -*- coding: utf-8 -*-
"""NLC_CursorDiag —— 记录 ZBrush 光标切换（只记录、不改行为）。

钩住 SetCursor 的 IAT 槽（RVA 0xDA21FA0），每次 ZBrush 调用 SetCursor 时
把光标句柄和调用者返回地址记到存根内存；定时器再把这些值连同 GetCursor()
当前光标、左/右键状态写入 %TEMP%\\nlr_cursor.log。
"""

import ctypes
import os
import struct
import time
from ctypes import wintypes

LOG = os.path.join(os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"), "nlr_cursor.log")

SETCURSOR_SLOT_RVA = 0xDA21FA0

WM_TIMER = 0x0113
TIMER_ID = 0x4E4C4352  # 'NLCR'
SUBCLASS_ID = 0x4E4C4353  # 'NLCS'

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40

user32 = ctypes.windll.user32
comctl32 = ctypes.WinDLL("comctl32")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t

SubclassProcType = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM,
    ctypes.c_void_p, ctypes.c_void_p)
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.SetTimer.restype = ctypes.c_void_p
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetCursor.restype = ctypes.c_void_p
user32.GetCursor.argtypes = []

comctl32.SetWindowSubclass.restype = wintypes.BOOL
comctl32.SetWindowSubclass.argtypes = [wintypes.HWND, SubclassProcType, ctypes.c_size_t, ctypes.c_size_t]
comctl32.DefSubclassProc.restype = LRESULT
comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]

kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
kernel32.VirtualProtect.restype = wintypes.BOOL
kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]


def _dlog(line: str) -> None:
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
    except Exception:
        pass


def _rd64(addr: int) -> int:
    return ctypes.c_uint64.from_address(addr).value


def _rd32(addr: int) -> int:
    return ctypes.c_uint32.from_address(addr).value


def _write_bytes(addr: int, data: bytes) -> bool:
    try:
        old = wintypes.DWORD()
        if not kernel32.VirtualProtect(
            ctypes.c_void_p(addr), len(data), PAGE_READWRITE, ctypes.byref(old)):
            return False
        ctypes.memmove(addr, data, len(data))
        kernel32.VirtualProtect(ctypes.c_void_p(addr), len(data), old.value, ctypes.byref(old))
        return True
    except Exception:
        return False


def _install() -> int:
    """安装 SetCursor IAT 钩子 + 0x11C49D0 光标类型记录，返回存根地址。"""
    global _type_stub
    base = int(kernel32.GetModuleHandleW(None) or 0)
    if not base:
        return 0
    slot = base + SETCURSOR_SLOT_RVA
    original = _rd64(slot)
    if not original:
        return 0
    page = int(kernel32.VirtualAlloc(
        None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE) or 0)
    if not page:
        return 0
    st = bytearray()
    st += b"\x48\x89\x0D" + struct.pack("<i", 0x40 - 0x07)   # mov [rip+0x39], rcx   -> +0x40
    st += b"\x48\x8B\x04\x24"                                 # mov rax, [rsp]        ; 返回地址
    st += b"\x48\x89\x05" + struct.pack("<i", 0x48 - 0x12)   # mov [rip+0x36], rax   -> +0x48
    st += b"\xFF\x05" + struct.pack("<i", 0x50 - 0x18)        # inc dword [rip+0x38]  -> +0x50
    st += b"\x48\xB8" + struct.pack("<Q", original)           # mov rax, original
    st += b"\xFF\xE0"                                         # jmp rax（尾调用）
    while len(st) < 0x40:
        st.append(0xCC)
    st += b"\x00" * 0x20
    ctypes.memmove(page, bytes(st), len(st))
    if not _write_bytes(slot, struct.pack("<Q", page)):
        return 0
    # 额外钩子：0x11C49D0 入口记录 ecx（光标类型 ID）
    t2 = int(kernel32.VirtualAlloc(
        None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE) or 0)
    if t2:
        st2 = bytearray()
        st2 += b"\x89\x0D" + struct.pack("<i", 0x40 - 0x06)      # mov [rip+0x3A], ecx -> +0x40
        st2 += b"\x48\x8B\x04\x24"                                # mov rax, [rsp]（调用者）
        st2 += b"\x48\x89\x05" + struct.pack("<i", 0x48 - 0x11)  # mov [rip+0x37], rax -> +0x48
        st2 += b"\xFF\x05" + struct.pack("<i", 0x50 - 0x17)       # inc dword [rip+0x39] -> +0x50
        st2 += bytes.fromhex("40534883ec30")                      # 原序言: push rbx; sub rsp,0x30
        # 原: mov rax, [rip+0x1c7f134b]（目标 RVA 0x1D8B5D28，距存根超 2GB，用绝对地址）
        st2 += b"\x48\xB8" + struct.pack("<Q", 0x140000000 + 0x1D8B5D28)  # mov rax, imm64
        st2 += b"\x48\x8B\x00"                                          # mov rax, [rax]
        st2 += b"\x48\xB8" + struct.pack("<Q", 0x1411C49DD) + b"\xFF\xE0"  # 跳回续点
        while len(st2) < 0x40:
            st2.append(0xCC)
        st2 += b"\x00" * 0x20
        ctypes.memmove(t2, bytes(st2), len(st2))
        if not _write_bytes(base + 0x11C49D0, b"\x49\xBB" + struct.pack("<Q", t2) + b"\x41\xFF\xE3" + b"\x90" * 3):
            t2 = 0
    _type_stub = t2
    _dlog("SetCursor hook stub=%#x typehook=%#x" % (page, t2))
    return page


_stub = 0
_type_stub = 0
_last_line = ""


def _snapshot() -> str:
    global _stub, _type_stub
    if not _stub:
        return ""
    cnt = _rd32(_stub + 0x50)
    cur = _rd64(_stub + 0x40)
    caller = _rd64(_stub + 0x48)
    now = int(user32.GetCursor() or 0)
    left = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
    right = bool(user32.GetAsyncKeyState(0x02) & 0x8000)
    extra = ""
    if _type_stub:
        tcnt = _rd32(_type_stub + 0x50)
        ttype = _rd32(_type_stub + 0x40)
        tcaller = _rd64(_type_stub + 0x48)
        extra = " tcnt=%d type=%#x tcaller=%#x" % (tcnt, ttype, tcaller)
    return "cnt=%d last=%#x caller=%#x cur=%#x L=%d R=%d%s" % (
        cnt, cur, caller, now, int(left), int(right), extra)


def _timer_tick():
    global _last_line
    line = _snapshot()
    if line and line != _last_line:
        _dlog(line)
        _last_line = line


def _handle_message(hwnd, msg, wparam, lparam) -> int:
    try:
        if msg == WM_TIMER and wparam == TIMER_ID:
            _timer_tick()
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


_enum_result = [None]


@WNDENUMPROC
def _enum_find(hwnd, lparam) -> bool:
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


def main() -> None:
    global _stub, _type_stub
    try:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("=== NLC_CursorDiag ===\npid=%d\n" % os.getpid())
    except Exception:
        pass
    _dlog("main start")
    hwnd = None
    for _ in range(40):
        _enum_result[0] = None
        try:
            user32.EnumWindows(_enum_find, 0)
        except Exception:
            pass
        hwnd = _enum_result[0]
        if hwnd and comctl32.SetWindowSubclass(hwnd, _subclass_proc, SUBCLASS_ID, 0):
            break
        time.sleep(0.5)
    if hwnd:
        user32.SetTimer(hwnd, TIMER_ID, 100, None)
        _dlog("timer on hwnd=%#x" % (hwnd or 0))
    _stub = _install()
    # _install 内部已记录 typehook 到日志


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
