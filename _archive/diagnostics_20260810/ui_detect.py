# -*- coding: utf-8 -*-
"""检测“光标是否在 ZBrush UI 上”——信号对比工具（独立脚本，非插件）。

用法：
  1. 启动 ZBrush；
  2. 运行 python ui_detect.py；
  3. 在 ZBrush 的顶部菜单 / 按钮 / 面板 / 画布 / 模型上来回移动鼠标，
     观察实时读数，找出哪个信号在“UI 区”和“画布区”之间会变化；
  4. Ctrl+C 退出。变化记录写入
     C:\\Users\\liuwenbo\\AppData\\Local\\Temp\\nlr_ui_detect.log
"""

import ctypes
import time
from ctypes import wintypes

u = ctypes.windll.user32
g = ctypes.windll.gdi32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        u.SetProcessDPIAware()
    except Exception:
        pass

LOG = r"C:\Users\liuwenbo\AppData\Local\Temp\nlr_ui_detect.log"


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


GetCursorPos = u.GetCursorPos
GetCursorPos.restype = wintypes.BOOL
GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
WindowFromPoint = u.WindowFromPoint
WindowFromPoint.restype = wintypes.HWND
WindowFromPoint.argtypes = [ctypes.POINTER(POINT)]
GetClassNameW = u.GetClassNameW
GetClassNameW.restype = ctypes.c_int
GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
GetCursorInfo = u.GetCursorInfo
GetCursorInfo.restype = wintypes.BOOL
GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]
GetIconInfo = u.GetIconInfo
GetIconInfo.restype = wintypes.BOOL
GetIconInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ICONINFO)]
GetObjectW = g.GetObjectW
GetObjectW.restype = ctypes.c_int
GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p]
GetBitmapBits = g.GetBitmapBits
GetBitmapBits.restype = ctypes.c_long
GetBitmapBits.argtypes = [wintypes.HANDLE, ctypes.c_long, ctypes.c_void_p]
DeleteObject = g.DeleteObject
DeleteObject.restype = wintypes.BOOL
DeleteObject.argtypes = [wintypes.HANDLE]
SendMessageW = u.SendMessageW
SendMessageW.restype = ctypes.c_ssize_t
SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
EnumWindows = u.EnumWindows
EnumWindows.restype = wintypes.BOOL
GetWindowThreadProcessId = u.GetWindowThreadProcessId
GetWindowThreadProcessId.restype = wintypes.DWORD

WM_NCHITTEST = 0x0084

HT_NAMES = {
    0: "HTNOWHERE", 1: "HTCLIENT", 2: "HTCAPTION", 3: "HTSYSMENU",
    4: "HTSIZE", 5: "HTMENU", 6: "HTHSCROLL", 7: "HTVSCROLL",
    8: "HTMINBUTTON", 9: "HTMAXBUTTON", 10: "HTLEFT", 11: "HTRIGHT",
    12: "HTTOP", 13: "HTTOPLEFT", 14: "HTTOPRIGHT", 15: "HTBOTTOM",
    16: "HTBOTTOMLEFT", 17: "HTBOTTOMRIGHT", 18: "HTBORDER", 19: "HTOBJECT",
    20: "HTCLOSE", 21: "HTHELP",
}


def _cls(h):
    if not h:
        return ""
    b = ctypes.create_unicode_buffer(256)
    GetClassNameW(h, b, 256)
    return b.value


def _cursor_handle():
    ci = CURSORINFO()
    ci.cbSize = ctypes.sizeof(CURSORINFO)
    if GetCursorInfo(ctypes.byref(ci)):
        return int(ci.hCursor or 0)
    return 0


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


def find_zbrush():
    found = [None]

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, lp):
        if _cls(h) == "ZBrush":
            found[0] = h
            return False
        return True

    EnumWindows(cb, 0)
    return found[0]


def main():
    hwnd = find_zbrush()
    print("ZBrush hwnd=%#x" % int(hwnd or 0), flush=True)
    print("在 ZBrush 的菜单/按钮/面板/画布上来回移动，观察读数变化。Ctrl+C 退出。", flush=True)
    try:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("=== UI 检测信号对比 ===\n")
            last = None
            while True:
                pt = POINT()
                GetCursorPos(ctypes.byref(pt))
                h = int(WindowFromPoint(ctypes.byref(pt)) or 0)
                ht = -1
                if hwnd:
                    lp = ((pt.y & 0xFFFF) << 16) | (pt.x & 0xFFFF)
                    ht = SendMessageW(hwnd, WM_NCHITTEST, 0, lp)
                cur = _cursor_handle()
                sig = _signature(cur)
                line = "pos=(%d,%d) WFP=%#x(%s) HT=%d(%s) CUR=%#x SIG=%#x" % (
                    pt.x, pt.y, h, _cls(h), ht, HT_NAMES.get(ht, "?"), cur, sig)
                if line != last:
                    last = line
                    print(line + " " * 8, end="\r", flush=True)
                    f.write(line + "\n")
                    f.flush()
                time.sleep(0.05)
    except KeyboardInterrupt:
        print("\ndone")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
