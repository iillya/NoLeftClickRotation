# -*- coding: utf-8 -*-
"""No Left Click Rotation V1 for ZBrush on Windows."""

import ctypes
import os
import struct
import time
from ctypes import wintypes
from zbrush import commands as zbc

VERSION = "1.0.0"

WM_TIMER = 0x0113
WM_CANCELMODE = 0x001F
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_CAPTURECHANGED = 0x0215
WM_NCDESTROY = 0x0082
SM_CXDRAG = 68
SM_CYDRAG = 69

MK_LBUTTON = 0x0001
MK_SHIFT = 0x0004
MK_CONTROL = 0x0008
MK_MBUTTON = 0x0010
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_SHIFT = 0x10
VK_CONTROL = 0x11

CANVAS_WINDOW_ID = 1004
WINDOW_ID_PATH = "Preferences:Utilities:View Window Id"
EDIT_PATH = "Transform:Edit"
LOCK_CAMERA_PATH = "Draw:Lock Camera"

PALETTE = "Zplugin:No Left Click Rotation"
BODY = PALETTE + ":V1"
ENABLE_PATH = BODY + ":Enable"
DELAY_PATH = BODY + ":Sculpt Start Delay"

IDLE = 0
UI_PASS = 1
MODEL_PASS = 2
CLASSIFY = 3
LIGHTBOX_PASS = 4
WAIT_MODEL = 5
START_PENDING = 6
SCULPTING = 7
LIGHTBOX_CLICK_DONE = 8

POLL_TIMER = 0x4E4C5631
CLASSIFY_TIMER = 0x4E4C5632
START_TIMER = 0x4E4C5633
CAMERA_TIMER = 0x4E4C5634
SUBCLASS_ID = 0x4E4C5631
POLL_MS = 5
CLASSIFY_MS = 20
RIGHT_RELOCK_MS = 2
DELAY_MIN_MS = 0
DELAY_MAX_MS = 10

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t
SubclassProc = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM,
    ctypes.c_void_p, ctypes.c_void_p,
)
EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
SetCursorProc = ctypes.WINFUNCTYPE(wintypes.HANDLE, wintypes.HANDLE)

user32 = ctypes.WinDLL("user32", use_last_error=True)
comctl32 = ctypes.WinDLL("comctl32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetCursor.restype = wintypes.HANDLE
user32.LoadCursorW.restype = wintypes.HANDLE
user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.EnumWindows.argtypes = [EnumProc, wintypes.LPARAM]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND,
                                            ctypes.POINTER(wintypes.DWORD)]
user32.SetTimer.restype = ctypes.c_size_t
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_size_t,
                            wintypes.UINT, ctypes.c_void_p]
user32.SendMessageW.restype = LRESULT
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
user32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_size_t]
comctl32.SetWindowSubclass.restype = wintypes.BOOL
comctl32.SetWindowSubclass.argtypes = [wintypes.HWND, SubclassProc,
                                       ctypes.c_size_t, ctypes.c_size_t]
comctl32.DefSubclassProc.restype = LRESULT
comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT,
                                     WPARAM, LPARAM]
comctl32.RemoveWindowSubclass.argtypes = [wintypes.HWND, SubclassProc,
                                          ctypes.c_size_t]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                    wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]

_hwnd = 0
_enabled = True
_state = IDLE
_injecting = False
_arrow_seen = False
_system_arrow = 0
_setcursor_slot = 0
_setcursor_address = 0
_setcursor_original = None
_setcursor_callback = None
_right_down = False
_right_relock_at = 0.0
_probe_point = (0, 0)
_physical_left_held = False
_hover_mat = None
_hover_mat_at = 0.0
_installed = False
_lock_state = None
_lock_assert_at = 0.0
_edit_cache = None
_edit_cache_at = 0.0

LOG = os.path.join(os.environ.get("TEMP", os.path.dirname(__file__)),
                   "nlr_v1.log")


def _log(line):
    try:
        with open(LOG, "a", encoding="utf-8") as stream:
            stream.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
    except Exception:
        pass


def _key(vkey):
    return bool(user32.GetAsyncKeyState(vkey) & 0x8000)


def _get_switch(path, default=False):
    try:
        return bool(zbc.exists(path) and float(zbc.get(path)))
    except Exception:
        return default


def _set_switch(path, value):
    try:
        if _get_switch(path) == bool(value):
            return
        try:
            zbc.set(path, float(bool(value)))
        except Exception:
            zbc.toggle(path)
    except Exception:
        pass


def _edit_mode():
    return _get_switch(EDIT_PATH)


def _active():
    return _enabled and _edit_mode()


def _window_id():
    try:
        return int(round(float(zbc.get(WINDOW_ID_PATH))))
    except Exception:
        return -1


def _window_id_path_works():
    try:
        float(zbc.get(WINDOW_ID_PATH))
        return True
    except Exception:
        return False


