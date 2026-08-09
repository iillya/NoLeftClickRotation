# -*- coding: utf-8 -*-
"""临时诊断插件：按 F9 开关录制光标状态（空闲/按下/拖动）。

用窗口子类 + 定时器（主线程消息循环触发），随 ZBrush 启动加载。
日志：C:\\Users\\liuwenbo\\AppData\\Local\\Temp\\nlr_hittest.log
"""

import ctypes
import os
import time
from ctypes import wintypes

LOG = r"C:\Users\liuwenbo\AppData\Local\Temp\nlr_hittest.log"

WM_TIMER = 0x0113
VK_F9 = 0x78
VK_LBUTTON = 0x01

DIAG_SUBCLASS_ID = 0x44494147  # 'DIAG'
DIAG_TIMER_ID = 0x44494754      # 'DIGT'

user32 = ctypes.windll.user32
comctl32 = ctypes.WinDLL("comctl32")

GetCursorPos = user32.GetCursorPos
GetCursorPos.restype = wintypes.BOOL
GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
WindowFromPoint = user32.WindowFromPoint
WindowFromPoint.restype = wintypes.HWND
WindowFromPoint.argtypes = [wintypes.POINT]
GetClassNameW = user32.GetClassNameW
GetClassNameW.restype = ctypes.c_int
GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
GetParent = user32.GetParent
GetParent.restype = wintypes.HWND
GetParent.argtypes = [wintypes.HWND]
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetWindowThreadProcessId.restype = wintypes.DWORD
GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
GetAsyncKeyState = user32.GetAsyncKeyState
GetAsyncKeyState.restype = ctypes.c_short
GetAsyncKeyState.argtypes = [ctypes.c_int]
MessageBoxW = user32.MessageBoxW
MessageBoxW.restype = ctypes.c_int
MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
SetTimer = user32.SetTimer
SetTimer.restype = ctypes.c_void_p
SetTimer.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p]
KillTimer = user32.KillTimer
KillTimer.restype = wintypes.BOOL
KillTimer.argtypes = [wintypes.HWND, ctypes.c_void_p]


class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hCursor", wintypes.HANDLE),
        ("ptScreenPos", wintypes.POINT),
    ]


GetCursorInfo = user32.GetCursorInfo
GetCursorInfo.restype = wintypes.BOOL
GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]

SubclassProcType = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
    ctypes.c_size_t, ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_void_p)

SetWindowSubclass = comctl32.SetWindowSubclass
SetWindowSubclass.restype = wintypes.BOOL
SetWindowSubclass.argtypes = [wintypes.HWND, SubclassProcType, ctypes.c_size_t, ctypes.c_size_t]
DefSubclassProc = comctl32.DefSubclassProc
DefSubclassProc.restype = ctypes.c_ssize_t
DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]

_recording = [False]
_prev_f9 = [0]
_prev_down = [False]
_press_pos = [None]
_drag_logged = [False]
_last_down_cursor = [0]
_last_hover = [None]
_tick = [0]


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


def _snap():
    pt = wintypes.POINT()
    GetCursorPos(ctypes.byref(pt))
    h = WindowFromPoint(pt)
    h = int(h or 0)
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(h, ctypes.byref(pid))
    p = GetParent(h)
    p = int(p or 0)
    return "pos=(%d,%d) hwnd=%#x cls=%r pid=%d parent=%#x pcls=%r cursor=%#x" % (
        pt.x, pt.y, h, _cls(h), pid.value, p, _cls(p), _cursor())


def _log(line):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


@SubclassProcType
def _proc(hwnd, msg, wparam, lparam, u_id, ref_data):
    try:
        if msg == WM_TIMER and wparam == DIAG_TIMER_ID:
            # F9 开关录制
            f9 = 1 if (GetAsyncKeyState(VK_F9) & 0x8000) else 0
            if f9 and not _prev_f9[0]:
                _recording[0] = not _recording[0]
                _log("=== REC %s ===" % ("ON" if _recording[0] else "OFF"))
            _prev_f9[0] = f9
            if not _recording[0]:
                return 0
            # 采样：空闲 / 按下 / 拖动
            pt = wintypes.POINT()
            gok = GetCursorPos(ctypes.byref(pt))
            down = bool(GetAsyncKeyState(VK_LBUTTON) & 0x8000)
            s = _snap()
            _tick[0] += 1
            if _tick[0] % 10 == 0:
                _log("SAMPLE gok=%d down=%d %s" % (int(gok), int(down), s))
            if down and not _prev_down[0]:
                _press_pos[0] = (pt.x, pt.y)
                _drag_logged[0] = False
                _last_down_cursor[0] = _cursor()
                _log("PRESS " + s)
            elif down and _prev_down[0]:
                pp = _press_pos[0]
                if pp and not _drag_logged[0] and (
                    abs(pt.x - pp[0]) > 5 or abs(pt.y - pp[1]) > 5
                ):
                    _drag_logged[0] = True
                    _log("DRAG-START " + s)
                cur = _cursor()
                if cur != _last_down_cursor[0]:
                    _last_down_cursor[0] = cur
                    _log("DRAG-CURSOR-CHANGE " + s)
            elif not down and _prev_down[0]:
                _log("RELEASE " + s)
                _drag_logged[0] = False
            else:
                if s != _last_hover[0]:
                    _last_hover[0] = s
                    _log("IDLE " + s)
            _prev_down[0] = down
            return 0
    except Exception as e:
        try:
            _log("ERR %r" % (e,))
        except Exception:
            pass
    return DefSubclassProc(hwnd, msg, wparam, lparam)


_proc_ref = _proc


def main():
    try:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("=== cursor diag plugin (timer) ===\n")
    except Exception:
        pass
    # 找本进程的 ZBrush 主窗口
    pid = os.getpid()
    found = [None]

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def enum_cb(h, lp):
        cls = ctypes.create_unicode_buffer(256)
        GetClassNameW(h, cls, 256)
        if cls.value == "ZBrush":
            wpid = wintypes.DWORD()
            GetWindowThreadProcessId(h, ctypes.byref(wpid))
            if wpid.value == pid:
                found[0] = h
                return False
        return True

    user32.EnumWindows(enum_cb, 0)
    hwnd = found[0]
    if not hwnd:
        _log("NO WINDOW")
        return
    if not SetWindowSubclass(hwnd, _proc, DIAG_SUBCLASS_ID, 0):
        _log("SUBCLASS FAIL")
        return
    if not SetTimer(hwnd, DIAG_TIMER_ID, 50, None):
        _log("TIMER FAIL")
        return
    _log("READY hwnd=%#x" % int(hwnd))
    MessageBoxW(
        hwnd,
        "光标诊断插件已启动。\n\n按 F9 开始/停止录制，然后依次在空白画布、"
        "模型、按钮上执行：空闲移动 / 按住不动 / 拖动。\n\n"
        "日志：C:\\Users\\liuwenbo\\AppData\\Local\\Temp\\nlr_hittest.log",
        "NoLeftClickRotation 诊断",
        0x40,  # MB_ICONINFORMATION
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
