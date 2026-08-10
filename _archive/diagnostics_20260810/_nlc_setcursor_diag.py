# -*- coding: utf-8 -*-
"""临时诊断插件：IAT 钩 SetCursor，记录 ZBrush 每次设置的光标（句柄+位图签名）。

原理：ZBrush 在 WndProc 里根据光标下是 UI 还是画布来选择光标并调用
SetCursor。钩住它就能看到 ZBrush 自己在每个位置设置了哪种光标——
这就是“当前点是不是 UI”的最直接回答。

随 ZBrush 启动加载，日志写入 C:\\Users\\liuwenbo\\AppData\\Local\\Temp\\nlr_setcursor.log
"""

import ctypes
import os
import struct
import sys
import traceback
from ctypes import wintypes

LOG = r"C:\Users\liuwenbo\AppData\Local\Temp\nlr_setcursor.log"

WM_TIMER = 0x0113
DIAG_SUBCLASS_ID = 0x53455443   # 'SETC'
DIAG_TIMER_ID = 0x53455454      # 'SETT'

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40
ORDINAL_FLAG = 0x8000000000000000

user32 = ctypes.windll.user32
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32")
comctl32 = ctypes.WinDLL("comctl32")


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hCursor", wintypes.HANDLE),
        ("ptScreenPos", POINT),
    ]


class BITMAP(ctypes.Structure):
    _fields_ = [
        ("bmType", ctypes.c_long),
        ("bmWidth", ctypes.c_long),
        ("bmHeight", ctypes.c_long),
        ("bmWidthBytes", ctypes.c_long),
        ("bmPlanes", ctypes.c_uint16),
        ("bmBitsPixel", ctypes.c_uint16),
        ("bmBits", ctypes.c_void_p),
    ]


class ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", wintypes.BOOL),
        ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD),
        ("hbmMask", wintypes.HANDLE),
        ("hbmColor", wintypes.HANDLE),
    ]


GetCursorPos = user32.GetCursorPos
GetCursorPos.restype = wintypes.BOOL
GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
GetCursorInfo = user32.GetCursorInfo
GetCursorInfo.restype = wintypes.BOOL
GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]
GetIconInfo = user32.GetIconInfo
GetIconInfo.restype = wintypes.BOOL
GetIconInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ICONINFO)]
GetObjectW = gdi32.GetObjectW
GetObjectW.restype = ctypes.c_int
GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p]
GetBitmapBits = gdi32.GetBitmapBits
GetBitmapBits.restype = ctypes.c_long
GetBitmapBits.argtypes = [wintypes.HANDLE, ctypes.c_long, ctypes.c_void_p]
DeleteObject = gdi32.DeleteObject
DeleteObject.restype = wintypes.BOOL
DeleteObject.argtypes = [wintypes.HANDLE]
GetClassNameW = user32.GetClassNameW
GetClassNameW.restype = ctypes.c_int
GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetWindowThreadProcessId.restype = wintypes.DWORD
GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
EnumWindows = user32.EnumWindows
EnumWindows.restype = wintypes.BOOL
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]

kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetProcAddress.restype = ctypes.c_void_p
kernel32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
kernel32.VirtualProtect.restype = wintypes.BOOL
kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]

SetTimer = user32.SetTimer
SetTimer.restype = ctypes.c_void_p
SetTimer.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p]
KillTimer = user32.KillTimer
KillTimer.restype = wintypes.BOOL
KillTimer.argtypes = [wintypes.HWND, ctypes.c_void_p]

SubclassProcType = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
    ctypes.c_size_t, ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_void_p)
SetWindowSubclass = comctl32.SetWindowSubclass
SetWindowSubclass.restype = wintypes.BOOL
SetWindowSubclass.argtypes = [wintypes.HWND, SubclassProcType, ctypes.c_size_t, ctypes.c_size_t]
DefSubclassProc = comctl32.DefSubclassProc
DefSubclassProc.restype = ctypes.c_ssize_t
DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]


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


def _find_iat_slot(func_name):
    """在 ZBrush.exe 导入表里找 func_name 的 IAT 槽，返回 (槽地址, 原始指针)。"""
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
        real = int(kernel32.GetProcAddress(kernel32.GetModuleHandleW("user32.dll"), func_name) or 0)
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