def _mat():
    try:
        x, y = zbc.get_mouse_pos(global_coordinates=False)
        return float(zbc.pixol_pick(5, float(x), float(y)))
    except Exception:
        return 0.0


def _delay_ms():
    try:
        return max(DELAY_MIN_MS, min(
            DELAY_MAX_MS, int(round(float(zbc.get(DELAY_PATH))))))
    except Exception:
        return DELAY_MIN_MS


def _lparam(hwnd):
    x, y = _client_point(hwnd)
    return ((y & 0xffff) << 16) | (x & 0xffff)


def _client_point(hwnd):
    point = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(point)):
        return (0, 0)
    if not user32.ScreenToClient(hwnd, ctypes.byref(point)):
        return (0, 0)
    return (int(point.x), int(point.y))


def _mods():
    value = 0
    if _key(VK_SHIFT):
        value |= MK_SHIFT
    if _key(VK_CONTROL):
        value |= MK_CONTROL
    return value


def _send(hwnd, message, wparam):
    global _injecting
    _injecting = True
    try:
        return user32.SendMessageW(hwnd, message, wparam, _lparam(hwnd))
    finally:
        _injecting = False


def _write_pointer(slot, value):
    old = wintypes.DWORD()
    if not kernel32.VirtualProtect(ctypes.c_void_p(slot), 8, 0x04,
                                   ctypes.byref(old)):
        return False
    ctypes.c_uint64.from_address(slot).value = int(value)
    unused = wintypes.DWORD()
    kernel32.VirtualProtect(ctypes.c_void_p(slot), 8, old.value,
                            ctypes.byref(unused))
    return True


def _find_setcursor_slot():
    module = int(kernel32.GetModuleHandleW(None) or 0)
    header = ctypes.string_at(module, 0x1000)
    pe = struct.unpack_from("<I", header, 0x3C)[0]
    optional = ctypes.string_at(module + pe + 24, 0x200)
    import_rva = struct.unpack_from("<I", optional, 120)[0]
    descriptor = module + import_rva
    while True:
        original, _, _, name_rva, first = struct.unpack(
            "<IIIII", ctypes.string_at(descriptor, 20))
        if not any((original, name_rva, first)):
            break
        dll = ctypes.string_at(module + name_rva).decode("ascii", "replace")
        if dll.casefold() == "user32.dll":
            lookup = module + (original or first)
            index = 0
            while True:
                entry = ctypes.c_uint64.from_address(lookup + index * 8).value
                if not entry:
                    break
                if not entry >> 63:
                    name = ctypes.string_at(module + entry + 2).decode(
                        "ascii", "replace")
                    if name == "SetCursor":
                        return module + first + index * 8
                index += 1
        descriptor += 20
    return 0


def _install_cursor_watch():
    global _setcursor_slot, _setcursor_address, _setcursor_original
    global _setcursor_callback, _system_arrow, _arrow_seen
    _setcursor_slot = _find_setcursor_slot()
    if not _setcursor_slot:
        return False
    _setcursor_address = ctypes.c_uint64.from_address(_setcursor_slot).value
    _setcursor_original = SetCursorProc(_setcursor_address)
    _system_arrow = int(user32.LoadCursorW(None, ctypes.c_void_p(32512)) or 0)

    @SetCursorProc
    def callback(cursor):
        global _arrow_seen
        if _state == CLASSIFY and int(cursor or 0) == _system_arrow:
            _arrow_seen = True
        return _setcursor_original(cursor)

    _setcursor_callback = callback
    return _write_pointer(
        _setcursor_slot, ctypes.cast(callback, ctypes.c_void_p).value)


def _restore_cursor_watch():
    if _setcursor_slot and _setcursor_address:
        _write_pointer(_setcursor_slot, _setcursor_address)


def _camera_lock(value):
    _set_switch(LOCK_CAMERA_PATH, value)


def _edit_mode_cached():
    global _edit_cache, _edit_cache_at
    now = time.perf_counter()
    if now >= _edit_cache_at:
        _edit_cache = _get_switch(EDIT_PATH)
        _edit_cache_at = now + 0.1
    return _edit_cache


def _sync_camera():
    global _lock_state, _lock_assert_at
    if not _enabled:
        want = False
    elif not _edit_mode_cached():
        want = False
    elif _right_down or _key(VK_RBUTTON):
        want = False
    elif time.perf_counter() < _right_relock_at:
        want = False
    else:
        want = True
    now = time.perf_counter()
    if want != _lock_state or now >= _lock_assert_at:
        _camera_lock(want)
        _lock_state = want
        _lock_assert_at = now + 0.2


def _sample_hover():
    global _hover_mat, _hover_mat_at
    if not (_enabled and _edit_mode_cached()) or _state != IDLE or _key(VK_LBUTTON):
        return
    now = time.perf_counter()
    if now - _hover_mat_at < 0.01:
        return
    _hover_mat = _mat()
    _hover_mat_at = now


