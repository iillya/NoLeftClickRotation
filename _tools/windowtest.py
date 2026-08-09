# -*- coding: utf-8 -*-
"""UI 窗口命中测试工具。

用法：python windowtest.py，然后在 ZBrush 里移动鼠标悬停：
  - 悬停变化自动记录光标处 WindowFromPoint 命中的窗口（句柄/类名/父链）；
  - 按 F9 在关键位置采样（建议：F9 分别按在 可点按钮 / 点不动的按钮 /
    顶部菜单 / 面板 / 空白画布 / 模型 上）。
结果写入 C:\\Users\\liuwenbo\\AppData\\Local\\Temp\\nlr_hittest.log
"""
import ctypes, time
from ctypes import wintypes

u = ctypes.windll.user32

GetCursorPos = u.GetCursorPos
GetCursorPos.restype = wintypes.BOOL
GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
WindowFromPoint = u.WindowFromPoint
WindowFromPoint.restype = wintypes.HWND
WindowFromPoint.argtypes = [wintypes.POINT]
GetClassNameW = u.GetClassNameW
GetClassNameW.restype = ctypes.c_int
GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
GetParent = u.GetParent
GetParent.restype = wintypes.HWND
GetParent.argtypes = [wintypes.HWND]
GetAncestor = u.GetAncestor
GetAncestor.restype = wintypes.HWND
GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
GetWindowThreadProcessId = u.GetWindowThreadProcessId
GetWindowThreadProcessId.restype = wintypes.DWORD
GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
GetAsyncKeyState = u.GetAsyncKeyState
GetAsyncKeyState.restype = ctypes.c_short
GetAsyncKeyState.argtypes = [ctypes.c_int]

LOG = r"C:\Users\liuwenbo\AppData\Local\Temp\nlr_hittest.log"
GA_ROOT = 2
VK_F9 = 0x78


class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hCursor", wintypes.HANDLE),
        ("ptScreenPos", wintypes.POINT),
    ]


GetCursorInfo = u.GetCursorInfo
GetCursorInfo.restype = wintypes.BOOL
GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]


def _cls(h):
    if not h:
        return ""
    b = ctypes.create_unicode_buffer(256)
    GetClassNameW(h, b, 256)
    return b.value


def _cursor():
    ci = CURSORINFO()
    ci.cbSize = ctypes.sizeof(CURSORINFO)
    if GetCursorInfo(ctypes.byref(ci)):
        return int(ci.hCursor or 0)
    return 0


def snapshot():
    pt = wintypes.POINT()
    GetCursorPos(ctypes.byref(pt))
    h = WindowFromPoint(pt)
    h = int(h or 0)
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(h, ctypes.byref(pid))
    p = int(GetParent(h) or 0)
    gp = int(GetParent(p) or 0)
    root = int(GetAncestor(h, GA_ROOT) or 0)
    return ("pos=(%d,%d) hwnd=%#x cls=%r pid=%d parent=%#x pcls=%r "
            "gparent=%#x gpcls=%r root=%#x rcls=%r cursor=%#x") % (
        pt.x, pt.y, h, _cls(h), pid.value, p, _cls(p), gp, _cls(gp),
        root, _cls(root), _cursor())


print("移动鼠标悬停观察；按 F9 采样。Ctrl+C 退出。", flush=True)
last = None
prev_f9 = 0
try:
    with open(LOG, "w", encoding="utf-8") as f:
        f.write("=== UI 窗口命中测试 ===\n")
        while True:
            try:
                s = snapshot()
                if s != last:
                    last = s
                    print("HOVER " + s, flush=True)
                    f.write("HOVER " + s + "\n")
                    f.flush()
            except Exception:
                pass
            f9 = 1 if (GetAsyncKeyState(VK_F9) & 0x8000) else 0
            if f9 and not prev_f9:
                try:
                    s = snapshot()
                except Exception:
                    s = "?"
                line = "KEY F9 " + s
                print(line, flush=True)
                f.write(line + "\n")
                f.flush()
            prev_f9 = f9
            time.sleep(0.05)
except KeyboardInterrupt:
    print("done")
