# -*- coding: utf-8 -*-
"""NoLeftClickRotation - Lock Camera + bridge v2 experiment.

Only active when the left button is pressed on BLANK canvas (decided by the
last idle pixol_pick sample). While blank-dragging, periodically sends a
short LBUTTONUP then re-presses with the CURRENT cursor coordinate, so
ZBrush re-runs its hit test at the cursor position and starts a stroke when
the cursor is over the mesh. Mesh-pressed strokes are never touched.
"""

import ctypes
import os
import struct
import time
from ctypes import wintypes

LOG = os.path.join(os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"),
                   "nlr_bridge2.log")

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_TIMER = 0x0113

MK_LBUTTON = 0x0001

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_CONTROL = 0x11
VK_MENU = 0x12

SUBCLASS_ID = 0x4E4C4232
TIMER_ID = 0x4E4C4233
RESET_TIMER_ID = 0x4E4C4234

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t

user32 = ctypes.WinDLL("user32")
comctl32 = ctypes.WinDLL("comctl32")

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
user32.KillTimer.restype = wintypes.BOOL
user32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.PostMessageW.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
user32.SendMessageW.restype = LRESULT
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetCursorPos.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.ScreenToClient.restype = wintypes.BOOL
user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]

comctl32.SetWindowSubclass.restype = wintypes.BOOL
comctl32.SetWindowSubclass.argtypes = [
    wintypes.HWND, SubclassProcType, ctypes.c_size_t, ctypes.c_size_t,
]
comctl32.DefSubclassProc.restype = LRESULT
comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]

# configurable via UI
_reset_delay_ms = 30      # UP -> DOWN gap
_bridge_interval_ms = 150  # reset period while blank-dragging
_enabled = True

_hwnd = None
_state = 0  # 0 idle, 1 armed(blank), 2 stroking(mesh)
_last_mesh = False
_cur_client = (0, 0)
_right_down = False
_last_report = 0.0
_synthetic_up = False


def _dlog(line: str) -> None:
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
    except Exception:
        pass


def _client_xy(hwnd) -> tuple:
    pt = wintypes.POINT()
    if user32.GetCursorPos(ctypes.byref(pt)) and user32.ScreenToClient(hwnd, ctypes.byref(pt)):
        return int(pt.x), int(pt.y)
    return _cur_client


def _pack_lparam(x, y) -> int:
    return (int(y) & 0xFFFF) << 16 | (int(x) & 0xFFFF)


def _sample_mesh() -> bool:
    try:
        import zbrush.commands as zbc
        pos = zbc.get_mouse_pos(global_coordinates=False)
        x, y = pos
        mat = float(zbc.pixol_pick(5, float(x), float(y)))
        return mat != 0.0
    except Exception:
        return _last_mesh


def _left_down() -> bool:
    return bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)


def _reset_stroke(hwnd) -> None:
    """Send UP synchronously; after delay sample and re-press DOWN."""
    global _synthetic_up
    x, y = _client_xy(hwnd)
    _cur_client = (x, y)
    lp = _pack_lparam(x, y)
    _synthetic_up = True
    user32.SendMessageW(hwnd, WM_LBUTTONUP, 0, lp)
    user32.SetTimer(hwnd, RESET_TIMER_ID, _reset_delay_ms, None)


def _handle_message(hwnd, msg, wparam, lparam) -> int:
    global _state, _last_mesh, _cur_client, _last_report, _right_down, _synthetic_up
    try:
        if msg == WM_RBUTTONDOWN:
            _right_down = True
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
        if msg == WM_RBUTTONUP:
            _right_down = False
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

        if msg == WM_TIMER and wparam == RESET_TIMER_ID:
            user32.KillTimer(hwnd, RESET_TIMER_ID)
            if _state == 1 and _left_down():
                time.sleep(0.01)  # let ZBrush finish the UP handling
                x, y = _client_xy(hwnd)
                _cur_client = (x, y)
                mesh = _sample_mesh()
                _last_mesh = mesh
                now = time.time()
                if now - _last_report >= 0.5:
                    _last_report = now
                    _dlog("up-window sample mesh=%s xy=(%d,%d)"
                          % (mesh, x, y))
                lp = _pack_lparam(x, y)
                user32.SendMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lp)
                user32.SetTimer(hwnd, TIMER_ID, _bridge_interval_ms, None)
            else:
                _state = 0
            return 0

        if msg == WM_TIMER and wparam == TIMER_ID:
            user32.KillTimer(hwnd, TIMER_ID)
            if _state == 1 and _left_down():
                _reset_stroke(hwnd)
            else:
                _state = 0
            return 0

        if msg == WM_MOUSEMOVE:
            x, y = _client_xy(hwnd)
            _cur_client = (x, y)
            if not _left_down():
                _last_mesh = _sample_mesh()
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

        if msg == WM_LBUTTONDOWN:
            if user32.GetAsyncKeyState(VK_CONTROL) & 0x8000 or \
               user32.GetAsyncKeyState(VK_MENU) & 0x8000:
                _state = 0
                return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
            x, y = _client_xy(hwnd)
            _cur_client = (x, y)
            if _last_mesh:
                _state = 2  # stroke on mesh: untouched
            else:
                _state = 1  # blank press: bridge
                user32.SetTimer(hwnd, TIMER_ID, _bridge_interval_ms, None)
            _dlog("LBDOWN state=%d last_mesh=%s xy=(%d,%d)"
                  % (_state, _last_mesh, x, y))
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

        if msg == WM_LBUTTONUP:
            if _synthetic_up:
                _synthetic_up = False
                return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
            if _state == 1:
                user32.KillTimer(hwnd, TIMER_ID)
                user32.KillTimer(hwnd, RESET_TIMER_ID)
            _state = 0
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
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
            f.write("=== nlr bridge2 ===\n")
    except Exception:
        pass
    _dlog("main start")
    try:
        import zbrush.commands as zbc
        try:
            if not bool(float(zbc.get("Draw:Lock Camera"))):
                zbc.toggle("Draw:Lock Camera")
                _dlog("lock camera enabled")
        except Exception as e:
            _dlog("lock camera err %r" % (e,))
    except Exception:
        pass
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
        _dlog("ready")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