def _clear_timers(hwnd):
    user32.KillTimer(hwnd, CLASSIFY_TIMER)
    user32.KillTimer(hwnd, START_TIMER)
    user32.KillTimer(hwnd, CAMERA_TIMER)


def _reset(hwnd):
    global _state
    _clear_timers(hwnd)
    if _state == WAIT_MODEL:
        _send(hwnd, WM_MBUTTONUP, _mods())
    _state = IDLE


def _begin_wait(hwnd):
    global _state
    if not _key(VK_LBUTTON):
        _state = IDLE
        return
    _state = WAIT_MODEL
    _send(hwnd, WM_MBUTTONDOWN, _mods() | MK_MBUTTON)


def _finish_classify(hwnd):
    global _state
    user32.KillTimer(hwnd, CLASSIFY_TIMER)
    if _state != CLASSIFY:
        return
    arrow = _arrow_seen or int(user32.GetCursor() or 0) == _system_arrow
    if arrow:
        held = _physical_left_held and _key(VK_LBUTTON)
        if held:
            # The probe DOWN+UP already produced exactly one LightBox click.
            # Wait for actual drag distance before replaying DOWN.
            _state = LIGHTBOX_CLICK_DONE
        else:
            _state = IDLE
        return
    _begin_wait(hwnd)


def _poll_model(hwnd):
    global _state
    if _state != WAIT_MODEL:
        return
    if not _active() or not _key(VK_LBUTTON):
        _reset(hwnd)
        return
    value = _mat()
    if value == 0.0:
        return
    _send(hwnd, WM_MBUTTONUP, _mods())
    _state = START_PENDING
    delay = _delay_ms()
    user32.SetTimer(hwnd, START_TIMER, max(1, delay), None)


def _start_sculpt(hwnd):
    global _state
    user32.KillTimer(hwnd, START_TIMER)
    if _state != START_PENDING:
        return
    if not _active() or not _key(VK_LBUTTON):
        _state = IDLE
        return
    _send(hwnd, WM_LBUTTONDOWN, _mods() | MK_LBUTTON)
    _send(hwnd, WM_MOUSEMOVE, _mods() | MK_LBUTTON)
    _state = SCULPTING


def _begin_left(hwnd, msg, wparam, lparam):
    global _state, _arrow_seen, _probe_point, _physical_left_held
    _physical_left_held = True
    if not _active():
        _state = IDLE
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
    wid = _window_id()
    if wid != CANVAS_WINDOW_ID:
        _state = UI_PASS
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
    if (_hover_mat if _hover_mat is not None else _mat()) != 0.0:
        _state = MODEL_PASS
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
    # Ctrl keeps its native canvas gesture. Alt+left follows the same
    # UI/model/LightBox/blank classification as an ordinary left press.
    if _key(VK_CONTROL):
        _state = UI_PASS
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    # Ambiguous LightBox/blank-canvas point: pass the real down, immediately
    # finish it with synthetic UP, then classify from the resulting cursor.
    result = comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
    _probe_point = _client_point(hwnd)
    _arrow_seen = False
    _state = CLASSIFY
    _send(hwnd, WM_LBUTTONUP, _mods())
    user32.SetTimer(hwnd, CLASSIFY_TIMER, CLASSIFY_MS, None)
    return result


