# -*- coding: utf-8 -*-
"""Observe nav/sculpt state switch: hook 0x5F0FC0 and 0x5F3880, record only."""

import ctypes
import os
import struct
import time
from ctypes import wintypes

LOG = os.path.join(os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"),
                   "nlr_state.log")

WM_TIMER = 0x0113
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
TIMER_ID = 0x4E4C5354
SUBCLASS_ID = 0x4E4C5355
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


HOOKS = [
    {"name": "frame_5f0fc0", "rva": 0x5F0FC0,
     "orig": bytes.fromhex("4c8bdc5553498d6ba14881ecc8000000"),
     "cont": 0x1405F0FD0,
     "read808": True},
]

_hooks = []


def _build_stub(page, orig, cont, read808):
    stb = bytearray()
    stb += orig
    n = len(orig)
    off = n
    # mov [rip+disp], rcx  -> +0x60 (controller, no deref - safe)
    stb += b"\x48\x89\x0D" + struct.pack("<i", 0x60 - (off + 7))
    off += 7
    # inc qword [rip+disp] -> +0x78
    stb += b"\x48\xFF\x05" + struct.pack("<i", 0x78 - (off + 7))
    off += 7
    # mov r11, cont ; jmp r11
    stb += b"\x49\xBB" + struct.pack("<Q", cont)
    stb += b"\x41\xFF\xE3"
    while len(stb) < 0x90:
        stb.append(0xCC)
    return bytes(stb)


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
        stub = _build_stub(page, h["orig"], h["cont"], h.get("read808", False))
        ctypes.memmove(page, stub, len(stub))
        patch = b"\x48\xB8" + struct.pack("<Q", page) + b"\xFF\xE0" + b"\x90" * (len(h["orig"]) - 13)
        if not _write_bytes(addr, patch):
            return False
        _hooks.append({"name": h["name"], "stub": page})
        _dlog("hook OK %s stub=%#x" % (h["name"], page))
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
    out = {}
    for h in _hooks:
        s = h["stub"]
        ctrl = ctypes.c_uint64.from_address(s + 0x60).value
        cnt = ctypes.c_uint64.from_address(s + 0x78).value
        b808 = _read_mem(ctrl + 0x808, 1)
        b74c = _read_mem(ctrl + 0x74C, 4)
        v808 = struct.unpack("<B", b808)[0] if b808 else None
        v74c = struct.unpack("<I", b74c)[0] if b74c else None
        out[h["name"]] = (ctrl, v808, v74c, cnt)
    return out


def _controller_bytes():
    if not _hooks:
        return 0, None
    stub = _hooks[0]["stub"]
    controller = ctypes.c_uint64.from_address(stub + 0x60).value
    if not controller:
        return 0, None
    return controller, _read_mem(controller, 0x1000)


def _log_diff(label, controller, before, after):
    if before is None or after is None:
        _dlog("%s ctrl=%#x snapshot-missing" % (label, controller))
        return
    changed = [
        (index, left, right)
        for index, (left, right) in enumerate(zip(before, after))
        if left != right
    ]
    _dlog("%s ctrl=%#x changed=%d" % (label, controller, len(changed)))
    for index, left, right in changed[:256]:
        _dlog("  +%#05x %02x>%02x" % (index, left, right))


_hwnd = None
_last_report = 0.0
_recording = False
_f9_prev = False
_installed = False
_left_prev = False
_edge_snapshot = None


def _tick() -> None:
    global _last_report, _recording, _f9_prev, _installed
    global _left_prev, _edge_snapshot
    try:
        f9 = bool(user32.GetAsyncKeyState(VK_F9) & 0x8000)
        if f9 and not _f9_prev:
            if not _installed:
                _installed = _install()
                _dlog("F9 install %s" % ("OK" if _installed else "FAILED"))
            _recording = _installed and not _recording
            _left_prev = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
            controller, _edge_snapshot = _controller_bytes()
            _dlog("baseline ctrl=%#x" % controller)
            _dlog("F9 -> recording %s" % ("ON" if _recording else "OFF"))
        _f9_prev = f9
        if not _recording:
            return
        down = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
        rdown = bool(user32.GetAsyncKeyState(0x02) & 0x8000)
        if _edge_snapshot is None:
            controller, current = _controller_bytes()
            if current is not None:
                _edge_snapshot = current
                _dlog("controller ready ctrl=%#x" % controller)
        if down != _left_prev:
            controller, current = _controller_bytes()
            _log_diff(
                "EDGE_DOWN" if down else "EDGE_UP",
                controller,
                _edge_snapshot,
                current,
            )
            _edge_snapshot = current
            _left_prev = down
        s = _snap()
        now = time.time()
        if now - _last_report >= 0.15:
            _last_report = now
            parts = []
            for name, (ctrl, v808, v74c, cnt) in s.items():
                parts.append("%s ctrl=%#x 808=%#x 74c=%#x n=%d"
                             % (name, ctrl, v808, v74c, cnt))
            _dlog("t=%.1f down=%d rdown=%d %s" % (time.time() % 1000, down, rdown, " | ".join(parts)))
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
            f.write("=== nlr state obs ===\n")
    except Exception:
        pass
    _dlog("main start")
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