# SetCursor 存根：
#   0x00 mov [rip+0x11], rcx   保存游标句柄 -> +0x18
#   0x07 mov rax, [rsp]        取返回地址（调用者）
#   0x0B mov [rip+0x0E], rax   保存调用者地址 -> +0x20
#   0x12 jmp [rip+0x10]        跳转真实 SetCursor（指针 -> +0x28）
SETCURSOR_STUB = bytes([
    0x48, 0x89, 0x0D, 0x11, 0x00, 0x00, 0x00,
    0x48, 0x8B, 0x04, 0x24,
    0x48, 0x89, 0x05, 0x0E, 0x00, 0x00, 0x00,
    0xFF, 0x25, 0x10, 0x00, 0x00, 0x00,
    0xCC, 0xCC, 0xCC,
])

_iat = {
    "slot": 0,
    "original": 0,
    "stub": 0,
    "last_cursor_addr": 0,
    "last_caller_addr": 0,
    "active": False,
}


def _install_setcursor_hook():
    if _iat["active"]:
        return True
    slot, original = _find_iat_slot(b"SetCursor")
    if not slot or not original:
        _log("HOOK FAIL slot=%s" % (hex(slot) if slot else None))
        return False
    real = int(kernel32.GetProcAddress(kernel32.GetModuleHandleW("user32.dll"), b"SetCursor") or 0)
    if not real or original != real:
        _log("HOOK FAIL original != real")
        return False
    page = int(kernel32.VirtualAlloc(None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE) or 0)
    if not page:
        _log("HOOK FAIL alloc")
        return False
    ctypes.memmove(page, SETCURSOR_STUB, len(SETCURSOR_STUB))
    ctypes.memmove(page + 0x28, struct.pack("<Q", real), 8)
    if not _wr64(slot, page):
        _log("HOOK FAIL patch")
        return False
    _iat.update(slot=slot, original=original, stub=page,
                last_cursor_addr=page + 0x18, last_caller_addr=page + 0x20,
                active=True)
    _log("HOOK OK slot=%#x stub=%#x real=%#x" % (slot, page, real))
    return True


def _restore_setcursor_hook():
    if not _iat["active"]:
        return
    if _iat["slot"] and _rd64(_iat["slot"]) == _iat["stub"]:
        _wr64(_iat["slot"], _iat["original"])
    _iat["active"] = False


