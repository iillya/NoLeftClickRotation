# -*- coding: utf-8 -*-
"""Capture real implementation functions from both dispatcher call sites.

Site A: 0x1418A0643  (18-byte window)  -> records r8
Site B: 0x1418A053F  (19-byte window)  -> records rax
Both write into their own ring buffer; a timer calls pixol_pick and reports.
"""

import ctypes
import os
import struct
import threading
import time
from ctypes import wintypes

LOG = os.path.join(os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"),
                   "nlr_real2.log")

WM_TIMER = 0x0113
TIMER_ID = 0x4E4C5232
SUBCLASS_ID = 0x4E4C5233

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
_REC_LAST = 0x60
_REC_COUNT = 0x70
_REC_BUF = 0x80
_REC_SLOTS = 64


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
    # site B: 17-byte window; record [r13+0x30] then jump to original call
    {
        "rva": 0x18A053F,
        "orig": bytes.fromhex("498b4530488d9424c0010000488d4c2470"),
        "cont": 0x14018A0552,  # skip the call, land after it
        "prefix": 17,
        "reg": "record",
    },
]


def _build_stub(page: int, prefix: bytes, reg: str, cont: int) -> bytes:
    if reg == "record":
        stb = bytearray()
        stb += prefix
        # 0x11: mov [rip+0x48], rax  -> +0x60 (real fn)
        stb += b"\x48\x89\x05" + struct.pack("<i", 0x60 - 0x18)
        # 0x18: inc qword [rip+0x51] -> +0x70 (counter)
        stb += b"\x48\xFF\x05" + struct.pack("<i", 0x70 - 0x1F)
        # 0x1F: mov r11, cont ; jmp r11
        stb += b"\x49\xBB" + struct.pack("<Q", cont)
        stb += b"\x41\xFF\xE3"
        while len(stb) < 0x80:
            stb.append(0xCC)
        return bytes(stb)
    if reg == "jmpcont":
        stb = bytearray()
        stb += prefix
        stb += b"\x49\xBB" + struct.pack("<Q", cont)
        stb += b"\x41\xFF\xE3"
        while len(stb) < 0x80:
            stb.append(0xCC)
        return bytes(stb)
    if reg == "passthrough":
        stb = bytearray()
        stb += prefix
        # 0x11: mov [rip+0x68], r13  -> +0x80
        stb += b"\x4C\x89\x2D" + struct.pack("<i", 0x80 - 0x18)
        # 0x18: mov [rip+0x69], rax  -> +0x88 (fn)
        stb += b"\x48\x89\x05" + struct.pack("<i", 0x88 - 0x1F)
        # 0x1F: call rax
        stb += b"\xFF\xD0"
        # 0x21: mov [rip+0x68], rax  -> +0x90 (retval)
        stb += b"\x48\x89\x05" + struct.pack("<i", 0x90 - 0x28)
        # 0x28: mov [rip+0x69], rsp  -> +0x98
        stb += b"\x48\x89\x25" + struct.pack("<i", 0x98 - 0x2F)
        # 0x2F: mov r11, cont ; jmp r11
        stb += b"\x49\xBB" + struct.pack("<Q", cont)
        stb += b"\x41\xFF\xE3"
        while len(stb) < 0xA0:
            stb.append(0xCC)
        return bytes(stb)
    if reg == "r8":
        stb = bytearray()
        stb += prefix  # 0x00.. (15 bytes)
        # 0x0F: mov [rip+0x4A], r8  -> +0x60
        stb += b"\x4C\x89\x05" + struct.pack("<i", _REC_LAST - 0x16)
        # 0x16: lea r9,[rip+0x63]    -> &buf (+0x80)
        stb += b"\x4C\x8D\x0D" + struct.pack("<i", _REC_BUF - 0x1D)
        # 0x1D: mov rax,[rip+0x4C]   -> counter (+0x70)
        stb += b"\x48\x8B\x05" + struct.pack("<i", _REC_COUNT - 0x24)
        # 0x24: mov r10, rax
        stb += b"\x49\x89\xC2"
        # 0x27: inc rax
        stb += b"\x48\xFF\xC0"
        # 0x2A: mov [rip+0x3F], rax  -> counter (+0x70)
        stb += b"\x48\x89\x05" + struct.pack("<i", _REC_COUNT - 0x31)
        # 0x31: and r10d, 63
        stb += b"\x41\x83\xE2\x3F"
        # 0x35: shl r10, 3
        stb += b"\x49\xC1\xE2\x03"
        # 0x39: mov [r9+r10*8], r8   -> buf[idx] = r8
        stb += b"\x4F\x89\x04\xD1"
        # 0x3D: call r8
        stb += b"\x41\xFF\xD0"
        # 0x40: mov r11, cont ; jmp r11
        stb += b"\x49\xBB" + struct.pack("<Q", cont)
        stb += b"\x41\xFF\xE3"
    else:
        stb = bytearray()
        stb += prefix  # 0x00.. (17 bytes)
        # 0x11: mov r10, rax           (keep fn in r10)
        stb += b"\x49\x89\xC2"
        # 0x14: mov [rip+0x45], r10  -> +0x60
        stb += b"\x4C\x89\x15" + struct.pack("<i", _REC_LAST - 0x1B)
        # 0x1B: lea r9,[rip+0x5E]    -> &buf (+0x80)
        stb += b"\x4C\x8D\x0D" + struct.pack("<i", _REC_BUF - 0x22)
        # 0x22: mov rax,[rip+0x47]   -> counter (+0x70)
        stb += b"\x48\x8B\x05" + struct.pack("<i", _REC_COUNT - 0x29)
        # 0x29: mov r8, rax
        stb += b"\x49\x89\xC0"
        # 0x2C: inc rax
        stb += b"\x48\xFF\xC0"
        # 0x2F: mov [rip+0x3A], rax  -> counter (+0x70)
        stb += b"\x48\x89\x05" + struct.pack("<i", _REC_COUNT - 0x36)
        # 0x36: and r8d, 63
        stb += b"\x41\x83\xE0\x3F"
        # 0x3A: shl r8, 3
        stb += b"\x49\xC1\xE0\x03"
        # 0x3E: mov [r9+r8*8], r10   -> buf[idx] = r10
        stb += b"\x4F\x89\x14\xC1"
        # 0x42: call r10
        stb += b"\x41\xFF\xD2"
        # 0x45: mov r11, cont ; jmp r11
        stb += b"\x49\xBB" + struct.pack("<Q", cont)
        stb += b"\x41\xFF\xE3"
    while len(stb) < _REC_BUF + _REC_SLOTS * 8:
        stb.append(0xCC)
    return bytes(stb)


