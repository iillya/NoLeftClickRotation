# -*- coding: utf-8 -*-
"""NLC Pixol Test - 实时显示 pixol_pick 返回值（材质/法线）。
纯读取，不修改 ZBrush 行为。定时器每 200ms 采样一次，
把鼠标所在画布坐标处的 mat/nx/ny/nz 显示在面板滑块上并写日志。"""

import ctypes
import os
import time
from ctypes import wintypes

LOG = os.path.join(
    os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"),
    "nlr_pixol_test.log",
)

WM_TIMER = 0x0113
TIMER_ID = 0x4E4C5058  # 'NLPX'
SUBCLASS_ID = 0x4E4C5059

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t

user32 = ctypes.windll.user32
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
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]

comctl32.SetWindowSubclass.restype = wintypes.BOOL
comctl32.SetWindowSubclass.argtypes = [
    wintypes.HWND, SubclassProcType, ctypes.c_size_t, ctypes.c_size_t,
]
comctl32.DefSubclassProc.restype = LRESULT
comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]

VK_LBUTTON = 0x01

PALETTE = "Zplugin:NLC Pixol Test"
BODY = PALETTE + ":Body"
SWITCH_PATH = BODY + ":运行"
X_PATH = BODY + ":X"
Y_PATH = BODY + ":Y"
MAT_PATH = BODY + ":材质"
NX_PATH = BODY + ":Nx"
NY_PATH = BODY + ":Ny"
NZ_PATH = BODY + ":Nz"

_running = True
_last_log = 0.0


def _dlog(line: str) -> None:
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
    except Exception:
        pass


def _noop(sender, value):
    pass


def _on_switch(sender, value):
    global _running
    _running = bool(value)


def setup_ui() -> None:
    import zbrush.commands as zbc

    if zbc.exists(PALETTE):
        zbc.close(PALETTE)
    if zbc.exists(BODY):
        zbc.close(BODY)
    zbc.add_subpalette(PALETTE, title_mode=0)
    zbc.add_subpalette(BODY, title_mode=2)
    zbc.add_switch(SWITCH_PATH, True, "暂停/继续采样", _on_switch,
                   initially_disabled=False, width=1.0)
    zbc.add_slider(X_PATH, 0.0, 0, 0.0, 4000.0, "鼠标画布 X", _noop, width=1.0)
    zbc.add_slider(Y_PATH, 0.0, 0, 0.0, 2500.0, "鼠标画布 Y", _noop, width=1.0)
    zbc.add_slider(MAT_PATH, 0.0, 0, 0.0, 255.0, "材质 mat", _noop, width=1.0)
    zbc.add_slider(NX_PATH, 0.0, 4, -2.0, 2.0, "法线 Nx", _noop, width=1.0)
    zbc.add_slider(NY_PATH, 0.0, 4, -2.0, 2.0, "法线 Ny", _noop, width=1.0)
    zbc.add_slider(NZ_PATH, 0.0, 4, -2.0, 2.0, "法线 Nz", _noop, width=1.0)


def _sample() -> None:
    global _last_log
    import zbrush.commands as zbc

    try:
        pos = zbc.get_mouse_pos(global_coordinates=False)
    except Exception:
        pos = (None, None)
    try:
        x, y = pos
        fx = float(x or 0.0)
        fy = float(y or 0.0)
        mat = zbc.pixol_pick(5, fx, fy)
        nx = zbc.pixol_pick(6, fx, fy)
        ny = zbc.pixol_pick(7, fx, fy)
        nz = zbc.pixol_pick(8, fx, fy)
        zbc.set(X_PATH, fx)
        zbc.set(Y_PATH, fy)
        zbc.set(MAT_PATH, float(mat))
        zbc.set(NX_PATH, float(nx))
        zbc.set(NY_PATH, float(ny))
        zbc.set(NZ_PATH, float(nz))
        now = time.time()
        if now - _last_log >= 0.5:
            _last_log = now
            down = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
            _dlog("xy=%.0f,%.0f mat=%s nx=%s ny=%s nz=%s down=%d"
                  % (fx, fy, mat, nx, ny, nz, down))
    except Exception as e:
        _dlog("sample err %r pos=%r" % (e, pos))


def _handle_message(hwnd, msg, wparam, lparam) -> int:
    try:
        if msg == WM_TIMER and wparam == TIMER_ID:
            if _running:
                _sample()
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
            f.write("=== nlc pixol test ===\n")
    except Exception:
        pass
    _dlog("main start")
    try:
        setup_ui()
        _dlog("ui ready")
    except Exception as e:
        _dlog("ui err %r" % (e,))
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
    if hwnd:
        comctl32.SetWindowSubclass(hwnd, _subclass_proc, SUBCLASS_ID, 0)
        user32.SetTimer(hwnd, TIMER_ID, 200, None)
        _dlog("ready")
    else:
        _dlog("no zbrush window")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
