# -*- coding: utf-8 -*-
"""Temporary ZBrush 2026.1.1 probe for PixolPick canvas selection.

The probe compares the native material result with the internal canvas-source
bit forced on and off.  The original flag is restored immediately after every
sample.  It does not consume or synthesize mouse messages.
"""

import ctypes
import os
import time
from ctypes import wintypes


WM_TIMER = 0x0113
TIMER_ID = 0x4E4C4250
SUBCLASS_ID = 0x4E4C4251
VK_LBUTTON = 0x01
SAMPLE_INTERVAL_MS = 80

# ZBrush 2026.1.1, ZBrush.exe 2026.1.1.1.
STATE_POINTER_RVA = 0x1C28C650
CANVAS_SOURCE_BIT = 0x00200000
STATE_FLAGS_OFFSET = 0x11584

LOG_PATH = os.path.join(
    os.environ.get("TEMP", os.path.dirname(__file__)),
    "pixol_buffer_probe.log",
)

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t
UINT_PTR = ctypes.c_size_t

user32 = ctypes.WinDLL("user32", use_last_error=True)
comctl32 = ctypes.WinDLL("comctl32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

SubclassProc = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    WPARAM,
    LPARAM,
    ctypes.c_void_p,
    ctypes.c_void_p,
)
EnumWindowsProc = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
)

kernel32.GetModuleHandleW.restype = ctypes.c_void_p
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(wintypes.DWORD),
]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
user32.SetTimer.restype = UINT_PTR
user32.SetTimer.argtypes = [
    wintypes.HWND,
    UINT_PTR,
    wintypes.UINT,
    ctypes.c_void_p,
]
comctl32.SetWindowSubclass.restype = wintypes.BOOL
comctl32.SetWindowSubclass.argtypes = [
    wintypes.HWND,
    SubclassProc,
    UINT_PTR,
    UINT_PTR,
]
comctl32.DefSubclassProc.restype = LRESULT
comctl32.DefSubclassProc.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    WPARAM,
    LPARAM,
]

_last_display = 0.0
_zbrush_hwnd = 0


def _log(message):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as stream:
            stream.write("%s %s\n" % (time.strftime("%H:%M:%S"), message))
    except OSError:
        pass


def _read_material(zbc, x, y):
    return float(zbc.pixol_pick(5, float(x), float(y)))


def _sample():
    global _last_display

    import zbrush.commands as zbc

    x, y = zbc.get_mouse_pos(global_coordinates=False)
    image_base = int(kernel32.GetModuleHandleW(None) or 0)
    state = ctypes.c_void_p.from_address(
        image_base + STATE_POINTER_RVA
    ).value
    if not state:
        raise RuntimeError("ZBrush state pointer is null")

    flags = ctypes.c_uint32.from_address(state + STATE_FLAGS_OFFSET)
    original = flags.value
    try:
        raw = _read_material(zbc, x, y)
        flags.value = original | CANVAS_SOURCE_BIT
        forced_on = _read_material(zbc, x, y)
        flags.value = original & ~CANVAS_SOURCE_BIT
        forced_off = _read_material(zbc, x, y)
    finally:
        flags.value = original

    left_down = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
    now = time.monotonic()
    if left_down or now - _last_display >= 0.5:
        _last_display = now
        line = (
            "xy=%d,%d LB=%d bit=%d raw=%.3f on=%.3f off=%.3f"
            % (
                int(x),
                int(y),
                int(left_down),
                int(bool(original & CANVAS_SOURCE_BIT)),
                raw,
                forced_on,
                forced_off,
            )
        )
        _log(line)
        zbc.set_notebar_text("Pixol buffers: " + line)


def _handle(hwnd, msg, wparam, lparam):
    if msg == WM_TIMER and int(wparam) == TIMER_ID:
        try:
            _sample()
        except Exception as exception:
            _log("sample_error=" + repr(exception))
        return 0
    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


@SubclassProc
def _subclass(hwnd, msg, wparam, lparam, subclass_id, ref_data):
    del subclass_id, ref_data
    try:
        return _handle(hwnd, msg, wparam, lparam)
    except Exception as exception:
        _log("callback_error=" + repr(exception))
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


@EnumWindowsProc
def _find_window(hwnd, lparam):
    del lparam
    global _zbrush_hwnd
    name = ctypes.create_unicode_buffer(128)
    if user32.GetClassNameW(hwnd, name, len(name)) and name.value == "ZBrush":
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == os.getpid():
            _zbrush_hwnd = int(hwnd)
            return False
    return True


def main():
    with open(LOG_PATH, "w", encoding="utf-8") as stream:
        stream.write("=== Pixol canvas buffer probe ===\n")

    user32.EnumWindows(_find_window, 0)
    if not _zbrush_hwnd:
        _log("ERROR ZBrush window not found")
        return
    if not comctl32.SetWindowSubclass(
        _zbrush_hwnd, _subclass, SUBCLASS_ID, 0
    ):
        _log("ERROR SetWindowSubclass failed")
        return
    if not user32.SetTimer(
        _zbrush_hwnd, TIMER_ID, SAMPLE_INTERVAL_MS, None
    ):
        _log("ERROR SetTimer failed")
        return
    _log("ready image_base=%#x" % int(kernel32.GetModuleHandleW(None) or 0))


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        _log("FATAL " + repr(exception))
