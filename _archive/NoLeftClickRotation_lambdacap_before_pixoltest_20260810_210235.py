# -*- coding: utf-8 -*-
"""运行时抓取 pixol_pick 真正调用的采样 lambda 地址。

钩住 pybind process_arguments 中的间接调用点 0x141898F90（14 字节窗口），
复刻其寄存器加载后记录 [r14]（lambda 指针）再照常调用。
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


# 钩点 0x141898F90（14 字节窗口）：
#   mov rdx,[rsi]; mov rcx,rdi; mov rax,[r14]; mov rdx,[rdx]; call rax
# 存根复刻加载、记录 [r14]（lambda），call 后跳回 0x141898F9E。
_CAP_RVA = 0x1898F90
_CAP_ORIG = bytes.fromhex("488b16488bcf498b06488b12")
_CONT = 0x1401898F9E

_cap = {"addr": 0, "stub": 0, "active": False}


def _cap_install() -> bool:
    if _cap["active"]:
        return True
    base = int(kernel32.GetModuleHandleW(None) or 0)
    if not base:
        return False
    addr = base + _CAP_RVA
    if ctypes.string_at(addr, len(_CAP_ORIG)) != _CAP_ORIG:
        _dlog("capture hook orig mismatch: %s" % ctypes.string_at(addr, 14).hex())
        return False
    page = kernel32.VirtualAlloc(None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
    if not page:
        return False
    page = int(page)
    stb = bytearray()
    stb += bytes.fromhex("488b16488bcf498b06488b12")  # 复刻 4 个加载
    stb += b"\x48\x89\x05" + struct.pack("<i", 0)    # mov [rip+disp],rax（记录点稍后填）
    stb += b"\xFF\xD0"                                # call rax
    stb += b"\xE9" + struct.pack("<i", 0)             # jmp 0x141898F9E
    rec_pos = 14
    jmp_pos = 21
    # 记录 lambda 到 stub+0x60
    stb[rec_pos + 3:rec_pos + 7] = struct.pack("<i", 0x60 - (rec_pos + 7))
    stb[jmp_pos + 1:jmp_pos + 5] = struct.pack("<i", _CONT - (jmp_pos + 5) - 0x140000000)
    while len(stb) < 0x60:
        stb.append(0xCC)
    stb += b"\x00\x00\x00\x00\x00\x00\x00\x00"
    ctypes.memmove(page, bytes(stb), len(stb))
    patch = b"\x48\xB8" + struct.pack("<Q", page) + b"\xFF\xE0" + b"\x90\x90"
    if not _write_bytes(addr, patch):
        return False
    _cap.update(addr=addr, stub=page, active=True)
    _dlog("capture hook OK stub=%#x" % page)
    return True


def _cap_lambda() -> int:
    if not _cap["active"]:
        return 0
    return ctypes.c_uint64.from_address(_cap["stub"] + 0x60).value


_hwnd = None
_start = 0.0
_done = False


def _run() -> None:
    global _done
    if _done:
        return
    _done = True
    _dlog("probe start")
    try:
        import zbrush.commands as zbc
        _dlog("calling pixol_pick(5,1548,948)")
        v = zbc.pixol_pick(5, 1548.0, 948.0)
        _dlog("pixol result=%s lambda=%#x" % (v, _cap_lambda()))
        _dlog("calling pixol_pick(6,1548,948)")
        v2 = zbc.pixol_pick(6, 1548.0, 948.0)
        _dlog("pixol result=%s lambda=%#x" % (v2, _cap_lambda()))
    except Exception as e:
        _dlog("probe err %r" % (e,))
    _dlog("probe done")


def _handle_message(hwnd, msg, wparam, lparam) -> int:
    try:
        if msg == WM_TIMER and wparam == TIMER_ID:
            if time.monotonic() > _start + 6:
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
    global _hwnd, _start
    _start = time.monotonic()
    try:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("=== nlr lambda capture ===\n")
    except Exception:
        pass
    _dlog("main start")
    if not _cap_install():
        return
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