_hooks_active = []


def _install_all() -> bool:
    global _hooks_active
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
            _dlog("orig mismatch %#x: %s" % (h["rva"], cur.hex()))
            return False
        page = kernel32.VirtualAlloc(
            None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
        if not page:
            _dlog("alloc fail %#x" % h["rva"])
            return False
        page = int(page)
        stub = _build_stub(page, h["orig"][:h["prefix"]], h["reg"], h["cont"])
        ctypes.memmove(page, stub, len(stub))
        patch = b"\x48\xB8" + struct.pack("<Q", page) + b"\xFF\xE0" + b"\x90" * (len(h["orig"]) - 13)
        if not _write_bytes(addr, patch):
            _dlog("patch fail %#x" % h["rva"])
            return False
        _hooks_active.append({"rva": h["rva"], "stub": page, "reg": h["reg"]})
        _dlog("hook OK %#x stub=%#x reg=%s" % (h["rva"], page, h["reg"]))
    return True


def _hook_stats():
    out = {}
    for h in _hooks_active:
        stub = h["stub"]
        count = ctypes.c_uint64.from_address(stub + _REC_COUNT).value
        last = ctypes.c_uint64.from_address(stub + _REC_LAST).value
        ring = []
        n = min(count, _REC_SLOTS)
        start = max(0, count - _REC_SLOTS) if count > _REC_SLOTS else 0
        for i in range(n):
            ring.append(ctypes.c_uint64.from_address(
                stub + _REC_BUF + ((start + i) % _REC_SLOTS) * 8).value)
        out[h["rva"]] = (count, last, sorted(set(ring)))
    return out


_hwnd = None
_last_report = 0.0
_last_err = ""
_last_xy = (1548.0, 948.0)
_last_mat = None
_boot = time.monotonic()
_probe_started = False
_poll_stop = threading.Event()
_poll_done = []
_poll_beat = 0.0


def _run() -> None:
    global _last_report, _last_err, _last_xy, _last_mat, _probe_started
    if time.monotonic() - _boot < 60:
        return
    if not _probe_started:
        _probe_started = True
        _dlog("probe start (after 60s delay)")
    try:
        import zbrush.commands as zbc
        err = ""
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
            down = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
            stats = _hook_stats()
            parts = []
            for rva in sorted(stats):
                count, last, uniq = stats[rva]
                parts.append("%#x:c=%d,l=%#x,u=%s" % (
                    rva, count, last, ",".join("%#x" % u for u in uniq)))
            _dlog("xy=%.0f,%.0f mat=%s down=%d %s"
                  % (_last_xy[0], _last_xy[1], _last_mat, down, " | ".join(parts)))
    except Exception as e:
        _dlog("probe err %r" % (e,))


def _poll_worker():
    global _poll_beat
    while not _poll_stop.is_set():
        try:
            now = time.time()
            if now - _poll_beat >= 2.0:
                _poll_beat = now
                _dlog("POLL alive stub=%#x v=%#x"
                      % (_hooks_active[0]["stub"] if _hooks_active else 0,
                         ctypes.c_uint64.from_address(
                             _hooks_active[0]["stub"] + 0x60).value
                         if _hooks_active else 0))
            if _hooks_active:
                stub = _hooks_active[0]["stub"]
                v = ctypes.c_uint64.from_address(stub + 0x60).value
                if v and v != 0xCCCCCCCCCCCCCCCC:
                    _dlog("POLL real_fn=%#x" % v)
        except Exception:
            pass
        time.sleep(0.05)


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
            f.write("=== nlr real2 capture ===\n")
    except Exception:
        pass
    _dlog("main start")
    if not _install_all():
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
        t = threading.Thread(target=_poll_worker, daemon=True)
        t.start()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