def _log(line):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _signature(h):
    if not h:
        return 0
    ii = ICONINFO()
    if not GetIconInfo(h, ctypes.byref(ii)):
        return 0
    hv = 1469598103934665603
    color = b""
    mask = b""
    w = 0
    ht = 0
    try:
        if ii.hbmColor:
            bm = BITMAP()
            if GetObjectW(ii.hbmColor, ctypes.sizeof(BITMAP), ctypes.byref(bm)) and bm.bmWidth > 0:
                w = bm.bmWidth
                ht = bm.bmHeight
                n = bm.bmWidthBytes * bm.bmHeight
                buf = ctypes.create_string_buffer(n)
                if GetBitmapBits(ii.hbmColor, n, buf):
                    color = buf.raw
        if ii.hbmMask:
            bm = BITMAP()
            if GetObjectW(ii.hbmMask, ctypes.sizeof(BITMAP), ctypes.byref(bm)) and bm.bmWidth > 0:
                if w == 0:
                    w = bm.bmWidth
                    ht = bm.bmHeight
                n = bm.bmWidthBytes * bm.bmHeight
                buf = ctypes.create_string_buffer(n)
                if GetBitmapBits(ii.hbmMask, n, buf):
                    mask = buf.raw
        hv = ((hv ^ w) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
        hv = ((hv ^ ht) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
        for b in color + mask:
            hv = ((hv ^ b) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    finally:
        if ii.hbmColor:
            DeleteObject(ii.hbmColor)
        if ii.hbmMask:
            DeleteObject(ii.hbmMask)
    return hv


_prev_set = [0]
_prev_caller = [0]
_lbutton_down = [False]

# 命中判定/光标选择函数（静态分析得到）：鼠标事件管线必经点
HITFUNC_RVA = 0x1807950
_hit = {"addr": 0, "orig": None, "stub": 0, "active": False}

# 视图参数更新函数（vtable+0x2A0，运行时确认）：旋转/平移/缩放汇聚点
VIEWFUNC_RVA = 0x17BB9F0
_view = {"addr": 0, "orig": None, "stub": 0, "active": False}


def _build_view_stub(page, base):
    """构造 0x17BB9F0 入口跳板：
    保存 [rsp]（调用者）、RCX（this）、RDX（视图参数）、R8（标志），
    执行原始 14 字节序言，跳回 +0x14。
    """
    st = bytearray()
    # mov rax, [rsp]
    st += b"\x48\x8B\x04\x24"
    # mov [rip+0x35], rax -> +0x40
    st += b"\x48\x89\x05" + struct.pack("<i", 0x40 - 0x0B)
    # mov [rip+0x36], rcx -> +0x48
    st += b"\x48\x89\x0D" + struct.pack("<i", 0x48 - 0x12)
    # mov [rip+0x37], rdx -> +0x50
    st += b"\x48\x89\x15" + struct.pack("<i", 0x50 - 0x19)
    # mov [rip+0x38], r8 -> +0x58
    st += b"\x4C\x89\x05" + struct.pack("<i", 0x58 - 0x20)
    # 原始 14 字节序言（0x17BB9F0..0x17BB9FD）
    st += _view["orig"]
    # 跳回 0x17BB9F0 + 14
    cont = base + VIEWFUNC_RVA + 14
    st += b"\x48\xB8" + struct.pack("<Q", cont) + b"\xFF\xE0"
    st += b"\xCC" * (0x40 - len(st))
    st += b"\x00" * 32  # 0x40 caller, 0x48 rcx, 0x50 rdx, 0x58 r8
    return bytes(st)


def _install_view_hook():
    if _view["active"]:
        return True
    base = int(kernel32.GetModuleHandleW(None) or 0)
    if not base:
        _log("VIEW HOOK FAIL base")
        return False
    addr = base + VIEWFUNC_RVA
    _view["orig"] = ctypes.string_at(addr, 14)
    page = int(kernel32.VirtualAlloc(None, 0x1000, MEM_COMMIT | MEM_RESERVE,
                                     PAGE_EXECUTE_READWRITE) or 0)
    if not page:
        _log("VIEW HOOK FAIL alloc")
        return False
    st = _build_view_stub(page, base)
    ctypes.memmove(page, st, len(st))
    patch = b"\x48\xB8" + struct.pack("<Q", page) + b"\xFF\xE0"
    old = wintypes.DWORD()
    if not kernel32.VirtualProtect(ctypes.c_void_p(addr), 12, PAGE_READWRITE,
                                   ctypes.byref(old)):
        _log("VIEW HOOK FAIL protect")
        return False
    ctypes.memmove(addr, patch, 12)
    kernel32.VirtualProtect(ctypes.c_void_p(addr), 12, old.value,
                            ctypes.byref(old))
    _view.update(addr=addr, stub=page, active=True)
    _log("VIEW HOOK OK addr=%#x stub=%#x" % (addr, page))
    return True


def _restore_view_hook():
    if not _view["active"]:
        return
    old = wintypes.DWORD()
    kernel32.VirtualProtect(ctypes.c_void_p(_view["addr"]), 12, PAGE_READWRITE,
                            ctypes.byref(old))
    ctypes.memmove(_view["addr"], _view["orig"], 12)
    kernel32.VirtualProtect(ctypes.c_void_p(_view["addr"]), 12, old.value,
                            ctypes.byref(old))
    _view["active"] = False


def _build_hit_stub(page, base):
    """构造 0x1807950 入口的跳板：
    捕获 [rsp..rsp+56] 共 8 个 qword（返回地址链）、RCX（this）、RDX（事件指针），
    执行原始 12 字节序言，再跳回 0x1807950+12。
    """
    st = bytearray()
    for i in range(8):
        sdisp = i * 8
        daddr = 0x90 + i * 8
        # mov rax, [rsp + imm8]
        st += bytes([0x48, 0x8B, 0x44, 0x24, sdisp])
        # mov [rip + disp32], rax ; 该指令位于 12*i+5，下一条 RIP = 12*i+12
        disp = daddr - (12 * i + 12)
        st += b"\x48\x89\x05" + struct.pack("<i", disp)
    assert len(st) == 0x60
    # 0x60: mov [rip+0x69], rcx  -> 保存 this 到 +0xD0
    st += b"\x48\x89\x0D" + struct.pack("<i", 0xD0 - 0x67)
    # 0x67: mov [rip+0x6A], rdx  -> 保存事件指针到 +0xD8
    st += b"\x48\x89\x15" + struct.pack("<i", 0xD8 - 0x6E)
    # 原始 12 字节序言（0x1807950..0x180795B）
    st += _hit["orig"]
    # 跳回 0x1807950 + 12
    cont = base + HITFUNC_RVA + 12
    st += b"\x48\xB8" + struct.pack("<Q", cont) + b"\xFF\xE0"
    # 填充到数据区
    st += b"\xCC" * (0x90 - len(st))
    st += b"\x00" * 64  # 8 qword 数据槽
    st += b"\x00" * 16  # +0xD0: rcx, +0xD8: rdx
    return bytes(st)


def _install_hitfunc_hook():
    if _hit["active"]:
        return True
    base = int(kernel32.GetModuleHandleW(None) or 0)
    if not base:
        _log("HIT HOOK FAIL base")
        return False
    addr = base + HITFUNC_RVA
    _hit["orig"] = ctypes.string_at(addr, 12)
    page = int(kernel32.VirtualAlloc(None, 0x1000, MEM_COMMIT | MEM_RESERVE,
                                     PAGE_EXECUTE_READWRITE) or 0)
    if not page:
        _log("HIT HOOK FAIL alloc")
        return False
    st = _build_hit_stub(page, base)
    ctypes.memmove(page, st, len(st))
    patch = b"\x48\xB8" + struct.pack("<Q", page) + b"\xFF\xE0"
    old = wintypes.DWORD()
    if not kernel32.VirtualProtect(ctypes.c_void_p(addr), 12, PAGE_READWRITE,
                                   ctypes.byref(old)):
        _log("HIT HOOK FAIL protect")
        return False
    ctypes.memmove(addr, patch, 12)
    kernel32.VirtualProtect(ctypes.c_void_p(addr), 12, old.value,
                            ctypes.byref(old))
    _hit.update(addr=addr, stub=page, active=True)
    _log("HIT HOOK OK addr=%#x stub=%#x" % (addr, page))
    return True


def _restore_hitfunc_hook():
    if not _hit["active"]:
        return
    old = wintypes.DWORD()
    kernel32.VirtualProtect(ctypes.c_void_p(_hit["addr"]), 12, PAGE_READWRITE,
                            ctypes.byref(old))
    ctypes.memmove(_hit["addr"], _hit["orig"], 12)
    kernel32.VirtualProtect(ctypes.c_void_p(_hit["addr"]), 12, old.value,
                            ctypes.byref(old))
    _hit["active"] = False


@SubclassProcType
def _proc(hwnd, msg, wparam, lparam, u_id, ref_data):
    try:
        if msg in (0x0201, 0x0202):  # WM_LBUTTONDOWN / WM_LBUTTONUP
            x = lparam & 0xFFFF
            y = (lparam >> 16) & 0xFFFF
            _log("MSG %s pos=(%d,%d)" % ("LDOWN" if msg == 0x0201 else "LUP", x, y))
            if msg == 0x0201:
                _lbutton_down[0] = True
                if not _hit["active"]:
                    try:
                        _install_hitfunc_hook()
                    except Exception as e:
                        _log("HIT ARM ERR %r\n%s" % (e, traceback.format_exc()))
                if not _view["active"]:
                    try:
                        _install_view_hook()
                    except Exception as e:
                        _log("VIEW ARM ERR %r\n%s" % (e, traceback.format_exc()))
            else:
                _lbutton_down[0] = False
                _restore_hitfunc_hook()
                _restore_view_hook()
        if msg == WM_TIMER and wparam == DIAG_TIMER_ID:
            if _iat["active"]:
                cur = _rd64(_iat["last_cursor_addr"])
                caller = _rd64(_iat["last_caller_addr"])
                if cur != _prev_set[0] or caller != _prev_caller[0]:
                    _prev_set[0] = cur
                    _prev_caller[0] = caller
                    pt = POINT()
                    GetCursorPos(ctypes.byref(pt))
                    sig = _signature(cur)
                    base = int(kernel32.GetModuleHandleW(None) or 0)
                    rva = (caller - base) if base and caller >= base else 0
                    _log("SETCURSOR pos=(%d,%d) cur=%#x sig=%#x caller=%#x rva=%#x"
                         % (pt.x, pt.y, cur, sig, caller, rva))
            if _hit["active"] and _lbutton_down[0]:
                c0 = _rd64(_hit["stub"] + 0x90)
                if c0:
                    base = int(kernel32.GetModuleHandleW(None) or 0)
                    parts = []
                    for i in range(8):
                        v = _rd64(_hit["stub"] + 0x90 + i * 8)
                        if base and base <= v < base + 0x1E937000:
                            parts.append("%#x" % (v - base))
                        else:
                            parts.append("%#x" % v)
                    extra = []
                    obj = _rd64(_hit["stub"] + 0xD0)
                    ev = _rd64(_hit["stub"] + 0xD8)
                    if ev:
                        try:
                            extra.append("evtype=%#x" % (_rd32(ev + 8) or 0))
                        except Exception:
                            pass
                    if obj:
                        try:
                            vt = _rd64(obj)
                            extra.append("obj=%#x" % obj)
                            if base and vt:
                                extra.append("vt=%#x" % (vt - base))
                                f78 = _rd64(vt + 0x78)
                                f2a0 = _rd64(vt + 0x2A0)
                                extra.append("vt78=%#x" % ((f78 - base) if f78 else 0))
                                extra.append("vt2a0=%#x" % ((f2a0 - base) if f2a0 else 0))
                        except Exception as e:
                            extra.append("vterr=%r" % (e,))
                    _log("HITCALL btn=1 stack=[%s] %s" % (", ".join(parts), " ".join(extra)))
                    _restore_hitfunc_hook()
            if _view["active"] and _lbutton_down[0]:
                vcaller = _rd64(_view["stub"] + 0x40)
                if vcaller:
                    base = int(kernel32.GetModuleHandleW(None) or 0)
                    vthis = _rd64(_view["stub"] + 0x48)
                    vparams = _rd64(_view["stub"] + 0x50)
                    vflag = _rd64(_view["stub"] + 0x58)
                    rva = (vcaller - base) if base and vcaller >= base else 0
                    idx = _rd32(base + 0x1D881AD8) if base else 0
                    _log("VIEWCALL btn=1 caller=%#x rva=%#x this=%#x params=%#x flag=%#x cidx=%d"
                         % (vcaller, rva, vthis, vparams, vflag, idx))
                    _restore_view_hook()
            return 0
    except Exception as e:
        _log("PROC ERR %r msg=%#x" % (e, msg))
        return 0
    return DefSubclassProc(hwnd, msg, wparam, lparam)


_proc_ref = _proc


def main():
    try:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("=== SetCursor IAT 探测 ===\n")
            f.write("py=%s pid=%d\n" % (sys.version.split()[0], os.getpid()))
    except Exception:
        pass
    pid = os.getpid()
    found = [None]

    @WNDENUMPROC
    def enum_cb(h, lp):
        try:
            cls = ctypes.create_unicode_buffer(256)
            GetClassNameW(h, cls, 256)
            if cls.value == "ZBrush":
                wpid = wintypes.DWORD()
                GetWindowThreadProcessId(h, ctypes.byref(wpid))
                if wpid.value == pid:
                    found[0] = h
                    return False
        except Exception as e:
            _log("ENUMCB ERR %r h=%r" % (e, h))
        return True

    try:
        EnumWindows(enum_cb, 0)
        _log("ENUMWINDOWS OK")
    except Exception as e:
        _log("ENUMWINDOWS ERR %r" % (e,))
        return
    hwnd = found[0]
    if not hwnd:
        _log("NO WINDOW")
        return
    try:
        ok = SetWindowSubclass(hwnd, _proc, DIAG_SUBCLASS_ID, 0)
        _log("SUBCLASS %r" % (ok,))
        if not ok:
            return
    except Exception as e:
        _log("SUBCLASS ERR %r" % (e,))
        return
    try:
        tid = SetTimer(hwnd, DIAG_TIMER_ID, 50, None)
        _log("TIMER %r" % (tid,))
        if not tid:
            return
    except Exception as e:
        _log("TIMER ERR %r" % (e,))
        return
    try:
        _install_setcursor_hook()
        _log("HOOK DONE active=%r" % (_iat["active"],))
    except Exception as e:
        _log("HOOK ERR %r\n%s" % (e, traceback.format_exc()))
    base = int(kernel32.GetModuleHandleW(None) or 0)
    _log("READY hwnd=%#x base=%#x" % (int(hwnd), base))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write("FATAL %r\n" % (e,))
        except Exception:
            pass