def _handle(hwnd, msg, wparam, lparam):
    global _state, _right_down, _right_relock_at, _physical_left_held
    global _hwnd, _lock_state, _hover_mat
    if _injecting:
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if msg == WM_TIMER:
        timer = int(wparam)
        if timer == POLL_TIMER:
            _sync_camera()
            _poll_model(hwnd)
            _sample_hover()
            return 0
        if timer == CLASSIFY_TIMER:
            _finish_classify(hwnd)
            return 0
        if timer == START_TIMER:
            _start_sculpt(hwnd)
            return 0
        if timer == CAMERA_TIMER:
            user32.KillTimer(hwnd, CAMERA_TIMER)
            _sync_camera()
            return 0

    if msg == WM_RBUTTONDOWN:
        _right_down = True
        _right_relock_at = 0.0
        user32.KillTimer(hwnd, CAMERA_TIMER)
        if _enabled and _edit_mode():
            _camera_lock(False)
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if msg == WM_RBUTTONUP:
        _right_down = False
        _right_relock_at = time.perf_counter() + RIGHT_RELOCK_MS / 1000.0
        user32.SetTimer(hwnd, CAMERA_TIMER, RIGHT_RELOCK_MS, None)
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if msg == WM_LBUTTONDOWN:
        return _begin_left(hwnd, msg, wparam, lparam)

    # Movement is always passed through. Camera lock prevents blank rotation.
    if msg == WM_MOUSEMOVE:
        if _state == LIGHTBOX_CLICK_DONE and _key(VK_LBUTTON):
            x, y = _client_point(hwnd)
            dx = abs(x - _probe_point[0])
            dy = abs(y - _probe_point[1])
            threshold_x = max(1, int(user32.GetSystemMetrics(SM_CXDRAG)))
            threshold_y = max(1, int(user32.GetSystemMetrics(SM_CYDRAG)))
            if dx >= threshold_x or dy >= threshold_y:
                _send(hwnd, WM_LBUTTONDOWN, _mods() | MK_LBUTTON)
                _send(hwnd, WM_MOUSEMOVE, _mods() | MK_LBUTTON)
                _state = LIGHTBOX_PASS
                return 0
            return 0
        _poll_model(hwnd)
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if msg == WM_LBUTTONUP:
        _physical_left_held = False
        previous = _state
        if previous == CLASSIFY:
            # The probe already delivered UP. Classification will replay a
            # complete click only if this was LightBox.
            return 0
        if previous == LIGHTBOX_CLICK_DONE:
            # Synthetic probe UP already completed this single click.
            _state = IDLE
            return 0
        if previous in (WAIT_MODEL, START_PENDING):
            _reset(hwnd)
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
        if previous in (UI_PASS, MODEL_PASS, LIGHTBOX_PASS, SCULPTING):
            _state = IDLE
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if msg in (WM_CANCELMODE, WM_CAPTURECHANGED):
        if not _key(VK_LBUTTON):
            _reset(hwnd)
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if msg == WM_NCDESTROY:
        _reset(hwnd)
        user32.KillTimer(hwnd, POLL_TIMER)
        _restore_cursor_watch()
        comctl32.RemoveWindowSubclass(hwnd, _subclass, SUBCLASS_ID)
        _camera_lock(False)
        _hwnd = 0
        _lock_state = None
        _hover_mat = None

    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


@SubclassProc
def _subclass(hwnd, msg, wparam, lparam, sid, reference):
    del sid, reference
    try:
        return _handle(hwnd, msg, wparam, lparam)
    except Exception:
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


@EnumProc
def _find(hwnd, unused):
    del unused
    global _hwnd
    name = ctypes.create_unicode_buffer(64)
    if user32.GetClassNameW(hwnd, name, len(name)) and name.value == "ZBrush":
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == os.getpid():
            _hwnd = int(hwnd)
            return False
    return True


def _toggle(sender, value):
    del sender
    global _enabled, _right_down, _right_relock_at, _hover_mat, _lock_state
    _enabled = bool(value)
    if _hwnd:
        _reset(_hwnd)
    if not _enabled:
        _right_down = False
        _right_relock_at = 0.0
        _hover_mat = None
        _lock_state = None
        _camera_lock(False)
    else:
        _sync_camera()


def _delay_changed(sender, value):
    del sender, value


def _setup_ui():
    if zbc.exists(PALETTE):
        zbc.close(PALETTE)
    if zbc.exists(BODY):
        zbc.close(BODY)
    zbc.add_subpalette(PALETTE, title_mode=0)
    zbc.add_subpalette(BODY, title_mode=2)
    zbc.add_switch(
        ENABLE_PATH, True,
        "Enable No Left Click Rotation V1. Disabling unlocks the camera.",
        _toggle, initially_disabled=False, width=0.0,
    )
    zbc.add_slider(
        DELAY_PATH, float(DELAY_MIN_MS), 1,
        float(DELAY_MIN_MS), float(DELAY_MAX_MS),
        "Delay in milliseconds between ending the middle wait and starting sculpting.",
        _delay_changed, initially_disabled=False, width=0.0,
    )


def main():
    global _installed
    if _installed:
        return
    try:
        _setup_ui()
        user32.EnumWindows(_find, 0)
        if not _hwnd:
            _log("ERROR: ZBrush window not found")
            _camera_lock(False)
            return
        wid_ok = _window_id_path_works()
        if not wid_ok:
            _log("WARNING: View Window Id path unavailable; camera lock only")
            zbc.set_notebar_text("NLC V1: View Window Id 不可用，仅相机锁定生效")
        if not _install_cursor_watch():
            _log("ERROR: SetCursor hook install failed")
            _camera_lock(False)
            return
        if not comctl32.SetWindowSubclass(_hwnd, _subclass, SUBCLASS_ID, 0):
            _restore_cursor_watch()
            _log("ERROR: window subclass install failed")
            _camera_lock(False)
            return
        _installed = True
        user32.SetTimer(_hwnd, POLL_TIMER, POLL_MS, None)
        _sync_camera()
        _log("V1 installed window_id_ok=%d" % int(wid_ok))
    except Exception as exc:
        _log("FATAL %r" % (exc,))
        _camera_lock(False)


main()
